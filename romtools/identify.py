"""Identificacion de ROMs: hashes, firmas de disco y heuristicas de titulo.

Una ROM se puede identificar de tres maneras, de mas fiable a menos:

1. **Hash**: el DAT trae md5, sha1 y crc32 de cada fichero. Si el hash
   coincide, es el juego: no hay duda.
2. **Firma de disco**: los discos de consola llevan su identificador dentro
   (PS1 ``SLUS_010.10``, PS2 ``SLUS-204.60``, Saturn ``SLUS_000.00``, GameCube
   ``GALE01``, Wii ``RVL-RZ4E``, Sega CD ``T-503 8914``, Xbox ``XE-1234``). Es
   lo que se usa cuando el hash no cuadra porque la imagen se ha reescrito.
3. **Titulo**: se compara el nombre del fichero con los titulos del DAT. Es
   una heuristica: por eso devuelve candidatos con su confianza y nunca
   renombra por debajo del umbral que se le pida.

Las firmas se leen de la cabecera con los offsets de cada formato. Los offsets
son un hecho del formato, no una implementacion: se pueden comprobar con
cualquier volcado de disco.
"""

from __future__ import annotations

import hashlib
import os
import re
import unicodedata
import zlib
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Sequence

# ── Firmas de cada formato ──────────────────────────────────────────────

#: GameCube: numero magico de 32 bits en 0x1C.
_GC_MAGIC = 0xC2339F3D
#: Wii: numero magico de 32 bits en 0x18.
_WII_MAGIC = 0x5D1C9EA3
#: Saturn: la cabecera lleva el nombre del sistema.
_SATURN_MAGICS = (b"SEGA SEGASATURN", b"SEGA SATURN ")
#: Sega CD.
_SEGACD_MAGICS = (b"SEGADISCSYSTEM", b"SEGA_CD")
#: Xbox: el volumen lleva el magic del formato XDVDF.
_XBOX_MAGIC = b"MICROSOFT*XBOX*MEDIA"
#: PlayStation: la ISO lleva la cadena de identificacion.
_PS_MAGICS = (b"PLAYSTATION", b"PlayStation")

#: Serial de PS1/PS2/Saturn: ``SLUS_010.10``, ``SLES-022.41``, ``SLUS-204.60``.
_SERIAL_SCAN_RE = re.compile(rb"\b([A-Z]{2,5}[_-]\d{3,5}[._]\d{2})\b")
#: Identificador de disco de Sega CD: ``T-503 8914  J``.
_SEGACD_ID_RE = re.compile(rb"\b([A-Z]{1,2}-\d{3} ?\d{4} ?[A-Z ]{0,3})\b")
#: Identificador de medio de Xbox: ``XE-1234``.
_XBOX_ID_RE = re.compile(rb"\b(X[A-Z]-\d{4})\b")
#: Codigo de juego de GameCube/Wii (4 caracteres) y fabricante (2).
_GAMECODE_RE = re.compile(rb"^([A-Z0-9]{4})([A-Z0-9]{2})")
#: Las etiquetas entre parentesis: region, idioma, ano, casa, marcas.
_TAG_STRIP_RE = re.compile(r"\([^()]*\)")

#: Sector donde vive el descriptor de volumen ISO 9660.
_ISO_VD_OFFSET = 0x8000
#: Ventana donde PS2/PS1 colocan su identificacion.
_PS_WINDOW = (0x8000, 0x8800)


def hash_file(path: str, algorithms: Sequence[str] = ("md5", "sha1", "crc32")) -> dict:
    """Calcula los hashes de un fichero (en un solo paso de lectura)."""
    wanted = {a.lower() for a in algorithms}
    digests = {a: hashlib.new(a) for a in wanted if a in ("md5", "sha1", "sha256")}
    crc = 0
    size = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            for dig in digests.values():
                dig.update(chunk)
            if "crc32" in wanted:
                crc = zlib.crc32(chunk, crc)
    out = {"size": size}
    for name, dig in digests.items():
        out[name] = dig.hexdigest()
    if "crc32" in wanted:
        out["crc32"] = f"{crc & 0xFFFFFFFF:08X}"
    return out


def _read_head(path: str, size: int = 0x40000) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read(size)
    except OSError:
        return b""


def normalize_title(text: str) -> str:
    """Normaliza un titulo para poder compararlo con otro.

    Quita acentos, pasa a minusculas, deja solo letras y digitos y colapsa los
    espacios.
    """
    raw = unicodedata.normalize("NFKD", text or "")
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s{2,}", " ", raw).strip()


def bare_title(text: str) -> str:
    """El titulo sin las etiquetas entre parentesis."""
    return normalize_title(_TAG_STRIP_RE.sub(" ", text or ""))


def title_similarity(a: str, b: str) -> float:
    """Similitud entre dos titulos, de 0 a 1.

    Se mezcla la similitud de secuencias (caracteres) con la de palabras: dos
    titulos largos se parecen mucho en caracteres, y por eso el juego de
    palabras es el que decide.
    """
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    words_a = set(na.split())
    words_b = set(nb.split())
    if not words_a or not words_b:
        return ratio
    inter = len(words_a & words_b)
    jaccard = inter / len(words_a | words_b)
    key_a = {w for w in words_a if len(w) > 3}
    key_b = {w for w in words_b if len(w) > 3}
    keys = (len(key_a & key_b) / len(key_a | key_b)) if (key_a and key_b) else 0.0
    return min(1.0, 0.45 * ratio + 0.25 * jaccard + 0.30 * keys)


def detect_platform(path: str, head: bytes | None = None) -> str | None:
    """De que plataforma es la imagen, leyendo su cabecera.

    Devuelve ``ps1``, ``ps2``, ``gc``, ``wii``, ``saturn``, ``segacd``,
    ``xbox`` o ``None`` si no se reconoce.
    """
    if head is None:
        head = _read_head(path)
    if not head:
        return None

    if _XBOX_MAGIC in head:
        return "xbox"

    if len(head) >= 0x20:
        if int.from_bytes(head[0x1C:0x20], "big") == _GC_MAGIC:
            return "gc"
        if int.from_bytes(head[0x18:0x1C], "big") == _WII_MAGIC:
            return "wii"

    if len(head) >= 0x20:
        for magic in _SATURN_MAGICS:
            if head[0x00:0x20].find(magic) >= 0:
                return "saturn"
        for magic in _SEGACD_MAGICS:
            if head[0x00:0x20].find(magic) >= 0:
                return "segacd"

    window = head[_PS_WINDOW[0]:_PS_WINDOW[1]]
    if any(magic in window for magic in _PS_MAGICS):
        return "ps2"
    if any(magic in head[:0x10000] for magic in _PS_MAGICS):
        return "ps1"

    # El volumen ISO 9660 con un identificador de PS2 delata la plataforma.
    if len(head) > _ISO_VD_OFFSET + 40 and head[_ISO_VD_OFFSET + 1:_ISO_VD_OFFSET + 6] == b"CD001":
        volume = _volume_id(head)
        if volume and re.match(r"^[A-Z]{2,5}[_-]\d{3,5}[._]\d{2}", volume):
            return "ps2"
    return None


@dataclass
class DiscSignature:
    """Lo que se ha podido leer de dentro de una imagen de disco."""

    platform: str | None = None
    serial: str | None = None
    game_code: str | None = None
    maker_code: str | None = None
    disc_number: int | None = None
    media_id: str | None = None
    volume_id: str | None = None
    disc_id: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def is_empty(self) -> bool:
        return not any(self.__dict__.values())


def disc_signature(path: str, head: bytes | None = None) -> DiscSignature:
    """Lee la firma de una imagen de disco.

    No lanza: si el fichero no se puede leer, devuelve la firma vacia. Cada
    detector es independiente, de forma que una imagen puede dar varias pistas
    a la vez (un ISO de PS2 da el volumen y el serial).
    """
    sig = DiscSignature()
    if head is None:
        head = _read_head(path)
    if not head:
        return sig

    platform = detect_platform(path, head)
    sig.platform = platform

    # ── GameCube y Wii: codigo de juego y fabricante en la cabecera ──
    if platform in ("gc", "wii"):
        match = _GAMECODE_RE.match(head[:6])
        if match:
            sig.game_code = match.group(1).decode("ascii", "replace")
            sig.maker_code = match.group(2).decode("ascii", "replace")
            sig.disc_number = head[6] or None
        if platform == "wii":
            # El identificador de disco de Wii es RVL-xxx (o RVL-RZZE...).
            match = re.search(rb"(RVL-[A-Z0-9]{3,4})", head[:0x4000])
            if match:
                sig.serial = match.group(1).decode("ascii", "replace")
        return sig

    # ── Xbox: identificador de medio ──
    if platform == "xbox":
        match = _XBOX_ID_RE.search(head)
        if match:
            sig.media_id = match.group(1).decode("ascii", "replace")
        volume = _volume_id(head)
        if volume:
            sig.volume_id = volume
        return sig

    # ── Sega CD: identificador de disco ──
    if platform == "segacd":
        match = _SEGACD_ID_RE.search(head[:0x2000])
        if match:
            sig.disc_id = " ".join(match.group(1).decode("ascii", "replace").split())
        return sig

    # ── ISO 9660: identificador de volumen ──
    if len(head) > _ISO_VD_OFFSET + 40 and head[_ISO_VD_OFFSET + 1:_ISO_VD_OFFSET + 6] == b"CD001":
        volume = _volume_id(head)
        if volume:
            sig.volume_id = volume
            match = _SERIAL_SCAN_RE.search(volume.encode("ascii", "replace"))
            if match:
                sig.serial = match.group(1).decode("ascii", "replace")
                if not platform:
                    sig.platform = "ps2"
        return sig

    # ── PS1 y Saturn en bruto (2352 bytes por sector) ──
    match = _SERIAL_SCAN_RE.search(head)
    if match:
        sig.serial = match.group(1).decode("ascii", "replace")
        if not platform:
            sig.platform = "ps1"
    return sig


def _volume_id(head: bytes) -> str | None:
    """Identificador de volumen de un ISO 9660 (offset 0x8028, 32 bytes)."""
    start = _ISO_VD_OFFSET + 0x28
    if len(head) < start + 32:
        return None
    raw = head[start:start + 32].split(b"\x00")[0]
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    return text or None


@dataclass
class Match:
    """Resultado de identificar una ROM contra un DAT."""

    path: str
    method: str = "none"
    confidence: float = 0.0
    entry: dict | None = None
    title: str | None = None
    serial: str | None = None
    signature: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)
    note: str = ""

    @property
    def matched(self) -> bool:
        return self.entry is not None

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "method": self.method,
            "confidence": round(self.confidence, 3),
            "entry": self.entry,
            "title": self.title,
            "serial": self.serial,
            "signature": self.signature,
            "candidates": self.candidates,
            "note": self.note,
            "matched": self.matched,
        }


def match_by_hash(index: dict, hashes: dict) -> dict | None:
    """Busca en el indice del DAT una entrada con estos hashes."""
    for key in ("sha1", "md5", "crc32"):
        value = hashes.get(key) or ""
        if not value:
            continue
        value = value.upper() if key == "crc32" else value.lower()
        found = index.get("by_hash", {}).get(f"{key}:{value}")
        if found:
            return found
    return None


def match_by_serial(index: dict, serial: str | None) -> dict | None:
    """Busca la entrada cuyo nombre de DAT lleva ese serial."""
    if not serial:
        return None
    needle = serial.strip().upper()
    for key in (needle, needle.replace("_", "-"), needle.replace("-", "_")):
        found = index.get("by_serial", {}).get(key)
        if found:
            return found
    return None


def match_by_name(index: dict, filename: str, size: int | None = None) -> dict | None:
    """Busca la entrada cuyo fichero se llama como el nuestro.

    El DAT trae el nombre exacto de cada fichero y su tamano: si los dos
    cuadran, es el mismo juego sin necesidad de hashear el fichero entero
    (que en una biblioteca de 40 GB seria eterno).
    """
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    key = normalize_title(stem)
    if not key:
        return None
    found = index.get("by_name", {}).get(key)
    if not found:
        return None
    expected = index.get("by_name_size", {}).get(key)
    if size is not None and expected and expected != size:
        # Mismo nombre, otro tamano: es otra version del juego.
        return None
    return found


def match_by_title(index: dict, title: str, limit: int = 5,
                   threshold: float = 0.55) -> list:
    """Candidatos por titulo, de mas parecido a menos.

    El indice trae ``by_title`` con las entradas agrupadas por titulo
    normalizado: solo se comparan las que comparten palabras, que es donde
    estan las coincidencias de verdad.
    """
    if not title:
        return []
    words = {w for w in normalize_title(title).split() if len(w) > 2}
    if not words:
        return []
    by_title = index.get("by_title", {})
    scored = []
    for key, entries in by_title.items():
        key_words = {w for w in key.split() if len(w) > 2}
        if not key_words:
            continue
        if not (words & key_words):
            continue
        for entry in entries:
            descripcion = entry.get("description") or entry.get("name") or ""
            score = title_similarity(title, descripcion)
            # Sin las etiquetas: dos bibliotecas pueden nombrar el mismo juego
            # de forma distinta («Juego (1995) (US)» frente a «Juego (USA)»).
            pelado = title_similarity(bare_title(title), bare_title(descripcion))
            if pelado > score:
                score = pelado
            if score >= threshold:
                scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"entry": e, "score": round(s, 3)} for s, e in scored[:limit]]


def identify(path: str, index: dict | None, title_hint: str | None = None,
             head: bytes | None = None, hash_allowed: bool = True) -> Match:
    """Identifica una ROM contra el indice de un DAT.

    ``hash_allowed`` permite saltarse el calculo de hashes (que obliga a
    leer el fichero entero) cuando la biblioteca es muy grande.
    """
    match = Match(path=path)
    if not index:
        match.note = "no hay DAT cargado para este sistema"
        return match

    try:
        size = os.path.getsize(path)
    except OSError:
        size = None
    match.signature = {"size": size}

    # 1 · Por nombre y tamano: no toca el disco y es lo que mas se da.
    found = match_by_name(index, path, size)
    if found:
        match.method = "nombre"
        match.confidence = 0.95
        match.entry = found
        match.title = found.get("description") or found.get("name")
        match.note = "el nombre y el tamano coinciden con los del DAT"
        return match

    # 2 · Por hash: es la prueba definitiva, pero hay que leer el fichero
    #     entero, asi que solo se hace si el nombre no cuadra y hay presupuesto.
    if hash_allowed:
        hashes = hash_file(path)
        match.signature["hashes"] = hashes
        found = match_by_hash(index, hashes)
        if found:
            match.method = "hash"
            match.confidence = 1.0
            match.entry = found
            match.title = found.get("description") or found.get("name")
            match.serial = found.get("serial")
            return match

    # 3 · Por el serial del disco.
    signature = disc_signature(path, head=head)
    match.signature.update(signature.as_dict())
    found = match_by_serial(index, signature.serial)
    if found:
        match.method = "serial"
        match.confidence = 0.9
        match.entry = found
        match.title = found.get("description") or found.get("name")
        match.serial = signature.serial
        return match

    # 4 · Por titulo: es una heuristica y se marca como tal.
    hint = title_hint or os.path.basename(path)
    candidates = match_by_title(index, hint)
    match.candidates = candidates
    if candidates:
        best = candidates[0]
        match.method = "titulo"
        match.confidence = best["score"]
        match.entry = best["entry"]
        match.title = best["entry"].get("description") or best["entry"].get("name")
        if match.confidence < 0.7:
            match.note = "coincidencia por titulo: conviene revisarla"
    else:
        match.note = "no se ha encontrado en el DAT"
    return match
