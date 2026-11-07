"""Motor de nombres: convenciones de sets al estilo de Romulus Manager.

Un DAT trae el nombre "oficial" del juego, que ya lleva dentro el titulo, las
etiquetas de region e idioma, el numero de disco, el serial y los marcadores de
dump bueno o malo:

    Ridge Racer (USA) (Track 1) [SLUS-00237]
    Grandia (Europe) (Disc 1) [SLES-02248]
    Zelda - Ocarina of Time (USA) [!].z64

Ese nombre **es** la convencion del set, asi que el gestor lo respeta tal cual.
Lo que decide este modulo es:

  - que etiquetas se quedan (region, serial, disco, clon),
  - como se numeran los discos que el DAT no separa,
  - como se resuelve una colision de nombres,
  - y que pasa cuando no hay DAT: el nombre del fichero se ordena con la misma
    gramática, para que un set reorderado siga siendo legible.

Reglas de la convencion estandar (las que usa Romulus y las que documenta
TOSEC/GoodTools):

  ``[!]`` volcado verificado (una buena senal, no un defecto).
  ``[b]`` volcado con datos malos.
  ``[x]`` checksum incorrecto.
  ``[f]`` volcado arreglado.
  ``[t]`` volcado traducido.
  ``[h]`` dump trucado.
  ``[p]`` copia pirata.
  ``(T)`` traduccion (en el nombre, no en la marca).
  ``(1)``, ``(2)``... variantes numeradas cuando el titulo se repite.
  ``(Disc 1)``, ``(Track 1)`` discos y pistas.
  ``(Parent)`` el juego del que es clon.
  ``[SLUS-12345]`` el serial del disco.

Los DAT de Redump ya traen el serial entre corchetes y el disco entre
parentesis; los de No-Intro usan las etiquetas de region e idioma y las marcas
``[!]`` / ``[b]``. Este modulo no reescribe lo que el DAT dice: solo ordena
lo que falta.

Ojo con una confusion habitual: en la tradicion GoodTools, ``!`` significa
volcado verificado (buena senal) y el volcado malo se marca ``[b]``.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# ── Expresiones regulares de la convencion ──────────────────────────────

#: ``(USA)``, ``(Europe)``, ``(T)``, ``(Disc 1)``, ``(Track 2)``, ``(Rev 1)``...
_TAG_RE = re.compile(r"\(([^()]*)\)")
#: ``[SLUS-00237]``, ``[RVL-RZ4E]``...
_SERIAL_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_\-]{2,15})\]")
#: Marcas de volcado: ``[b]`` y ``[x]`` son malas; ``[!]`` es verificado.
_BAD_MARK_RE = re.compile(r"\[(?:b|x)\]")
_GOOD_MARK_RE = re.compile(r"\[!\]")
#: Cualquier marca entre corchetes que no sea el serial.
_MARK_RE = re.compile(r"\[([^\[\]]{1,12})\]")

#: Etiquetas que describen el disco o la version, no la region.
_DISC_TAGS = ("disc", "disco", "cd", "dvd", "track", "pista", "side", "face", "part")
#: Etiquetas de region/idioma que se reconocen.
_REGION_TAGS = {
    "usa", "europe", "europee", "japan", "japan", "world", "asia", "korea",
    "brazil", "australia", "canada", "spain", "italy", "france", "germany",
    "netherlands", "sweden", "norway", "denmark", "finland", "portugal",
    "russia", "china", "taiwan", "hong kong", "new zealand", "mexico",
    "argentina", "chile", "peru", "colombia", "venezuela", "turkey",
    "multi", "worldwide", "unknown", "und", "jp", "us", "eu", "es",
}

#: Caracteres que no se permiten en un nombre de fichero (Windows y Batocera).
_ILLEGAL_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
#: Espacios repetidos.
_SPACES_RE = re.compile(r"\s{2,}")


@dataclass
class NamingOptions:
    """Decisiones del usuario sobre como se compone el nombre final."""

    #: Añadir el serial del disco (``[SLUS-00237]``).
    serial: bool = True
    #: Añadir la region/idioma (``(USA)``, ``(En,Fr,De)``).
    region: bool = True
    #: Mantener el numero de disco o pista.
    disc: bool = True
    #: Añadir el nombre del clon (``(Parent)``).
    clone: bool = True
    #: Marcas de dump bueno/malo (``!`` / ``~``).
    marks: bool = True
    #: Longitud maxima del nombre (sin extension).
    max_length: int = 200

    def as_dict(self) -> dict:
        return {
            "serial": self.serial,
            "region": self.region,
            "disc": self.disc,
            "clone": self.clone,
            "marks": self.marks,
            "max_length": self.max_length,
        }


@dataclass
class DatName:
    """El nombre de un DAT descompuesto en sus piezas."""

    title: str
    tags: list[str] = field(default_factory=list)
    serial: str | None = None
    marks: list[str] = field(default_factory=list)
    bad: bool = False
    good: bool = False

    @property
    def region_tags(self) -> list[str]:
        return [t for t in self.tags if t.strip().lower() in _REGION_TAGS]

    @property
    def disc_tags(self) -> list[str]:
        out = []
        for tag in self.tags:
            low = tag.strip().lower()
            if any(low.startswith(d) for d in _DISC_TAGS):
                out.append(tag)
        return out

    @property
    def other_tags(self) -> list[str]:
        """Etiquetas que no son region ni disco (traducciones, demo, proto...)."""
        regions = {t.strip().lower() for t in self.region_tags}
        discs = {t.strip().lower() for t in self.disc_tags}
        return [t for t in self.tags
                if t.strip().lower() not in regions and t.strip().lower() not in discs]


def parse_dat_name(name: str) -> DatName:
    """Descompone el nombre de un DAT en titulo, etiquetas, serial y marcas.

    >>> p = parse_dat_name("Ridge Racer (USA) (Track 1) [SLUS-00237]")
    >>> p.title, p.tags, p.serial
    ('Ridge Racer', ['USA', 'Track 1'], 'SLUS-00237')
    """
    text = (name or "").strip()
    # La extension no es parte del titulo, pero ojo: un serial como
    # «SLUS_204.60» tampoco lo es y se queda.
    raiz, punto, sufijo = text.rpartition(".")
    if punto and raiz and sufijo.isalpha() and 1 <= len(sufijo) <= 4:
        text = raiz
    serial = None
    match = _SERIAL_RE.search(text)
    if match:
        serial = match.group(1)
        text = text[:match.start()] + text[match.end():]

    tags: list[str] = []
    for match in _TAG_RE.finditer(text):
        tags.append(match.group(1).strip())
    # Se quita el texto de las etiquetas, dejando el titulo.
    title = _TAG_RE.sub(" ", text)
    title = _SPACES_RE.sub(" ", title).strip(" -_")

    marks = [m.group(0) for m in _MARK_RE.finditer(text)]
    return DatName(
        title=title,
        tags=tags,
        serial=serial,
        marks=marks,
        bad=bool(_BAD_MARK_RE.search(text)),
        good=bool(_GOOD_MARK_RE.search(text)),
    )


def compose_name(title: str, tags: Sequence[str], serial: str | None,
                 ext: str = "", clone: str | None = None,
                 options: NamingOptions | None = None,
                 bad: bool = False, good: bool = False,
                 marks: Sequence[str] = ()) -> str:
    """Compone el nombre final a partir de sus piezas."""
    opts = options or NamingOptions()
    parts: list[str] = [sanitize_name(title)]

    for tag in tags:
        low = tag.strip().lower()
        is_region = low in _REGION_TAGS
        is_disc = any(low.startswith(d) for d in _DISC_TAGS)
        if is_region and not opts.region:
            continue
        if is_disc and not opts.disc:
            continue
        parts.append(f"({tag.strip()})")

    if clone and opts.clone:
        parts.append(f"({sanitize_name(clone)})")

    if opts.marks:
        for mark in marks:
            parts.append(mark)
        if not marks and bad:
            parts.append("[b]")
        elif not marks and good:
            parts.append("[!]")

    name = " ".join(p for p in parts if p)
    if serial and opts.serial:
        name = f"{name} [{serial.strip()}]"

    if opts.max_length and len(name) > opts.max_length:
        name = name[:opts.max_length].rstrip(" -_[")

    if ext:
        if not ext.startswith("."):
            ext = "." + ext
        name += ext.lower()
    return name


def sanitize_name(name: str) -> str:
    """Quita lo que un fichero no admite y normaliza espacios."""
    text = unicodedata.normalize("NFC", name or "")
    text = _ILLEGAL_RE.sub("", text)
    text = text.replace("", "")
    text = _SPACES_RE.sub(" ", text).strip(" .")
    return text


def target_name(entry: dict, ext: str = "", options: NamingOptions | None = None,
                disc: int | None = None) -> str:
    """Nombre destino de una entrada del DAT.

    ``entry`` es un diccionario tal y como lo produce :func:`romtools.dats.parse_dat`:
    con ``name``, ``description``, ``cloneof`` y ``roms``.
    """
    opts = options or NamingOptions()
    parsed = parse_dat_name(entry.get("name") or entry.get("description") or "")

    title = parsed.title or (entry.get("description") or "").strip()
    tags = list(parsed.tags)

    # El DAT puede no traer el numero de disco (solo un <rom> por juego): si el
    # usuario ha indicado de que disco se trata, se anade.
    if disc and not parsed.disc_tags:
        tags.append(f"Disc {disc}")

    clone = None
    if opts.clone and entry.get("cloneof"):
        clone = parse_dat_name(entry.get("cloneof") or "").title or entry.get("cloneof")

    return compose_name(title, tags, parsed.serial, ext, clone=clone, options=opts,
                        bad=parsed.bad, good=parsed.good, marks=parsed.marks)


def rom_target_name(entry: dict, filename: str,
                    options: NamingOptions | None = None) -> str:
    """El nombre destino segun el DAT: el del fichero que corresponde.

    Un DAT trae el nombre exacto de cada fichero (``<rom name="...">``), y ese
    es el nombre que hay que poner: incluye el numero de pista, el serial y
    las marcas de volcado. Si no hay ningun ROM que encaje con la extension
    del fichero, se compone el nombre a partir del juego.
    """
    ext = os.path.splitext(filename)[1].lower()
    stem = os.path.splitext(os.path.basename(filename))[0]
    backup = None
    for rom in entry.get("roms", []):
        name = rom.get("name") or ""
        if not name:
            continue
        if os.path.splitext(name)[1].lower() != ext:
            continue
        if os.path.splitext(os.path.basename(name))[0] == stem:
            return name
        if backup is None:
            backup = name
    if backup and os.path.splitext(backup)[1].lower() == ext:
        return backup
    # El DAT no trae ningun fichero con esta extension (un volcado de Wii
    # frente a la ISO que tiene el DAT): se compone el nombre con la del
    # DAT y se deja la extension del fichero que hay.
    return target_name(entry, ext, options)


#: El sufijo con el codigo del disco que llevan las carpetas de Wii.
_CODE_SUFFIX_RE = re.compile(r"\s*\[([A-Za-z0-9_.-]+)\]\s*$")


def folder_target_name(entry: dict, folder_name: str, ext: str = "",
                       options: NamingOptions | None = None) -> str:
    """El nombre destino de la carpeta de un juego.

    Los juegos de Wii viven en una carpeta (``Juego [REXP01]``) con el
    volcado dentro. El nombre lo da el DAT, pero la carpeta conserva el
    sufijo con el codigo del disco, que es como los guarda Batocera.
    """
    base = target_name(entry, "", options)
    match = _CODE_SUFFIX_RE.search(folder_name or "")
    if match:
        base = f"{base} [{match.group(1)}]"
    if ext:
        base += ext if ext.startswith(".") else "." + ext
    return base


def fallback_name(filename: str, options: NamingOptions | None = None,
                  disc: int | None = None) -> str:
    """Nombre destino cuando no hay DAT: el del fichero, ordenado.

    Se separan las etiquetas, el serial y las marcas, y se recomponen con el
    mismo orden que usa el DAT: titulo, etiquetas, serial.
    """
    opts = options or NamingOptions()
    base = os.path.basename(filename or "")
    stem, ext = os.path.splitext(base)
    parsed = parse_dat_name(stem)

    title = parsed.title or stem
    tags = list(parsed.tags)
    if disc and not parsed.disc_tags:
        tags.append(f"Disc {disc}")
    return compose_name(title, tags, parsed.serial, ext, options=opts,
                        bad=parsed.bad, good=parsed.good, marks=parsed.marks)


def unique_path(directory: str, filename: str, taken: Iterable[str] = ()) -> str:
    """Devuelve un nombre que no pise nada en ``directory``."""
    used = {t.lower() for t in taken}
    stem, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while (candidate.lower() in used) or os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{stem} ({counter}){ext}"
        counter += 1
        if counter > 999:  # pragma: no cover - salvaguarda
            break
    return candidate
