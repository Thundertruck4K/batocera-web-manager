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

import os
import re
import shutil
import struct
import zipfile
import zlib
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


#: Como se llama cada formato y que se puede hacer con el.
FORMAT_CATALOGUE = {
    "bin-cue": ("BIN + CUE", ["convertir a ISO", "convertir a PBP", "comprimir", "identificar"]),
    "iso": ("ISO 9660", ["convertir a BIN/CUE", "comprimir", "identificar"]),
    "pbp": ("PBP (PlayStation)", ["convertir a BIN/CUE", "comprimir", "identificar"]),
    "xiso": ("XDVDF (Xbox)", ["convertir a ISO", "comprimir", "identificar"]),
    "gcm": ("GCM (GameCube)", ["convertir a ISO", "comprimir", "identificar"]),
    "gciso": ("GCISO (GameCube)", ["comprimir", "identificar"]),
    "chd": ("CHD (compressed hunks)", ["convertir a ISO", "identificar"]),
    "wbfs": ("WBFS (Wii)", ["identificar"]),
    "wia": ("WIA (Wii)", ["identificar"]),
    "rvz": ("RVZ", ["identificar"]),
    "mdf": ("MDF / CCD / IMG", ["identificar"]),
    "g64": ("G64 / NDD", ["identificar"]),
    "3do": ("3DO", ["identificar"]),
    "wad": ("WAD (Nintendo DS)", ["identificar"]),
    "nsp": ("NSP (Nintendo Switch)", ["identificar"]),
    "zip": ("ZIP", ["descomprimir", "identificar"]),
    "ips": ("Parche IPS", ["aplicar"]),
    "bps": ("Parche BPS", ["identificar"]),
}

#: Formatos que se pueden convertir a ISO.
CONVERTIBLE_TO_ISO = ("bin-cue", "iso", "pbp", "xiso", "gcm", "chd")


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


def detect_format(path: str) -> FormatInfo:
    """Detecta el formato de un fichero de ROM."""
    path = os.path.abspath(path)
    size = _size(path)
    ext = os.path.splitext(path)[1].lower()
    stem = os.path.splitext(os.path.basename(path))[0]

    info = FormatInfo(path=path, size=size)

    # Un .cue describe su BIN: se mira el binario, no el texto.
    if ext == ".cue":
        bin_path = _bin_for_cue(path)
        if bin_path:
            info.kind = "bin-cue"
            info.label = FORMAT_CATALOGUE["bin-cue"][0]
            info.details = {"bin": os.path.basename(bin_path),
                            "cue": os.path.basename(path)}
            info.actions = list(FORMAT_CATALOGUE["bin-cue"][1])
            return info

    head = _head(path, 0x100)

    if head.startswith(b"MComprHD"):
        info.kind = "chd"
        info.label = FORMAT_CATALOGUE["chd"][0]
        info.details = _chd_header(path)
        info.actions = list(FORMAT_CATALOGUE["chd"][1])
        return info

    if head.startswith(b"WBFS"):
        info.kind = "wbfs"
        info.label = FORMAT_CATALOGUE["wbfs"][0]
        info.details = _wbfs_header(path)
        info.actions = list(FORMAT_CATALOGUE["wbfs"][1])
        return info

    if head.startswith(b"WIA\x00"):
        info.kind = "wia"
        info.label = FORMAT_CATALOGUE["wia"][0]
        info.actions = list(FORMAT_CATALOGUE["wia"][1])
        return info

    if head.startswith(b"RVZ\x00"):
        info.kind = "rvz"
        info.label = FORMAT_CATALOGUE["rvz"][0]
        info.actions = list(FORMAT_CATALOGUE["rvz"][1])
        return info

    if head.startswith(b"PBP\x01"):
        info.kind = "pbp"
        info.label = FORMAT_CATALOGUE["pbp"][0]
        info.details = _pbp_header(path)
        info.actions = list(FORMAT_CATALOGUE["pbp"][1])
        return info

    if head.startswith(b"MICROSOFT*XBOX*MEDIA") or b"XBOXMEDIA" in head[:0x10000]:
        info.kind = "xiso"
        info.label = FORMAT_CATALOGUE["xiso"][0]
        info.actions = list(FORMAT_CATALOGUE["xiso"][1])
        return info

    if ext == ".gcm":
        info.kind = "gcm"
        info.label = FORMAT_CATALOGUE["gcm"][0]
        info.actions = list(FORMAT_CATALOGUE["gcm"][1])
        return info

    if ext == ".wbfs":
        info.kind = "wbfs"
        info.label = FORMAT_CATALOGUE["wbfs"][0]
        info.actions = list(FORMAT_CATALOGUE["wbfs"][1])
        return info

    if ext in (".iso", ".bin") and _looks_iso(path):
        info.kind = "iso"
        info.label = FORMAT_CATALOGUE["iso"][0]
        info.details = {"volume_id": _iso_volume_id(path)}
        info.actions = list(FORMAT_CATALOGUE["iso"][1])
        return info

    if ext in (".iso", ".gci") and head[0x14:0x18] == b"\x00\x00\x00\x00":
        pass  # sigue siendo ISO: la comprobacion de arriba ya lo ha cubierto

    if ext in (".mdf", ".img", ".ccd"):
        info.kind = "mdf"
        info.label = FORMAT_CATALOGUE["mdf"][0]
        info.actions = list(FORMAT_CATALOGUE["mdf"][1])
        return info

    if ext in (".g64", ".ndd"):
        info.kind = "g64"
        info.label = FORMAT_CATALOGUE["g64"][0]
        info.actions = list(FORMAT_CATALOGUE["g64"][1])
        return info

    if ext in (".3do", ".iso3"):
        info.kind = "3do"
        info.label = FORMAT_CATALOGUE["3do"][0]
        info.actions = list(FORMAT_CATALOGUE["3do"][1])
        return info

    if ext == ".wad":
        info.kind = "wad"
        info.label = FORMAT_CATALOGUE["wad"][0]
        info.actions = list(FORMAT_CATALOGUE["wad"][1])
        return info

    if ext == ".nsp":
        info.kind = "nsp"
        info.label = FORMAT_CATALOGUE["nsp"][0]
        info.actions = list(FORMAT_CATALOGUE["nsp"][1])
        return info

    if ext in (".zip", ".gz", ".7z", ".rar"):
        info.kind = "zip" if ext == ".zip" else "archive"
        info.label = "ZIP" if ext == ".zip" else f"Archivo {ext[1:].upper()}"
        info.actions = list(FORMAT_CATALOGUE["zip"][1]) if ext == ".zip" else []
        return info

    if ext == ".ips":
        info.kind = "ips"
        info.label = FORMAT_CATALOGUE["ips"][0]
        info.actions = list(FORMAT_CATALOGUE["ips"][1])
        return info

    if ext == ".bps":
        info.kind = "bps"
        info.label = FORMAT_CATALOGUE["bps"][0]
        info.actions = list(FORMAT_CATALOGUE["bps"][1])
        return info

    # Un .bin con CUE hermano es un set BIN+CUE completo: se ofrecen todas
    # las conversiones, no solo las de un BIN suelto.
    if ext == ".bin":
        cue = _cue_for_bin(path)
        if cue:
            info.kind = "bin-cue"
            info.label = FORMAT_CATALOGUE["bin-cue"][0]
            info.details = {"bin": os.path.basename(path),
                            "cue": os.path.basename(cue)}
            info.actions = list(FORMAT_CATALOGUE["bin-cue"][1])
            return info

    # Un .bin suelto (sin CUE) es un volcado de 2352 bytes por sector.
    if ext == ".bin" and size % SECTOR_RAW == 0 and size > 0:
        info.kind = "bin-cue"
        info.label = "BIN (sin CUE)"
        info.details = {"sectors": size // SECTOR_RAW}
        info.actions = ["convertir a ISO", "comprimir", "identificar"]
        return info

    info.details = {"ext": ext}
    return info


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


def build_iso(sectors: Iterable[bytes], volume_id: str = "BWM") -> bytes:
    """Construye un ISO 9660 valido a partir de sectores de 2048 bytes.

    Es el mismo esqueleto que usan las herramientas de conversion clasicas:
    area de sistema, descriptor de volumen, tabla de rutas, directorio raiz y
    los datos.
    """
    data = bytearray()
    for sector in sectors:
        data.extend(sector[:SECTOR_ISO].ljust(SECTOR_ISO, b"\x00"))
    total_data = len(data) // SECTOR_ISO

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
    out.extend(data)
    return bytes(out)


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
    with open(out_path, "wb") as fh:
        fh.write(build_iso(sectors(), volume_id=volume))
    return {"ok": True, "out": out_path,
            "size": os.path.getsize(out_path),
            "note": "solo la primera pista de datos"}


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
    with open(out_path, "wb") as fh:
        fh.write(build_iso(sectors(), volume_id=volume))
    return {"ok": True, "out": out_path,
            "size": os.path.getsize(out_path),
            "note": "el BIN no tenia CUE: se han usado los sectores en bruto"}


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


def chd_to_iso(chd_path: str, out_path: str | None = None) -> dict:
    """Extrae el contenido de un CHD v5 (compresion zlib) a un BIN.

    El CHD guarda los datos en «hunks» comprimidos, con una tabla que dice
    cuanto ocupa cada uno. Se leen en orden y se descomprimen con zlib.
    """
    out_path = out_path or os.path.splitext(chd_path)[0] + ".bin"
    with open(chd_path, "rb") as fh:
        head = fh.read(0x100)
        if not head.startswith(b"MComprHD"):
            raise ValueError("no es un CHD")
        version, _flags, compression = struct.unpack(">III", head[8:20])
        if version < 5:
            raise ValueError(f"solo se pueden leer los CHD v5 (este es v{version})")
        if compression not in (0, 1):
            raise ValueError(f"solo se puede descomprimir zlib o sin comprimir (este usa {compression})")
        total_frames, bytes_per_frame = struct.unpack(">II", head[0x18:0x20])
        total_hunks, = struct.unpack(">I", head[0x28:0x2C])
        data_offset, _meta_offset, map_offset = struct.unpack(">QQQ", head[0x50:0x68])
        fh.seek(map_offset)
        map_data = fh.read(total_hunks * 4)
        sizes = struct.unpack(f">{total_hunks}I", map_data)

        fh.seek(data_offset)
        with open(out_path, "wb") as dst:
            for size in sizes:
                chunk = fh.read(size)
                if compression == 1:
                    chunk = zlib.decompress(chunk)
                dst.write(chunk)
    return {"ok": True, "out": out_path, "size": os.path.getsize(out_path),
            "frames": total_frames, "bytes_per_frame": bytes_per_frame}


def convert(path: str, target: str, out_path: str | None = None) -> dict:
    """Convierte un fichero al formato pedido."""
    path = os.path.abspath(path)
    info = detect_format(path)
    target = (target or "").lower()

    if target == "iso":
        if info.kind == "bin-cue":
            if path.lower().endswith(".cue"):
                return bin_cue_to_iso(path, out_path or _replace_ext(path, ".iso"))
            # El BIN puede traerse su CUE al lado o no: con CUE se respeta la
            # pista que dice el CUE; sin CUE se usan los sectores en bruto.
            cue = _cue_for_bin(path)
            if cue:
                return bin_cue_to_iso(cue, out_path or _replace_ext(path, ".iso"))
            return raw_bin_to_iso(path, out_path or _replace_ext(path, ".iso"))
        if info.kind == "iso":
            return {"ok": True, "out": path, "note": "ya era un ISO"}
        if info.kind == "pbp":
            out_dir = os.path.dirname(path)
            tmp = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".bin")
            pbp_to_bin_cue(path, out_dir)
            cue = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".cue")
            return bin_cue_to_iso(cue, out_path or _replace_ext(path, ".iso"))
        if info.kind == "xiso":
            return xiso_to_iso(path, out_path or _replace_ext(path, ".iso"))
        if info.kind == "gcm":
            return gcm_to_iso(path, out_path or _replace_ext(path, ".iso"))
        if info.kind == "chd":
            out = out_path or _replace_ext(path, ".bin")
            return chd_to_iso(path, out)
        raise ValueError(f"no se puede convertir de {info.label} a ISO")

    if target == "bin-cue":
        if info.kind == "iso":
            return iso_to_bin_cue(path, out_path)
        if info.kind == "pbp":
            return pbp_to_bin_cue(path, out_path and os.path.dirname(out_path))
        raise ValueError(f"no se puede convertir de {info.label} a BIN/CUE")

    if target == "pbp":
        if info.kind == "bin-cue":
            if path.lower().endswith(".cue"):
                cue = path
            else:
                cue = _cue_for_bin(path)
            if not cue:
                raise ValueError("para convertir a PBP hace falta el CUE del BIN")
            return bin_cue_to_pbp(cue, out_path or _replace_ext(cue, ".pbp"))
        raise ValueError(f"no se puede convertir de {info.label} a PBP")

    raise ValueError(f"conversion no soportada: {target}")


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
