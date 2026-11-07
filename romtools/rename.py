"""Renombrado de ROMs segun las convenciones de set, con vuelta atras.

El flujo es de tres pasos, y el primero no toca el disco:

1. **Plan**: se recorren los ficheros de un sistema, se identifican contra el
   DAT y se calcula el nombre destino. El plan se enseña entero antes de
   hacer nada.
2. **Aplicar**: se renombran los ficheros y sus acompanantes (el CUE de un
   BIN, la M3U de varios discos), sin sobrescribir nada.
3. **Deshacer**: cada aplicacion deja un journal en disco, asi que la ultima
   tanda se puede revertir.

Las reglas de seguridad son las de siempre: nunca se sale de la carpeta del
sistema, nunca se pisa un fichero que ya existe y un plan con poca confianza
se marca para que lo revise el usuario en vez de renombrar a ciegas.
"""

from __future__ import annotations

import json
import os
import posixpath
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import naming, sets
from .identify import Match, identify

#: Donde se guarda el journal de renombrados.
JOURNAL_NAME = "batocera_manager_renames.json"

#: Ficheros que se renombran junto al juego.
_COMPANIONS = sets.COMPANION_EXTENSIONS


@dataclass
class RenameItem:
    """Un fichero del plan."""

    path: str
    current: str
    proposed: str = ""
    action: str = "skip"
    reason: str = ""
    confidence: float = 0.0
    method: str = ""
    entry: dict | None = None
    companions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    carpeta: str = ""
    hashes: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "file": os.path.basename(self.path),
            "current": self.current,
            "proposed": self.proposed,
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "method": self.method,
            "title": (self.entry or {}).get("description") if self.entry else None,
            "dat_name": (self.entry or {}).get("name") if self.entry else None,
            "companions": self.companions,
            "warnings": self.warnings,
            "carpeta": self.carpeta,
            "hashes": self.hashes,
        }


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


def companions_of(path: str) -> list:
    """Los ficheros que acompañan a este y se renombran con el."""
    stem = os.path.splitext(path)[0]
    out = []
    for ext in sorted(_COMPANIONS):
        candidate = stem + ext
        if os.path.isfile(candidate):
            out.append(candidate)
    # Los discos multiples tienen un BIN por pista: "Juego (Track 2).bin".
    directory = os.path.dirname(path)
    base = os.path.basename(stem)
    try:
        for name in os.listdir(directory):
            low = name.lower()
            if low.startswith(base.lower()) and re_track(low):
                full = os.path.join(directory, name)
                if full != path and os.path.isfile(full) and full not in out:
                    out.append(full)
    except OSError:
        pass
    return out


def re_track(name: str) -> bool:
    """Si el nombre es el de una pista secundaria (``.track 2.bin``)."""
    return ".track " in name or name.endswith(".track01.bin")


def _hashes_del_cruce(match: Match) -> dict:
    """Los dos lados del cruce: los hashes del fichero y los del DAT.

    En los discos de Wii el DAT hashea la ISO (4,7 GB) y el volcado lleva
    su propio MD5 del juego, asi que los hashes no son los mismos: lo que
    cruza es el codigo de juego. Se devuelven los dos para que se vea el
    cruce entero.
    """
    info = {}
    wii = (match.signature or {}).get("wii") or {}
    if wii:
        info["archivo"] = {clave: wii.get(clave) for clave in
                           ("game_code", "md5", "title", "region")
                           if wii.get(clave)}
    entrada = match.entry or {}
    for rom in entrada.get("roms", []) or []:
        dat = {clave: rom.get(clave) for clave in ("crc", "md5", "sha1")
               if rom.get(clave)}
        if dat:
            info["dat"] = dat
            break
    return info


def _hashes_del_cruce(match: Match) -> dict:
    """Los dos lados del cruce: los hashes del fichero y los del DAT.

    En los discos de Wii el DAT hashea la ISO (4,7 GB) y el volcado lleva
    su propio MD5 del juego, asi que los hashes no son los mismos: lo que
    cruza es el codigo de juego. Se devuelven los dos para que se vea el
    cruce entero.
    """
    info = {}
    wii = (match.signature or {}).get("wii") or {}
    if wii:
        info["archivo"] = {clave: wii.get(clave) for clave in
                           ("game_code", "md5", "title", "region")
                           if wii.get(clave)}
    entrada = match.entry or {}
    for rom in entrada.get("roms", []) or []:
        dat = {clave: rom.get(clave) for clave in ("crc", "md5", "sha1")
               if rom.get(clave)}
        if dat:
            info["dat"] = dat
            break
    return info


def plan_rename(files: Sequence[str], index: dict | None,
                options: naming.NamingOptions | None = None,
                region_priority: Sequence[str] = sets.DEFAULT_REGION_PRIORITY,
                min_confidence: float = 0.75,
                hash_budget: int = 512 * 1024 * 1024) -> dict:
    """Calcula el plan de renombrado de una lista de ficheros.

    ``index`` es el indice del DAT del sistema (o ``None`` si no hay DAT: en
    ese caso solo se ordenan los nombres existentes).

    Cada elemento de ``files`` es el fichero del juego. Puede ser una ruta
    suelta (un ``.iso`` en la carpeta del sistema) o un diccionario con la
    carpeta en la que vive el juego: ``{"path", "carpeta", "ext"}``. En el
    segundo caso lo que se renombra es la **carpeta** (los juegos de Wii
    viven en ``Juego [REXP01]/REXP01.wbfs``) y el fichero de dentro se
    queda como estaba.
    """
    opts = options or naming.NamingOptions()
    items: list = []
    # El hash obliga a leer el fichero entero: con bibliotecas de 40 GB eso
    # es eterno, asi que se lleva un presupuesto de bytes.
    restante = hash_budget

    for unidad in sorted(files, key=lambda u: u.get("path", "") if isinstance(u, dict) else str(u)):
        if isinstance(unidad, dict):
            path = unidad.get("path") or ""
            carpeta = (unidad.get("carpeta") or "").replace(os.sep, "/")
            ext_carpeta = unidad.get("ext") or ""
        else:
            path = str(unidad)
            carpeta = ""
            ext_carpeta = ""
        if not path or not os.path.isfile(path):
            continue
        # El juego vive en una carpeta: lo que se renombra es la carpeta.
        nombre_carpeta = os.path.basename(carpeta) if carpeta else ""
        current = nombre_carpeta or os.path.basename(path)
        ext = os.path.splitext(current)[1]
        item = RenameItem(path=path, current=current, carpeta=carpeta)

        if index:
            try:
                tamano = os.path.getsize(path)
            except OSError:
                tamano = 0
            hashear = tamano <= restante
            if hashear:
                restante -= tamano
            match: Match = identify(path, index, title_hint=os.path.splitext(current)[0],
                                    hash_allowed=hashear)
            item.method = match.method
            item.confidence = match.confidence
            item.entry = match.entry
            if match.entry:
                if carpeta:
                    proposed = naming.folder_target_name(match.entry, nombre_carpeta,
                                                         ext_carpeta, opts)
                else:
                    proposed = naming.rom_target_name(match.entry, current, opts)
                item.hashes = _hashes_del_cruce(match)
                if match.method == "titulo" and match.candidates:
                    # Hay varias entradas parecidas: se elige la mejor y se
                    # explica por que. La eleccion se hace entre las entradas
                    # del MISMO juego: si no, un juego distinto que comparta
                    # subtitulo se llevaria el renombrado del otro.
                    best, score, _grupo = sets.pick_best_variant(
                        match.candidates, source=current,
                        region_priority=region_priority)
                    if best is not None and best.get("name") != match.entry.get("name"):
                        item.entry = best
                        proposed = naming.rom_target_name(best, current, opts)
                        item.reason = "de entre varias coincidencias se ha elegido la mejor variante"
                        item.warnings.append(
                            "candidatas: " + ", ".join(
                                c["entry"].get("name", "") for c in match.candidates[:4]))
                    else:
                        item.reason = score.reasons[0] if score and score.reasons else match.note
                else:
                    item.reason = match.note or "coincidencia por " + match.method
                if not hashear and match.method not in ("nombre",):
                    item.warnings.append(
                        "no se ha verificado por hash: la biblioteca es muy grande")
                item.proposed = proposed
                if match.confidence < min_confidence:
                    item.action = "revisar"
                    item.reason = f"la confianza es baja ({match.confidence:.0%}): revisa el nombre"
                elif proposed.lower() == current.lower():
                    item.action = "igual"
                    item.reason = "el nombre ya sigue la convencion"
                else:
                    item.action = "renombrar"
            else:
                item.action = "sin DAT"
                item.reason = match.note or "no aparece en el DAT"
                item.proposed = naming.fallback_name(current, opts)
                item.confidence = 0.0
        else:
            item.action = "sin DAT"
            item.reason = "no hay DAT para este sistema"
            item.proposed = naming.fallback_name(current, opts)

        if item.action in ("renombrar", "revisar") and not carpeta:
            item.companions = [os.path.basename(c) for c in companions_of(path)]

        items.append(item)

    stats = {
        "total": len(items),
        "renombrar": sum(1 for i in items if i.action == "renombrar"),
        "revisar": sum(1 for i in items if i.action == "revisar"),
        "igual": sum(1 for i in items if i.action == "igual"),
        "sin_dat": sum(1 for i in items if i.action == "sin DAT"),
    }
    stats["identificados"] = sum(1 for i in items if i.entry)
    return {"items": [i.as_dict() for i in items], "stats": stats}


# ── El gamelist.xml y la media ──────────────────────────────────────────

#: Carpetas donde Batocera guarda la media de un sistema.
MEDIA_DIRS = ("images", "videos", "manuals", "downloads")

#: Etiquetas del gamelist.xml que apuntan a un fichero de media.
MEDIA_TAGS = ("image", "video", "marquee", "thumbnail", "miximage", "fanart",
              "manual", "titleshot", "screenshot")


def _tallo(nombre: str) -> str:
    """El nombre de un fichero sin su extension."""
    return os.path.splitext(os.path.basename(nombre))[0]


def _media_nueva(nombre: str, viejo: str, nuevo: str) -> str | None:
    """El nombre nuevo de un fichero de media, si sigue al nombre del juego.

    ``Clay Fighter-image.png`` sigue a ``Clay Fighter.smd``: se cambia el
    tallo y se deja el sufijo. Un fichero que solo empieza por el nombre del
    juego **no** se toca: ``Super Mario`` no es ``Super Mario Bros``.
    """
    base, sufijo = os.path.splitext(nombre)
    if not base.startswith(viejo):
        return None
    resto = base[len(viejo):]
    if resto and not resto.startswith("-"):
        return None
    return nuevo + resto + sufijo


def _renombrar_media(folder: str, viejo: str, nuevo: str) -> list:
    """Renombra los ficheros de media que siguen el nombre del juego."""
    salida = []
    for sub in MEDIA_DIRS:
        carpeta = os.path.join(folder, sub)
        if not os.path.isdir(carpeta):
            continue
        try:
            nombres = sorted(os.listdir(carpeta))
        except OSError:
            continue
        for nombre in nombres:
            nuevo_nombre = _media_nueva(nombre, viejo, nuevo)
            if not nuevo_nombre or nuevo_nombre == nombre:
                continue
            origen = os.path.join(carpeta, nombre)
            destino = os.path.join(carpeta, nuevo_nombre)
            if os.path.exists(destino):
                continue
            try:
                os.rename(origen, destino)
            except OSError:
                continue
            salida.append({"from": origen, "to": destino})
    return salida


def update_gamelist(folder: str, moves: list) -> dict:
    """Actualiza el gamelist.xml tras un renombrado.

    Para cada ficha que apunta a un fichero renombrado:

    - el ``<path>`` pasa al nombre nuevo;
    - los ficheros de media que siguen el nombre del juego (en ``images/``,
      ``videos/``…) se renombran con el tallo nuevo, y las etiquetas de media
      se apuntan a los ficheros nuevos.

    Asi el ``gamelist.xml`` sigue cuadrando con los ficheros, con la media y
    con los metadatos: sin esto, EmulationStation se quedaria sin las fichas
    de los juegos renombrados.

    Devuelve los cambios hechos (para poder deshacerlos) y el texto que
    tenia el gamelist antes de tocarlo.
    """
    gl = os.path.join(folder, "gamelist.xml")
    vacio = {"ok": True, "cambios": [], "media": [], "gamelist": None}
    if not os.path.isfile(gl):
        return vacio
    try:
        with open(gl, "r", encoding="utf-8") as fh:
            antes = fh.read()
        root = ET.fromstring(antes)
    except (OSError, ValueError):
        return {"ok": False, "cambios": [], "media": [], "gamelist": None,
                "error": "el gamelist.xml no se puede leer"}

    renombres = {}
    for entrada in moves or []:
        origen = entrada.get("from") or ""
        destino = entrada.get("to") or ""
        if not origen or not destino:
            continue
        renombres[os.path.basename(origen)] = os.path.basename(destino)
        # Si lo renombrado fue una carpeta, su nombre tambien cambia y las
        # rutas del gamelist la llevan como una parte mas.
        dir_origen = os.path.dirname(origen)
        dir_destino = os.path.dirname(destino)
        if dir_origen != dir_destino:
            renombres[os.path.basename(dir_origen)] = os.path.basename(dir_destino)
        # Si lo renombrado fue una carpeta, su nombre tambien cambia y las
        # rutas del gamelist la llevan como una parte mas.
        dir_origen = os.path.dirname(origen)
        dir_destino = os.path.dirname(destino)
        if dir_origen != dir_destino:
            renombres[os.path.basename(dir_origen)] = os.path.basename(dir_destino)

    cambios = []
    media = []
    for game in root.findall("game"):
        el_path = game.find("path")
        if el_path is None or not el_path.text:
            continue
        ruta = el_path.text.strip()
        # La ruta se compone de partes (la carpeta del juego y el fichero):
        # cada parte se cambia si su nombre cambio.
        partes = ruta.split("/")
        nuevas = []
        cambio = False
        for parte in partes:
            nuevo = renombres.get(parte)
            if nuevo and nuevo != parte:
                cambio = True
                nuevas.append(nuevo)
            else:
                nuevas.append(parte)
        if not cambio:
            continue
        el_path.text = "/".join(nuevas)
        cambios.append({"de": ruta, "a": el_path.text})

        nombre = posixpath.basename(ruta)
        nuevo_nombre = posixpath.basename(el_path.text)

        viejo_tallo = _tallo(nombre)
        nuevo_tallo = _tallo(nuevo_nombre)
        if viejo_tallo == nuevo_tallo:
            continue

        # Los ficheros de media que siguen el nombre del juego.
        media += _renombrar_media(folder, viejo_tallo, nuevo_tallo)

        # Y las etiquetas que los apuntan.
        for tag in MEDIA_TAGS:
            el = game.find(tag)
            if el is None or not el.text:
                continue
            valor = el.text.strip()
            base = posixpath.basename(valor)
            nuevo_base = _media_nueva(base, viejo_tallo, nuevo_tallo)
            if not nuevo_base or nuevo_base == base:
                continue
            subcarpeta = posixpath.dirname(valor.lstrip("./"))
            origen = os.path.join(folder, subcarpeta.replace("/", os.sep), base)
            destino = os.path.join(folder, subcarpeta.replace("/", os.sep), nuevo_base)
            if os.path.isfile(origen) and not os.path.exists(destino):
                try:
                    os.rename(origen, destino)
                    media.append({"from": origen, "to": destino})
                except OSError:
                    pass
            el.text = posixpath.join(posixpath.dirname(valor), nuevo_base)

    if not cambios and not media:
        return vacio

    try:
        ET.indent(root, space="    ")
        xml_out = ('<?xml version="1.0" encoding="UTF-8"?>\n' +
                   ET.tostring(root, encoding="unicode"))
        with open(gl, "w", encoding="utf-8") as fh:
            fh.write(xml_out)
    except OSError as exc:
        return {"ok": False, "cambios": cambios, "media": media,
                "gamelist": None, "error": str(exc)}

    return {"ok": True, "cambios": cambios, "media": media,
            "gamelist": {"path": gl, "antes": antes}}


def apply_plan(plan: dict, folder: str, root: str = "/userdata/system",
               include_review: bool = False) -> dict:
    """Ejecuta el plan: renombra y deja journal para poder deshacer.

    ``include_review`` permite renombrar tambien los ficheros marcados como
    «revisar» (los que tienen coincidencia por titulo pero poca confianza).
    """
    folder = os.path.abspath(folder)
    moved = []
    skipped = []
    errors = []

    for item in plan.get("items", []):
        action = item.get("action")
        if action == "renombrar" or (include_review and action == "revisar"):
            pass
        else:
            skipped.append({"file": item.get("file"), "reason": item.get("reason")})
            continue

        proposed = item.get("proposed") or ""
        carpeta = item.get("carpeta") or ""
        if carpeta:
            # El juego vive en una carpeta: se renombra la carpeta y el
            # fichero de dentro se queda con su nombre (el codigo del disco).
            path = os.path.join(folder, carpeta)
            if not os.path.isdir(path):
                skipped.append({"file": item.get("file"), "reason": "ya no esta en la carpeta"})
                continue
            if not proposed:
                skipped.append({"file": item.get("file"), "reason": "no hay nombre destino"})
                continue
            target = os.path.join(folder, naming.unique_path(folder, proposed))
            try:
                os.rename(path, target)
            except OSError as exc:
                errors.append({"file": carpeta, "error": str(exc)})
                continue
            moved.append({"from": path, "to": target, "when": time.time()})
            continue

        path = os.path.join(folder, item.get("file", ""))
        if not os.path.isfile(path):
            skipped.append({"file": item.get("file"), "reason": "ya no esta en la carpeta"})
            continue
        if not proposed:
            skipped.append({"file": item.get("file"), "reason": "no hay nombre destino"})
            continue
        if os.path.dirname(os.path.abspath(path)) != folder:
            errors.append({"file": item.get("file"), "error": "fuera de la carpeta del sistema"})
            continue

        # El destino va dentro de la carpeta del sistema: si se deja el
        # nombre suelto, el rename intentaria moverlo al directorio actual.
        target = os.path.join(folder, naming.unique_path(folder, proposed))
        try:
            os.rename(path, target)
        except OSError as exc:
            errors.append({"file": item.get("file"), "error": str(exc)})
            continue

        entry = {"from": path, "to": target, "when": time.time()}
        moved.append(entry)

        # Los acompanantes se renombran con el mismo tallo.
        for companion in item.get("companions", []):
            companion_path = os.path.join(folder, companion)
            if not os.path.isfile(companion_path):
                continue
            new_companion = os.path.join(
                folder, os.path.splitext(os.path.basename(target))[0] +
                os.path.splitext(companion)[1])
            try:
                os.rename(companion_path, new_companion)
                moved.append({"from": companion_path, "to": new_companion, "when": time.time()})
            except OSError as exc:
                errors.append({"file": companion, "error": str(exc)})

    # El gamelist.xml y la media se actualizan con los nombres nuevos: si no,
    # las fichas apuntarian a ficheros que ya no existen y las imagenes se
    # quedarian sin su juego.
    gamelist = update_gamelist(folder, moved)
    moved += gamelist.get("media") or []

    if moved:
        journal = _read_journal(root)
        entrada = {"batch": moved, "when": time.time()}
        if gamelist.get("gamelist"):
            entrada["gamelist"] = gamelist["gamelist"]
        journal.append(entrada)
        _write_journal(root, journal[-20:])

    return {"ok": not errors, "renamed": len(moved), "skipped": skipped,
            "errores": errors, "moved": moved,
            "gamelist": {"cambios": len(gamelist.get("cambios") or []),
                         "media": len(gamelist.get("media") or []),
                         "error": gamelist.get("error")}}


def undo_last(root: str = "/userdata/system") -> dict:
    """Deshace la ultima tanda de renombrados."""
    journal = _read_journal(root)
    if not journal:
        return {"ok": False, "error": "no hay nada que deshacer"}
    batch = journal[-1]
    restored = []
    errors = []
    for entry in reversed(batch.get("batch", [])):
        source = entry.get("from")
        target = entry.get("to")
        if not source or not os.path.exists(target):
            errors.append({"file": target, "error": "no existe"})
            continue
        try:
            os.rename(target, source)
            restored.append(target)
        except OSError as exc:
            errors.append({"file": target, "error": str(exc)})
    # El gamelist.xml vuelve a como estaba: con los nombres viejos.
    gl = batch.get("gamelist")
    if gl and gl.get("path") and gl.get("antes") is not None:
        try:
            with open(gl["path"], "w", encoding="utf-8") as fh:
                fh.write(gl["antes"])
        except OSError as exc:
            errors.append({"file": gl.get("path"), "error": str(exc)})

    journal.pop()
    _write_journal(root, journal)
    return {"ok": not errors, "restored": restored, "errores": errors}


def journal_batches(root: str = "/userdata/system") -> list:
    """Las tandas que se pueden deshacer (la ultima es la primera)."""
    journal = _read_journal(root)
    out = []
    for entry in reversed(journal):
        batch = entry.get("batch", [])
        out.append({"when": entry.get("when"), "count": len(batch),
                    "files": [os.path.basename(m.get("to", "")) for m in batch[:8]]})
    return out
