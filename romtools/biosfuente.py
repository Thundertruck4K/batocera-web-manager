"""La fuente de BIOS: donde se baja lo que falta en la consola.

El catalogo de Batocera dice que BIOS hace falta en cada sistema, pero no las
trae: solo dice el nombre y el hash. Para que el usuario no tenga que buscar
cada BIOS a mano, el manager las baja de una fuente que ya las tiene todas, en
la misma disposicion en que Batocera las espera.

La fuente es un **indice de directorios de Apache**: una pagina HTML con la
lista de ficheros y carpetas. Las rutas coinciden con las que Batocera espera
bajo ``/userdata/bios`` (``Acorn/basic2.rom``, ``bk/DISK_327.ROM``,
``enterprise/ep128emu/roms/exos21.rom``...), asi que descargar una BIOS es
copiarla a su sitio.

El indice se construye **dirigido**: solo se bajan las carpetas que hacen
falta para las BIOS que faltan. Indexar el arbol entero son ~64 peticiones y
varios minutos en la consola, y no hace falta: con las carpetas justas, las
51 BIOS que faltaban en la consola de desarrollo se resolven con 6 peticiones.

Lo que no esta en la fuente, **no esta**: se informa y se deja como estaba. No
se busca en ningun otro sitio ni se inventa nada.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .progress import Progress

#: La fuente que se usa por defecto.
FUENTE_BIOS = "http://rgsretro1986.ds78102.seedhost.eu/update/Batocera/bios/"

#: Tope por fichero. Una BIOS es un fichero pequeno: por encima de esto ya no
#: es una BIOS (mismo tope que el asistente de BIOS de ``app.py``).
MAX_BIOS = 64 * 1024 * 1024

#: Los enlaces de un indice de Apache.
_HREF = re.compile(r'href="([^"]+)"')

#: Un fichero que se puede bajar (no una carpeta, ni un enlace de navegacion).
_ENLACE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._+()\-]*$')


def parse_indice(texto: str) -> list:
    """Saca los nombres de un indice de directorios de Apache.

    Devuelve una lista de nombres, tal y como aparecen en el indice. Las
    carpetas terminan en ``/``.
    """
    salida = []
    for href in _HREF.findall(texto or ""):
        if href.startswith("?") or href.startswith("/"):
            continue                      # orden de columnas o ruta absoluta
        nombre = html.unescape(href)
        if nombre in ("./", "../"):
            continue
        salida.append(nombre)
    return salida


def ruta_valida(rel: str) -> bool:
    """Si una ruta relativa es aceptable como destino.

    Ni absolutas, ni con ``..``, ni con carpetas vacias: el destino siempre
    esta debajo de la carpeta de BIOS.
    """
    if not rel or rel.startswith("/") or rel.startswith("\\"):
        return False
    if re.match(r"^[A-Za-z]:", rel):
        return False
    partes = rel.replace("\\", "/").split("/")
    for parte in partes:
        if parte in ("", ".", ".."):
            return False
    return True


def _decodificar(nombre: str) -> str:
    """Quita el %20 y demas escapes de un nombre de enlace."""
    return urllib.parse.unquote(nombre)


class Fuente:
    """La fuente de BIOS, con su indice cacheado en memoria."""

    def __init__(self, url: str = FUENTE_BIOS, timeout: int = 30):
        self.url = url if url.endswith("/") else url + "/"
        self.timeout = timeout
        #: Carpeta -> nombres que hay en ella.
        self._carpetas: dict = {}
        #: Ruta relativa (dentro de la fuente) -> nombre del fichero.
        self.index: dict = {}
        #: Nombre de fichero (en minusculas) -> ruta relativa.
        self._por_nombre: dict = {}

    # ── Red ──────────────────────────────────────────────────────────────

    def _url(self, rel: str) -> str:
        """La URL de un fichero de la fuente, con las carpetas escapadas."""
        partes = [p for p in rel.replace("\\", "/").split("/") if p]
        return self.url + "/".join(urllib.parse.quote(p) for p in partes)

    def _leer(self, url: str) -> bytes:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": "BatoceraManager/1.0"})
        with urllib.request.urlopen(peticion, timeout=self.timeout) as resp:
            return resp.read(MAX_BIOS + 1)

    def listar(self, carpeta: str = "") -> list:
        """Los nombres que hay en una carpeta de la fuente (cacheado).

        Una carpeta que no existe no es un error: simply no hay nada ahi.
        """
        if carpeta in self._carpetas:
            return self._carpetas[carpeta]
        nombres = []
        try:
            texto = self._leer(self._url(carpeta)).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            texto = ""
        except Exception:
            texto = ""
        for nombre in parse_indice(texto):
            if nombre.endswith("/"):
                continue
            nombres.append(_decodificar(nombre))
        self._carpetas[carpeta] = nombres
        return nombres

    # ── Indice ───────────────────────────────────────────────────────────

    def indexar(self, rutas) -> dict:
        """Indexa la fuente para poder emparejar estas rutas.

        Solo se bajan las carpetas que hacen falta: la raiz (siempre, porque
        sirve para el emparejamiento por nombre) y las carpetas de las rutas
        pedidas.
        """
        prefijos = {""}
        for ruta in rutas or []:
            partes = [p for p in str(ruta).replace("\\", "/").split("/")[:-1] if p]
            for i in range(len(partes)):
                prefijos.add("/".join(partes[:i + 1]) + "/")
        # De padre a hijo: para llegar a "ep128emu/roms/" hace falta haber
        # visto antes "ep128emu/".
        for prefijo in sorted(prefijos, key=lambda p: (p.count("/"), p)):
            for nombre in self.listar(prefijo):
                if nombre.endswith("/"):
                    continue              # una carpeta no es una BIOS
                completa = prefijo + nombre
                if not ruta_valida(completa):
                    continue              # una ruta que se sale de la fuente
                self.index[completa] = nombre
                self._por_nombre.setdefault(nombre.lower(), completa)
        return self.index

    def emparejar(self, ruta: str):
        """El fichero de la fuente que corresponde a esta ruta (o ``None``).

        El orden es: ruta exacta, ruta exacta ignorando mayusculas y, por
        ultimo, el mismo nombre de fichero en otra carpeta.
        """
        if not ruta:
            return None
        if ruta in self.index:
            return ruta
        minuscula = ruta.lower()
        for completa in self.index:
            if completa.lower() == minuscula:
                return completa
        base = ruta.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return self._por_nombre.get(base)

    def emparejar_todas(self, rutas) -> dict:
        """Empareja varias rutas: devuelve ``{ruta: ruta_fuente}``."""
        salida = {}
        for ruta in rutas or []:
            encontrada = self.emparejar(ruta)
            if encontrada:
                salida[ruta] = encontrada
        return salida

    # ── Descarga ─────────────────────────────────────────────────────────

    def descargar(self, ruta_fuente: str, destino: str) -> dict:
        """Baja un fichero de la fuente a un destino.

        Nunca lanza: devuelve ``{ok, error?, md5?, size?}``.
        """
        try:
            datos = self._leer(self._url(ruta_fuente))
        except Exception as exc:
            return {"ok": False, "error": f"no se pudo descargar: {exc}"}
        if len(datos) > MAX_BIOS:
            return {"ok": False, "error": "el fichero es demasiado grande"}
        try:
            carpeta = os.path.dirname(destino)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
            with open(destino, "wb") as fh:
                fh.write(datos)
        except Exception as exc:
            return {"ok": False, "error": f"no se pudo guardar: {exc}"}
        return {"ok": True, "md5": hashlib.md5(datos).hexdigest(),
                "size": len(datos)}


def bajar_faltantes(bios_dir: str, faltantes, url: str = FUENTE_BIOS,
                    progreso=None, timeout: int = 30,
                    fuente: Fuente = None) -> dict:
    """Baja de la fuente las BIOS que faltan y las deja en su sitio.

    ``faltantes`` es una lista de diccionarios con ``file`` (la ruta que
    Batocera espera) y, si se quiere, ``system``.

    ``progreso`` recibe el estado del trabajo (cuanto lleva, que fichero va,
    que porcentaje), como en el plan de renombrado.

    Devuelve ``{ok, fuente, total, descargadas, no_encontradas, fallidas}``.
    """
    prog = Progress(max(len(faltantes or []), 1), "preparando la descarga",
                    notificar=progreso)
    prog.avisar()

    if fuente is None:
        fuente = Fuente(url, timeout)

    wanted = []
    for item in faltantes or []:
        rel = item.get("file") if isinstance(item, dict) else str(item)
        if rel and ruta_valida(rel):
            wanted.append(rel)

    # 1) Indexar la fuente (dirigido: solo las carpetas que hacen falta).
    prog.reiniciar(max(len(wanted), 1), "buscando en la fuente")
    prog.empezar("indexando la fuente", 0, 0)
    try:
        fuente.indexar(wanted)
    except Exception as exc:
        prog.completar()
        return {"ok": False, "fuente": url, "total": len(wanted),
                "error": f"no se pudo hablar con la fuente: {exc}",
                "descargadas": [], "no_encontradas": wanted, "fallidas": []}
    prog.terminar_unidad()

    # 2) Emparejar.
    emparejadas = fuente.emparejar_todas(wanted)
    no_encontradas = [r for r in wanted if r not in emparejadas]

    # 3) Descargar una a una.
    prog.reiniciar(max(len(emparejadas), 1), "descargando las BIOS")
    descargadas = []
    fallidas = []
    for indice, rel in enumerate(sorted(emparejadas)):
        origen = emparejadas[rel]
        prog.empezar(rel, 0, indice)
        destino = os.path.join(bios_dir, *rel.replace("\\", "/").split("/"))
        resultado = fuente.descargar(origen, destino)
        if resultado.get("ok"):
            descargadas.append({"file": rel, "origen": origen,
                                 "md5": resultado.get("md5"),
                                 "size": resultado.get("size")})
        else:
            fallidas.append({"file": rel, "error": resultado.get("error")})
        prog.terminar_unidad()
    prog.completar()

    return {
        "ok": True,
        "fuente": url,
        "total": len(wanted),
        "descargadas": descargadas,
        "no_encontradas": no_encontradas,
        "fallidas": fallidas,
    }
