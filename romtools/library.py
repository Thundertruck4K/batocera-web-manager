"""Inventario y auditoría de la biblioteca de ROMs.

El manager ya sabe contar juegos, leer el `gamelist.xml` y tocar ficheros, pero
no tenía una vista de la biblioteca **como conjunto**: qué hay, qué sobra, qué
está duplicado y cuánto ocupa. Este módulo la construye.

Lo importante es el tamaño: una biblioteca puede tener **1,8 TB** (la del
autor: 257 sistemas, 2.770 juegos, 1.805 GB). Hashearla entera son horas, así
que los duplicados se buscan con una **huella rápida** (tamaño + los primeros
y los últimos 64 KB) y solo a los candidatos se les confirma con el hash
completo, con un presupuesto de bytes para que la confirmación no se endless.
Con eso la radiografía entera tarda menos de un minuto.

Nada se borra: lo que sobra se mueve a una **cuarentena**
(`/userdata/roms/.quarantine/`) y cada tanda queda en un journal para poder
deshacerla, igual que el renombrado.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .progress import Progress

#: Carpetas que guardan media, no juegos.
MEDIA_DIRS = {"images", "videos", "manuals", "downloads", "media"}
#: Cuantos bytes se leen por cabeza y por cola en la huella rápida.
MUESTRA = 64 * 1024
#: Journal de la biblioteca (a lado del del renombrado).
JOURNAL_NAME = "batocera_manager_library.json"
#: Carpeta de cuarentena, dentro de la propia biblioteca.
QUARANTINE = ".quarantine"
#: Etiquetas que Batocera pone a los ficheros de media.
MEDIA_TAGS = ("image", "marquee", "thumb", "thumbnail", "video", "manual",
              "screenshot", "wheel", "mixrb", "fanart", "box-2d", "video-2d",
              "titleshot", "physic", "region", "logo", "clearlogo")
#: Un fichero de 0 bytes no cuenta para el duplicado: todos serían iguales.
TAMANO_MINIMO = 1
#: Presupuesto de bytes para confirmar los duplicados con el hash completo.
#: Una ISO de 4 GB tarda: confirmarlos todos sería horas.
PRESUPUESTO_CONFIRMAR = 8 * 1024 * 1024 * 1024
#: Longitud mínima de un prefijo para darlo por bueno (evita falsos positivos).
PREFIJO_MINIMO = 4
#: Cuántos elementos devuelve cada lista de la auditoría como máximo.
TOPE_LISTAS = 2000


# ── Huellas ─────────────────────────────────────────────────────────────

def huella_rapida(path: str) -> str | None:
    """Huella de un fichero sin leerlo entero.

    Es el tamaño más los primeros y los últimos 64 KB: dos ficheros con la
    misma huella son casi seguro el mismo, y comparar 1,8 TB no se puede leer
    entero. La confirmación con el hash completo la hace después, y solo de
    los candidatos.
    """
    try:
        size = os.path.getsize(path)
        h = hashlib.md5()
        h.update(str(size).encode("ascii"))
        with open(path, "rb") as fh:
            h.update(fh.read(MUESTRA))
            if size > MUESTRA:
                fh.seek(-MUESTRA, os.SEEK_END)
                h.update(fh.read(MUESTRA))
        return h.hexdigest()
    except OSError:
        return None


def hash_completo(path: str, on_bytes=None) -> str | None:
    """El md5 del fichero entero (se usa solo para confirmar candidatos).

    ``on_bytes`` recibe cuantos bytes se han leído: así la barra de progreso
    avanza dentro del fichero y no se queda parada en el 90 %.
    """
    h = hashlib.md5()
    try:
        with open(path, "rb") as fh:
            while True:
                bloque = fh.read(4 * 1024 * 1024)
                if not bloque:
                    break
                h.update(bloque)
                if on_bytes is not None:
                    on_bytes(len(bloque))
    except OSError:
        return None
    return h.hexdigest()


def _norm(texto: str) -> str:
    """Normaliza un nombre para poder compararlo con otro."""
    return re.sub(r"\s+", " ", (texto or "").strip().lower())


def _ficheros_de_carpeta(carpeta: Path):
    """Los ficheros de una carpeta con su ruta relativa, ordenados."""
    salida = []
    try:
        for item in _recorrer(carpeta):
            try:
                tam = item.stat().st_size
            except OSError:
                continue
            try:
                rel = str(item.relative_to(carpeta)).replace(os.sep, "/")
            except ValueError:
                rel = item.name
            salida.append((rel, tam))
    except OSError:
        pass
    salida.sort()
    return salida


def huella_rapida_carpeta(path) -> str | None:
    """La huella de una carpeta **sin leer el contenido**.

    Solo con los nombres y los tamanos: dos juegos en carpeta con los mismos
    ficheros y los mismos tamanos son candidatos, y el contenido se comprueba
    despues con el hash completo.
    """
    ficheros = _ficheros_de_carpeta(Path(path))
    if not ficheros:
        return None
    h = hashlib.md5()
    for rel, tam in ficheros:
        h.update(rel.encode("utf-8", "replace"))
        h.update(b":")
        h.update(str(tam).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def hash_completo_carpeta(path, on_bytes=None) -> str | None:
    """El md5 de una carpeta entera (los nombres y el contenido)."""
    carpeta = Path(path)
    h = hashlib.md5()
    try:
        for rel, _tam in _ficheros_de_carpeta(carpeta):
            h.update(rel.encode("utf-8", "replace"))
            h.update(b":")
            with open(carpeta / rel, "rb") as fh:
                while True:
                    bloque = fh.read(4 * 1024 * 1024)
                    if not bloque:
                        break
                    h.update(bloque)
                    if on_bytes is not None:
                        on_bytes(len(bloque))
            h.update(b"\n")
    except OSError:
        return None
    return h.hexdigest()


# ── Recorrido de la biblioteca ──────────────────────────────────────────

class Archivo:
    """Un juego de la biblioteca (fichero suelto o carpeta-juego)."""

    __slots__ = ("sistema", "ruta", "nombre", "tamano", "mtime", "carpeta",
                 "hash_rel", "hash_size", "hash_carpeta")

    def __init__(self, sistema, ruta, nombre, tamano, mtime, carpeta=False,
                 hash_rel=None, hash_size=None, hash_carpeta=False):
        self.sistema = sistema
        self.ruta = ruta          # ruta relativa a la carpeta del sistema
        self.nombre = nombre
        self.tamano = tamano      # lo que ocupa el juego (con la carpeta)
        self.mtime = mtime
        self.carpeta = carpeta    # True si el juego es una carpeta
        # Que se hashea: el fichero (`hash_rel`) o la carpeta entera. Una
        # carpeta-juego se compara **entera**: su fichero mas grande es el
        # motor (ScummVM, DOSBox), que es el mismo para todos los juegos.
        self.hash_rel = hash_rel or ruta
        self.hash_size = tamano if hash_size is None else hash_size
        self.hash_carpeta = hash_carpeta

    @property
    def clave(self) -> str:
        """La ruta completa, como se usa en la API."""
        return f"{self.sistema}/{self.ruta}"

    def as_dict(self) -> dict:
        return {"sistema": self.sistema, "ruta": self.ruta, "nombre": self.nombre,
                "bytes": self.tamano, "carpeta": self.carpeta}


def _recorrer(carpeta: Path):
    """Los ficheros de una carpeta y sus subcarpetas (sin seguir enlaces)."""
    for raiz, _dirs, files in os.walk(str(carpeta), followlinks=False):
        for name in files:
            yield Path(raiz) / name


def _tamano_de_carpeta(carpeta: Path) -> int:
    total = 0
    try:
        for item in _recorrer(carpeta):
            try:
                total += item.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return total


def es_juego(nombre: str, exts) -> bool:
    """Si el nombre es el de un juego del sistema."""
    if not nombre or nombre.startswith("."):
        return False
    if nombre == "gamelist.xml":
        return False
    ext = Path(nombre).suffix.lower()
    if not ext:
        return False
    return ext in exts


def recolectar(base: str, sistemas, exts_por_sistema) -> dict:
    """Recorre la biblioteca y separa juegos, sobras y carpetas de media.

    ``exts_por_sistema`` son las extensiones que son juego en cada sistema
    (``system_game_extensions`` del backend): con esa regla se sabe que un
    ``.txt`` es información y no un juego, y que una subcarpeta es un juego
    (los ports guardan el juego dentro).
    """
    juegos: list = []
    sobras: list = []
    vacios: list = []
    base_path = Path(base)
    for sistema in sistemas:
        folder = base_path / sistema
        if not folder.is_dir():
            continue
        exts = exts_por_sistema.get(sistema) or set()
        try:
            items = sorted(folder.iterdir())
        except OSError:
            continue
        for item in items:
            nombre = item.name
            if nombre.startswith(".") or nombre == "gamelist.xml":
                continue
            if item.is_dir():
                if nombre.lower() in MEDIA_DIRS:
                    continue
                # Una carpeta es un juego (ports, motores, carpeta-juego).
                # Se compara **entera**: su fichero mas grande es el motor
                # (ScummVM, DOSBox), que es el mismo para todos los juegos.
                tam = _tamano_de_carpeta(item)
                juegos.append(Archivo(sistema, nombre, nombre, tam,
                                      item.stat().st_mtime, carpeta=True,
                                      hash_rel=nombre, hash_size=tam,
                                      hash_carpeta=True))
                continue
            try:
                tam = item.stat().st_size
                mtime = item.stat().st_mtime
            except OSError:
                continue
            if es_juego(nombre, exts):
                juegos.append(Archivo(sistema, nombre, nombre, tam, mtime))
                if tam == 0:
                    vacios.append(Archivo(sistema, nombre, nombre, tam, mtime))
            else:
                sobras.append(Archivo(sistema, nombre, nombre, tam, mtime))
    return {"juegos": juegos, "sobras": sobras, "vacios": vacios}


def leer_gamelist(path: str) -> dict:
    """Las fichas de un ``gamelist.xml`` (``{ruta: game}``)."""
    salida: dict = {}
    try:
        tree = ET.parse(path)
    except (OSError, ValueError):
        return salida
    for game in tree.findall(".//game"):
        ruta = (game.findtext("path", "") or "").lstrip("./")
        if ruta:
            salida[ruta] = game
    return salida


# ── Duplicados ──────────────────────────────────────────────────────────

def _grupo_por_tamano(juegos) -> dict:
    por_tam: dict = {}
    for juego in juegos:
        if juego.hash_size < TAMANO_MINIMO:
            continue
        por_tam.setdefault(juego.hash_size, []).append(juego)
    return por_tam


def _grupo_duplicado(md5, miembros, confirmado) -> dict:
    """El bloque que se enseña en la interfaz para un grupo de duplicados."""
    bytes_uno = miembros[0].hash_size
    return {
        "md5": md5,
        "confirmado": confirmado,
        "bytes": bytes_uno,
        "mb": round(bytes_uno / 1048576, 2),
        "copias": len(miembros),
        # Lo que se puede liberar dejando una sola copia.
        "ahorro": bytes_uno * (len(miembros) - 1),
        "ahorro_mb": round(bytes_uno * (len(miembros) - 1) / 1048576, 2),
        "ficheros": [m.as_dict() for m in miembros],
        "nombres": sorted({m.nombre for m in miembros}),
        "sistemas": sorted({m.sistema for m in miembros}),
    }


def duplicados(base: str, juegos, confirmar=True, max_confirmar=60,
               max_bytes=PRESUPUESTO_CONFIRMAR, progreso=None) -> list:
    """Los juegos que están repetidos en la biblioteca.

    Primero se agrupan por tamaño (barato), luego se calcula la **huella
    rápida** de cada candidato y solo los que coinciden se confirman con el
    hash completo. Sin ese segundo paso, dos ficheros distintos del mismo
    tamaño aparecerían como duplicados.

    La confirmación tiene un **presupuesto de bytes**: hashear una ISO de
    4 GB cuesta, así que solo se confirman los primeros grupos que caben en
    el presupuesto. Los que se quedan fuera se devuelven igual, pero marcados
    como ``confirmado: false`` (son candidatos, no una certeza).

    Las **carpetas-juego** (Wii, ScummVM, DOSBox) se comparan enteras: su
    fichero más grande es el motor, que es el mismo para todos los juegos, así
    que hashearlo daría duplicados falsos.
    """
    prog = Progress(len(juegos), "buscando duplicados", notificar=progreso)
    por_tam = _grupo_por_tamano(juegos)
    candidatos = [v for v in por_tam.values() if len(v) > 1]

    total_candidatos = sum(len(grupo) for grupo in candidatos)
    prog.reiniciar(total_candidatos, "comparando los candidatos")
    por_huella: dict = {}
    hechos = 0
    for grupo in candidatos:
        for juego in grupo:
            prog.empezar(juego.clave, juego.hash_size, hechos=hechos)
            ruta = os.path.join(base, juego.sistema, juego.hash_rel)
            if juego.hash_carpeta:
                huella = huella_rapida_carpeta(ruta)
            else:
                huella = huella_rapida(ruta)
            if huella:
                por_huella.setdefault((juego.hash_size, huella), []).append(juego)
            hechos += 1

    grupos = [g for g in por_huella.values() if len(g) > 1]

    # Se reparten los grupos: los que caben en el presupuesto se confirman,
    # los demás se quedan como candidatos.
    a_confirmar: list = []
    sin_confirmar: list = []
    gastado = 0
    for grupo in grupos:
        tam = grupo[0].hash_size
        if confirmar and len(a_confirmar) < max_confirmar and gastado + tam <= max_bytes:
            gastado += tam
            a_confirmar.append(grupo)
        else:
            sin_confirmar.append(grupo)

    prog.reiniciar(sum(len(g) for g in a_confirmar), "confirmando los duplicados")
    salida: list = []
    hechos = 0
    for grupo in a_confirmar:
        digests: dict = {}
        for juego in grupo:
            prog.empezar(juego.clave, juego.hash_size, hechos=hechos)
            ruta = os.path.join(base, juego.sistema, juego.hash_rel)
            if juego.hash_carpeta:
                md5 = hash_completo_carpeta(ruta, on_bytes=prog.leidos)
            else:
                md5 = hash_completo(ruta, on_bytes=prog.leidos)
            if md5:
                digests.setdefault(md5, []).append(juego)
            hechos += 1
        for md5, miembros in digests.items():
            if len(miembros) < 2:
                continue
            salida.append(_grupo_duplicado(md5, miembros, True))

    for grupo in sin_confirmar:
        salida.append(_grupo_duplicado(None, grupo, False))

    salida.sort(key=lambda x: -x["ahorro"])
    return salida


def repetidos_entre_sistemas(juegos, max_grupos=200) -> list:
    """El mismo juego repetido en varios sistemas.

    Se agrupa por nombre normalizado (sin extensión): es el caso típico de
    los arcades, donde `naomi` y `atomiswave` guardan las mismas ROMs (mismo
    hardware) en carpetas distintas.
    """
    por_nombre: dict = {}
    for juego in juegos:
        if juego.carpeta:
            continue
        nombre = _norm(Path(juego.nombre).stem)
        if not nombre:
            continue
        por_nombre.setdefault(nombre, []).append(juego)
    salida = []
    for nombre, grupo in por_nombre.items():
        sistemas = sorted({j.sistema for j in grupo})
        if len(sistemas) < 2:
            continue
        salida.append({
            "nombre": nombre,
            "sistemas": sistemas,
            "bytes": sum(j.tamano for j in grupo),
            "ahorro_mb": round(sum(j.tamano for j in grupo) / 1048576, 2),
            "ficheros": [j.as_dict() for j in grupo],
        })
    salida.sort(key=lambda x: -x["bytes"])
    return salida[:max_grupos]


# ── Auditoría ───────────────────────────────────────────────────────────

def _coincide_media(tallo: str, tallos_set: set, tallos_ordenados: list) -> bool:
    """Si el nombre de una media corresponde a algún juego del sistema.

    Se comparan tres cosas, porque los nombres no siempre cuadran al milímetro:

    - el nombre de la media es exactamente el del juego;
    - el nombre de la media está cortado (``Juego (U`` por un límite del
      explorador de archivos);
    - el juego se renombró a algo más largo y la media se quedó con el nombre
      viejo.
    """
    if not tallo:
        return False
    if tallo in tallos_set:
        return True
    # ¿El nombre de la media es el principio de algún juego?
    i = bisect.bisect_left(tallos_ordenados, tallo)
    if i < len(tallos_ordenados) and tallos_ordenados[i].startswith(tallo):
        return True
    # ¿El nombre de la media empieza por el nombre de algún juego?
    for largo in range(PREFIJO_MINIMO, len(tallo) + 1):
        prefijo = tallo[:largo]
        i = bisect.bisect_left(tallos_ordenados, prefijo)
        if i < len(tallos_ordenados) and tallos_ordenados[i] == prefijo:
            return True
    return False


def _media_huerfana(base: str, sistema: str, nombres_juego, entradas) -> list:
    """Media (imágenes, vídeos) cuyo juego ya no está.

    La media se llama ``<tallo>-<etiqueta>.png``; se busca ese ``tallo`` entre
    los juegos del sistema y entre las fichas del gamelist. Si no aparece, la
    imagen no le corresponde a nadie (el juego se borró o se renombró sin
    renombrar la media).
    """
    carpeta = Path(base) / sistema / "images"
    if not carpeta.is_dir():
        return []
    tallos = set()
    for nombre in nombres_juego:
        norm = _norm(nombre)
        if norm:
            tallos.add(norm)
    for ruta in entradas:
        norm = _norm(Path(ruta).stem)
        if norm:
            tallos.add(norm)
    tallos_ordenados = sorted(tallos)
    huerfanos = []
    try:
        for item in sorted(carpeta.iterdir()):
            if not item.is_file():
                continue
            nombre = item.stem
            etiqueta = ""
            for tag in MEDIA_TAGS:
                sufijo = f"-{tag}"
                if nombre.lower().endswith(sufijo):
                    etiqueta = nombre[: -len(sufijo)]
                    break
            if not etiqueta:
                etiqueta = nombre
            if _coincide_media(_norm(etiqueta), tallos, tallos_ordenados):
                continue
            try:
                tam = item.stat().st_size
            except OSError:
                tam = 0
            huerfanos.append({"sistema": sistema, "fichero": f"images/{item.name}",
                              "bytes": tam})
    except OSError:
        pass
    return huerfanos


def _recortar(lista: list, tope: int = TOPE_LISTAS) -> dict:
    """Recorta una lista larga y dice quantos había en total."""
    return {"total": len(lista), "lista": lista[:tope]}


def auditoria(base: str, sistemas, exts_por_sistema, progreso=None,
              confirmar=True, max_bytes=PRESUPUESTO_CONFIRMAR) -> dict:
    """La radiografía completa de la biblioteca.

    Devuelve el resumen, los duplicados, lo que sobra y lo que está roto.

    **Ojo con el progreso**: `Progress.completar()` avisa de que el trabajo
    ha terminado, y el trabajo en segundo plano se cierra con ese aviso. Por
    eso, entre fases se usa `reiniciar()` y `completar()` se llama **una sola
    vez**, al final. Si se llamara al terminar cada fase, el trabajo se
    cerraría con el resultado a medias (y el `job` se quedaría sin resultado).
    """
    sistemas = list(sistemas)
    prog = Progress(len(sistemas), "recorriendo la biblioteca", notificar=progreso)
    datos = recolectar(base, sistemas, exts_por_sistema)
    juegos = datos["juegos"]

    por_sistema: dict = {sistema: [] for sistema in sistemas}
    for juego in juegos:
        por_sistema.setdefault(juego.sistema, []).append(juego)
    espacio = []
    for sistema, lista in por_sistema.items():
        espacio.append({"sistema": sistema, "juegos": len(lista),
                        "bytes": sum(j.tamano for j in lista),
                        "gb": round(sum(j.tamano for j in lista) / 1073741824, 2)})
    espacio.sort(key=lambda x: -x["bytes"])

    # Las fichas del gamelist y las que ya no tienen fichero.
    prog.reiniciar(len(sistemas), "leyendo los gamelists")
    fichas_sin_fichero = []
    entradas_por_sistema = {}
    con_partidas = sin_partidas = 0
    for sistema in sistemas:
        folder = Path(base) / sistema
        gl = folder / "gamelist.xml"
        entradas = leer_gamelist(str(gl)) if gl.exists() else {}
        entradas_por_sistema[sistema] = entradas
        for ruta, game in entradas.items():
            if not (folder / ruta).exists():
                fichas_sin_fichero.append({"sistema": sistema, "ruta": ruta})
            try:
                n = int(game.findtext("playcount", "") or 0)
            except ValueError:
                n = 0
            if n > 0:
                con_partidas += 1
            else:
                sin_partidas += 1
        prog.terminar_unidad()

    # Los duplicados (lo lento: la huella rápida y la confirmación).
    dups = duplicados(base, juegos, confirmar=confirmar, max_bytes=max_bytes,
                       progreso=progreso)

    # La media que ya no tiene juego.
    prog.reiniciar(len(sistemas), "buscando media huerfana")
    huerfanos = []
    for sistema in sistemas:
        nombres = {Path(j.nombre).stem for j in por_sistema.get(sistema, [])}
        huerfanos.extend(_media_huerfana(base, sistema, nombres,
                                         entradas_por_sistema.get(sistema) or {}))
        prog.terminar_unidad()

    repetidos = repetidos_entre_sistemas(juegos)

    total_bytes = sum(j.tamano for j in juegos)
    prog.completar()
    return {
        "resumen": {
            "sistemas": len([s for s in sistemas if (Path(base) / s).is_dir()]),
            "juegos": len(juegos),
            "bytes": total_bytes,
            "gb": round(total_bytes / 1073741824, 1),
        },
        "duplicados": dups,
        "repetidos_entre_sistemas": repetidos,
        "fichas_sin_fichero": _recortar(fichas_sin_fichero),
        "ficheros_vacios": _recortar([j.as_dict() for j in datos["vacios"]]),
        "sobras": _recortar([j.as_dict() for j in datos["sobras"]]),
        "media_huerfana": _recortar(huerfanos),
        "partidas": {"con_partidas": con_partidas, "sin_partidas": sin_partidas},
        "espacio": espacio,
        "mayores": [j.as_dict() for j in
                    sorted(juegos, key=lambda j: -j.tamano)[:20]],
    }


# ── Acciones: cuarentena y limpieza del gamelist ────────────────────────

def journal_path(root: str = "/userdata/system") -> str:
    return os.path.join(root, JOURNAL_NAME)


def _read_journal(root: str) -> list:
    try:
        with open(journal_path(root), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _write_journal(root: str, entries: list) -> None:
    path = journal_path(root)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entries, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def _dentro_de(base: Path, ruta: Path) -> bool:
    """Si una ruta esta dentro de la carpeta de la biblioteca.

    Sin esta comprobacion, un ``../`` en la ruta moveria ficheros de fuera
    de la biblioteca a la cuarentena.
    """
    try:
        base_real = os.path.realpath(str(base))
        ruta_real = os.path.realpath(str(ruta))
    except OSError:
        return False
    return ruta_real == base_real or ruta_real.startswith(base_real + os.sep)


def _destino_libre(destino: Path, nombre: str) -> Path:
    """Un nombre que no pise nada (dos juegos pueden llamarse igual)."""
    final = destino / nombre
    if not final.exists():
        return final
    for numero in range(1, 1000):
        final = destino / f"{nombre}.{numero}"
        if not final.exists():
            return final
    return destino / f"{nombre}.{int(time.time())}"


def cuarentena(base: str, ficheros, root: str = "/userdata/system") -> dict:
    """Mueve ficheros a la cuarentena (no se borra nada).

    ``ficheros`` son rutas ``sistema/ruta``. La cuarentena está dentro de la
    propia biblioteca (``/userdata/roms/.quarantine``), así que el move es un
    renombrado: instantáneo y sin copiar 63 GB.
    """
    base_path = Path(base)
    destino = base_path / QUARANTINE
    movidos = []
    errores = []
    for clave in ficheros or []:
        sistema, _, ruta = str(clave).partition("/")
        if not sistema or not ruta:
            errores.append({"fichero": clave, "error": "ruta no valida"})
            continue
        origen = base_path / sistema / ruta
        if not _dentro_de(base_path, origen):
            errores.append({"fichero": clave, "error": "ruta fuera de la biblioteca"})
            continue
        if not origen.exists():
            errores.append({"fichero": clave, "error": "no existe"})
            continue
        try:
            final = _destino_libre(destino / sistema, os.path.basename(ruta))
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(origen), str(final))
            movidos.append({"from": str(origen), "to": str(final),
                            "sistema": sistema, "ruta": ruta})
        except OSError as exc:
            errores.append({"fichero": clave, "error": str(exc)})

    # En el journal solo quedan las tandas que movieron algo: una tanda
    # vacía no se puede deshacer y solo ensucia el historial.
    if movidos:
        journal = _read_journal(root)
        journal.append({"when": time.time(), "tipo": "cuarentena", "batch": movidos})
        _write_journal(root, journal[-20:])
    return {"ok": not errores, "movidos": movidos, "errores": errores}


def limpiar_gamelist(base: str, sistema: str, root: str = "/userdata/system") -> dict:
    """Quita del ``gamelist.xml`` las fichas cuyo fichero ya no existe.

    El texto original se guarda en el journal, así que se puede deshacer.
    """
    gl = Path(base) / sistema / "gamelist.xml"
    if not _dentro_de(Path(base), gl):
        return {"ok": False, "error": "el sistema no esta en la biblioteca",
                "quitadas": 0}
    if not gl.is_file():
        return {"ok": False, "error": "el sistema no tiene gamelist.xml",
                "quitadas": 0}
    try:
        antes = gl.read_text(encoding="utf-8")
        root_xml = ET.fromstring(antes)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"el gamelist.xml no se puede leer: {exc}",
                "quitadas": 0}

    carpeta = gl.parent
    quitadas = []
    for game in list(root_xml.findall(".//game")):
        ruta = (game.findtext("path", "") or "").lstrip("./")
        if not ruta:
            continue
        if (carpeta / ruta).exists():
            continue
        # Se quita la ficha y sus imagenes huerfanas del gamelist.
        for hijo in list(game):
            if hijo.tag in ("image", "video", "marquee", "thumbnail", "manual",
                            "screenshot", "fanart"):
                game.remove(hijo)
        for padre in root_xml.iter():
            if game in list(padre):
                padre.remove(game)
                break
        quitadas.append(ruta)

    if not quitadas:
        return {"ok": True, "quitadas": 0, "fichero": str(gl)}

    try:
        nuevo = ET.tostring(root_xml, encoding="unicode")
        if not nuevo.startswith("<?xml"):
            nuevo = '<?xml version="1.0"?>\n' + nuevo
        gl.write_text(nuevo, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": str(exc), "quitadas": 0}

    journal = _read_journal(root)
    journal.append({"when": time.time(), "tipo": "gamelist",
                    "batch": [], "gamelist": {"path": str(gl), "antes": antes}})
    _write_journal(root, journal[-20:])
    return {"ok": True, "quitadas": len(quitadas), "fichero": str(gl),
            "rutas": quitadas[:50]}


def undo_last(root: str = "/userdata/system") -> dict:
    """Deshace la ultima tanda de la biblioteca."""
    journal = _read_journal(root)
    if not journal:
        return {"ok": False, "error": "no hay nada que deshacer"}
    batch = journal[-1]
    restaurados = []
    errores = []
    for entrada in reversed(batch.get("batch") or []):
        origen = entrada.get("from")
        destino = entrada.get("to")
        if not origen or not destino:
            continue
        if not os.path.exists(destino):
            errores.append({"fichero": destino, "error": "no existe"})
            continue
        try:
            os.makedirs(os.path.dirname(origen), exist_ok=True)
            shutil.move(destino, origen)
            restaurados.append(origen)
        except OSError as exc:
            errores.append({"fichero": destino, "error": str(exc)})

    gl = batch.get("gamelist")
    if gl and gl.get("path") and gl.get("antes") is not None:
        try:
            with open(gl["path"], "w", encoding="utf-8") as fh:
                fh.write(gl["antes"])
        except OSError as exc:
            errores.append({"fichero": gl.get("path"), "error": str(exc)})

    journal.pop()
    _write_journal(root, journal)
    return {"ok": not errores, "restaurados": restaurados, "errores": errores}


def journal_batches(root: str = "/userdata/system") -> list:
    """Las tandas que se pueden deshacer (la ultima es la primera)."""
    journal = _read_journal(root)
    salida = []
    for entrada in reversed(journal):
        batch = entrada.get("batch") or []
        gl = entrada.get("gamelist")
        salida.append({
            "when": entrada.get("when"),
            "tipo": entrada.get("tipo", "cuarentena"),
            "count": len(batch),
            "gamelist": gl.get("path") if gl else None,
            "files": [os.path.basename(m.get("to", "")) for m in batch[:8]],
        })
    return salida
