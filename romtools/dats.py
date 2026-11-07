"""DAT: donde seatomy, como se descargan y como se indexan.

Un DAT es un XML con la lista de juegos de un sistema: como se llama cada
fichero, de que tamano es y que hashes tiene. Es la lista con la que se
compara una ROM para saber que juego es y como se debe llamar. El nombre que
manda es el del DAT: eso es justo lo que hace Romulus Manager, que no inventa
nombres, los copia del DAT importado.

De donde salen
-------------

La fuente principal es el **espejo de libretro-database**, que publica los DAT
de Redump (discos) y de No-Intro (cartuchos) como ficheros sueltos y
estables, con los hashes y el serial:

    https://raw.githubusercontent.com/libretro/libretro-database/master/
        metadat/redump/Sony - PlayStation 2.dat
        metadat/no-intro/Nintendo - Super Nintendo Entertainment System.dat

Como alternativa, el **rebuild diario** de Redump y No-Intro publica un indice
clrmamepro y un ZIP con todos los DAT dentro. Se usa para los sistemas que
libretro no tiene. De ese ZIP solo se descarga el DAT que interesa: se lee el
directorio central con peticiones por rango y se baja solo su parte
comprimida, en vez de bajar 27 MB (Redump) o 106 MB (No-Intro) enteros.

    https://github.com/hugo19941994/auto-datfile-generator/releases/
        download/Daily_Rebuild/redump.zip

Como se guardan
---------------

En ``/userdata/system/batocera_manager_dats`` queda:

    <slug>.dat          el DAT descargado
    <slug>.json         el indice ya parseado (para no reparsear el XML)

El indice en memoria tiene cuatro mapas: por hash, por serial, por nombre de
fichero y por titulo.
"""

from __future__ import annotations

import io
import json
import os
import re
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from typing import Callable, Iterable, Sequence

from .identify import normalize_title

#: Carpeta donde viven los DAT (dentro de /userdata/system).
DAT_DIR_NAME = "batocera_manager_dats"

#: Release del rebuild diario de Redump y No-Intro.
_MIRROR = ("https://github.com/hugo19941994/auto-datfile-generator/releases/"
           "download/Daily_Rebuild/")

#: Espejo de libretro-database: ficheros sueltos, sin tokens ni scraping.
_LIBRETRO = ("https://raw.githubusercontent.com/libretro/libretro-database/"
             "master/metadat/")

#: Fuentes de DAT conocidas.
SOURCES = {
    "libretro-redump": {
        "name": "Redump (libretro)",
        "author": "redump.org",
        "kind": "discos",
        "base": _LIBRETRO + "redump/",
        "files": True,
    },
    "libretro-no-intro": {
        "name": "No-Intro (libretro)",
        "author": "no-intro.org",
        "kind": "cartuchos",
        "base": _LIBRETRO + "no-intro/",
        "files": True,
    },
    "redump": {
        "name": "Redump (rebuild diario)",
        "author": "redump.org",
        "kind": "discos",
        "index": _MIRROR + "redump.xml",
        "bundle": _MIRROR + "redump.zip",
        "files": False,
    },
    "no-intro": {
        "name": "No-Intro (rebuild diario)",
        "author": "no-intro.org",
        "kind": "cartuchos",
        "index": _MIRROR + "no-intro.xml",
        "bundle": _MIRROR + "no-intro.zip",
        "files": False,
    },
}

#: De cada sistema de Batocera, que DAT le toca. El nombre es exactamente el
#: del fichero en el espejo de libretro.
SYSTEM_DAT = {
    # ── Discos: Redump ──
    "psx": ("libretro-redump", "Sony - PlayStation"),
    "ps2": ("libretro-redump", "Sony - PlayStation 2"),
    "ps3": ("libretro-redump", "Sony - PlayStation 3"),
    "psp": ("libretro-redump", "Sony - PlayStation Portable"),
    "saturn": ("libretro-redump", "Sega - Saturn"),
    "segacd": ("libretro-redump", "Sega - Mega-CD - Sega CD"),
    "xbox": ("libretro-redump", "Microsoft - Xbox"),
    "xbox360": ("libretro-redump", "Microsoft - Xbox 360"),
    "gc": ("libretro-redump", "Nintendo - GameCube"),
    "wii": ("libretro-redump", "Nintendo - Wii"),
    "3do": ("libretro-redump", "The 3DO Company - 3DO"),
    "pcecd": ("libretro-redump", "NEC - PC Engine CD - TurboGrafx-CD"),
    "dc": ("libretro-redump", "Sega - Dreamcast"),
    "naomi": ("libretro-redump", "Sega - Naomi"),
    "naomi2": ("libretro-redump", "Sega - Naomi 2"),
    "jaguarcd": ("libretro-redump", "Atari - Jaguar CD"),
    "cdi": ("libretro-redump", "Philips - CD-i"),
    "pc-9800": ("libretro-redump", "NEC - PC-98"),
    "pc-fx": ("libretro-redump", "NEC - PC-FX"),
    # ── Cartuchos: No-Intro ──
    "snes": ("libretro-no-intro", "Nintendo - Super Nintendo Entertainment System"),
    "nes": ("libretro-no-intro", "Nintendo - Nintendo Entertainment System"),
    "gb": ("libretro-no-intro", "Nintendo - Game Boy"),
    "gbc": ("libretro-no-intro", "Nintendo - Game Boy Color"),
    "gba": ("libretro-no-intro", "Nintendo - Game Boy Advance"),
    "n64": ("libretro-no-intro", "Nintendo - Nintendo 64"),
    "virtualboy": ("libretro-no-intro", "Nintendo - Virtual Boy"),
    "megadrive": ("libretro-no-intro", "Sega - Mega Drive - Genesis"),
    "mastersystem": ("libretro-no-intro", "Sega - Master System - Mark III"),
    "gamegear": ("libretro-no-intro", "Sega - Game Gear"),
    "sg1000": ("libretro-no-intro", "Sega - SG-1000"),
    "pico": ("libretro-no-intro", "Sega - PICO"),
    "atari2600": ("libretro-no-intro", "Atari - 2600"),
    "atari5200": ("libretro-no-intro", "Atari - 5200"),
    "atari7800": ("libretro-no-intro", "Atari - 7800"),
    "atari-800": ("libretro-no-intro", "Atari - 8-bit Family"),
    "lynx": ("libretro-no-intro", "Atari - Lynx"),
    "jaguar": ("libretro-no-intro", "Atari - Jaguar"),
    "vectrex": ("libretro-no-intro", "GCE - Vectrex"),
    "wonderswan": ("libretro-no-intro", "Bandai - WonderSwan"),
    "wonderswancolor": ("libretro-no-intro", "Bandai - WonderSwan Color"),
    "ngp": ("libretro-no-intro", "SNK - Neo Geo Pocket"),
    "ngpc": ("libretro-no-intro", "SNK - Neo Geo Pocket Color"),
    "c64": ("libretro-no-intro", "Commodore - 64"),
    "vic20": ("libretro-no-intro", "Commodore - VIC-20"),
    "amiga": ("libretro-no-intro", "Commodore - Amiga"),
    "amstradcpc": ("libretro-no-intro", "Amstrad - CPC"),
    "intellivision": ("libretro-no-intro", "Mattel - Intellivision"),
    "supervision": ("libretro-no-intro", "Watara - Supervision"),
    "channelf": ("libretro-no-intro", "Fairchild - Channel F"),
    "apf": ("libretro-no-intro", "APF - Imagination Machine"),
    "odyssey2": ("libretro-no-intro", "Magnavox - Odyssey2"),
    "videopac-g7400": ("libretro-no-intro", "Philips - Videopac+"),
    "msx1": ("libretro-no-intro", "Microsoft - MSX"),
    "msx2": ("libretro-no-intro", "Microsoft - MSX2"),
    "zxspectrum": ("libretro-no-intro", "Sinclair - ZX Spectrum +3"),
    "pce": ("libretro-no-intro", "NEC - PC Engine - TurboGrafx 16"),
    "scv": ("libretro-no-intro", "Epoch - Super Cassette Vision"),
}

#: Serial de disco entre corchetes: ``[SLUS-00237]``.
_SERIAL_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_\-]{2,15})\]")


def dat_dir(root: str = "/userdata/system") -> str:
    """Carpeta donde se guardan los DAT."""
    return os.path.join(root, DAT_DIR_NAME)


# ── Descarga ────────────────────────────────────────────────────────────

def _open(url: str, headers: dict | None = None, timeout: int = 120):
    request = urllib.request.Request(url, headers=headers or {
        "User-Agent": "batocera-web-manager"})
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_bytes(url: str, timeout: int = 180) -> bytes:
    """Descarga un fichero entero a memoria."""
    with _open(url, timeout=timeout) as response:
        return response.read()


def fetch_range(url: str, start: int, end: int, timeout: int = 180) -> bytes:
    """Descarga un tramo de un fichero (peticiones por rango)."""
    headers = {"User-Agent": "batocera-web-manager",
               "Range": f"bytes={start}-{end}"}
    with _open(url, headers, timeout=timeout) as response:
        return response.read()


def _content_length(url: str, timeout: int = 120) -> int:
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "batocera-web-manager"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.headers.get("Content-Length") or 0)
    except (urllib.error.URLError, OSError, ValueError):
        return 0


def fetch_zip_member(url: str, member: str, timeout: int = 300) -> bytes:
    """Descarga **un solo fichero** de un ZIP remoto.

    Se lee el directorio central del ZIP con peticiones por rango y se baja
    solo la parte comprimida del DAT que interesa. Si el servidor no soporta
    rangos, se cae a la descarga completa.
    """
    total = _content_length(url, timeout)
    if total > 0:
        try:
            return _fetch_zip_member_by_range(url, member, total, timeout)
        except Exception:
            pass
    return _fetch_zip_member_full(url, member, timeout)


def _fetch_zip_member_by_range(url: str, member: str, total: int,
                               timeout: int) -> bytes:
    tail_len = min(total, 1 << 20)
    tail = fetch_range(url, total - tail_len, total - 1, timeout)
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise ValueError("no se encuentra el final del directorio central")
    cd_size, cd_offset = struct.unpack("<II", tail[eocd + 12:eocd + 20])
    directory = fetch_range(url, cd_offset, cd_offset + cd_size - 1, timeout)

    pos = 0
    while pos < len(directory) - 4:
        if directory[pos:pos + 4] != b"PK\x01\x02":
            break
        method, = struct.unpack("<H", directory[pos + 10:pos + 12])
        comp_size, uncomp_size = struct.unpack("<II", directory[pos + 20:pos + 28])
        name_len, extra_len, comment_len = struct.unpack("<HHH", directory[pos + 28:pos + 34])
        local_offset, = struct.unpack("<I", directory[pos + 42:pos + 46])
        name = directory[pos + 46:pos + 46 + name_len].decode("utf-8", "replace")
        pos += 46 + name_len + extra_len + comment_len
        if name.rsplit("/", 1)[-1] != member.rsplit("/", 1)[-1]:
            continue
        header = fetch_range(url, local_offset, local_offset + 29, timeout)
        if header[:4] != b"PK\x03\x04":
            raise ValueError("cabecera local invalida")
        l_name, l_extra = struct.unpack("<HH", header[26:30])
        data_start = local_offset + 30 + l_name + l_extra
        raw = fetch_range(url, data_start, data_start + comp_size - 1, timeout)
        if method == 0:
            return raw
        if method == 8:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
        raise ValueError(f"metodo de compresion no soportado: {method}")

    raise ValueError(f"el ZIP no contiene {member}")


def _fetch_zip_member_full(url: str, member: str, timeout: int) -> bytes:
    """Descarga el ZIP entero y saca el miembro (si no hay rangos)."""
    import zipfile
    data = fetch_bytes(url, timeout)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.rsplit("/", 1)[-1] == member.rsplit("/", 1)[-1]:
                return zf.read(name)
    raise ValueError(f"el ZIP no contiene {member}")


# ── Indice de DAT ───────────────────────────────────────────────────────

def fetch_index(source: str, cache_dir: str | None = None,
                refresh: bool = False, timeout: int = 180) -> list:
    """El indice clrmamepro de una fuente: que DAT hay y de que fecha.

    Solo tiene sentido para las fuentes empaquetadas (el rebuild diario); las
    de libretro son ficheros sueltos y se descargan directamente.
    """
    if source not in SOURCES:
        raise ValueError(f"fuente de DAT desconocida: {source}")
    if not SOURCES[source].get("index"):
        return []
    cache_path = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, f"indice-{source}.json")
        if not refresh and os.path.exists(cache_path):
            age = time.time() - os.path.getmtime(cache_path)
            if age < 24 * 3600:
                try:
                    with open(cache_path, "r", encoding="utf-8") as fh:
                        return json.load(fh)
                except (OSError, ValueError):
                    pass

    raw = fetch_bytes(SOURCES[source]["index"], timeout=timeout)
    root = ET.fromstring(raw)
    entries = []
    for node in root.findall("datfile"):
        entries.append({
            "name": node.findtext("name") or "",
            "description": node.findtext("description") or "",
            "version": node.findtext("version") or "",
            "file": node.findtext("file") or "",
            "url": node.findtext("url") or "",
            "author": node.findtext("author") or "",
        })
    if cache_path:
        try:
            with open(cache_path, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, ensure_ascii=False)
        except OSError:
            pass
    return entries


# ── Descarga de un DAT ──────────────────────────────────────────────────

def download_dat(source: str, dat_name: str, cache_dir: str,
                 timeout: int = 600, progress: Callable | None = None) -> dict:
    """Descarga el DAT de un sistema y lo deja en ``cache_dir``.

    Devuelve un diccionario con lo hecho: donde ha quedado, de que fecha es y
    cuanto ocupa.
    """
    if source not in SOURCES:
        raise ValueError(f"fuente de DAT desconocida: {source}")
    info = SOURCES[source]
    os.makedirs(cache_dir, exist_ok=True)

    if info.get("files"):
        url = info["base"] + urllib.parse.quote(dat_name + ".dat")
        if progress:
            progress(f"descargando {dat_name}…")
        data = fetch_bytes(url, timeout=timeout)
        target = os.path.join(cache_dir, dat_name + ".dat")
        with open(target, "wb") as fh:
            fh.write(data)
        return {"source": source, "dat": dat_name, "file": target,
                "version": None, "size": len(data), "url": url}

    entry = None
    for candidate in fetch_index(source, cache_dir):
        if candidate["name"] == dat_name:
            entry = candidate
            break
    if entry is None:
        raise ValueError(f"la fuente {source} no tiene el DAT «{dat_name}»")
    if not entry.get("file"):
        raise ValueError(f"el DAT «{dat_name}» no tiene fichero asociado")

    target = os.path.join(cache_dir, os.path.basename(entry["file"]))
    if progress:
        progress(f"descargando {dat_name}…")
    data = fetch_zip_member(info["bundle"], entry["file"], timeout=timeout)
    with open(target, "wb") as fh:
        fh.write(data)
    return {"source": source, "dat": dat_name, "file": target,
            "version": entry.get("version"), "size": len(data)}


# ── Parseo ──────────────────────────────────────────────────────────────

def _field(node, name: str, default: str = "") -> str:
    """El valor de un campo, venga como atributo o como elemento hijo.

    Los DAT de Redump son Logiqx (atributos: ``<rom name="x" crc="y"/>``) y
    los de No-Intro y libretro son clrmamepro (hijos: ``<rom name="x" crc
    "y"/>``). Los dos se leen igual.
    """
    value = node.get(name)
    if value is not None:
        return value
    for child in node:
        if child.tag == name:
            return (child.text or "").strip()
    return default


def parse_dat(path: str) -> list:
    """Lee un DAT (Logiqx o clrmamepro) y devuelve la lista de juegos.

    El formato Logiqx es XML y se lee con ``iterparse`` (el DAT de
    PlayStation 2 pesa varios MB y con ``fromstring`` se va a la memoria de
    golpe). El formato clrmamepro no es XML y tiene su propio lector.
    """
    with open(path, "rb") as fh:
        magic = fh.read(16).lstrip()
    if magic.startswith(b"clrmamepro") or b"game (" in magic:
        return parse_clrmamepro(path)
    games = []
    game = None
    for event, node in ET.iterparse(path, events=("start", "end")):
        if event == "start":
            if node.tag == "game":
                game = {
                    "name": _field(node, "name"),
                    "description": "",
                    "cloneof": _field(node, "cloneof"),
                    "romof": _field(node, "romof"),
                    "region": _field(node, "region"),
                    "serial": _field(node, "serial"),
                    "roms": [],
                }
            continue
        if node.tag == "rom" and game is not None:
            game["roms"].append({
                "name": _field(node, "name"),
                "size": int(_field(node, "size", "0") or 0),
                "crc": _field(node, "crc").upper(),
                "md5": _field(node, "md5").lower(),
                "sha1": _field(node, "sha1").lower(),
                "serial": _field(node, "serial"),
            })
        elif node.tag == "game" and game is not None:
            game["description"] = _field(node, "description") or game["name"]
            game["serial"] = game["serial"] or _serial_of(game["name"])
            games.append(game)
            game = None
            node.clear()
    return games


def _serial_of(name: str) -> str | None:
    match = _SERIAL_RE.search(name or "")
    return match.group(1) if match else None


def build_index(games: Sequence[dict]) -> dict:
    """Construye los mapas de busqueda a partir de los juegos de un DAT."""
    by_hash: dict = {}
    by_serial: dict = {}
    by_name: dict = {}
    by_name_size: dict = {}
    by_title: dict = {}

    for game in games:
        for rom in game.get("roms", []):
            for key, value in (("sha1", rom.get("sha1")), ("md5", rom.get("md5")),
                                ("crc32", rom.get("crc"))):
                if not value:
                    continue
                # El CRC32 se guarda en mayusculas (es como viene en los
                # DAT) y los demas en minusculas.
                value = value.upper() if key == "crc32" else value.lower()
                by_hash.setdefault(f"{key}:{value}", game)
            rom_name = rom.get("name") or ""
            if rom_name:
                key = normalize_title(os.path.splitext(os.path.basename(rom_name))[0])
                if key:
                    by_name.setdefault(key, game)
                    by_name_size.setdefault(key, rom.get("size") or 0)
            serial = rom.get("serial") or game.get("serial")
            if serial:
                by_serial.setdefault(serial.upper(), game)
        serial = game.get("serial")
        if serial:
            by_serial.setdefault(serial.upper(), game)
        title = normalize_title(game.get("description") or game.get("name") or "")
        if title:
            bucket = by_title.setdefault(title, [])
            if len(bucket) < 12:
                bucket.append(game)

    return {"by_hash": by_hash, "by_serial": by_serial,
            "by_name": by_name, "by_name_size": by_name_size,
            "by_title": by_title}


# ── Formato clrmamepro (no es XML) ─────────────────────────────────────

#: ``clave "valor"`` dentro de un bloque clrmamepro.
_CLR_FIELD_RE = re.compile(r'(\w+)\s+"([^"]*)"')
#: ``clave valor`` (sin comillas), como ``size 8192`` o ``crc 931A0BDC``.
_CLR_PLAIN_RE = re.compile(r'\b(size|crc|md5|sha1|serial)\s+([^\s")]+)')


def _clr_block(text: str, start: int) -> tuple:
    """El contenido del bloque que empieza en el parentesis ``start``.

    Devuelve ``(contenido, posicion_despues)``.
    """
    depth = 0
    pos = start
    while pos < len(text):
        char = text[pos]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start + 1:pos], pos + 1
        pos += 1
    return text[start + 1:], len(text)


def parse_clrmamepro(path: str) -> list:
    """Lee un DAT en formato clrmamepro.

    Los bloques son ``game ( ... )`` y dentro ``rom ( ... )``. Se recorren con
    un contador de parentesis, que es lo unico fiable: los valores van entre
    comillas y pueden contener parentesis.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    games = []
    pos = 0
    while True:
        match = re.compile(r"\bgame\s*\(").search(text, pos)
        if not match:
            break
        block, pos = _clr_block(text, text.index("(", match.start()))
        game = {
            "name": "", "description": "", "cloneof": "", "romof": "",
            "region": "", "serial": "", "roms": [],
        }
        # Los ROM van dentro del bloque del juego: se sacan primero para que
        # sus campos (name, serial...) no pisen los del juego.
        rom_blocks = []
        rom_pos = 0
        while True:
            rom_match = re.compile(r"\brom\s*\(").search(block, rom_pos)
            if not rom_match:
                break
            rom_block, rom_pos = _clr_block(block, block.index("(", rom_match.start()))
            rom_blocks.append(rom_block)
            rom = {"name": "", "size": 0, "crc": "", "md5": "", "sha1": "",
                   "serial": ""}
            for key, value in _CLR_FIELD_RE.findall(rom_block):
                key = key.lower()
                if key in rom:
                    rom[key] = value
            for key, value in _CLR_PLAIN_RE.findall(rom_block):
                key = key.lower()
                if key == "size":
                    rom["size"] = int(value or 0)
                elif key in rom:
                    rom[key] = value
            rom["crc"] = rom["crc"].upper()
            rom["md5"] = rom["md5"].lower()
            rom["sha1"] = rom["sha1"].lower()
            if rom["name"]:
                game["roms"].append(rom)
        # Los campos del juego son los que estan fuera de los ROM.
        fuera = block
        for rom_block in rom_blocks:
            fuera = fuera.replace(rom_block, " ")
        for key, value in _CLR_FIELD_RE.findall(fuera):
            key = key.lower()
            if key in game:
                game[key] = value
        game["description"] = game["description"] or game["name"]
        game["serial"] = game["serial"] or _serial_of(game["name"])
        games.append(game)
    return games


# ── Cache en disco ──────────────────────────────────────────────────────

def dat_files(cache_dir: str) -> list:
    """Los DAT descargados, con su estado."""
    out = []
    if not os.path.isdir(cache_dir):
        return out
    for name in sorted(os.listdir(cache_dir)):
        if not name.endswith(".dat"):
            continue
        slug = name[:-4]
        path = os.path.join(cache_dir, name)
        info = {"system": slug, "file": path, "size": os.path.getsize(path),
                "source": None, "dat": None, "version": None, "games": None}
        side = os.path.join(cache_dir, slug + ".json")
        if os.path.exists(side):
            try:
                with open(side, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                info["source"] = meta.get("source")
                info["dat"] = meta.get("dat")
                info["version"] = meta.get("version")
                info["games"] = meta.get("games")
                info["generated"] = meta.get("generated")
            except (OSError, ValueError):
                pass
        out.append(info)
    return out


def install_dat(system: str, cache_dir: str, timeout: int = 600,
                progress: Callable | None = None) -> dict:
    """Descarga e indexa el DAT de un sistema de Batocera."""
    if system not in SYSTEM_DAT:
        raise ValueError(f"el sistema «{system}» no tiene DAT configurado")
    source, dat_name = SYSTEM_DAT[system]

    info = download_dat(source, dat_name, cache_dir, timeout=timeout, progress=progress)
    target = os.path.join(cache_dir, system + ".dat")
    if info["file"] != target:
        os.replace(info["file"], target)

    if progress:
        progress(f"leyendo {dat_name}…")
    games = parse_dat(target)
    index = build_index(games)

    meta = {
        "system": system,
        "source": source,
        "dat": dat_name,
        "version": info.get("version"),
        "generated": time.time(),
        "games": len(games),
        "by_hash": index["by_hash"],
        "by_serial": index["by_serial"],
        "by_name": index["by_name"],
        "by_name_size": index["by_name_size"],
        "by_title": index["by_title"],
    }
    side = os.path.join(cache_dir, system + ".json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)

    return {"system": system, "source": source, "dat": dat_name,
            "version": info.get("version"), "games": len(games),
            "file": target, "size": os.path.getsize(target)}


def load_index(system: str, cache_dir: str) -> dict | None:
    """El indice de un sistema ya descargado (o ``None``)."""
    side = os.path.join(cache_dir, system + ".json")
    if not os.path.exists(side):
        return None
    try:
        with open(side, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return None
    return {
        "by_hash": meta.get("by_hash", {}),
        "by_serial": meta.get("by_serial", {}),
        "by_name": meta.get("by_name", {}),
        "by_name_size": meta.get("by_name_size", {}),
        "by_title": meta.get("by_title", {}),
        "system": system,
        "dat": meta.get("dat"),
        "source": meta.get("source"),
        "version": meta.get("version"),
        "games": meta.get("games"),
    }


def remove_dat(system: str, cache_dir: str) -> dict:
    """Borra el DAT y su indice de un sistema."""
    removed = []
    for name in (system + ".dat", system + ".json"):
        path = os.path.join(cache_dir, name)
        if os.path.exists(path):
            os.remove(path)
            removed.append(name)
    return {"ok": True, "removed": removed}


def systems_with_dat() -> list:
    """Los sistemas de Batocera que tienen DAT, con su fuente."""
    out = []
    for system, (source, dat_name) in sorted(SYSTEM_DAT.items()):
        out.append({"system": system, "source": source,
                    "source_name": SOURCES[source]["name"], "dat": dat_name})
    return out
