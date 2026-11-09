"""Formatos de ROM: deteccion, conversion, compresion y parcheo.

Todo se hace con la biblioteca estandar de Python: la consola no tiene
herramientas de linea de comandos y no se puede depender de chdman, xiso o
cualquier otro binario externo.

Lo que se sabe hacer:

============  ==========================================================
Formato       Operacion
============  ==========================================================
BIN + CUE     deteccion, ISO -> BIN/CUE, BIN/CUE -> ISO, -> PBP
ISO           deteccion, -> BIN/CUE, extraccion del identificador
PBP (PS1)     deteccion, -> BIN/CUE, BIN/CUE -> PBP
XDVDF (Xbox)  deteccion, -> ISO
GCM (GameCube) deteccion, -> ISO (GCISO)
CHD           deteccion (cabecera y pistas), -> ISO (v5 con zlib)
WBFS (Wii)    deteccion y ficha del disco (codigo RVL-xxx)
MDF/CCD/IMG   deteccion (cabecera)
WIA / RVZ     deteccion (cabecera)
3DO / G64     deteccion
IPS           aplicacion de parches (con copia del original)
ZIP           creacion (compresion)
============  ==========================================================

Las limitaciones van dichas: una conversion que no se puede hacer con la
biblioteca estandar se detecta y se explica, pero no se simula.
"""

from __future__ import annotations

import gzip
import itertools
import os
import re
import shutil
import struct
import subprocess
import zipfile
import zlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable

# ── Constantes ──────────────────────────────────────────────────────────

SECTOR_RAW = 2352
SECTOR_ISO = 2048

#: Firma de un sector CD-ROM (MODE1): 12 bytes de sincronizacion + 4 de cabecera.
_CD_SYNC = b"\x00" * 12 + b"\x01\x00\x00\x00"


@dataclass
class FormatInfo:
    """Lo que se sabe de un fichero: que formato es y que se puede hacer."""

    path: str
    kind: str = "desconocido"
    label: str = "Desconocido"
    size: int = 0
    details: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "file": os.path.basename(self.path),
            "kind": self.kind,
            "label": self.label,
            "size": self.size,
            "details": self.details,
            "actions": self.actions,
        }


#: Cada conversion posible: su identificador, el texto del boton y la
#: explicacion. El backend devuelve estos identificadores y el frontend los
#: pinta: no se comparan etiquetas de texto.
CAPACIDADES = {
    "iso": {"label": "ISO", "ayuda": "imagen de 2048 bytes por sector"},
    "bin-cue": {"label": "BIN + CUE", "ayuda": "imagen original de 2352 bytes"},
    "pbp": {"label": "PBP", "ayuda": "formato de PlayStation"},
    "chd": {"label": "CHD", "ayuda": "imagen comprimida: ocupa menos"},
    "cso": {"label": "CSO", "ayuda": "ISO comprimida"},
    "gcz": {"label": "GCZ", "ayuda": "ISO de GameCube comprimida"},
    "ciso": {"label": "CISO", "ayuda": "ISO comprimida"},
    "rvz": {"label": "RVZ", "ayuda": "imagen de Dolphin"},
    "wia": {"label": "WIA", "ayuda": "imagen de Wii"},
    "wbfs": {"label": "WBFS", "ayuda": "particion de Wii"},
    "nsp": {"label": "NSP", "ayuda": "paquete de Nintendo Switch"},
    "xci": {"label": "XCI", "ayuda": "cartucho de Nintendo Switch"},
    "n64": {"label": "N64", "ayuda": "big endian"},
    "z64": {"label": "Z64", "ayuda": "little endian"},
    "v64": {"label": "V64", "ayuda": "byte swapped"},
    "sfc": {"label": "SFC", "ayuda": "super nintendo sin cabecera"},
    "smc": {"label": "SMC", "ayuda": "super nintendo con cabecera"},
    "fig": {"label": "FIG", "ayuda": "super nintendo con cabecera de 512 bytes"},
    "zip": {"label": "ZIP", "ayuda": "comprimido en ZIP"},
    "7z": {"label": "7Z", "ayuda": "comprimido en 7Z (squeeza mas que el ZIP)"},
    "extraer": {"label": "Extraer", "ayuda": "descomprimir en una carpeta al lado"},
    "gcm": {"label": "GCM", "ayuda": "imagen de GameCube"},
    "xiso": {"label": "XISO", "ayuda": "imagen de Xbox"},
}

#: Como se llama cada formato y a que se puede convertir.
#:
#: Aqui solo van los **candidatos**: que se puede sacar de un fichero de este
#: tipo. Lo que el sistema admite lo filtra despues otro modulo
#: (``romtools.formatos_sistemas``), que es quien sabe si un PSP admite un
#: ZIP o si un GameCube admite un CHD. Por eso el catalogo puede ser
#: generico: no hace falta que sepa de que consola se trata.
FORMAT_CATALOGUE = {
    "bin-cue": ("BIN + CUE", ["iso", "pbp", "chd", "zip", "7z"]),
    "iso": ("ISO 9660", ["bin-cue", "chd", "cso", "gcz", "ciso", "pbp", "zip", "7z"]),
    "iso-gamecube": ("ISO de GameCube", ["gcz", "ciso", "rvz", "wbfs", "chd", "zip", "7z"]),
    "iso-wii": ("ISO de Wii", ["rvz", "wbfs", "ciso", "chd", "zip", "7z"]),
    "iso-ps1": ("ISO de PlayStation", ["bin-cue", "pbp", "chd", "zip", "7z"]),
    "iso-ps2": ("ISO de PlayStation 2", ["chd", "cso", "zip", "7z"]),
    "pbp": ("PBP (PlayStation)", ["bin-cue", "iso", "zip", "7z"]),
    "chd": ("CHD (imagen comprimida)", ["iso", "bin-cue"]),
    "gcm": ("GCM (GameCube)", ["iso", "zip", "7z"]),
    "xiso": ("XDVDF (Xbox)", ["iso", "zip", "7z"]),
    "cso": ("CSO (PSP)", ["iso", "zip", "7z"]),
    "gcz": ("GCZ (GameCube)", ["iso", "zip", "7z"]),
    "ciso": ("CISO (GameCube o Wii)", ["iso", "zip", "7z"]),
    "rvz": ("RVZ (Dolphin)", []),
    "wia": ("WIA (Wii)", []),
    "wbfs": ("WBFS (Wii)", []),
    "mdf": ("MDF / CCD / IMG / MDS", ["iso"]),
    "gdi": ("GDI (Dreamcast)", ["iso"]),
    # El CDI es un contenedor binario del que no se sabe leer la sesion:
    # no se ofrece conversion en vez de ofrecer una que falla.
    "cdi": ("CDI (DiscJuggler)", []),
    "nrg": ("NRG (Nero)", ["iso"]),
    "g64": ("G64 / NDD", []),
    "n64-z64": ("Nintendo 64 (little endian)", ["n64", "v64", "zip", "7z"]),
    "n64-n64": ("Nintendo 64 (big endian)", ["z64", "v64", "zip", "7z"]),
    "n64-v64": ("Nintendo 64 (byte swapped)", ["z64", "n64", "zip", "7z"]),
    "snes-smc": ("Super Nintendo (con cabecera)", ["sfc", "fig", "zip", "7z"]),
    "snes-sfc": ("Super Nintendo (sin cabecera)", ["smc", "fig", "zip", "7z"]),
    "snes-fig": ("Super Nintendo (FIG)", ["sfc", "smc", "zip", "7z"]),
    "megadrive": ("Mega Drive", ["zip", "7z"]),
    "3do-iso": ("3DO", ["zip", "7z"]),
    "nesica": ("Nesica (arcade)", []),
    "atari8": ("Atari 8-bit", []),
    "pcengine-rom": ("PC Engine (rom)", []),
    "wad": ("WAD (Nintendo DS)", []),
    "nsp": ("NSP (Nintendo Switch)", []),
    "xci": ("XCI (Nintendo Switch)", []),
    "3ds": ("Nintendo 3DS", []),
    "zip": ("ZIP", ["extraer"]),
    "7z": ("7Z", ["extraer"]),
    "ips": ("Parche IPS", []),
    "bps": ("Parche BPS", []),
    "desconocido": ("Formato no reconocido", []),
}

#: Formatos que se pueden convertir a ISO.
CONVERTIBLE_TO_ISO = ("bin-cue", "iso", "iso-gamecube", "iso-wii", "iso-ps1",
                      "iso-ps2", "pbp", "xiso", "gcm", "chd", "cso", "gcz",
                      "ciso", "gdi", "mdf", "cdi", "nrg")


def acciones_de(info) -> list:
    """Las conversiones que admite un fichero, ya en forma de botones.

    Devuelve una lista de ``{"id", "label", "nota"}``. Si esta vacia, el
    fichero no se puede convertir: el frontend lo dice en vez de dejar un
    hueco.
    """
    datos = FORMAT_CATALOGUE.get(info.kind)
    if not datos:
        return []
    out = []
    for id_accion in datos[1]:
        cap = CAPACIDADES.get(id_accion)
        if not cap:
            continue
        out.append({"id": id_accion, "label": cap["label"],
                    "nota": cap["ayuda"]})
    return out


# ── Deteccion ───────────────────────────────────────────────────────────

def _size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _head(path: str, size: int = 64) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read(size)
    except OSError:
        return b""


def _cola(path: str, size: int = 16) -> bytes:
    """Los ultimos bytes del fichero.

    Hay formatos que llevan su firma al final (el NRG de Nero, por ejemplo).
    """
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            total = fh.tell()
            fh.seek(max(total - size, 0))
            return fh.read()
    except OSError:
        return b""


def detect_format(path: str, sistema: str | None = None) -> FormatInfo:
    """Detecta el formato de un fichero de ROM.

    Se mira la cabecera primero (que no miente) y la extension despues. El
    ``sistema`` es el slug de Batocera: sirve de pista, no de veredicto, porque
    hay ficheros con la extension cambiada.
    """
    path = os.path.abspath(path)
    size = _size(path)
    ext = os.path.splitext(path)[1].lower()
    info = FormatInfo(path=path, size=size)
    head = _head(path, 0x100)

    def puesto(kind, **detalles):
        """Asigna el formato y sus capacidades."""
        datos = FORMAT_CATALOGUE.get(kind, ("Desconocido", []))
        info.kind = kind
        info.label = datos[0]
        info.details = detalles
        info.actions = acciones_de(info)
        return info

    # ── 1 · Firmas de disco ──────────────────────────────────────────────
    if head.startswith(b"MComprHD"):
        return puesto("chd", **_chd_header(path))

    # El NRG de Nero lleva su firma al final del fichero (el pie dice donde
    # empieza la cadena de chunks), pero algunos volcados la poner delante.
    # Solo se mira el pie en los ficheros que podrian ser un disco.
    if head.startswith(b"NERO") or head.startswith(b"NER5"):
        return puesto("nrg")
    if ext in (".iso", ".bin", ".img", ".mdf", ".mds", ".ccd") and _firma_nrg(path):
        return puesto("nrg")

    if head.startswith(b"WBFS"):
        return puesto("wbfs", **_wbfs_header(path))

    if head.startswith(b"WIA\x00"):
        return puesto("wia")

    if head.startswith(b"RVZ\x00"):
        return puesto("rvz")

    if head.startswith(b"PBP\x01"):
        return puesto("pbp", **_pbp_header(path))

    if head.startswith(b"MICROSOFT*XBOX*MEDIA") or b"XBOXMEDIA" in head[:0x10000]:
        return puesto("xiso")

    if head[:4] == b"\x01\xc0\x0b\xb1":
        return puesto("gcz")

    if head.startswith(b"CISO"):
        return puesto("ciso")

    if head.startswith(b"CSO!"):
        return puesto("cso")

    if head.startswith(b"WUX0") or head.startswith(b"WUD0"):
        return puesto("wbfs")

    if head.startswith(b"PFS0"):
        return puesto("nsp")

    if head.startswith(b"XCIH"):
        return puesto("xci")

    if head.startswith(b"NCSD") or head.startswith(b"NCCH"):
        return puesto("3ds")

    if head.startswith(b"NCSD") or head[:2] == b"\x00\x00" and ext == ".cia":
        return puesto("3ds")

    # Nintendo 64: el byte order se ve en la magia, no en el nombre. Hay
    # volcados que se llaman .v64 y estan en big endian (y al reves).
    if head[:4] in (b"\x40\x12\x37\x80", b"\x80\x37\x12\x40", b"\x37\x80\x40\x12"):
        if head[:4] == b"\x80\x37\x12\x40":
            return puesto("n64-z64", orden="little endian")
        if head[:4] == b"\x40\x12\x37\x80":
            return puesto("n64-n64", orden="big endian")
        return puesto("n64-v64", orden="byte swapped")

    # 3DO: cabecera propia, con «CD-ROM» en el 0x28.
    if head[:7] == b"\x01ZZZZZ\x01" or head[0x28:0x34] == b"CD-ROM":
        return puesto("3do-iso", cabecera="3DO")

    # Super Nintendo y Mega Drive: la cabecera de copista tiene «aa bb» en el 8.
    if head[0x08:0x0A] == b"\xaa\xbb":
        if (head[0x0A] or 0) in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x0A, 0x0B):
            return puesto("snes-smc", cabecera=512)
        return puesto("megadrive", cabecera=512)

    # ── 2 · Un CUE describe su BIN: se mira el binario, no el texto ───────
    if ext == ".cue":
        bin_path = _bin_for_cue(path)
        if bin_path:
            return puesto("bin-cue", bin=os.path.basename(bin_path),
                          cue=os.path.basename(path))

    # ── 3 · Imagen de disco: se mira de que consola es ─────────────────
    # Un ISO 9660 lleva su «CD001» en el sector 16, pero los discos de
    # GameCube y de Wii son imagenes propias sin descriptor de volumen: se
    # reconocen por la magia de la consola.
    if ext in (".iso", ".bin", ".img"):
        plataforma = _plataforma_iso(path)
        if plataforma or _looks_iso(path):
            detalles = {"plataforma": plataforma} if plataforma else {}
            if plataforma in (None, "ps1", "ps2"):
                detalles["volume_id"] = _iso_volume_id(path)
            if plataforma == "gamecube":
                return puesto("iso-gamecube", **detalles)
            if plataforma == "wii":
                return puesto("iso-wii", **detalles)
            if plataforma == "ps2":
                return puesto("iso-ps2", **detalles)
            if plataforma == "ps1":
                return puesto("iso-ps1", **detalles)
            return puesto("iso", **detalles)

    # ── 4 · Por extension ───────────────────────────────────────────────
    if ext == ".gcm":
        return puesto("gcm")

    if ext in (".gdi",):
        return puesto("gdi")

    if ext in (".cdi",):
        return puesto("cdi")

    if ext in (".mdf", ".img", ".ccd", ".mds"):
        return puesto("mdf")

    if ext == ".nrg":
        return puesto("nrg")

    if ext in (".g64", ".ndd"):
        return puesto("g64")

    if ext in (".3do", ".iso3"):
        return puesto("3do-iso", cabecera="3DO")

    if ext in (".nesica",):
        return puesto("nesica")

    if ext in (".atr", ".xex"):
        return puesto("atari8")

    if ext in (".pce",):
        return puesto("pcengine-rom")

    if ext in (".wad",):
        return puesto("wad")

    if ext in (".nsp",):
        return puesto("nsp")

    if ext in (".xci",):
        return puesto("xci")

    if ext in (".3ds", ".cci", ".cia", ".zcci"):
        return puesto("3ds")

    if ext in (".z64", ".n64", ".v64"):
        # Sin la magia (ficheros truncados o vacios): se fia de la extension.
        return puesto({"z64": "n64-z64", "n64": "n64-n64",
                       "v64": "n64-v64"}[ext[1:]], orden="por extension")

    if ext in (".smc", ".sfc", ".fig", ".swc"):
        if ext == ".fig":
            return puesto("snes-fig", cabecera=512)
        if ext == ".smc":
            return puesto("snes-smc", cabecera=512)
        # Un .sfc puede llevar cabecera de copista: se comprueba el «aa bb».
        if head[0x08:0x0A] == b"\xaa\xbb" or head[0x7FC0:0x7FC2] == b"\xaa\xbb" \
                or head[0xFFC0:0xFFC2] == b"\xaa\xbb":
            return puesto("snes-sfc", cabecera="sin cabecera de copista")
        return puesto("snes-sfc", cabecera="sin cabecera de copista")

    if ext in (".smd", ".md", ".gen", ".sgd", ".sg"):
        return puesto("megadrive")

    if ext == ".zip":
        return puesto("zip")
    if ext == ".7z":
        return puesto("7z")
    if ext in (".gz", ".rar", ".tar"):
        return puesto("desconocido", extension=ext)

    if ext == ".ips":
        return puesto("ips")
    if ext == ".bps":
        return puesto("bps")

    # Un .bin con CUE hermano es un set BIN+CUE completo.
    if ext == ".bin":
        cue = _cue_for_bin(path)
        if cue:
            return puesto("bin-cue", bin=os.path.basename(path),
                          cue=os.path.basename(cue))
        if size and size % SECTOR_RAW == 0:
            return puesto("bin-cue", sectores=size // SECTOR_RAW, cue=None)

    if ext == ".bin" and sistema == "megadrive":
        return puesto("megadrive")

    return puesto("desconocido", extension=ext)


def _plataforma_iso(path: str) -> str | None:
    """De que consola es un ISO 9660 (si se puede saber).

    Se mira la cabecera que cada consola pone en su sitio: GameCube y Wii
    tienen su magia, y PlayStation y PS2 se distinguen por el ``SYSTEM.CNF``
    (que dice ``BOOT`` o ``BOOT2``).
    """
    try:
        with open(path, "rb") as fh:
            fh.seek(0x1C)
            if fh.read(4) == b"\xc2\x33\x9f\x3d":
                return "gamecube"
            fh.seek(0x18)
            if fh.read(4) == b"\x5d\x1c\x9e\xa3":
                return "wii"
            fh.seek(0)
            head = fh.read(0x10000)
    except OSError:
        return None

    if b"BOOT2" in head:
        return "ps2"
    if b"BOOT=cdrom" in head or b"BOOT = cdrom" in head:
        return "ps1"
    return None


def _looks_iso(path: str) -> bool:
    """Un ISO tiene el magic «CD001» en el sector 16."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0x8000)
            return fh.read(6)[1:6] == b"CD001"
    except OSError:
        return False


def _iso_volume_id(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            fh.seek(0x8028)
            raw = fh.read(32).split(b"\x00")[0]
        return raw.decode("ascii", "replace").strip() or None
    except OSError:
        return None


def _bin_for_cue(cue_path: str) -> str | None:
    """El BIN que describe un CUE (ruta relativa al propio CUE)."""
    try:
        with open(cue_path, "r", encoding="latin-1", errors="replace") as fh:
            for line in fh:
                match = re.match(r'\s*FILE\s+"([^"]+)"', line, re.I)
                if match:
                    candidate = os.path.join(os.path.dirname(cue_path), match.group(1))
                    if os.path.isfile(candidate):
                        return candidate
    except OSError:
        return None
    return None


def _cue_for_bin(bin_path: str) -> str | None:
    """El CUE que describe un BIN.

    Primero se busca el CUE hermano (mismo nombre, extension ``.cue``). Si no
    esta, se recorre la carpeta buscando un CUE que mencione ese BIN, que es
    como vienen las colecciones de varios discos.
    """
    hermano = os.path.splitext(bin_path)[0] + ".cue"
    if os.path.isfile(hermano):
        return hermano
    carpeta = os.path.dirname(bin_path)
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        return None
    objetivo = os.path.abspath(bin_path)
    for nombre in nombres:
        if not nombre.lower().endswith(".cue"):
            continue
        candidato = os.path.join(carpeta, nombre)
        binario = _bin_for_cue(candidato)
        if binario and os.path.abspath(binario) == objetivo:
            return candidato
    return None


def _pbp_header(path: str) -> dict:
    """Cabecera PBP:Offsets de las cinco secciones."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(0x100)
    except OSError:
        return {}
    if len(data) < 0x10:
        return {}
    offsets = struct.unpack(">5I", data[4:0x18])
    return {"offsets": list(offsets), "size": _size(path)}


def _chd_header(path: str) -> dict:
    """Cabecera CHD (v1-v5).

    Los offsets son los de MAME: version en 0x08, compresion en 0x10, frames
    totales en 0x18, bytes por frame en 0x1C, hunks totales en 0x28 y los
    desplazamiento de datos, metadatos y mapa a partir de 0x50.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(128)
    except OSError:
        return {}
    if len(head) < 24 or not head.startswith(b"MComprHD"):
        return {}
    version, flags, compression = struct.unpack(">III", head[8:20])
    out = {"version": version, "compression": compression, "flags": flags}
    if len(head) >= 0x20:
        total_frames, bytes_per_frame = struct.unpack(">II", head[0x18:0x20])
        out["total_frames"] = total_frames
        out["bytes_per_frame"] = bytes_per_frame
        out["sectors"] = total_frames
    if len(head) >= 0x2C:
        frames_per_hunk, = struct.unpack(">I", head[0x20:0x24])
        out["frames_per_hunk"] = frames_per_hunk
    if len(head) >= 0x2C and version >= 5:
        total_hunks, = struct.unpack(">I", head[0x28:0x2C])
        out["total_hunks"] = total_hunks
    if len(head) >= 0x68 and version >= 5:
        data_offset, meta_offset, map_offset = struct.unpack(">QQQ", head[0x50:0x68])
        out["data_offset"] = data_offset
        out["meta_offset"] = meta_offset
        out["map_offset"] = map_offset
    return out


def _wbfs_header(path: str) -> dict:
    """Cabecera WBFS: se leen los metadatos de los discos."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(0x100)
    except OSError:
        return {}
    if len(head) < 0x40:
        return {}
    magic, version, disc_count, disc_size, split_size = struct.unpack(">4sIIIQ", head[0:0x18])
    chunk_size, padded_chunk_size = struct.unpack(">II", head[0x20:0x28])
    out = {
        "version": version,
        "discs": disc_count,
        "disc_size": disc_size,
        "split_size": split_size,
        "chunk_size": chunk_size,
    }
    # Los metadatos de disco estan a partir de 0x40: nombre, codigo, tipo...
    try:
        with open(path, "rb") as fh:
            fh.seek(0x40)
            meta = fh.read(0x60)
        name = meta[0:32].split(b"\x00")[0].decode("utf-8", "replace")
        disc_id = meta[0x40:0x46].split(b"\x00")[0].decode("ascii", "replace")
        if disc_id:
            out["disc_id"] = disc_id
        if name:
            out["title"] = name
    except OSError:
        pass
    return out


# ── CUE ─────────────────────────────────────────────────────────────────

_CUE_FILE_RE = re.compile(r'^\s*FILE\s+"?([^"\r\n]+)"?\s+(BINARY|MOTOROLA)', re.I)
_CUE_TRACK_RE = re.compile(r"^\s*TRACK\s+(\d+)\s+(MODE[12](?:/\d{4})?|AUDIO)", re.I)
_CUE_INDEX_RE = re.compile(r"^\s*INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)", re.I)


def parse_cue(cue_path: str) -> list:
    """Parsea un CUE y devuelve la lista de pistas."""
    tracks = []
    current = None
    with open(cue_path, "r", encoding="latin-1", errors="replace") as fh:
        for line in fh:
            match = _CUE_FILE_RE.match(line)
            if match:
                current = {"file": match.group(1), "tracks": []}
                tracks.append(current)
                continue
            match = _CUE_TRACK_RE.match(line)
            if match and current is not None:
                current["tracks"].append({
                    "number": int(match.group(1)),
                    "mode": match.group(2).upper(),
                    "index": [],
                })
                continue
            match = _CUE_INDEX_RE.match(line)
            if match and current is not None and current["tracks"]:
                current["tracks"][-1]["index"].append({
                    "index": int(match.group(1)),
                    "sector": int(match.group(2)) * 60 * 75 + int(match.group(3)) * 75 + int(match.group(4)),
                })
    return tracks


def _sector_to_user_data(sector: bytes) -> bytes | None:
    """Saca los datos de usuario de un sector de 2352 bytes."""
    if len(sector) < SECTOR_RAW:
        return None
    mode = sector[15]
    if mode == 1:
        return sector[16:16 + SECTOR_ISO]
    if mode == 2:
        form = sector[18] >> 2
        if form == 1:
            return sector[24:24 + SECTOR_ISO]
        return None  # Mode 2 Form 2 (XA): 2324 bytes, no cabe en un ISO
    return None


def _user_to_sector(data: bytes, sector: bytes | None = None) -> bytes:
    """Envuelve los datos de usuario en un sector de 2352 bytes (MODE1)."""
    out = bytearray(SECTOR_RAW)
    out[0:12] = _CD_SYNC[0:12]
    out[12:15] = b"\x01\x00\x00"
    out[15] = 0x01
    out[16:16 + len(data)] = data
    if sector is not None and len(sector) >= 16:
        out[12:15] = sector[12:15]
    return bytes(out)


# ── ISO 9660 ────────────────────────────────────────────────────────────

def _both_endian32(value: int) -> bytes:
    return struct.pack("<I", value) + struct.pack(">I", value)


def _both_endian16(value: int) -> bytes:
    return struct.pack("<H", value) + struct.pack(">H", value)


def _str_field(text: str, size: int) -> bytes:
    raw = (text or "").encode("ascii", "replace")[:size]
    return raw.ljust(size, b" ")


def _root_record(lba: int, size: int) -> bytes:
    """El registro de directorio raiz (34 bytes mas el identificador)."""
    record = bytearray(34)
    record[0] = 38            # longitud del registro
    record[1] = 0             # atributos extendidos
    record[2:10] = struct.pack("<II", lba, lba)
    record[10:18] = struct.pack("<II", size, size)
    record[18:25] = b"1970" + b"01" + b"01"   # fecha
    record[25] = 0x02         # es un directorio
    record[26] = 0            # tamano de unidad
    record[27] = 0            # salto
    record[28:32] = struct.pack("<HH", 1, 1)
    record[32] = 5            # longitud del identificador
    record[33:38] = b"ROOT\x00"
    return bytes(record)


def _iso_esqueleto(volume_id: str, total_data: int) -> bytes:
    """El esqueleto de un ISO 9660: area de sistema, PVD, tablas y raiz.

    Es el mismo esqueleto que usan las herramientas de conversion clasicas:
    area de sistema, descriptor de volumen, tabla de rutas, directorio raiz y
    los datos (que van aparte, para no tenerlos en memoria).
    """
    lba_pvd = 16
    lba_term = 17
    lba_path_l = 18
    lba_path_m = 19
    lba_root = 20
    lba_data = 21
    total_sectors = lba_data + total_data

    # ── Descriptor de volumen primario ──
    pvd = bytearray(SECTOR_ISO)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[6] = 1
    pvd[8:40] = _str_field("LINUX", 32)
    pvd[40:72] = _str_field(volume_id[:32], 32)
    pvd[80:88] = _both_endian32(total_sectors)
    pvd[120:124] = _both_endian16(1)             # volumenes del conjunto
    pvd[124:128] = _both_endian16(1)             # numero de secuencia
    pvd[128:132] = _both_endian16(SECTOR_ISO)    # tamano del bloque
    pvd[132:136] = struct.pack("<I", 10)         # tamano de la tabla de rutas
    pvd[136:140] = struct.pack("<I", lba_path_l)
    pvd[140:144] = struct.pack("<I", 0)
    pvd[144:148] = struct.pack(">I", lba_path_m)
    pvd[148:152] = struct.pack(">I", 0)
    pvd[152:190] = _root_record(lba_root, SECTOR_ISO)
    pvd[186:314] = _str_field("", 128)
    pvd[314:442] = _str_field("", 128)
    pvd[442:570] = _str_field("", 128)
    pvd[570:698] = _str_field("BATOCERA MANAGER", 128)
    pvd[698:735] = _str_field("", 37)
    pvd[735:772] = _str_field("", 37)
    pvd[772:809] = _str_field("", 37)
    pvd[813:830] = b"1970010100000000\x00"
    pvd[830:847] = b"1970010100000000\x00"
    pvd[847:864] = b"1970010100000000\x00"
    pvd[864:881] = b"1970010100000000\x00"
    pvd[881] = 1                                 # version de la estructura

    # ── Descriptor de volumen terminador ──
    term = bytearray(SECTOR_ISO)
    term[0] = 0xFF
    term[1:6] = b"CD001"
    term[6] = 1

    # ── Tablas de rutas (L y M): una entrada, la del directorio raiz ──
    entrada_l = bytes([1, 0]) + struct.pack("<I", lba_root) + struct.pack("<H", 1) + b"\x00\x00"
    entrada_m = bytes([1, 0]) + struct.pack(">I", lba_root) + struct.pack(">H", 1) + b"\x00\x00"

    # ── Directorio raiz ──
    root = bytearray(SECTOR_ISO)
    root[0:38] = _root_record(lba_root, SECTOR_ISO)

    out = bytearray()
    out.extend(b"\x00" * (16 * SECTOR_ISO))
    out.extend(pvd)
    out.extend(term)
    # Las tablas de rutas ocupan un sector cada una, aunque solo usen 10 bytes.
    out.extend(entrada_l.ljust(SECTOR_ISO, b"\x00"))
    out.extend(entrada_m.ljust(SECTOR_ISO, b"\x00"))
    out.extend(root)
    return bytes(out)


def build_iso(sectors: Iterable[bytes], volume_id: str = "BWM") -> bytes:
    """Construye un ISO 9660 valido a partir de sectores de 2048 bytes.

    Se usa para ISO de prueba y para imagenes pequenas; para las conversiones
    grandes se usa :func:`_escribir_iso`, que va a disco sector a sector.
    """
    data = bytearray()
    for sector in sectors:
        data.extend(sector[:SECTOR_ISO].ljust(SECTOR_ISO, b"\x00"))
    return _iso_esqueleto(volume_id, len(data) // SECTOR_ISO) + bytes(data)


def _escribir_iso(sectores: Iterable[bytes], out_path: str,
                  volume_id: str = "BWM", total_data: int = 0) -> dict:
    """Escribe un ISO a partir de los sectores de datos, sin cargarlos todos.

    Si los datos ya traen su propio descriptor de volumen, el ISO se
    reconstruye byte a byte: es lo que pasa cuando un ISO se convierte en
    BIN/CUE y vuelve, y asi el resultado es identico al original (con su
    sistema de ficheros intacto). Si no lo traen, se monta el esqueleto de
    ISO 9660 de toda la vida.
    """
    primeros = []
    for sector in sectores:
        primeros.append(sector[:SECTOR_ISO].ljust(SECTOR_ISO, b"\x00"))
        if len(primeros) >= 21:
            break
    conserva = any(s[1:6] == b"CD001" and s[0] in (1, 2) for s in primeros)

    with open(out_path, "wb") as fh:
        if not conserva:
            fh.write(_iso_esqueleto(volume_id, total_data))
        for sector in primeros:
            fh.write(sector)
        for sector in sectores:
            fh.write(sector[:SECTOR_ISO].ljust(SECTOR_ISO, b"\x00"))
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path)}


# ── Conversiones ────────────────────────────────────────────────────────

def bin_cue_to_iso(cue_path: str, out_path: str) -> dict:
    """Convierte un BIN + CUE en un ISO de 2048 bytes por sector.

    Solo se toma la primera pista de datos: las pistas de audio no caben en un
    ISO y las herramientas clasicas hacen lo mismo.
    """
    tracks = parse_cue(cue_path)
    if not tracks:
        raise ValueError("el CUE no describe ninguna pista")
    group = tracks[0]
    bin_path = os.path.join(os.path.dirname(cue_path), group["file"])
    if not os.path.isfile(bin_path):
        raise ValueError(f"no se encuentra el BIN: {group['file']}")

    data_track = None
    for track in group["tracks"]:
        if track["mode"].startswith("MODE"):
            data_track = track
            break
    if data_track is None:
        raise ValueError("el CUE no tiene ninguna pista de datos")

    def sectors():
        with open(bin_path, "rb") as fh:
            while True:
                sector = fh.read(SECTOR_RAW)
                if not sector:
                    break
                if len(sector) < SECTOR_RAW:
                    break
                user = _sector_to_user_data(sector)
                if user is None:
                    raise ValueError("la imagen tiene un tipo de sector que no se puede convertir a ISO")
                yield user

    volume = os.path.splitext(os.path.basename(bin_path))[0][:32]
    total = os.path.getsize(bin_path) // SECTOR_RAW
    salida = _escribir_iso(sectors(), out_path, volume_id=volume,
                            total_data=total)
    salida["note"] = "solo la primera pista de datos"
    return salida


def raw_bin_to_iso(bin_path: str, out_path: str) -> dict:
    """Convierte un BIN de 2352 bytes por sector en un ISO, sin CUE.

    El tipo de sector (Mode 1 o Mode 2) se lee de la cabecera de cada sector,
    asi que no hace falta el CUE para saber donde estan los datos de usuario.
    """
    def sectors():
        with open(bin_path, "rb") as fh:
            while True:
                sector = fh.read(SECTOR_RAW)
                if not sector:
                    break
                if len(sector) < SECTOR_RAW:
                    break
                user = _sector_to_user_data(sector)
                if user is None:
                    raise ValueError(
                        "la imagen tiene un tipo de sector que no se puede convertir a ISO")
                yield user

    volume = os.path.splitext(os.path.basename(bin_path))[0][:32]
    total = os.path.getsize(bin_path) // SECTOR_RAW
    salida = _escribir_iso(sectors(), out_path, volume_id=volume,
                            total_data=total)
    salida["note"] = "el BIN no tenia CUE: se han usado los sectores en bruto"
    return salida


def iso_to_bin_cue(iso_path: str, out_bin: str | None = None,
                   out_cue: str | None = None) -> dict:
    """Convierte un ISO de 2048 bytes en un BIN + CUE de 2352 bytes."""
    if not _looks_iso(iso_path):
        raise ValueError("el fichero no parece un ISO 9660")
    stem = os.path.splitext(iso_path)[0]
    # Si se dice donde va el BIN, el CUE va a su lado y no con el nombre del
    # origen: si no, el CUE acababa llamandose como el ISO de partida.
    if out_bin:
        if not out_bin.lower().endswith(".bin"):
            out_bin = out_bin + ".bin"
    else:
        out_bin = f"{stem}.bin"
    if out_cue:
        if not out_cue.lower().endswith(".cue"):
            out_cue = out_cue + ".cue"
    else:
        out_cue = os.path.splitext(out_bin)[0] + ".cue"

    with open(iso_path, "rb") as src, open(out_bin, "wb") as dst:
        while True:
            user = src.read(SECTOR_ISO)
            if not user:
                break
            dst.write(_user_to_sector(user))

    with open(out_cue, "w", encoding="latin-1", newline="\r\n") as fh:
        fh.write(f'FILE "{os.path.basename(out_bin)}" BINARY\n')
        fh.write("  TRACK 01 MODE1/2352\n")
        fh.write("    INDEX 01 00:00:00\n")
    return {"ok": True, "bin": out_bin, "cue": out_cue}


def pbp_to_bin_cue(pbp_path: str, out_dir: str | None = None) -> dict:
    """Convierte un PBP de PlayStation en BIN + CUE."""
    out_dir = out_dir or os.path.dirname(pbp_path)
    stem = os.path.splitext(os.path.basename(pbp_path))[0]
    out_bin = os.path.join(out_dir, f"{stem}.bin")
    out_cue = os.path.join(out_dir, f"{stem}.cue")

    with open(pbp_path, "rb") as fh:
        head = fh.read(0x100)
        if not head.startswith(b"PBP\x01"):
            raise ValueError("no es un fichero PBP")
        offsets = struct.unpack(">5I", head[4:0x18])
        data_offset = offsets[0]
        fh.seek(data_offset)
        with open(out_bin, "wb") as dst:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)

    with open(out_cue, "w", encoding="latin-1", newline="\r\n") as fh:
        fh.write(f'FILE "{os.path.basename(out_bin)}" BINARY\n')
        fh.write("  TRACK 01 MODE1/2352\n")
        fh.write("    INDEX 01 00:00:00\n")
    return {"ok": True, "bin": out_bin, "cue": out_cue}


def bin_cue_to_pbp(cue_path: str, out_path: str | None = None) -> dict:
    """Convierte un BIN + CUE en un PBP de PlayStation."""
    tracks = parse_cue(cue_path)
    if not tracks:
        raise ValueError("el CUE no describe ninguna pista")
    group = tracks[0]
    bin_path = os.path.join(os.path.dirname(cue_path), group["file"])
    if not os.path.isfile(bin_path):
        raise ValueError(f"no se encuentra el BIN: {group['file']}")
    out_path = out_path or os.path.join(
        os.path.dirname(cue_path),
        os.path.splitext(os.path.basename(cue_path))[0] + ".pbp")

    with open(bin_path, "rb") as fh:
        data = fh.read()

    # El PBP lleva cinco bloques de cabecera antes de los datos.
    blocks = [
        (b"\x00" * 0x100, b"PS-X EXE"),          # cabecera de la ISO
        (b"CD001" + b"\x00" * (0x100 - 5), b""),  # descriptor primario
        (b"BOGUS" + b"\x00" * (0x100 - 5), b""),  # descriptor secundario
        (b"CD001" + b"\x00" * (0x100 - 5), b""),  # volumen suplementario
        (b"BOGUS" + b"\x00" * (0x100 - 5), b""),  # terminador
    ]
    with open(out_path, "wb") as fh:
        fh.write(b"PBP\x01")
        offset = 4 + 4 * 5
        fh.write(struct.pack(">5I", *[offset] * 5))
        offset += 4 * 5
        for payload, _ in blocks:
            fh.write(payload)
            offset += len(payload)
        fh.write(data)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path)}


def xiso_to_iso(xiso_path: str, out_path: str | None = None) -> dict:
    """Convierte una imagen XDVDF de Xbox en un ISO.

    La diferencia esta en el descriptor de volumen: se cambia el magic de
    Xbox por el de ISO 9660 y se deja el resto intacto.
    """
    out_path = out_path or os.path.splitext(xiso_path)[0] + ".iso"
    with open(xiso_path, "rb") as src:
        head = src.read(SECTOR_ISO)
        if not head:
            raise ValueError("el fichero esta vacio")
        if b"CD001" in head[:0x8000] and not head.startswith(b"\x00\x00\x00\x00"):
            pass
        src.seek(0)
        with open(out_path, "wb") as dst:
            offset = 0
            while True:
                sector = src.read(SECTOR_ISO)
                if not sector:
                    break
                if offset == 32:
                    sector = bytearray(sector)
                    # El descriptor de Xbox empieza con "MICROSOFT*XBOX*MEDIA":
                    # se sustituye por el descriptor de ISO.
                    if sector[0x14:0x28].startswith(b"MICROSOFT*XBOX*MEDIA"):
                        sector[0x00] = 1
                        sector[0x01:0x06] = b"CD001"
                        sector[0x06] = 1
                        sector[0x14:0x28] = b"\x00" * 20
                    sector = bytes(sector)
                dst.write(sector)
                offset += 1
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path)}


def gcm_to_iso(gcm_path: str, out_path: str | None = None) -> dict:
    """Convierte un GCM de GameCube en una ISO (el formato GCISO)."""
    out_path = out_path or os.path.splitext(gcm_path)[0] + ".iso"
    with open(gcm_path, "rb") as src:
        header = src.read(0x440)
        if len(header) < 0x440:
            raise ValueError("el GCM esta incompleto")
        with open(out_path, "wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "note": "imagen GCISO (volcado de los sectores)"}


# ── Nombres de salida ───────────────────────────────────────────────────

def _salida_libre(path: str, ext: str) -> str:
    """Un nombre de salida que no pise nada.

    Si ya existe «Juego.chd» sale «Juego (1).chd»: nunca se sobrescribe un
    fichero sin querer.
    """
    base = os.path.splitext(os.path.basename(path))[0]
    carpeta = os.path.dirname(path)
    destino = os.path.join(carpeta, base + ext)
    numero = 1
    while os.path.exists(destino):
        destino = os.path.join(carpeta, f"{base} ({numero}){ext}")
        numero += 1
    return destino


def _stem_libre(path: str) -> str:
    """Un nombre sin extension del que salen el BIN y su CUE.

    Los dos tienen que estar libres: el CUE apunta al BIN, asi que si el BIN
    ya existe el nombre no vale aunque el CUE no este.
    """
    base = os.path.splitext(os.path.basename(path))[0]
    carpeta = os.path.dirname(path)
    stem = os.path.join(carpeta, base)
    numero = 1
    while os.path.exists(stem + ".bin") or os.path.exists(stem + ".cue"):
        stem = os.path.join(carpeta, f"{base} ({numero})")
        numero += 1
    return stem


def _escribir_cue(bin_path: str, cue_path: str) -> None:
    """Escribe el CUE que accompanye a un BIN de una pista."""
    with open(cue_path, "w", encoding="latin-1", newline="\r\n") as fh:
        fh.write(f'FILE "{os.path.basename(bin_path)}" BINARY\n')
        fh.write("  TRACK 01 MODE1/2352\n")
        fh.write("    INDEX 01 00:00:00\n")


# ── Nintendo 64 ─────────────────────────────────────────────────────────

def _swap16(data: bytes) -> bytes:
    """Intercambia los bytes de cada palabra de 16 bits."""
    out = bytearray(data)
    out[0::2], out[1::2] = out[1::2], out[0::2]
    return bytes(out)


def _swap32(data: bytes) -> bytes:
    """Invierte cada grupo de 4 bytes (las palabras de 32 bits)."""
    out = bytearray(data)
    out[0::4], out[1::4], out[2::4], out[3::4] = (
        out[3::4], out[2::4], out[1::4], out[0::4])
    return bytes(out)


#: De un byte order a otro, que intercambios hay que hacer.
#:
#: Las tres ROM de Nintendo 64 son la misma con los bytes cambiados de sitio:
#: la nativa va en big endian (``.n64``, magia ``40 12 37 80``), la little
#: endian (``.z64``, ``80 37 12 40``) y la byte swapped (``.v64``,
#: ``37 80 40 12``). De la nativa a la little endian se invierte cada grupo de
#: 4 bytes; de la nativa a la byte swapped ademas se intercambian los bytes de
#: cada palabra de 16 bits.
_N64_PASOS = {
    ("n64", "z64"): (_swap32,),
    ("z64", "n64"): (_swap32,),
    ("n64", "v64"): (_swap32, _swap16),
    ("v64", "n64"): (_swap16, _swap32),
    ("z64", "v64"): (_swap16,),
    ("v64", "z64"): (_swap16,),
}


def n64_convert(path: str, target: str, out_path: str | None = None) -> dict:
    """Convierte una ROM de Nintendo 64 entre sus tres byte orders.

    El byte order se deduce de la cabecera, no del nombre: hay volcados que
    se llaman ``.v64`` y estan en big endian.
    """
    path = os.path.abspath(path)
    info = detect_format(path)
    origen = {"n64-z64": "z64", "n64-n64": "n64", "n64-v64": "v64"}.get(info.kind)
    if origen is None:
        raise ValueError("no es una ROM de Nintendo 64")
    destino = (target or "").lower()
    pasos = _N64_PASOS.get((origen, destino))
    if pasos is None:
        raise ValueError(f"no se puede convertir de {origen} a {destino}")

    out_path = out_path or _salida_libre(path, "." + destino)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(path, "rb") as src, open(out_path, "wb") as dst:
        while True:
            trozo = src.read(1 << 20)
            if not trozo:
                break
            for paso in pasos:
                trozo = paso(trozo)
            dst.write(trozo)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": f"convertida de {origen} a {destino}"}


# ── Super Nintendo ──────────────────────────────────────────────────────

#: La cabecera de copista de la Super Nintendo son 512 bytes.
_SNES_CABECERA = 512


def _snes_partes(path: str) -> tuple:
    """Separa una ROM de Super Nintendo en (cabeza, cuerpo, tipo).

    Hay tres variantes: la ``.sfc`` va pelada, la ``.smc`` lleva delante una
    cabecera de copista de 512 bytes con el «aa bb» en el 8, y la ``.fig``
    lleva delante su propia cabecera de 512 bytes (que empieza por «FIG »).
    """
    with open(path, "rb") as fh:
        head = fh.read(_SNES_CABECERA)
        rest = fh.read()
    if head[:4] == b"FIG ":
        return head, rest, "fig"
    if head[0x08:0x0A] == b"\xaa\xbb":
        return head, rest, "smc"
    return head, rest, "sfc"


def _snes_cuerpo(path: str) -> bytes:
    """La ROM de Super Nintendo sin ninguna cabecera delante."""
    head, rest, tipo = _snes_partes(path)
    if tipo == "fig":
        # La FIG lleva su cabecera y despues la ROM con su cabecera de copista.
        if rest[0x08:0x0A] == b"\xaa\xbb":
            return rest[_SNES_CABECERA:]
        return rest
    if tipo == "smc":
        return rest
    return head + rest


def _snes_cabecera_copista() -> bytes:
    """La cabecera de copista de 512 bytes (la que lleva el «aa bb»)."""
    cabecera = bytearray(_SNES_CABECERA)
    cabecera[0x08:0x0A] = b"\xaa\xbb"
    return bytes(cabecera)


def snes_convert(path: str, target: str, out_path: str | None = None) -> dict:
    """Convierte una ROM de Super Nintendo entre SFC, SMC y FIG."""
    destino = (target or "").lower()
    if destino not in ("sfc", "smc", "fig"):
        raise ValueError(f"no se puede convertir a {destino}")
    path = os.path.abspath(path)
    cuerpo = _snes_cuerpo(path)
    if not cuerpo:
        raise ValueError("el fichero esta vacio")

    if destino == "sfc":
        datos = cuerpo
        nota = "cabecera de copista quitada"
    elif destino == "smc":
        datos = _snes_cabecera_copista() + cuerpo
        nota = "cabecera de copista anadida"
    else:
        cabecera = bytearray(_SNES_CABECERA)
        cabecera[0x00:0x04] = b"FIG "
        cabecera[0x04:0x08] = b"alnd"
        cabecera[0x08:0x0C] = b"ver "
        cabecera[0x0C:0x10] = b"NTSC"
        nombre = os.path.splitext(os.path.basename(path))[0][:31]
        # El nombre ocupa 32 bytes fijos: si se escribe mas corto, la
        # cabecera se encoge y el fichero sale mal.
        cabecera[0x10:0x30] = nombre.encode("ascii", "replace").ljust(32, b"\x00")[:32]
        datos = bytes(cabecera) + _snes_cabecera_copista() + cuerpo
        nota = "cabecera FIG anadida"

    out_path = out_path or _salida_libre(path, "." + destino)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(datos)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": nota}


# ── ZIP ─────────────────────────────────────────────────────────────────

def extract_zip(path: str, out_dir: str | None = None) -> dict:
    """Descomprime un ZIP en una carpeta al lado.

    Es lo que necesitan las sets de recreativa, que vienen en ZIP.
    """
    path = os.path.abspath(path)
    if out_dir is None:
        base = os.path.splitext(os.path.basename(path))[0]
        carpeta = os.path.dirname(path)
        out_dir = os.path.join(carpeta, base)
        numero = 1
        while os.path.exists(out_dir):
            out_dir = os.path.join(carpeta, f"{base} ({numero})")
            numero += 1
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(path) as zf:
        miembros = zf.namelist()
        raiz = os.path.abspath(out_dir)
        for member in miembros:
            destino = os.path.normpath(os.path.join(out_dir, member))
            if not os.path.abspath(destino).startswith(raiz):
                raise ValueError("el ZIP intenta escribir fuera de la carpeta")
        zf.extractall(out_dir)
    return {"ok": True, "out": out_dir, "nota": "contenido extraido",
            "miembros": len(miembros)}


# ── 7Z, con el 7z de la consola ─────────────────────────────────────────

#: Rutas donde puede estar el 7z de la consola (p7zip).
_7Z_RUTAS = ("/usr/bin/7z", "/usr/local/bin/7z", "/usr/bin/p7zip",
             "/usr/bin/7za", "/usr/bin/7zr")


def _sevenzip_path() -> str | None:
    """Donde esta el 7z, si esta.

    En la consola esta en ``/usr/bin/7z``. En un PC se busca en el PATH, que
    tambien encuentra el ``7z.exe`` de Windows.
    """
    exe = shutil.which("7z")
    if exe:
        return exe
    for ruta in _7Z_RUTAS:
        if os.path.isfile(ruta) and os.access(ruta, os.X_OK):
            return ruta
    return None


def sevenzip_disponible() -> bool:
    """Si la consola tiene el 7z (p7zip)."""
    return _sevenzip_path() is not None


def _7z(args: list, cwd: str | None = None, timeout: int = 7200) -> str:
    """Ejecuta el 7z y devuelve su salida.

    Se llama siempre con una lista de argumentos y sin shell, para que las
    rutas con espacios no se rompan.
    """
    exe = _sevenzip_path()
    if not exe:
        raise ValueError("falta la utilidad 7z para comprimir en 7Z")
    try:
        res = subprocess.run([exe] + args, capture_output=True, text=True,
                             timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise ValueError("el 7z ha tardado demasiado y se ha parado")
    except OSError as exc:
        raise ValueError(f"no se ha podido ejecutar el 7z: {exc}")
    if res.returncode != 0:
        mensaje = (res.stderr or res.stdout or "").strip()
        raise ValueError(mensaje[-400:] or "el 7z no pudo hacer la conversion")
    return res.stdout or ""


def compress_7z(path: str, out_path: str | None = None, level: int = 5) -> dict:
    """Comprime un fichero (o una carpeta) en un 7Z.

    Se usa el 7z de la consola (p7zip), que squeezea mas que el ZIP. El
    fichero se comprime desde dentro de su carpeta, asi que el 7Z guarda solo
    el nombre y no todo el camino.
    """
    path = os.path.abspath(path)
    out_path = out_path or _replace_ext(path, ".7z")
    if not _sevenzip_path():
        raise ValueError("falta la utilidad 7z para comprimir en 7Z")
    carpeta = os.path.dirname(path)
    nombre = os.path.basename(path)
    _7z(["a", "-t7z", f"-mx={level}", out_path, nombre], cwd=carpeta)
    if not os.path.exists(out_path):
        raise ValueError("el 7z no ha creado el fichero 7Z")
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "comprimido en 7Z", "before": _size(path)}


def extract_7z(path: str, out_dir: str | None = None) -> dict:
    """Descomprime un 7Z en una carpeta al lado.

    Antes de descomprimir se mira lo que lleva dentro, para que no pueda
    escribir fuera de la carpeta de destino.
    """
    path = os.path.abspath(path)
    if out_dir is None:
        base = os.path.splitext(os.path.basename(path))[0]
        carpeta = os.path.dirname(path)
        out_dir = os.path.join(carpeta, base)
        numero = 1
        while os.path.exists(out_dir):
            out_dir = os.path.join(carpeta, f"{base} ({numero})")
            numero += 1
    os.makedirs(out_dir, exist_ok=True)
    raiz = os.path.abspath(out_dir)
    listado = _7z(["l", "-slt", "-ba", path])
    for linea in listado.splitlines():
        if not linea.lower().startswith("path = "):
            continue
        miembro = linea[len("path = "):].strip()
        if os.path.abspath(miembro) == path:
            continue                      # el propio fichero 7Z
        destino = os.path.normpath(os.path.join(out_dir, miembro))
        absoluto = os.path.abspath(destino)
        if absoluto != raiz and not absoluto.startswith(raiz + os.sep):
            raise ValueError("el 7Z intenta escribir fuera de la carpeta")
    _7z(["x", "-y", "-o" + out_dir, path])
    return {"ok": True, "out": out_dir, "nota": "contenido extraido"}


# ── Formatos comprimidos: CSO, CISO y GCZ ───────────────────────────────

#: Bloque de 2048 bytes con el que se trocean los CSO y los CISO.
_BLOQUE = 2048


def _bloques_leer(fh, block_size: int, total: int):
    """Lee los bloques de un CSO o un CISO.

    Cada bloque lleva delante cuatro bytes con el tamano de los datos que
    siguen. Si ese tamano es el del bloque, los datos van sin comprimir; si
    no, van comprimidos con deflate.
    """
    leidos = 0
    while leidos < total:
        cabecera = fh.read(4)
        if len(cabecera) < 4:
            break
        (tam,) = struct.unpack("<I", cabecera)
        if tam == block_size:
            datos = fh.read(block_size)
        else:
            datos = fh.read(tam)
            if not datos:
                break
            try:
                datos = zlib.decompress(datos)
            except zlib.error as exc:
                raise ValueError(f"el bloque comprimido no se puede descomprimir: {exc}")
        if not datos:
            break
        yield datos
        leidos += len(datos)


def _bloques_escribir(dst, src, block_size: int) -> None:
    """Escribe un fichero como bloques de CSO o CISO."""
    while True:
        bloque = src.read(block_size)
        if not bloque:
            break
        if len(bloque) < block_size:
            bloque = bloque.ljust(block_size, b"\x00")
        comprimido = zlib.compress(bloque, 9)
        if len(comprimido) >= block_size:
            dst.write(struct.pack("<I", block_size))
            dst.write(bloque)
        else:
            dst.write(struct.pack("<I", len(comprimido)))
            dst.write(comprimido)


def cso_to_iso(cso_path: str, out_path: str) -> dict:
    """Descomprime un CSO (PSP) a ISO."""
    with open(cso_path, "rb") as fh:
        head = fh.read(24)
        if head[:4] != b"CSO!":
            raise ValueError("no es un CSO")
        (header_size,) = struct.unpack("<I", head[4:8])
        (uncompressed,) = struct.unpack("<Q", head[8:16])
        (block_size,) = struct.unpack("<I", head[16:20])
        if not block_size:
            raise ValueError("el CSO no tiene tamano de bloque")
        fh.seek(header_size)
        with open(out_path, "wb") as out:
            for datos in _bloques_leer(fh, block_size, uncompressed):
                out.write(datos)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "descomprimido con deflate"}


def iso_to_cso(iso_path: str, out_path: str) -> dict:
    """Comprime un ISO a CSO version 1 (deflate).

    La version 2 (LZ4) no se escribe: haria falta la libreria de LZ4, que no
    esta en la consola.
    """
    total = _size(iso_path)
    with open(iso_path, "rb") as src, open(out_path, "wb") as dst:
        dst.write(b"CSO!" + struct.pack("<I", 24) + struct.pack("<Q", total)
                  + struct.pack("<I", _BLOQUE) + struct.pack("<I", 1))
        _bloques_escribir(dst, src, _BLOQUE)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "CSO version 1 (deflate)"}


def ciso_to_iso(ciso_path: str, out_path: str) -> dict:
    """Descomprime un CISO (GameCube o Wii) a ISO."""
    with open(ciso_path, "rb") as fh:
        head = fh.read(24)
        if head[:4] != b"CISO":
            raise ValueError("no es un CISO")
        (header_size,) = struct.unpack("<I", head[4:8])
        (uncompressed,) = struct.unpack("<Q", head[8:16])
        (block_size,) = struct.unpack("<I", head[16:20])
        if not block_size:
            raise ValueError("el CISO no tiene tamano de bloque")
        fh.seek(header_size)
        with open(out_path, "wb") as out:
            for datos in _bloques_leer(fh, block_size, uncompressed):
                out.write(datos)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "descomprimido con deflate"}


def iso_to_ciso(iso_path: str, out_path: str) -> dict:
    """Comprime un ISO a CISO (bloques de 2048 con deflate)."""
    total = _size(iso_path)
    with open(iso_path, "rb") as src, open(out_path, "wb") as dst:
        dst.write(b"CISO" + struct.pack("<I", 24) + struct.pack("<Q", total)
                  + struct.pack("<I", _BLOQUE) + struct.pack("<I", 0))
        _bloques_escribir(dst, src, _BLOQUE)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "CISO con deflate"}


def gcz_to_iso(gcz_path: str, out_path: str) -> dict:
    """Descomprime un GCZ (GameCube) a ISO: es un gzip con cuatro bytes delante."""
    with open(gcz_path, "rb") as fh:
        if fh.read(4) != b"\x01\xc0\x0b\xb1":
            raise ValueError("no es un GCZ")
        with gzip.GzipFile(fileobj=fh) as gz, open(out_path, "wb") as out:
            shutil.copyfileobj(gz, out, 1 << 20)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "descomprimido con gzip"}


def iso_to_gcz(iso_path: str, out_path: str) -> dict:
    """Comprime un ISO de GameCube a GCZ (un gzip con cuatro bytes delante)."""
    with open(iso_path, "rb") as src, open(out_path, "wb") as dst:
        dst.write(b"\x01\xc0\x0b\xb1")
        with gzip.GzipFile(fileobj=dst, mode="wb", compresslevel=6) as gz:
            shutil.copyfileobj(src, gz, 1 << 20)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "comprimido con gzip"}


# ── CHD, con el chdman de MAME ──────────────────────────────────────────

#: Rutas donde puede estar el chdman de MAME.
_CHDMAN_RUTAS = ("/usr/bin/chdman", "/usr/local/bin/chdman",
                 "/usr/bin/mame/chdman")

#: Un CD cabe en 737.280.000 bytes; a partir de ahi es un DVD.
_TAMANO_CD = 737280000


def _chdman_path() -> str | None:
    """Donde esta el chdman, si esta."""
    exe = shutil.which("chdman")
    if exe:
        return exe
    for ruta in _CHDMAN_RUTAS:
        if os.path.isfile(ruta) and os.access(ruta, os.X_OK):
            return ruta
    return None


def chdman_disponible() -> bool:
    """Si la consola tiene el chdman de MAME."""
    return _chdman_path() is not None


def _chdman(args: list, timeout: int = 7200) -> str:
    """Ejecuta el chdman y devuelve su salida."""
    exe = _chdman_path()
    if not exe:
        raise ValueError("chdman no esta en la consola: no se pueden convertir CHD")
    try:
        res = subprocess.run([exe] + args, capture_output=True, text=True,
                             timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError("chdman ha tardado demasiado y se ha parado")
    if res.returncode != 0:
        mensaje = (res.stderr or res.stdout or "").strip()
        raise ValueError(mensaje[-400:] or "chdman no pudo hacer la conversion")
    return res.stdout or ""


def _chdman_numero(texto: str, etiqueta: str) -> int:
    """Un numero de la salida de «chdman info» («Unit Size: 2,448 bytes»)."""
    match = re.search(rf"{re.escape(etiqueta)}:\s*([\d,.]+)", texto)
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", "").replace(".", ""))
    except ValueError:
        return 0


def _chd_unidades(chd_path: str) -> tuple:
    """El tamano de la unidad y el numero de unidades de un CHD.

    chdman lo dice en su «info»: en un CD la unidad son 2.448 bytes (el
    sector con su correccion de errores) y en un DVD 2.048.
    """
    info = _chdman(["info", "-i", chd_path])
    unit_size = _chdman_numero(info, "Unit Size")
    total = _chdman_numero(info, "Total Units")
    if not unit_size:
        raise ValueError("chdman no ha dicho el tamano de la unidad del CHD")
    return unit_size, total


def iso_to_chd(iso_path: str, out_path: str) -> dict:
    """Comprime un ISO en un CHD con el chdman de MAME.

    Se usa «createcd» para un CD y «createdvd» para un DVD, que es lo que
    espera cada emulador.
    """
    total = _size(iso_path)
    if total > _TAMANO_CD:
        _chdman(["createdvd", "-i", iso_path, "-o", out_path, "-c", "zlib"])
        nota = "comprimido en un CHD de DVD"
    else:
        _chdman(["createcd", "-i", iso_path, "-o", out_path, "-c", "cdzl"])
        nota = "comprimido en un CHD de CD"
    if not os.path.exists(out_path):
        raise ValueError("chdman no ha creado el CHD")
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": nota}


def _chd_datos(chd_path: str) -> bytes:
    """Saca los datos en crudo de un CHD y devuelve el tamano de la unidad."""
    unit_size, total = _chd_unidades(chd_path)
    crudo = chd_path + ".crudo"
    try:
        _chdman(["extractraw", "-i", chd_path, "-o", crudo])
        with open(crudo, "rb") as fh:
            datos = fh.read()
    finally:
        if os.path.exists(crudo):
            os.remove(crudo)
    return datos, unit_size


def _chd_tiene_pvd(datos: bytes, unit_size: int, offset: int) -> bool:
    """Si con este desplazamiento el disco trae su descriptor de volumen."""
    inicio = 16 * unit_size
    if inicio + unit_size > len(datos):
        return False
    sector = datos[inicio + offset:inicio + offset + SECTOR_ISO]
    return len(sector) == SECTOR_ISO and sector[1:6] == b"CD001"


def _chd_modo(datos: bytes, unit_size: int) -> int:
    """De donde empiezan los datos de usuario dentro de cada unidad.

    Hay dos clases de CHD y se distinguen por como se guardaron los sectores:

    - El CHD hecho de un **BIN/CUE** guarda el sector entero: sus 12 bytes de
      sincronizacion, los 4 de cabecera y los 2.048 de datos (más la
      correccion de errores). Los datos empiezan en el 16.
    - El CHD hecho de un **ISO** guarda los 2.048 bytes de datos sin cabecera
      (más 400 bytes de relleno). Los datos empiezan en el 0.

    Si el disco tiene sistema de ficheros, se decide por el descriptor de
    volumen; si no, por la sincronizacion del primer sector con contenido.
    """
    if unit_size <= SECTOR_ISO:
        return 0
    for offset in (16, 0):
        if _chd_tiene_pvd(datos, unit_size, offset):
            return offset
    for inicio in range(0, len(datos) - unit_size + 1, unit_size):
        unidad = datos[inicio:inicio + unit_size]
        if not any(unidad[:SECTOR_ISO]):
            continue        # sector vacio: no dice nada
        if unidad[0:12] == b"\x00" * 12 and unidad[12] == 0x01:
            return 16
        return 0
    return 16


def chd_to_iso(chd_path: str, out_path: str | None = None) -> dict:
    """Saca el ISO de un CHD.

    El CHD guarda las unidades del disco: en un CD son 2.448 bytes (el sector
    con su correccion de errores) y en un DVD 2.048. De dentro de cada unidad
    se saca el sector de 2.048 bytes, tenga o no cabecera.
    """
    chd_path = os.path.abspath(chd_path)
    out_path = out_path or _salida_libre(chd_path, ".iso")
    datos, unit_size = _chd_datos(chd_path)
    offset = _chd_modo(datos, unit_size)
    with open(out_path, "wb") as out:
        for inicio in range(0, len(datos) - unit_size + 1, unit_size):
            unidad = datos[inicio:inicio + unit_size]
            out.write(unidad[offset:offset + SECTOR_ISO])
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "nota": "extraido con chdman"}


def chd_to_bin_cue(chd_path: str, out_bin: str | None = None,
                   out_cue: str | None = None) -> dict:
    """Saca el BIN (2352 bytes por sector) y su CUE de un CHD."""
    chd_path = os.path.abspath(chd_path)
    if out_bin is None or out_cue is None:
        stem = _stem_libre(chd_path)
        out_bin = out_bin or stem + ".bin"
        out_cue = out_cue or stem + ".cue"
    datos, unit_size = _chd_datos(chd_path)
    if unit_size < SECTOR_RAW:
        raise ValueError("un DVD no se puede convertir a BIN/CUE")
    offset = _chd_modo(datos, unit_size)
    with open(out_bin, "wb") as out:
        for inicio in range(0, len(datos) - unit_size + 1, unit_size):
            unidad = datos[inicio:inicio + unit_size]
            if offset == 16:
                # El sector ya viene con su sincronizacion y su cabecera.
                out.write(unidad[0:SECTOR_RAW])
            else:
                # Venian sin cabecera: se monta el sector MODE1.
                out.write(_user_to_sector(unidad[0:SECTOR_ISO]))
    _escribir_cue(out_bin, out_cue)
    return {"ok": True, "out": out_bin, "cue": out_cue,
            "size": os.path.getsize(out_bin),
            "nota": "extraido con chdman"}


# ── Imagenes de disco proprietarias ──────────────────────────────────────

#: Los tamanos de sector que se pueden encontrar en una imagen de disco:
#: 2352 (MODE1), 2448 (con la correccion de errores), 2336 (MODE2) y 2048
#: (que ya son los datos de usuario).
_TAMANOS_SECTOR = (SECTOR_RAW, 2448, 2336, SECTOR_ISO)


def _datos_de_sector(sector: bytes) -> bytes | None:
    """Los 2048 bytes de usuario de un sector, sea del tamano que sea."""
    if len(sector) < SECTOR_ISO:
        return None
    if len(sector) == SECTOR_ISO:
        return sector[:SECTOR_ISO]
    if len(sector) in (SECTOR_RAW, 2448):
        return _sector_to_user_data(sector[:SECTOR_RAW])
    if len(sector) == 2336:
        return sector[8:8 + SECTOR_ISO]
    return None


def _tamano_sector(path: str) -> int:
    """De que tamano son los sectores de una imagen en crudo."""
    size = _size(path)
    for tamano in _TAMANOS_SECTOR:
        if size and size % tamano == 0:
            return tamano
    return SECTOR_RAW


def _sectores_de_imagen(ruta: str, tamano: int, inicio: int = 0,
                        cuantos: int | None = None):
    """Los sectores de datos de usuario de una imagen en crudo.

    Se van sacando de uno en uno, para no tener el disco entero en memoria.
    """
    with open(ruta, "rb") as fh:
        fh.seek(inicio * tamano)
        leidos = 0
        while cuantos is None or leidos < cuantos:
            bruto = fh.read(tamano)
            if len(bruto) < tamano:
                break
            datos = _datos_de_sector(bruto)
            if datos is None:
                raise ValueError(
                    "la imagen tiene un tipo de sector que no se puede convertir a ISO")
            yield datos
            leidos += 1


def _escribir_iso_de_imagen(ruta: str, out_path: str, tamano: int,
                            inicio: int, cuantos: int, volumen: str) -> dict:
    """Escribe el ISO de una imagen en crudo, con su esqueleto si hace falta."""
    return _escribir_iso(_sectores_de_imagen(ruta, tamano, inicio, cuantos),
                         out_path, volume_id=volumen[:32], total_data=cuantos)


# ── GDI (Dreamcast) ──────────────────────────────────────────────────────

#: El GDI de Sega: una linea por pista con el numero, el LBA donde empieza,
#: el tipo (4 datos, 0 audio), el tamano de sector, el fichero y el
#: desplazamiento. El nombre del fichero puede llevar espacios.
_GDI_SEGA_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+?)\s+(\d+)\s*$")

#: El area de alta densidad de un GD-ROM (donde esta el juego) empieza en
#: este LBA: es la pista 3. Antes esta la zona de baja densidad, que es el
#: menu de la consola y no va en el ISO.
_GDI_LBA_ALTA = 45000

#: Tambien se leen los GDI derivados del CUE (TRACK/INDEX/FILE), que son los
#: que hay en los discos rippeados en modo multicue.
_GDI_TRACK_RE = re.compile(r"^\s*TRACK\s+(\d+)\s+(\S+)", re.I)
_GDI_INDEX_RE = re.compile(r"^\s*INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)", re.I)
_GDI_FILE_RE = re.compile(r'^\s*FILE\s+"?([^"\r\n]+?)"?\s+(\d+)\s+(\d+)', re.I)


def _parse_gdi(gdi_path: str) -> list:
    """Lee un GDI y devuelve sus pistas.

    Un GDI es un fichero de texto con una linea por pista: el tipo (DATA o
    AUDIO), el sector donde empieza y, al final, el fichero de datos con su
    desplazamiento y su longitud (en bytes; un 0 quiere decir "hasta el final").
    """
    pistas = []
    actual = None
    with open(gdi_path, "r", encoding="latin-1", errors="replace") as fh:
        for linea in fh:
            linea = linea.rstrip("\n")
            match = _GDI_SEGA_RE.match(linea)
            if match:
                pistas.append({
                    "numero": int(match.group(1)),
                    "lba": int(match.group(2)),
                    "tipo": "DATA" if match.group(3) == "4" else "AUDIO",
                    "sector": int(match.group(4)),
                    "archivo": match.group(5).strip(),
                    "offset": 0, "longitud": 0, "inicio": 0,
                    "formato": "sega"})
                continue
            match = _GDI_TRACK_RE.match(linea)
            if match:
                actual = {"numero": int(match.group(1)),
                          "tipo": match.group(2).upper(),
                          "inicio": 0, "archivo": None,
                          "offset": 0, "longitud": 0, "lba": 0,
                          "sector": 0, "formato": "cue"}
                pistas.append(actual)
                continue
            match = _GDI_INDEX_RE.match(linea)
            if match and actual is not None:
                actual["inicio"] = (int(match.group(2)) * 60 * 75
                                    + int(match.group(3)) * 75
                                    + int(match.group(4)))
                continue
            match = _GDI_FILE_RE.match(linea)
            if match and actual is not None:
                actual["archivo"] = match.group(1)
                actual["offset"] = int(match.group(2))
                actual["longitud"] = int(match.group(3))
    return pistas


def _datos_del_gdi(gdi_path: str, pista: dict) -> str:
    """El fichero de datos de la pista de datos de un GDI."""
    carpeta = os.path.dirname(gdi_path)
    archivo = pista.get("archivo")
    if archivo:
        candidato = os.path.join(carpeta, archivo)
        # El GDI no puede sacar la lectura de la carpeta de las ROMs: un GDI
        # manipulado podria pedir un fichero de cualquier sitio.
        base = os.path.abspath(carpeta)
        destino = os.path.abspath(candidato)
        if destino != base and not destino.startswith(base + os.sep):
            return ""
        if os.path.isfile(candidato):
            if candidato.lower().endswith(".cue"):
                return _bin_for_cue(candidato) or candidato
            return candidato
        if candidato.lower().endswith(".cue"):
            binario = _bin_for_cue(candidato)
            if binario:
                return binario
    # El GDI no lo dice (o no esta el fichero): se busca el BIN o el CUE que
    # estan al lado.
    base = os.path.splitext(gdi_path)[0]
    for extension in (".bin", ".cue"):
        candidato = base + extension
        if os.path.isfile(candidato):
            if candidato.lower().endswith(".cue"):
                return _bin_for_cue(candidato) or candidato
            return candidato
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        return ""
    for nombre in nombres:
        if nombre.lower().endswith(".bin"):
            return os.path.join(carpeta, nombre)
    return ""


def _empieza_pista_datos(ruta: str, tamano: int, inicio: int) -> bool:
    """Si en ese sector empieza una pista de datos (un ISO 9660).

    La pista de datos de un disco de juego es un ISO 9660: en el sector 16
    esta su descriptor de volumen. Sirve para saber si el INDEX del GDI
   说的是 la posicion dentro del fichero o la posicion en el disco.
    """
    try:
        with open(ruta, "rb") as fh:
            fh.seek((inicio + 16) * tamano)
            sector = fh.read(SECTOR_ISO)
    except OSError:
        return False
    return len(sector) == SECTOR_ISO and sector[1:6] == b"CD001"


def _gdi_sega_a_iso(gdi_path: str, out_path: str, pistas: list,
                    de_datos: list) -> dict:
    """Convierte un GDI de Sega (una linea por pista con el LBA).

    El GDI de Sega describe las pistas del GD-ROM: la zona de baja densidad
    (LBA 0, que es el menu de la consola) y la zona de alta densidad (LBA
    45000, que es el juego). Al ISO solo va la de alta densidad; y si el juego
    esta repartido en varias pistas van todas seguidas, porque el indice del
    filesystem cuenta desde el LBA 45000 y asi el resultado es el mismo disco.

    El audio del CD se queda en su BIN: un ISO de Dreamcast no lleva pistas de
    audio.
    """
    alta = [p for p in de_datos if p["lba"] >= _GDI_LBA_ALTA]
    if alta:
        elegidas = sorted(alta, key=lambda p: p["lba"])
    else:
        elegidas = [max(de_datos, key=lambda p: p["lba"])]

    fuentes = []
    for pista in elegidas:
        origen = _datos_del_gdi(gdi_path, pista)
        if not origen or not os.path.isfile(origen):
            raise ValueError(
                "no se encuentra el fichero de datos del GDI (%s)"
                % (pista.get("archivo") or "sin nombre"))
        tamano = pista.get("sector") or 0
        if tamano not in _TAMANOS_SECTOR:
            tamano = _tamano_sector(origen)
        fuentes.append((origen, tamano))

    total = sum(_size(origen) // tamano for origen, tamano in fuentes)
    if total <= 0:
        raise ValueError("el GDI no dice donde estan los datos del disco")
    volumen = os.path.splitext(os.path.basename(fuentes[0][0]))[0]
    generador = itertools.chain(
        *[_sectores_de_imagen(origen, tamano) for origen, tamano in fuentes])
    salida = _escribir_iso(generador, out_path, volume_id=volumen[:32],
                            total_data=total)
    hay_audio = any(p["tipo"] == "AUDIO" for p in pistas)
    if len(fuentes) > 1:
        nota = "pistas de datos unidas: %d" % len(fuentes)
    else:
        nota = "pista de datos convertida"
    if hay_audio:
        nota += "; el audio se queda en su BIN"
    salida["nota"] = nota
    return salida


def _gdi_cue_a_iso(gdi_path: str, out_path: str, pistas: list,
                   de_datos: list) -> dict:
    """Convierte un GDI derivado del CUE (TRACK / INDEX / FILE).

    El INDEX dice donde empieza la pista: normalmente dentro del fichero,
    pero en los GDI que guardan cada pista en su fichero es la posicion en
    el disco. Se mira cual de las dos vale.
    """
    pista = de_datos[0]
    origen = _datos_del_gdi(gdi_path, pista)
    if not origen or not os.path.isfile(origen):
        raise ValueError("no se encuentra el BIN de datos del GDI")

    tamano = _tamano_sector(origen)
    total = _size(origen) // tamano
    inicio = pista["offset"] // tamano + pista["inicio"]
    if inicio > total:
        inicio = pista["offset"] // tamano
    if not _empieza_pista_datos(origen, tamano, inicio):
        otro = pista["offset"] // tamano
        if otro != inicio and _empieza_pista_datos(origen, tamano, otro):
            inicio = otro
    cuantos = None
    if pista["longitud"]:
        cuantos = pista["longitud"] // tamano
    for otra in pistas:
        if otra is pista:
            continue
        if otra["inicio"] > inicio:
            limite = otra["inicio"] - inicio
            if cuantos is None or limite < cuantos:
                cuantos = limite
    if cuantos is None:
        cuantos = max(total - inicio, 0)
    if cuantos <= 0:
        raise ValueError("el GDI no dice donde estan los datos del disco")

    volumen = os.path.splitext(os.path.basename(origen))[0]
    salida = _escribir_iso_de_imagen(origen, out_path, tamano, inicio, cuantos,
                                     volumen)
    hay_audio = any(p["tipo"] == "AUDIO" for p in pistas)
    salida["nota"] = ("solo la pista de datos: el audio se queda en su BIN"
                      if hay_audio else "pista de datos convertida")
    return salida


def gdi_to_iso(gdi_path: str, out_path: str | None = None) -> dict:
    """Convierte un GDI (Dreamcast) en un ISO de 2048 bytes por sector.

    Se leen los dos formatos de GDI que hay: el de Sega, que es una linea por
    pista con su LBA, y el derivado del CUE, con TRACK/INDEX/FILE.
    """
    gdi_path = os.path.abspath(gdi_path)
    out_path = out_path or _salida_libre(gdi_path, ".iso")
    pistas = _parse_gdi(gdi_path)
    if not pistas:
        raise ValueError("el GDI no describe ninguna pista")
    de_datos = [p for p in pistas if p["tipo"] == "DATA"]
    if not de_datos:
        raise ValueError("el GDI no tiene ninguna pista de datos")
    if pistas[0].get("formato") == "sega":
        return _gdi_sega_a_iso(gdi_path, out_path, pistas, de_datos)
    return _gdi_cue_a_iso(gdi_path, out_path, pistas, de_datos)


# ── MDS y CCD (Alcohol 120% y CloneCD) ─────────────────────────────────

def _xml_raiz(path: str):
    """Lee el XML de un descriptor (MDS o CCD).

    Los descriptores no siempre son un XML bien formado: el MDS de Alcohol
    120% tiene dos raices (la de las notas y la del contenido). Si no se
    puede leer tal cual, se envuelve todo en una raiz y se vuelve a leer.
    """
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            texto = fh.read()
    except OSError:
        raise ValueError("no se puede leer el descriptor")
    try:
        return ET.fromstring(texto)
    except ET.ParseError:
        pass
    cuerpo = re.sub(r"<\?xml[^>]*\?>", "", texto, count=1).strip()
    try:
        return ET.fromstring("<raiz>" + cuerpo + "</raiz>")
    except ET.ParseError:
        raise ValueError("el descriptor no es un XML valido")


def _elemento_imagen(raiz):
    """El elemento IMAGE del descriptor: que fichero y de que tamano."""
    for elem in raiz.iter():
        if elem.tag.rsplit("}", 1)[-1].upper() == "IMAGE":
            return elem
    return None


def _atributo(elem, nombre: str, defecto: str = "") -> str:
    """Un atributo del descriptor, buscandolo sin distinguir mayusculas."""
    for clave, valor in elem.attrib.items():
        if clave.rsplit("}", 1)[-1].upper() == nombre.upper():
            return valor
    return defecto


def _tamano_de_formato(formato: str) -> int:
    """El tamano de sector que dice el descriptor (2352, 2048...)."""
    digitos = ""
    for caracter in (formato or ""):
        if caracter.isdigit():
            digitos += caracter
        else:
            break
    if not digitos:
        return 0
    valor = int(digitos)
    return valor if valor in _TAMANOS_SECTOR else 0


def _img_del_descriptor(desc_path: str, imagen) -> str:
    """El fichero de imagen que dice el descriptor (o el que esta al lado)."""
    carpeta = os.path.dirname(desc_path)
    nombre = _atributo(imagen, "FNAME")
    if nombre:
        candidato = os.path.join(carpeta, nombre)
        # El descriptor no puede sacar la lectura de la carpeta de las ROMs: un
        # MDS manipulado podria pedir un fichero de cualquier sitio.
        base = os.path.abspath(carpeta)
        destino = os.path.abspath(candidato)
        if (destino == base or destino.startswith(base + os.sep)) \
                and os.path.isfile(candidato):
            return candidato
    base = os.path.splitext(desc_path)[0]
    for extension in (".img", ".mdf", ".bin"):
        candidato = base + extension
        if os.path.isfile(candidato):
            return candidato
    return ""


def _descriptor_a_iso(desc_path: str, out_path: str | None,
                      etiqueta: str) -> dict:
    """Convierte un descriptor (MDS o CCD) en ISO, usando su fichero de datos.

    El descriptor (MDS de Alcohol 120% o CCD de CloneCD) es un XML que dice
    como es el disco y en que fichero estan los datos. El ISO sale de ese
    fichero, con los sectores de datos de usuario.
    """
    desc_path = os.path.abspath(desc_path)
    out_path = out_path or _salida_libre(desc_path, ".iso")
    raiz = _xml_raiz(desc_path)
    imagen = _elemento_imagen(raiz)
    if imagen is None:
        raise ValueError(f"el {etiqueta} no dice que fichero de imagen tiene")
    img_path = _img_del_descriptor(desc_path, imagen)
    if not img_path:
        raise ValueError(f"no se encuentra el fichero de imagen del {etiqueta}")

    tamano = _tamano_de_formato(_atributo(imagen, "FORMAT"))
    if not tamano:
        tamano = _tamano_sector(img_path)
    total = _size(img_path) // tamano

    # El descriptor puede dar el tamano en bytes o en sectores: se usa el que
    # cuadre con el fichero de imagen.
    declarado = _atributo(imagen, "SIZE")
    if declarado.isdigit() and int(declarado):
        valor = int(declarado)
        if valor % tamano == 0 and valor // tamano <= total:
            total = valor // tamano
        elif valor <= total:
            total = valor
    if total <= 0:
        raise ValueError(f"el {etiqueta} no dice cuantos sectores tiene el disco")

    volumen = os.path.splitext(os.path.basename(img_path))[0]
    salida = _escribir_iso_de_imagen(img_path, out_path, tamano, 0, total,
                                     volumen)
    salida["nota"] = f"imagen del {etiqueta} convertida a ISO"
    return salida


def mds_to_iso(mds_path: str, out_path: str | None = None) -> dict:
    """Convierte un MDS (Alcohol 120%) en un ISO de 2048 bytes por sector.

    El MDS es un descriptor: dice como es el disco y en que fichero estan los
    datos (el IMG o el MDF que estan al lado).
    """
    return _descriptor_a_iso(mds_path, out_path, "MDS")


def ccd_to_iso(ccd_path: str, out_path: str | None = None) -> dict:
    """Convierte un CCD (CloneCD) en un ISO de 2048 bytes por sector.

    El CCD es un descriptor: dice como es el disco y en que fichero estan los
    datos (el IMG que esta al lado).
    """
    return _descriptor_a_iso(ccd_path, out_path, "CCD")


def img_to_iso(img_path: str, out_path: str | None = None) -> dict:
    """Convierte una imagen en crudo (2352 bytes por sector) en un ISO."""
    img_path = os.path.abspath(img_path)
    out_path = out_path or _salida_libre(img_path, ".iso")
    tamano = _tamano_sector(img_path)
    total = _size(img_path) // tamano
    if total <= 0:
        raise ValueError("la imagen esta vacia")
    volumen = os.path.splitext(os.path.basename(img_path))[0]
    salida = _escribir_iso_de_imagen(img_path, out_path, tamano, 0, total,
                                     volumen)
    salida["nota"] = "imagen en crudo convertida a ISO"
    return salida


def cdi_to_iso(cdi_path: str, out_path: str | None = None) -> dict:
    """Convierte un CDI (DiscJuggler) en un ISO.

    El CDI es un contenedor binario propietario de DiscJuggler: con la
    biblioteca estandar no se puede leer con fiabilidad, asi que se explica y
    no se inventa una conversion que salga mal.
    """
    raise ValueError("no se sabe leer este CDI (DiscJuggler): "
                     "usa un GDI o un BIN/CUE del mismo disco")


def mdf_a_iso(mdf_path: str, out_path: str | None = None) -> dict:
    """El MDF, el CCD, el IMG y el MDS: cada uno se lee de una manera."""
    ext = os.path.splitext(mdf_path)[1].lower()
    if ext == ".mds":
        return mds_to_iso(mdf_path, out_path)
    if ext == ".ccd":
        return ccd_to_iso(mdf_path, out_path)
    if ext == ".img":
        return img_to_iso(mdf_path, out_path)
    raise ValueError("no se sabe leer este MDF (Alcohol 120%): "
                     "usa el descriptor .mds que va con el")


# ── NRG (Nero) ──────────────────────────────────────────────────────────

def _firma_nrg(path: str) -> bool:
    """Si el fichero es un NRG de Nero.

    La firma no esta al principio, sino en el pie: cuatro bytes de
    identificador ("NERO" en la version 1 y "NER5" en la 2) seguidos del
    desplazamiento del primer chunk.
    """
    cola = _cola(path, 12)
    if len(cola) >= 12 and cola[-12:-8] == b"NER5":
        return True
    if len(cola) >= 8 and cola[-8:-4] == b"NERO":
        return True
    return False


def _nrg_chunks(nrg_path: str) -> dict:
    """Los chunks del NRG, que van al final del fichero.

    El pie del NRG dice donde empieza la cadena de chunks: cuatro bytes de
    identificador ("NERO" en la version 1 y "NER5" en la 2) y el
    desplazamiento del primer chunk (32 bits o 64 bits segun la version).
    """
    with open(nrg_path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        total = fh.tell()
        fh.seek(max(total - 12, 0))
        pie = fh.read()
        if len(pie) >= 12 and pie[-12:-8] == b"NER5":
            inicio = struct.unpack(">Q", pie[-8:])[0]
        elif len(pie) >= 8 and pie[-8:-4] == b"NERO":
            inicio = struct.unpack(">I", pie[-4:])[0]
        else:
            raise ValueError("no es un NRG de Nero")
        fh.seek(inicio)
        chunks = {}
        while True:
            cabecera = fh.read(8)
            if len(cabecera) < 8:
                break
            identificador = cabecera[:4]
            (tamano,) = struct.unpack(">I", cabecera[4:8])
            if identificador == b"END!":
                break
            cuerpo = fh.read(tamano)
            if len(cuerpo) < tamano:
                break
            chunks[identificador] = cuerpo
    return chunks


def _nrg_pistas_dao(cuerpo: bytes, version2: bool) -> list:
    """Las pistas de un chunk DAOI/DAOX (disco a disco).

    El chunk lleva una cabecera (el UPC, el tipo de TOC y el numero de
    pistas) y despues una entrada por pista: su ISRC, el tamano de sector, el
    modo y los desplazamientos de los tres indices.
    """
    pistas = []
    pos = 22                     # cabecera del chunk
    ancho = 8 if version2 else 4
    tamano = 18 + 3 * ancho
    while pos + tamano <= len(cuerpo):
        (sector_size,) = struct.unpack(">H", cuerpo[pos + 12:pos + 14])
        (modo,) = struct.unpack(">H", cuerpo[pos + 14:pos + 16])
        pos += 18
        if version2:
            idx0, idx1, fin = struct.unpack(">QQQ", cuerpo[pos:pos + 24])
        else:
            idx0, idx1, fin = struct.unpack(">III", cuerpo[pos:pos + 12])
        pos += 3 * ancho
        pistas.append({"sector_size": sector_size, "modo": modo,
                       "pregap": idx0, "inicio": idx1, "fin": fin})
    return pistas


def _nrg_pistas_tao(cuerpo: bytes, version2: bool) -> list:
    """Las pistas de un chunk ETNF/ETN2 (pista a pista).

    Cada entrada dice el desplazamiento en el fichero, la longitud en bytes,
    el modo, el sector del disco donde empieza la pista y un dato sin usar.
    """
    pistas = []
    pos = 0
    ancho = 8 if version2 else 4
    tamano = 12 + 8 + ancho
    while pos + tamano <= len(cuerpo):
        if version2:
            (inicio,) = struct.unpack(">Q", cuerpo[pos:pos + 8])
            (longitud,) = struct.unpack(">Q", cuerpo[pos + 8:pos + 16])
            (modo,) = struct.unpack(">I", cuerpo[pos + 16:pos + 20])
            (lba,) = struct.unpack(">I", cuerpo[pos + 20:pos + 24])
        else:
            (inicio,) = struct.unpack(">I", cuerpo[pos:pos + 4])
            (longitud,) = struct.unpack(">I", cuerpo[pos + 4:pos + 8])
            (modo,) = struct.unpack(">I", cuerpo[pos + 8:pos + 12])
            (lba,) = struct.unpack(">I", cuerpo[pos + 12:pos + 16])
        pos += tamano
        pistas.append({"inicio": inicio, "longitud": longitud, "modo": modo,
                       "lba": lba, "sector_size": 0})
    return pistas


def _nrg_cue(cuerpo: bytes, version2: bool) -> list:
    """Las entradas del cue sheet: el control y el sector de cada indice."""
    entradas = []
    ancho = 8 if version2 else 4
    pos = 0
    while pos + 8 + ancho <= len(cuerpo):
        control = cuerpo[pos]
        numero = cuerpo[pos + 1]
        indice = cuerpo[pos + 2]
        if version2:
            (lba,) = struct.unpack(">i", cuerpo[pos + 4:pos + 8])
        else:
            lba = (cuerpo[pos + 5] * 60 + cuerpo[pos + 6]) * 75 + cuerpo[pos + 7]
        entradas.append({"control": control, "pista": numero,
                         "indice": indice, "lba": lba})
        pos += 8 + ancho
    return entradas


def _nrg_tamano_sector(nrg_path: str, inicio: int, longitud: int) -> int:
    """De que tamano son los sectores de la pista, mirando el primer sector.

    Un sector en crudo empieza con la sincronizacion (12 bytes de 00 y 10 de
    FF); si no la tiene, son sectores de 2048 o de 2336 bytes.
    """
    try:
        with open(nrg_path, "rb") as fh:
            fh.seek(inicio)
            primero = fh.read(16)
    except OSError:
        primero = b""
    if primero[:12] == b"\x00" + b"\xff" * 10 + b"\x00":
        return SECTOR_RAW
    for tamano in (SECTOR_ISO, 2336):
        if longitud and longitud % tamano == 0:
            return tamano
    return SECTOR_ISO


def nrg_to_iso(nrg_path: str, out_path: str | None = None) -> dict:
    """Convierte un NRG (Nero) en un ISO de 2048 bytes por sector.

    El NRG es un fichero de Nero: los datos del disco estan al principio y al
    final hay una cadena de chunks con la tabla de pistas. De las pistas solo
    se mete la de datos, que es la que lleva el sistema de ficheros.
    """
    nrg_path = os.path.abspath(nrg_path)
    out_path = out_path or _salida_libre(nrg_path, ".iso")
    chunks = _nrg_chunks(nrg_path)

    pistas = []
    lbas = {}
    if b"DAOX" in chunks or b"DAOI" in chunks:
        version2 = b"DAOX" in chunks
        identificador = b"DAOX" if version2 else b"DAOI"
        pistas = _nrg_pistas_dao(chunks[identificador], version2)
        if b"CUEX" in chunks:
            for entrada in _nrg_cue(chunks[b"CUEX"], True):
                if entrada["indice"] == 1:
                    lbas[entrada["pista"]] = entrada["lba"]
        elif b"CUES" in chunks:
            for entrada in _nrg_cue(chunks[b"CUES"], False):
                if entrada["indice"] == 1:
                    lbas[entrada["pista"]] = entrada["lba"]
    elif b"ETN2" in chunks or b"ETNF" in chunks:
        version2 = b"ETN2" in chunks
        identificador = b"ETN2" if version2 else b"ETNF"
        pistas = _nrg_pistas_tao(chunks[identificador], version2)
    if not pistas:
        raise ValueError("el NRG no dice como son sus pistas")

    # La pista de datos es la que tiene el control de datos en el cue sheet
    # (0x40) o, si no hay cue sheet, la que guarda sectores de 2048 bytes.
    elegida = None
    for numero, pista in enumerate(pistas, start=1):
        if pista.get("sector_size") == SECTOR_ISO:
            elegida = pista
            break
    if elegida is None and pistas:
        elegida = pistas[0]

    tamano = elegida.get("sector_size") or 0
    if tamano not in _TAMANOS_SECTOR:
        tamano = _nrg_tamano_sector(nrg_path, elegida["inicio"],
                                    elegida.get("longitud", 0))
    if tamano not in _TAMANOS_SECTOR:
        tamano = SECTOR_ISO

    lba = elegida.get("lba")
    if lba is None:
        lba = lbas.get(1, 0)
    # El desplazamiento de la pista es el de su sector 0: el sector 0 del
    # disco esta antes, si la pista no empieza en el.
    inicio = elegida["inicio"] - lba * tamano
    if inicio < 0:
        inicio = elegida["inicio"]

    if "longitud" in elegida and elegida["longitud"]:
        cuantos = elegida["longitud"] // tamano
    else:
        cuantos = (elegida["fin"] - elegida["inicio"]) // tamano
    if cuantos <= 0:
        raise ValueError("el NRG no dice cuantos sectores tiene la pista de datos")

    volumen = os.path.splitext(os.path.basename(nrg_path))[0]
    salida = _escribir_iso_de_imagen(nrg_path, out_path, tamano, inicio,
                                     cuantos, volumen)
    salida["nota"] = "pista de datos extraida del NRG"
    return salida


# ── El despachador ──────────────────────────────────────────────────────

def convert(path: str, target: str, out_path: str | None = None,
            sistema: str | None = None) -> dict:
    """Convierte un fichero al formato pedido.

    ``target`` es el identificador de una capacidad (los de
    :data:`CAPACIDADES`), no una etiqueta de texto.
    """
    path = os.path.abspath(path)
    target = (target or "").lower()
    if not target:
        raise ValueError("no se ha dicho a que formato convertir")
    info = detect_format(path, sistema)
    kind = info.kind

    if target == "zip":
        return compress_zip(path, out_path or _salida_libre(path, ".zip"))
    if target == "7z":
        return compress_7z(path, out_path or _salida_libre(path, ".7z"))
    if target == "extraer":
        if kind == "zip":
            return extract_zip(path, out_path)
        if kind == "7z":
            return extract_7z(path, out_path)
        raise ValueError("solo se puede extraer un ZIP o un 7Z")
    if target == "rvz":
        raise ValueError("no se puede convertir a RVZ: falta la utilidad dolphin-tool")
    if target in ("wbfs", "wia"):
        raise ValueError(f"no se puede convertir a {target.upper()}: "
                         "falta la utilidad wiitool")
        return extract_zip(path, out_path)
    if target in ("n64", "z64", "v64"):
        return n64_convert(path, target, out_path)
    if target in ("sfc", "smc", "fig"):
        return snes_convert(path, target, out_path)
    if target == "iso":
        return _a_iso(path, kind, out_path)
    if target == "bin-cue":
        return _a_bin_cue(path, kind, out_path)
    if target == "pbp":
        return _a_pbp(path, kind, out_path)
    if target == "chd":
        return _a_chd(path, kind, out_path)
    if target == "gcz":
        return _a_gcz(path, kind, out_path)
    if target == "ciso":
        return _a_ciso(path, kind, out_path)
    if target == "cso":
        return _a_cso(path, kind, out_path)

    raise ValueError(f"conversion no soportada: {target}")


def _a_iso(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva cualquier disco a un ISO de 2048 bytes por sector."""
    salida = out_path or _salida_libre(path, ".iso")
    if kind == "bin-cue":
        cue = path if path.lower().endswith(".cue") else _cue_for_bin(path)
        if cue:
            return bin_cue_to_iso(cue, salida)
        return raw_bin_to_iso(path, salida)
    if kind.startswith("iso"):
        return {"ok": True, "out": path, "nota": "ya era un ISO"}
    if kind == "pbp":
        stem = _stem_libre(path)
        _pbp_a_bin_cue(path, stem + ".bin", stem + ".cue")
        try:
            return bin_cue_to_iso(stem + ".cue", salida)
        finally:
            for sobra in (stem + ".bin", stem + ".cue"):
                if os.path.exists(sobra):
                    os.remove(sobra)
    if kind == "xiso":
        return xiso_to_iso(path, salida)
    if kind == "gcm":
        return gcm_to_iso(path, salida)
    if kind == "chd":
        return chd_to_iso(path, salida)
    if kind == "cso":
        return cso_to_iso(path, salida)
    if kind == "gcz":
        return gcz_to_iso(path, salida)
    if kind == "ciso":
        return ciso_to_iso(path, salida)
    if kind == "gdi":
        return gdi_to_iso(path, salida)
    if kind == "mdf":
        return mdf_a_iso(path, salida)
    if kind == "cdi":
        return cdi_to_iso(path, salida)
    if kind == "nrg":
        return nrg_to_iso(path, salida)
    raise ValueError(f"no se puede convertir de {kind} a ISO")


def _a_bin_cue(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un disco a un BIN de 2352 bytes con su CUE."""
    if kind == "bin-cue":
        return {"ok": True, "out": path, "nota": "ya era un BIN/CUE"}
    if kind.startswith("iso"):
        if out_path:
            out_bin = out_path if out_path.lower().endswith(".bin") else out_path + ".bin"
            out_cue = os.path.splitext(out_bin)[0] + ".cue"
        else:
            stem = _stem_libre(path)
            out_bin = stem + ".bin"
            out_cue = stem + ".cue"
        iso_to_bin_cue(path, out_bin, out_cue)
        return {"ok": True, "out": out_bin, "cue": out_cue,
                "size": os.path.getsize(out_bin),
                "nota": "convertido a BIN/CUE"}
    if kind == "chd":
        return chd_to_bin_cue(path, out_path)
    if kind == "pbp":
        stem = _stem_libre(path)
        out_bin = stem + ".bin"
        out_cue = stem + ".cue"
        _pbp_a_bin_cue(path, out_bin, out_cue)
        return {"ok": True, "out": out_bin, "cue": out_cue,
                "size": os.path.getsize(out_bin),
                "nota": "convertido a BIN/CUE"}
    raise ValueError(f"no se puede convertir de {kind} a BIN/CUE")


def _a_pbp(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un disco de PlayStation a un PBP."""
    if kind == "pbp":
        return {"ok": True, "out": path, "nota": "ya era un PBP"}
    if kind == "bin-cue":
        cue = path if path.lower().endswith(".cue") else _cue_for_bin(path)
        if not cue:
            raise ValueError("para convertir a PBP hace falta el CUE del BIN")
        salida = out_path or _salida_libre(cue, ".pbp")
        return bin_cue_to_pbp(cue, salida)
    if kind == "iso-ps1":
        salida = out_path or _salida_libre(path, ".pbp")
        return _iso_a_pbp(path, salida)
    if kind == "iso":
        salida = out_path or _salida_libre(path, ".pbp")
        return _iso_a_pbp(path, salida)
    raise ValueError(f"no se puede convertir de {kind} a PBP")


def _a_chd(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un ISO a un CHD."""
    if kind == "chd":
        return {"ok": True, "out": path, "nota": "ya era un CHD"}
    if not kind.startswith("iso"):
        raise ValueError(f"no se puede convertir de {kind} a CHD")
    salida = out_path or _salida_libre(path, ".chd")
    return iso_to_chd(path, salida)


def _a_gcz(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un ISO de GameCube a un GCZ."""
    if kind == "gcz":
        return {"ok": True, "out": path, "nota": "ya era un GCZ"}
    if not kind.startswith("iso"):
        raise ValueError(f"no se puede convertir de {kind} a GCZ")
    salida = out_path or _salida_libre(path, ".gcz")
    return iso_to_gcz(path, salida)


def _a_ciso(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un ISO de GameCube o Wii a un CISO."""
    if kind == "ciso":
        return {"ok": True, "out": path, "nota": "ya era un CISO"}
    if not kind.startswith("iso"):
        raise ValueError(f"no se puede convertir de {kind} a CISO")
    salida = out_path or _salida_libre(path, ".ciso")
    return iso_to_ciso(path, salida)


def _a_cso(path: str, kind: str, out_path: str | None = None) -> dict:
    """Lleva un ISO de PSP a un CSO."""
    if kind == "cso":
        return {"ok": True, "out": path, "nota": "ya era un CSO"}
    if not kind.startswith("iso"):
        raise ValueError(f"no se puede convertir de {kind} a CSO")
    salida = out_path or _salida_libre(path, ".cso")
    return iso_to_cso(path, salida)


def _pbp_a_bin_cue(pbp_path: str, out_bin: str, out_cue: str) -> dict:
    """Saca los datos de un PBP a un BIN y escribe su CUE."""
    with open(pbp_path, "rb") as fh:
        head = fh.read(0x100)
        if not head.startswith(b"PBP\x01"):
            raise ValueError("no es un fichero PBP")
        offsets = struct.unpack(">5I", head[4:0x18])
        fh.seek(offsets[0])
        with open(out_bin, "wb") as dst:
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)
    _escribir_cue(out_bin, out_cue)
    return {"ok": True, "out": out_bin, "cue": out_cue,
            "size": os.path.getsize(out_bin)}


def _iso_a_pbp(iso_path: str, out_path: str) -> dict:
    """De un ISO de PlayStation a un PBP."""
    stem = _stem_libre(iso_path)
    out_bin = stem + ".bin"
    out_cue = stem + ".cue"
    try:
        iso_to_bin_cue(iso_path, out_bin, out_cue)
        return bin_cue_to_pbp(out_cue, out_path)
    finally:
        for sobra in (out_bin, out_cue):
            if os.path.exists(sobra):
                os.remove(sobra)


def _replace_ext(path: str, ext: str) -> str:
    return os.path.splitext(path)[0] + ext


# ── Compresion ──────────────────────────────────────────────────────────

def compress_zip(path: str, out_path: str | None = None,
                 level: int = 6) -> dict:
    """Comprime un fichero (o una carpeta) en un ZIP."""
    path = os.path.abspath(path)
    out_path = out_path or _replace_ext(path, ".zip")
    if os.path.isdir(path):
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=level) as zf:
            base = os.path.dirname(path)
            for root, _dirs, files in os.walk(path):
                for name in files:
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, base))
    else:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=level) as zf:
            zf.write(path, os.path.basename(path))
    return {"ok": True, "out": out_path,
            "size": os.path.getsize(out_path),
            "before": _size(path)}


def decompress_zip(path: str, out_dir: str | None = None) -> dict:
    """Descomprime un ZIP junto al propio fichero."""
    path = os.path.abspath(path)
    out_dir = out_dir or os.path.dirname(path)
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            target = os.path.normpath(os.path.join(out_dir, member))
            if not target.startswith(os.path.abspath(out_dir)):
                raise ValueError("el ZIP intenta escribir fuera de la carpeta")
        zf.extractall(out_dir)
    return {"ok": True, "out": out_dir}


# ── Parches IPS ─────────────────────────────────────────────────────────

def parse_ips(ips_path: str) -> list:
    """Lee un parche IPS y devuelve la lista de escrituras."""
    with open(ips_path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"PATCH"):
        raise ValueError("no es un parche IPS")
    pos = 5
    writes = []
    while pos < len(data):
        if data[pos:pos + 3] == b"EOF":
            pos += 3
            break
        if pos + 5 > len(data):
            break
        offset = int.from_bytes(data[pos:pos + 3], "big")
        size = int.from_bytes(data[pos + 3:pos + 5], "big")
        pos += 5
        if size == 0:
            if pos + 3 > len(data):
                break
            length = int.from_bytes(data[pos:pos + 2], "big")
            value = data[pos + 2:pos + 3]
            pos += 3
            writes.append((offset, value * length))
        else:
            if pos + size > len(data):
                break
            writes.append((offset, data[pos:pos + size]))
            pos += size
    return writes


def apply_ips(rom_path: str, ips_path: str, backup: bool = True) -> dict:
    """Aplica un parche IPS a una ROM.

    Se guarda una copia del original (``.bak``) para poder deshacerlo: el
    formato IPS no lleva los bytes originales, asi que el unico modo de volver
    atras es guardarlos.
    """
    writes = parse_ips(ips_path)
    if not writes:
        raise ValueError("el parche no escribe nada")
    backup_path = None
    if backup:
        backup_path = rom_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(rom_path, backup_path)

    with open(rom_path, "r+b") as fh:
        for offset, payload in writes:
            fh.seek(offset)
            fh.write(payload)
    return {"ok": True, "rom": rom_path, "backup": backup_path,
            "writes": len(writes),
            "size": os.path.getsize(rom_path)}


def revert_ips(rom_path: str) -> dict:
    """Deshace un parche IPS restaurando la copia del original."""
    backup_path = rom_path + ".bak"
    if not os.path.exists(backup_path):
        raise ValueError("no hay copia del original: no se puede deshacer")
    shutil.copy2(backup_path, rom_path)
    return {"ok": True, "rom": rom_path, "backup": backup_path}


def revert_ips_and_cleanup(rom_path: str) -> dict:
    """Deshace el parche y borra la copia (la operacion completa)."""
    out = revert_ips(rom_path)
    backup = out.get("backup")
    if backup and os.path.exists(backup):
        os.remove(backup)
    return out
