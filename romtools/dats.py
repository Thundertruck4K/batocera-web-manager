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

import difflib
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
             "master/")
_LIBRETRO_METADAT = _LIBRETRO + "metadat/"
_LIBRETRO_DAT = _LIBRETRO + "dat/"

#: Fuentes de DAT conocidas.
SOURCES = {
    "libretro-redump": {
        "name": "Redump (libretro)",
        "author": "redump.org",
        "kind": "discos",
        "base": _LIBRETRO_METADAT + "redump/",
        "files": True,
    },
    "libretro-no-intro": {
        "name": "No-Intro (libretro)",
        "author": "no-intro.org",
        "kind": "cartuchos",
        "base": _LIBRETRO_METADAT + "no-intro/",
        "files": True,
    },
    "libretro-dat": {
        "name": "Libretro (DAT por sistema)",
        "author": "libretro",
        "kind": "sistemas",
        "base": _LIBRETRO_DAT,
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

#: De cada sistema de Batocera, que DAT le toca.
#:
#: La clave es **el nombre de la carpeta en /userdata/roms**, que es lo que usa
#: el backend para abrir la carpeta del sistema. El valor es la fuente y el
#: nombre exacto del fichero DAT en el espejo.
#:
#: Las fuentes son:
#:
#: - ``libretro-redump`` / ``libretro-no-intro``: ficheros sueltos en el espejo
#:   de ``libretro-database``. Son los DAT de una sola version por sistema, sin
#:   variantes de volcado: los que se usan para renombrar.
#: - ``redump`` / ``no-intro``: el rebuild diario, que tiene mas sistemas
#:   (placas de recreativa, PC-88, X68000...) pero son ZIP: se baja solo el
#:   miembro que interesa.
SYSTEM_DAT = {
    # ── Discos: Redump (libretro) ──
    "3do": ("libretro-redump", "The 3DO Company - 3DO"),
    "psx": ("libretro-redump", "Sony - PlayStation"),
    "ps2": ("libretro-redump", "Sony - PlayStation 2"),
    "ps3": ("libretro-redump", "Sony - PlayStation 3"),
    "psp": ("libretro-redump", "Sony - PlayStation Portable"),
    "saturn": ("libretro-redump", "Sega - Saturn"),
    "megacd": ("libretro-redump", "Sega - Mega-CD - Sega CD"),
    "xbox": ("libretro-redump", "Microsoft - Xbox"),
    "xbox360": ("libretro-redump", "Microsoft - Xbox 360"),
    "gamecube": ("libretro-redump", "Nintendo - GameCube"),
    "wii": ("libretro-redump", "Nintendo - Wii"),
    "dreamcast": ("libretro-redump", "Sega - Dreamcast"),
    "naomi": ("libretro-redump", "Sega - Naomi"),
    "naomi2": ("libretro-redump", "Sega - Naomi 2"),
    "pcenginecd": ("libretro-redump", "NEC - PC Engine CD - TurboGrafx-CD"),
    "pc98": ("libretro-redump", "NEC - PC-98"),
    "pcfx": ("libretro-redump", "NEC - PC-FX"),
    "cdi": ("libretro-redump", "Philips - CD-i"),
    "jaguarcd": ("libretro-redump", "Atari - Jaguar CD"),
    # ── Discos: Redump (rebuild diario) ──
    "chihiro": ("redump", "Arcade - Sega - Chihiro"),
    "lindbergh": ("redump", "Arcade - Sega - Lindbergh"),
    "triforce": ("redump", "Arcade - Namco - Sega - Nintendo - Triforce"),
    "namco2x6": ("redump", "Arcade - Namco - System 246"),
    "neogeocd": ("redump", "SNK - Neo Geo CD"),
    "amigacd32": ("libretro-dat", "Commodore - CD32"),
    "amigacdtv": ("redump", "Commodore - Amiga CDTV"),
    "fmtowns": ("redump", "Fujitsu - FM-Towns"),
    "pc88": ("redump", "NEC - PC-88 series"),
    "x68000": ("redump", "Sharp - X68000"),
    "archimedes": ("redump", "Acorn - Archimedes"),
    "macintosh": ("redump", "Apple - Macintosh"),
    # ── Cartuchos: No-Intro (libretro) ──
    "snes": ("libretro-no-intro", "Nintendo - Super Nintendo Entertainment System"),
    "snes-msu1": ("libretro-no-intro", "Nintendo - Super Nintendo Entertainment System"),
    "nes": ("libretro-no-intro", "Nintendo - Nintendo Entertainment System"),
    "gb": ("libretro-no-intro", "Nintendo - Game Boy"),
    "gb2players": ("libretro-no-intro", "Nintendo - Game Boy"),
    "sgb": ("libretro-no-intro", "Nintendo - Game Boy"),
    "gbc": ("libretro-no-intro", "Nintendo - Game Boy Color"),
    "gbc2players": ("libretro-no-intro", "Nintendo - Game Boy Color"),
    "gba": ("libretro-no-intro", "Nintendo - Game Boy Advance"),
    "n64": ("libretro-no-intro", "Nintendo - Nintendo 64"),
    "n64dd": ("libretro-no-intro", "Nintendo - Nintendo 64DD"),
    "virtualboy": ("libretro-no-intro", "Nintendo - Virtual Boy"),
    "megadrive": ("libretro-no-intro", "Sega - Mega Drive - Genesis"),
    "mastersystem": ("libretro-no-intro", "Sega - Master System - Mark III"),
    "gamegear": ("libretro-no-intro", "Sega - Game Gear"),
    "sg1000": ("libretro-no-intro", "Sega - SG-1000"),
    "pico": ("libretro-no-intro", "Sega - PICO"),
    "atari2600": ("libretro-no-intro", "Atari - 2600"),
    "atari5200": ("libretro-no-intro", "Atari - 5200"),
    "atari7800": ("libretro-no-intro", "Atari - 7800"),
    "atari800": ("libretro-no-intro", "Atari - 8-bit Family"),
    "lynx": ("libretro-no-intro", "Atari - Lynx"),
    "camplynx": ("libretro-no-intro", "Atari - Lynx"),
    "jaguar": ("libretro-no-intro", "Atari - Jaguar"),
    "vectrex": ("libretro-no-intro", "GCE - Vectrex"),
    "wswan": ("libretro-no-intro", "Bandai - WonderSwan"),
    "wswanc": ("libretro-no-intro", "Bandai - WonderSwan Color"),
    "ngp": ("libretro-no-intro", "SNK - Neo Geo Pocket"),
    "ngpc": ("libretro-no-intro", "SNK - Neo Geo Pocket Color"),
    "c64": ("libretro-no-intro", "Commodore - 64"),
    "c20": ("libretro-no-intro", "Commodore - VIC-20"),
    "amiga1200": ("libretro-no-intro", "Commodore - Amiga"),
    "amiga500": ("libretro-no-intro", "Commodore - Amiga"),
    "amstradcpc": ("libretro-dat", "Amstrad - CPC"),
    "intellivision": ("libretro-no-intro", "Mattel - Intellivision"),
    "supervision": ("libretro-no-intro", "Watara - Supervision"),
    "channelf": ("libretro-no-intro", "Fairchild - Channel F"),
    "apfm1000": ("no-intro", "APF - Imagination Machine"),
    "odyssey2": ("libretro-no-intro", "Magnavox - Odyssey2"),
    "videopacplus": ("libretro-no-intro", "Philips - Videopac+"),
    "msx1": ("libretro-no-intro", "Microsoft - MSX"),
    "msx2": ("libretro-no-intro", "Microsoft - MSX2"),
    "zxspectrum": ("libretro-dat", "Sinclair - ZX Spectrum"),
    "pcengine": ("libretro-no-intro", "NEC - PC Engine - TurboGrafx 16"),
    "supergrafx": ("no-intro", "NEC - PC Engine SuperGrafx"),
    "scv": ("libretro-no-intro", "Epoch - Super Cassette Vision"),
    "cassettevision": ("libretro-no-intro", "Epoch - Super Cassette Vision"),
    "colecovision": ("libretro-no-intro", "Coleco - ColecoVision"),
    "advision": ("libretro-no-intro", "Entex - Adventure Vision"),
    "arcadia": ("libretro-no-intro", "Emerson - Arcadia 2001"),
    "gameandwatch": ("no-intro", "Nintendo - Game & Watch"),
    "gamecom": ("libretro-no-intro", "Tiger - Game.com"),
    "gamepock": ("no-intro", "Epoch - Game Pocket Computer"),
    "gp32": ("libretro-no-intro", "GamePark - GP32"),
    "arduboy": ("libretro-no-intro", "Arduboy Inc - Arduboy"),
    "fds": ("libretro-no-intro", "Nintendo - Family Computer Disk System"),
    "3ds": ("libretro-no-intro", "Nintendo - Nintendo 3DS"),
    "nds": ("libretro-no-intro", "Nintendo - Nintendo DS"),
    "psvita": ("libretro-no-intro", "Sony - PlayStation Vita"),
    "wiiu": ("libretro-dat", "Nintendo - Wii U"),
    "pokemini": ("libretro-no-intro", "Nintendo - Pokemon Mini"),
    "loopy": ("no-intro", "Casio - Loopy (BigEndian)"),
    "gamate": ("no-intro", "Bit Corporation - Gamate"),
    "megaduck": ("no-intro", "Welback - Mega Duck"),
    "sufami": ("libretro-no-intro", "Nintendo - Sufami Turbo"),
    "supracan": ("no-intro", "Funtech - Super Acan"),
    "sega32x": ("libretro-no-intro", "Sega - 32X"),
    "ti99": ("no-intro", "Texas Instruments - TI-99-4A (A2R)"),
    "sc3000": ("no-intro", "Sega - SG-1000 - SC-3000"),
    "x1": ("no-intro", "Sharp - X1 (Waveform)"),
    "gmaster": ("libretro-no-intro", "Hartung - Game Master"),
    "gx4000": ("libretro-no-intro", "NEC - PC Engine - TurboGrafx 16"),
    # ── Sistemas que solo cubre el conjunto `dat/` de libretro ──
    "atomiswave": ("libretro-dat", "Atomiswave"),
    "neogeo": ("libretro-dat", "SNK - Neo Geo"),
    "switch": ("libretro-dat", "Nintendo - Nintendo Switch"),
    "scummvm": ("libretro-dat", "ScummVM"),
    "zx81": ("libretro-dat", "Sinclair - ZX 81"),
    "tic80": ("libretro-dat", "TIC-80"),
    "tvc": ("libretro-dat", "Videoton - TV-Computer"),
    "uzebox": ("libretro-dat", "Uzebox"),
    "vircon32": ("libretro-dat", "Vircon32"),
    "wasm4": ("libretro-dat", "WASM-4"),
    "traider1": ("libretro-dat", "Tomb Raider"),
    "cplus4": ("libretro-no-intro", "Commodore - Plus-4"),
    "vsmile": ("libretro-no-intro", "VTech - V.Smile"),
    "astrocade": ("no-intro", "Bally - Astrocade"),
    "atarist": ("no-intro", "Atari - Atari ST"),
    "crvision": ("no-intro", "VTech - CreatiVision"),
    "pv1000": ("no-intro", "Casio - PV-1000"),
    "satellaview": ("no-intro", "Nintendo - Satellaview"),
    "vc4000": ("no-intro", "Interton - VC 4000"),
}

#: Palabras extra de un sistema, para buscarlo por nombre cuando no esta en el
#: mapa. Solo se usan si la busqueda automatica falla.
SYSTEM_ALIASES = {
    "gamecube": "gc",
    "dreamcast": "dc",
    "megacd": "segacd mega cd sega cd",
    "megadrive": "genesis md smd",
    "pcengine": "pce turbografx turbo grafx",
    "pcenginecd": "pcecd turbografx cd",
    "atari800": "8 bit 8-bit x8",
    "snes": "super nes super famicom",
    "nes": "famicom",
    "n64": "nintendo 64",
    "gba": "game boy advance",
    "gbc": "game boy color",
    "gb": "game boy",
    "3do": "3do company panasonic",
    "lynx": "atari lynx camputers",
    "naomi": "sega naomi",
    "wswan": "wonderswan bandai",
    "wswanc": "wonderswan color bandai",
    "mame": "arcade mame",
    "fbneo": "arcade final burn neo",
    "neogeo": "arcade neo geo snk",
    "atomiswave": "arcade sega atomiswave",
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


def _gamecode_of(serial: str | None) -> str:
    """El codigo de juego de un serial del DAT ("RVL-REXP-EUR" -> "REXP").

    Es la clave con la que los discos de Wii se identifican: el volcado
    lleva el codigo dentro y el DAT lo lleva en el serial.
    """
    if not serial:
        return ""
    match = _GAMECODE_SERIAL_RE.match(serial.strip().upper())
    return match.group(1) if match else ""


def build_index(games: Sequence[dict]) -> dict:
    """Construye los mapas de busqueda a partir de los juegos de un DAT."""
    compacto = build_index_compacto(games)
    juegos = compacto["juegos"]

    def _resolver(mapa: dict) -> dict:
        return {clave: juegos[pos] for clave, pos in mapa.items()}

    by_title = {}
    for clave, posiciones in compacto["by_title"].items():
        by_title[clave] = [juegos[pos] for pos in posiciones]

    by_gamecode = {}
    for codigo, posiciones in compacto.get("by_gamecode", {}).items():
        by_gamecode[codigo] = [juegos[pos] for pos in posiciones]

    return {"by_hash": _resolver(compacto["by_hash"]),
            "by_serial": _resolver(compacto["by_serial"]),
            "by_name": _resolver(compacto["by_name"]),
            "by_name_size": compacto["by_name_size"],
            "by_title": by_title,
            "by_gamecode": by_gamecode}


def build_index_compacto(games: Sequence[dict]) -> dict:
    """Los mapas de busqueda guardando la posicion del juego.

    Los mapas guardan **la posicion del juego** en la lista, no el juego
    entero. Si guardaran el juego, el indice de un DAT grande (el de Super
    Nintendo tiene miles de juegos) ocuparia gigabytes: cada hash repetiria
    la lista de roms del juego al que pertenece.
    """
    by_hash: dict = {}
    by_serial: dict = {}
    by_name: dict = {}
    by_name_size: dict = {}
    by_title: dict = {}
    by_gamecode: dict = {}

    for pos, game in enumerate(games):
        for rom in game.get("roms", []):
            for key, value in (("sha1", rom.get("sha1")), ("md5", rom.get("md5")),
                                ("crc32", rom.get("crc"))):
                if not value:
                    continue
                # El CRC32 se guarda en mayusculas (es como viene en los
                # DAT) y los demas en minusculas.
                value = value.upper() if key == "crc32" else value.lower()
                by_hash.setdefault(f"{key}:{value}", pos)
            rom_name = rom.get("name") or ""
            if rom_name:
                key = normalize_title(os.path.splitext(os.path.basename(rom_name))[0])
                if key:
                    by_name.setdefault(key, pos)
                    by_name_size.setdefault(key, rom.get("size") or 0)
            serial = rom.get("serial") or game.get("serial")
            if serial:
                by_serial.setdefault(serial.upper(), pos)
        serial = game.get("serial")
        if serial:
            by_serial.setdefault(serial.upper(), pos)
        # El codigo de juego (el de los discos de Wii) va en el serial.
        for candidato in (serial, *(rom.get("serial") for rom in game.get("roms", []))):
            codigo = _gamecode_of(candidato)
            if not codigo:
                continue
            lista = by_gamecode.setdefault(codigo, [])
            if pos not in lista and len(lista) < 12:
                lista.append(pos)
        title = normalize_title(game.get("description") or game.get("name") or "")
        if title:
            bucket = by_title.setdefault(title, [])
            if len(bucket) < 12:
                bucket.append(pos)

    return {"juegos": list(games),
            "by_hash": by_hash, "by_serial": by_serial,
            "by_name": by_name, "by_name_size": by_name_size,
            "by_title": by_title, "by_gamecode": by_gamecode}


# ── Formato clrmamepro (no es XML) ─────────────────────────────────────

#: ``clave "valor"`` dentro de un bloque clrmamepro.
_CLR_FIELD_RE = re.compile(r'(\w+)\s+"([^"]*)"')
#: ``clave valor`` (sin comillas), como ``size 8192`` o ``crc 931A0BDC``.
_CLR_PLAIN_RE = re.compile(r'\b(size|crc|md5|sha1|serial)\s+([^\s")]+)')

#: El codigo de juego de un disco va en el serial del DAT ("RVL-REXP-EUR").
_GAMECODE_SERIAL_RE = re.compile(r"^[A-Z]{2,4}-([A-Z][A-Z0-9]{3})(?:-|$)")


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

def _leer_meta(cache_dir: str, slug: str) -> dict:
    """Los metadatos de un DAT instalado (o un diccionario vacio).

    Se leen del fichero de metadatos, que es diminuto. Si no existe (un DAT
    instalado antes de esta separacion), se recurre al indice, que si lleva
    los metadatos dentro.
    """
    meta_side = os.path.join(cache_dir, slug + ".meta.json")
    if os.path.exists(meta_side):
        try:
            with open(meta_side, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    side = os.path.join(cache_dir, slug + ".json")
    if not os.path.exists(side):
        return {}
    try:
        with open(side, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {clave: meta.get(clave) for clave in
            ("system", "source", "dat", "version", "generated", "games")}


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
        meta = _leer_meta(cache_dir, slug)
        if meta:
            info["source"] = meta.get("source")
            info["dat"] = meta.get("dat")
            info["version"] = meta.get("version")
            info["games"] = meta.get("games")
            info["generated"] = meta.get("generated")
        out.append(info)
    return out


def install_dat(system: str, cache_dir: str, timeout: int = 600,
                progress: Callable | None = None,
                catalogo: list | None = None) -> dict:
    """Descarga e indexa el DAT de un sistema de Batocera."""
    resolucion = resolve_dat(system, None, catalogo)
    if not resolucion:
        raise ValueError(f"el sistema «{system}» no tiene DAT configurado")
    source, dat_name = resolucion["source"], resolucion["dat"]

    info = download_dat(source, dat_name, cache_dir, timeout=timeout, progress=progress)
    target = os.path.join(cache_dir, system + ".dat")
    if info["file"] != target:
        os.replace(info["file"], target)

    if progress:
        progress(f"leyendo {dat_name}…")
    games = parse_dat(target)
    index = build_index_compacto(games)

    meta = {
        "system": system,
        "source": source,
        "dat": dat_name,
        "version": info.get("version"),
        "generated": time.time(),
        "games": len(games),
    }
    # Los metadatos van en su propio fichero, aparte del indice: el estado
    # de los DAT solo necesita saber de donde salio cada uno y cuantos
    # juegos tiene, y el indice puede pesar varios megas. Si se leyera entero
    # en cada consulta, un DAT grande se comeria la memoria de la consola.
    meta_side = os.path.join(cache_dir, system + ".meta.json")
    with open(meta_side, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)

    indice = {
        # La lista de juegos va una sola vez: los mapas guardan la posicion.
        "juegos": index["juegos"],
        "by_hash": index["by_hash"],
        "by_serial": index["by_serial"],
        "by_name": index["by_name"],
        "by_name_size": index["by_name_size"],
        "by_title": index["by_title"],
        "by_gamecode": index["by_gamecode"],
    }
    side = os.path.join(cache_dir, system + ".json")
    with open(side, "w", encoding="utf-8") as fh:
        json.dump(indice, fh, ensure_ascii=False)

    return {"system": system, "source": source, "dat": dat_name,
            "version": info.get("version"), "games": len(games),
            "file": target, "size": os.path.getsize(target)}


def _migrar_indice(system: str, cache_dir: str, meta: dict) -> dict | None:
    """Reconstruye un indice viejo y lo deja en el formato nuevo.

    Un indice instalado antes de que los mapas guardaran la posicion del
    juego lleva el juego entero dentro de cada mapa, y en «games» solo el
    numero de juegos. Ese indice no sirve para comparar la biblioteca con el
    DAT: le falta la lista de juegos.

    Como el DAT sigue descargado, se vuelve a construir el indice desde el
    DAT, que es la fuente de verdad, y se deja escrito en el formato nuevo.
    Reconstruirlo con los mapas no vale: los mapas guardan un solo juego por
    nombre, asi que se perderian los juegos que comparten nombre.

    Devuelve el indice compacto nuevo, o ``None`` si no se pudo rehacer.
    """
    dat = os.path.join(cache_dir, system + ".dat")
    juegos = None
    if os.path.exists(dat):
        try:
            juegos = parse_dat(dat)
        except (OSError, ValueError):
            juegos = None
    if not juegos:
        return None

    indice = build_index_compacto(juegos)

    lado = os.path.join(cache_dir, system + ".json")
    temporal = lado + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as fh:
            json.dump({
                "juegos": indice["juegos"],
                "by_hash": indice["by_hash"],
                "by_serial": indice["by_serial"],
                "by_name": indice["by_name"],
                "by_name_size": indice["by_name_size"],
                "by_title": indice["by_title"],
                "by_gamecode": indice.get("by_gamecode", {}),
            }, fh, ensure_ascii=False)
        os.replace(temporal, lado)
    except OSError:
        try:
            os.remove(temporal)
        except OSError:
            pass

    lado_meta = os.path.join(cache_dir, system + ".meta.json")
    temporal_meta = lado_meta + ".tmp"
    try:
        with open(temporal_meta, "w", encoding="utf-8") as fh:
            json.dump({
                "system": system,
                "source": meta.get("source"),
                "dat": meta.get("dat"),
                "version": meta.get("version"),
                "generated": meta.get("generated") or time.time(),
                "games": len(juegos),
            }, fh, ensure_ascii=False)
        os.replace(temporal_meta, lado_meta)
    except OSError:
        try:
            os.remove(temporal_meta)
        except OSError:
            pass

    return indice


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
    juegos = meta.get("juegos")
    mapas = meta
    if not isinstance(juegos, list):
        # Indice viejo: no tiene la lista de juegos (solo el numero). Se
        # rehace desde el DAT, que sigue descargado, y se deja escrito en el
        # formato nuevo.
        compacto = _migrar_indice(system, cache_dir, meta)
        if compacto is None:
            return None
        juegos = compacto["juegos"]
        mapas = compacto

    def _resolver(mapa: dict) -> dict:
        """Los mapas guardan la posicion del juego; aqui se resuelve.

        Un indice viejo (con el juego entero dentro) tambien vale: los
        valores que no son numeros se dejan como estaban.
        """
        if not juegos:
            return mapa
        salida = {}
        for clave, valor in mapa.items():
            if isinstance(valor, int) and 0 <= valor < len(juegos):
                salida[clave] = juegos[valor]
            else:
                salida[clave] = valor
        return salida

    by_title = {}
    for clave, valores in (mapas.get("by_title") or {}).items():
        if isinstance(valores, list):
            by_title[clave] = [
                juegos[v] if isinstance(v, int) and 0 <= v < len(juegos) else v
                for v in valores]
        else:
            by_title[clave] = valores

    by_gamecode = {}
    for codigo, valores in (mapas.get("by_gamecode") or {}).items():
        if isinstance(valores, list):
            by_gamecode[codigo] = [
                juegos[v] if isinstance(v, int) and 0 <= v < len(juegos) else v
                for v in valores]
        else:
            by_gamecode[codigo] = valores

    return {
        "by_hash": _resolver(mapas.get("by_hash", {})),
        "by_serial": _resolver(mapas.get("by_serial", {})),
        "by_name": _resolver(mapas.get("by_name", {})),
        # Los tamanos no son posiciones: se dejan como estan.
        "by_name_size": mapas.get("by_name_size", {}),
        "by_title": by_title,
        "by_gamecode": by_gamecode,
        # La lista de juegos, para quien necesite el DAT entero (comparar la
        # biblioteca con el, por ejemplo). Los mapas guardan la posicion, asi
        # que la lista no se duplica: ya esta en memoria.
        "juegos": juegos,
        "system": system,
        "dat": meta.get("dat"),
        "source": meta.get("source"),
        "version": meta.get("version"),
        "games": meta.get("games"),
    }


def remove_dat(system: str, cache_dir: str) -> dict:
    """Borra el DAT y su indice de un sistema."""
    removed = []
    for name in (system + ".dat", system + ".json", system + ".meta.json"):
        path = os.path.join(cache_dir, name)
        if os.path.exists(path):
            os.remove(path)
            removed.append(name)
    return {"ok": True, "removed": removed}


def systems_with_dat(sistemas=None, catalogo=None) -> list:
    """Los sistemas de Batocera que tienen DAT, con su fuente.

    ``sistemas`` es la lista de sistemas que ve el manager (slug y nombre
    legible). Para los que no estan en el mapa se busca por nombre contra el
    catalogo real, y se anota con que confianza se resolvio.
    """
    out = []
    vistos = set()
    for system, (source, dat_name) in sorted(SYSTEM_DAT.items()):
        out.append({"system": system, "source": source,
                    "source_name": SOURCES[source]["name"], "dat": dat_name,
                    "confianza": 1.0, "resuelto": "mapa"})
        vistos.add(system)

    for item in sistemas or []:
        if isinstance(item, dict):
            system = item.get("name") or ""
            nombre = item.get("fullname") or ""
        else:
            system = str(item)
            nombre = ""
        if not system or system in vistos:
            continue
        resolucion = resolve_dat(system, nombre, catalogo)
        if not resolucion:
            continue
        out.append({**resolucion,
                    "source_name": SOURCES.get(resolucion["source"], {}).get(
                        "name", resolucion["source"])})
        vistos.add(system)
    return out


# ── Catalogo en vivo y resolucion por nombre ────────────────────────────

#: GitHub lista el contenido de una carpeta con su API.
_LIBRETRO_API = ("https://api.github.com/repos/libretro/libretro-database/"
                 "contents/metadat/{}")

#: Cuanto tiempo se considera bueno el catalogo descargado (un dia).
_CATALOGO_TTL = 86400


def _tokens(texto: str) -> set:
    """Palabras significativas de un nombre de sistema o de DAT.

    Las palabras sueltas pegadas a numeros cuentan tambien unidas: «MZ-700» y
    «MZ700» comparten «mz700», y asi un numero suelto («800») no empareja dos
    sistemas distintos por casualidad.
    """
    limpio = re.sub(r"\(.*?\)", " ", texto.lower())
    palabras = set()
    for parte in re.split(r"[^A-Za-z0-9+]+", limpio):
        if len(parte) > 1 and not parte.isdigit() and parte not in _RUIDO:
            palabras.add(parte)
    for grupo in re.findall(r"[a-z]+[0-9]+|[0-9]+[a-z]+", limpio):
        if len(grupo) > 2:
            palabras.add(grupo)
    return palabras


#: Palabras que no distinguen un sistema de otro.
_RUIDO = {
    "the", "company", "series", "system", "systems", "game", "games",
    "interactive", "multimedia", "super", "entertainment", "computer",
    "compatible", "disc", "discs", "family", "edition", "collection",
    "source", "code", "and", "for", "de", "del", "la", "el", "arcade",
}


def _catalogo_fichero(cache_dir: str) -> str:
    return os.path.join(cache_dir, "catalogo.json")


def catalogue(cache_dir: str | None = None, timeout: int = 90,
              refresh: bool = False) -> list:
    """Los DAT que hay disponibles ahora mismo.

    Se leen del espejo de libretro (ficheros sueltos) y del rebuild diario
    (que tiene mas sistemas, en ZIP). Se cachean un dia en disco.
    """
    if cache_dir:
        ruta = _catalogo_fichero(cache_dir)
        if not refresh and os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
                if (time.time() - meta.get("generado", 0)) < _CATALOGO_TTL:
                    return meta.get("catalogo", [])
            except (OSError, ValueError):
                pass

    items = []
    for carpeta, source in (("redump", "libretro-redump"),
                            ("no-intro", "libretro-no-intro")):
        for nombre in _listar_libretro(carpeta, timeout):
            items.append({"dat": nombre, "source": source})
    for nombre in _listar_libretro_dat(timeout):
        items.append({"dat": nombre, "source": "libretro-dat"})
    for source in ("redump", "no-intro"):
        # El indice de cada fuente se cachea en disco: la segunda vez no se
        # vuelve a descargar el XML entero.
        for entrada in fetch_index(source, cache_dir, refresh=refresh,
                                   timeout=timeout):
            nombre = entrada.get("name") or ""
            if not nombre or nombre.startswith("Source Code"):
                continue
            items.append({"dat": nombre, "source": source})

    if cache_dir:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(_catalogo_fichero(cache_dir), "w", encoding="utf-8") as fh:
                json.dump({"generado": time.time(), "catalogo": items}, fh,
                          ensure_ascii=False)
        except OSError:
            pass
    return items


def _listar_libretro(carpeta: str, timeout: int = 90) -> list:
    """Los DAT sueltos del espejo de libretro."""
    request = urllib.request.Request(
        _LIBRETRO_API.format(carpeta),
        headers={"User-Agent": "batocera-web-manager"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            datos = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [f["name"][:-4] for f in datos
            if isinstance(f, dict) and f.get("name", "").endswith(".dat")]


def _listar_libretro_dat(timeout: int = 90) -> list:
    """Los DAT sueltos de la carpeta `dat/` de libretro."""
    request = urllib.request.Request(
        _LIBRETRO_API.replace("metadat/", "dat/"),
        headers={"User-Agent": "batocera-web-manager"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            datos = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [f["name"][:-4] for f in datos
            if isinstance(f, dict) and f.get("name", "").endswith(".dat")]


def _listar_rebuild(archivo: str, timeout: int = 300) -> list:
    """Los DAT del rebuild diario (vienen en un ZIP, aqui solo los nombres)."""
    url = _MIRROR + archivo
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "batocera-web-manager"}),
                timeout=timeout) as response:
            texto = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return []
    nombres = re.findall(r"<name>([^<]+)</name>", texto)
    return sorted({n.replace("&amp;", "&") for n in nombres})


def resolve_dat(system: str, nombre: str | None = None,
                catalogo: list | None = None) -> dict | None:
    """El DAT que le toca a un sistema de Batocera.

    Primero se mira el mapa. Si el sistema no esta, se busca por nombre
    contra el catalogo real: gana el DAT que mas palabras comparte, pero solo
    si gana con ventaja (si hay empate, no se arriesga).
    """
    if system in SYSTEM_DAT:
        source, dat_name = SYSTEM_DAT[system]
        return {"system": system, "source": source, "dat": dat_name,
                "confianza": 1.0, "resuelto": "mapa"}

    if not catalogo:
        return None

    sistema_tokens = _tokens(nombre or system)
    sistema_tokens |= _tokens(system.replace("-", " ").replace("_", " "))
    alias = SYSTEM_ALIASES.get(system)
    if alias:
        sistema_tokens |= _tokens(alias)
    if not sistema_tokens:
        return None

    # Cuantos DAT comparten cada palabra: una palabra que aparece en muchos
    # DAT no vale casi nada, y una que aparece en uno solo vale mucho.
    apariciones = {}
    for item in catalogo:
        for token in _tokens(item["dat"]):
            apariciones[token] = apariciones.get(token, 0) + 1

    mejor = None
    for item in catalogo:
        comunes = sistema_tokens & _tokens(item["dat"])
        if not comunes:
            continue
        # Se exige que el DAT cubra **todas** las palabras del sistema: si solo
        # coincide en una palabra generica («Wolfenstein») no es el mismo
        # sistema («Wolfenstein 3D» no es «Enemy Territory»).
        if len(comunes) < len(sistema_tokens):
            continue
        peso = sum(1.0 / apariciones.get(t, 1) for t in comunes)
        ratio = difflib.SequenceMatcher(
            None, (nombre or system).lower(), item["dat"].lower()).ratio()
        puntos = peso * 10 + ratio * 3
        if mejor is None or puntos > mejor[0]:
            mejor = (puntos, item)

    if mejor is None:
        return None
    puntos, item = mejor
    confianza = round(min(1.0, puntos / 14), 2)
    if confianza < 0.7:
        return None
    return {"system": system, "source": item["source"], "dat": item["dat"],
            "confianza": confianza, "resuelto": "nombre"}
