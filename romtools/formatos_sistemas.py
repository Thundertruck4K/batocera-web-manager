# -*- coding: utf-8 -*-
"""Los formatos que admite cada sistema y las utilidades que hacen falta.

El catalogo de `formats.py` es **por formato**: dice que de una ISO se puede
pasar a CHD, pero no si el sistema que se esta mirando admite ese formato. Un
PSP no admite un ZIP y un GameCube no admite un CHD, asi que ofrecer esas
conversiones es ofrecer un trabajo que luego no sirve.

Aqui esta el mapa de cada sistema:

- que formatos admite (segun el `es_systems.cfg` de Batocera 43.1 y la wiki
  oficial, que van en el mismo lado);
- cual es el formato que se suele usar en cada caso;
- que utilidad hace falta para cada conversion, y si la consola la trae.

La lista de formatos sale de dos sitios y manda el de la consola: el
`es_systems.cfg` que hay instalado (que ademas incluye los sistemas
personalizados del usuario) y, si no esta, la tabla de aqui.

Lo que **no** esta en la fuente no se inventa: si una utilidad falta en la
consola, la conversion aparece pero desactivada, diciendo que falta y como
conseguirla. Es mejor que callarse el problema.
"""

from __future__ import annotations

import shutil

# ── Utilidades ──────────────────────────────────────────────────────────
#: Cada utilidad externa que puede hacer falta, con su binario en la consola,
#: de donde sale y que licencia tiene. ``binario: None`` significa que la hace
#: el propio manager (biblioteca estandar de Python).
HERRAMIENTAS = {
    "nativo": {
        "nombre": "El manager",
        "binario": None,
        "url": None,
        "licencia": "MIT (este proyecto)",
        "para": "La conversion la hace el manager, sin nada externo.",
        "instalar": "Ya esta: es el propio manager.",
    },
    "chdman": {
        "nombre": "chdman (MAME)",
        "binario": "chdman",
        "url": "https://github.com/mamedev/mame",
        "licencia": "GPL-2.0-or-later",
        "para": "Crea y extrae CHD, el formato comprimido de MAME: CHD a ISO y CHD a BIN/CUE.",
        "instalar": "Ya viene en Batocera: /usr/bin/chdman",
    },
    "zip": {
        "nombre": "Info-ZIP",
        "binario": "zip",
        "url": "https://infozip.sourceforge.net/Zip.html",
        "licencia": "BSD-like (Info-ZIP)",
        "para": "Comprime un fichero en ZIP. El manager usa la biblioteca estandar, pero esta aqui por si se quiere la de la consola.",
        "instalar": "Ya viene en Batocera: /usr/bin/zip",
    },
    "7z": {
        "nombre": "7-Zip (p7zip)",
        "binario": "7z",
        "url": "https://www.7-zip.org/",
        "licencia": "LGPL-2.1-or-later (p7zip, con la restriccion de unRAR)",
        "para": "Comprime en 7Z, que squeeze mas que el ZIP.",
        "instalar": "Ya viene en Batocera: /usr/bin/7z",
    },
    "rom-converto": {
        "nombre": "rom-converto",
        "binario": "rom-converto",
        "url": "https://github.com/DevYukine/rom-converto",
        "licencia": "MIT",
        "para": "La mas completa de todas: convierte entre CSO, ZSO, CHD, RVZ, WBFS, WIA, GCZ, XISO, NSP, XCI, 3DS, PBP, ZAR y mas.",
        "instalar": "El install.sh la instala sola: baja el binario de su release, comprueba el sha256 y lo deja en /userdata/system/bin.",
    },
    "nodtool": {
        "nombre": "nodtool (nod)",
        "binario": "nodtool",
        "url": "https://github.com/encounter/nod",
        "licencia": "Apache-2.0",
        "para": "Crea y extrae los comprimidos de Dolphin: CISO, GCZ, RVZ, WBFS, WIA y GCM.",
        "instalar": "El install.sh la instala sola: baja el binario estatico de su release y comprueba el sha256.",
    },
    "dolphin-tool": {
        "nombre": "dolphin-tool",
        "binario": "dolphin-tool",
        "url": "https://github.com/dolphin-emu/dolphin",
        "licencia": "GPL-2.0-or-later",
        "para": "Crea y extrae RVZ, el formato comprimido de Dolphin (GameCube y Wii), que es el que recomienda la wiki de Batocera.",
        "instalar": "No viene en la consola: el dolphin-emu de Batocera es la interfaz grafica y no construye la herramienta de linea de comandos.",
    },
    "wiitool": {
        "nombre": "wiitool",
        "binario": "wiitool",
        "url": "https://github.com/dolphin-emu/dolphin/wiki/ExternalTools",
        "licencia": "GPL-3.0-or-later",
        "para": "Crea y extrae WBFS y WIA, los formatos de Wii.",
        "instalar": "No se puede instalar sola: no hay release con binarios de Linux (el wiitool original no tiene repositorio oficial). Su equivalente actual es el Wiimms ISO Tools.",
    },
    "extract-xiso": {
        "nombre": "extract-xiso",
        "binario": "extract-xiso",
        "url": "https://github.com/XboxDev/extract-xiso",
        "licencia": "Sin licencia declarada en el repositorio",
        "para": "Extrae XDVDF (Xbox) a ISO.",
        "instalar": "No hace falta: el manager ya lo hace en Python.",
    },
    "ndstool": {
        "nombre": "ndstool",
        "binario": "ndstool",
        "url": "https://github.com/devkitPro/ndstool",
        "licencia": "MIT o GPL-3.0-or-later (dual)",
        "para": "Convierte una ROM de Nintendo DS a cartucho (NOA/GB) y saca su contenido.",
        "instalar": "No se puede instalar sola: no hay release con binarios de Linux, hay que compilarlo.",
    },
    "3dstool": {
        "nombre": "3dstool",
        "binario": "3dstool",
        "url": "https://github.com/dnasdw/3dstool",
        "licencia": "MIT",
        "para": "Empaqueta el contenido de un 3DS en un CIA.",
        "instalar": "El install.sh la instala sola en las consolas x86_64: baja el tarball de su release y comprueba el sha256.",
    },
    "maxcso": {
        "nombre": "maxcso",
        "binario": "maxcso",
        "url": "https://github.com/unknownbrackets/maxcso",
        "licencia": "ISC",
        "para": "Comprime la ISO en CSO, CSO2, ZSO o DAX (PSP y PS2).",
        "instalar": "No hace falta: el manager ya lo hace en Python.",
    },
    "xorriso": {
        "nombre": "xorriso",
        "binario": "xorriso",
        "url": "https://www.gnu.org/software/xorriso/",
        "licencia": "GPL-3.0-or-later",
        "para": "Monta y extrae XDVDF (Xbox) y otras imagenes de disco.",
        "instalar": "No se puede instalar sola: solo se publica el codigo fuente, hay que compilarlo.",
    },
}

# ── Conversiones ────────────────────────────────────────────────────────
#: Que extension produce cada conversion. Lo que no esta, la extension es su
#: propio identificador (``iso`` -> ``.iso``). ``None`` significa que la
#: conversion no deja un fichero nuevo (descomprimir).
EXTENSION_ACCION = {
    "bin-cue": "cue",
    "extraer": None,
}

#: Que utilidad hace falta para cada conversion. Lo que no esta, lo hace el
#: propio manager con la biblioteca estandar de Python.
HERRAMIENTA_ACCION = {
    "chd": "chdman",
    "7z": "7z",
    "rvz": "rom-converto",
    "wbfs": "rom-converto",
}

#: Las compresiones no dependen del formato del fichero sino del sistema: si
#: el sistema admite .zip o .7z, cualquier ROM se puede comprimir.
COMPRESIONES = ("zip", "7z")


# ── Los sistemas ────────────────────────────────────────────────────────
#: Que formatos admite cada sistema. La lista sale del `es_systems.cfg` de
#: Batocera 43.1 (253 sistemas) y de la wiki oficial, que van en el mismo
#: lado. Solo estan los sistemas en los que el formato importa de verdad: en
#: el resto manda el `es_systems.cfg` de la consola.
#:
#: ``formatos``: extensiones que acepta el sistema.
#: ``preferido``: el formato que se suele usar (el que da menos problemas).
#: ``nota``: lo que hay que saber de ese sistema.
SISTEMAS = {
    # ── Disco ───────────────────────────────────────────────────────────────
    "gamecube": {
        "formatos": ["ciso", "dol", "elf", "gcm", "gcz", "iso", "json", "m3u", "rvz",
                       "wbfs"],
        "preferido": "rvz",
        "nota": "Dolphin: el RVZ es el formato recomendado. El GCM es el volcado original y la ISO la imagen sin comprimir.",
    },
    "wii": {
        "formatos": ["ciso", "dol", "elf", "gcm", "gcz", "iso", "json", "m3u", "rvz",
                       "wad", "wbfs"],
        "preferido": "rvz",
        "nota": "Dolphin: el RVZ es el formato recomendado. El WBFS es la particion de la Wii.",
    },
    "wiiu": {
        "formatos": ["rpx", "squashfs", "wud", "wua", "wup", "wux"],
        "preferido": "rpx",
        "nota": "El WUP es el instalador y no se recomienda. El WUA es el juego comprimido en un solo fichero (Cemu 1.27 o mas) y el WUX es el WUD comprimido.",
    },
    "ps3": {
        "formatos": ["iso", "ps3", "psn", "squashfs"],
        "preferido": "iso",
        "nota": "Los ISO tienen que estar descifrados. El PSN es un fichero de texto con el identificador del titulo.",
    },
    "ps2": {
        "formatos": ["bin", "chd", "cso", "dump", "gz", "img", "iso", "m3u", "mdf",
                       "nrg"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado desde la version 31 (antes se usaba el CSO).",
    },
    "psx": {
        "formatos": ["bin", "cbn", "ccd", "chd", "cue", "img", "iso", "m3u", "mdf",
                       "pbp", "toc"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado. El PBP es propietario de Sony y la wiki no lo recomienda. El formato admitido depende del emulador: el PCSX-ReARMed no lee el ISO, el DuckStation si.",
    },
    "psp": {
        "formatos": ["chd", "cso", "iso", "pbp"],
        "preferido": "cso",
        "nota": "El CSO es el recomendado, pero el core libretro-ppsspp no lo lee: en ese caso hay que usar el ISO.",
    },
    "psvita": {
        "formatos": ["psvita", "zip"],
        "preferido": "zip",
        "nota": "El ZIP es el volcado del formato Mai.",
    },
    "saturn": {
        "formatos": ["ccd", "chd", "cue", "iso", "m3u", "zip"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado. Para los juegos de varios discos, el M3U.",
    },
    "dreamcast": {
        "formatos": ["cdi", "chd", "cue", "gdi", "m3u"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado. El GDI es la imagen original del GD-ROM.",
    },
    "3do": {
        "formatos": ["chd", "cue", "iso"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado. El emulador Opera no carga los discos multiples desde un M3U.",
    },
    "neogeocd": {
        "formatos": ["chd", "cue", "iso"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado.",
    },
    "pcenginecd": {
        "formatos": ["ccd", "chd", "cue", "img", "iso", "pce"],
        "preferido": "chd",
        "nota": "El CHD es el preferido: lleva dentro la propia hoja CUE.",
    },
    "megacd": {
        "formatos": ["chd", "cue", "iso", "m3u"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado.",
    },
    "jaguarcd": {
        "formatos": ["bigpimg", "cdi", "cue"],
        "preferido": "cue",
        "nota": "El BIGPIMG solo lo entiende el BigPEmu.",
    },
    "pcfx": {
        "formatos": ["7z", "ccd", "chd", "cue", "m3u", "toc", "zip"],
        "preferido": "chd",
        "nota": "El CHD esta en la lista de formatos admitidos.",
    },
    "supergrafx": {
        "formatos": ["7z", "ccd", "chd", "cue", "pce", "sgx", "zip"],
        "preferido": "chd",
        "nota": "El CHD esta en la lista de formatos admitidos.",
    },
    "fmtowns": {
        "formatos": ["1dd", "7z", "bin", "cdr", "chd", "cqi", "cqm", "cue", "d77",
                       "d88", "dfi", "dsk", "gdi", "hfe", "imd", "iso", "m3u", "mfi",
                       "mfm", "nrg", "td0", "toc", "xdf", "zip"],
        "preferido": "cue",
        "nota": "Admite casi de todo. El CHD solo lo aceptan el MAME y el libretro-mame; el tsugaru no.",
    },
    "amigacd32": {
        "formatos": ["bin", "chd", "cue", "iso"],
        "preferido": "chd",
        "nota": "El amiberry no acepta el CHD: hay que usar el BIN/CUE o el ISO.",
    },
    "amigacdtv": {
        "formatos": ["bin", "chd", "cue", "iso", "m3u"],
        "preferido": "chd",
        "nota": "El CHD es el recomendado.",
    },
    "cdi": {
        "formatos": ["cdr", "chd", "cue", "gdi", "iso", "nrg", "toc"],
        "preferido": "gdi",
        "nota": "DiscJuggler admite el GDI, el CDR, el TOC y el NRG de Nero.",
    },
    "macintosh": {
        "formatos": ["1dd", "2mg", "360", "7z", "cdr", "chd", "cqi", "cqm", "cue",
                       "d77", "d88", "dc42", "dfi", "dsk", "gdi", "hd", "hdi", "hdv",
                       "hfe", "ima", "imd", "img", "ipf", "iso", "mfi", "mfm", "nrg",
                       "td0", "toc", "ufi", "woz", "zip"],
        "preferido": "cue",
        "nota": "El 2MG es el formato propio del emulador y los descartes de disco.",
    },
    "dos": {
        "formatos": ["cue", "dos", "dosz", "iso", "m3u", "pc", "squashfs", "zip"],
        "preferido": "dosz",
        "nota": "El DOSZ es el juego comprimido de DOSBox. El ZIP solo lo acepta el DOSBox_Pure.",
    },
    "scummvm": {
        "formatos": ["scummvm", "squashfs"],
        "preferido": "scummvm",
        "nota": "ScummVM usa carpetas: el juego es la carpeta, no un fichero.",
    },
    "daphne": {
        "formatos": ["daphne", "squashfs"],
        "preferido": "daphne",
        "nota": "El juego es una carpeta con su DAPHNE.",
    },
    "xbox": {
        "formatos": ["iso", "squashfs"],
        "preferido": "iso",
        "nota": "El ISO es el formato de la consola.",
    },
    "xbox360": {
        "formatos": ["iso", "xbox360", "xex"],
        "preferido": "iso",
        "nota": "El XBOX360 es un fichero de texto con el nombre del titulo.",
    },
    "windows": {
        "formatos": ["exe", "pc", "wine", "wsquashfs", "wtgz"],
        "preferido": "pc",
        "nota": "El WTGZ es el juego comprimido y el WSQUASHFS el SQUASHFS de Windows.",
    },
    "jaguar": {
        "formatos": ["7z", "abs", "cdi", "cof", "cue", "j64", "jag", "rom", "zip"],
        "preferido": "rom",
        "nota": "El J64 es el volcado del cartucho.",
    },
    "ports": {
        "formatos": ["sh"],
        "preferido": "sh",
        "nota": "Los ports llevan su propio run.sh.",
    },
    "steam": {
        "formatos": ["steam"],
        "preferido": "steam",
        "nota": "Cada juego es una carpeta con sus datos.",
    },
    "moonlight": {
        "formatos": ["moonlight"],
        "preferido": "moonlight",
        "nota": "Cada juego es una carpeta con sus datos.",
    },
    "openbor": {
        "formatos": ["pak"],
        "preferido": "pak",
        "nota": "El PAK es el volcado del juego.",
    },
    "triforce": {
        "formatos": ["ciso", "dol", "elf", "gcm", "gcz", "iso", "m3u", "wbfs"],
        "preferido": "iso",
        "nota": "Triforce (arcade) usa los mismos formatos que el GameCube.",
    },
    # ── Cartucho ────────────────────────────────────────────────────────────
    "n64": {
        "formatos": ["7z", "n64", "v64", "z64", "zip"],
        "preferido": "z64",
        "nota": "Lo normal es el Z64 (little endian) o el ZIP.",
    },
    "n64dd": {
        "formatos": ["7z", "n64", "ndd", "z64", "zip"],
        "preferido": "z64",
        "nota": "El NDD es el volcado del disco magnético.",
    },
    "snes": {
        "formatos": ["7z", "bsx", "dx2", "fig", "gd3", "gd7", "sfc", "smc", "swc",
                       "zip"],
        "preferido": "sfc",
        "nota": "La SFC va sin cabecera y el ZIP es lo mas comodo. El SMC lleva la cabecera de copista.",
    },
    "megadrive": {
        "formatos": ["7z", "bin", "gen", "md", "sg", "smd", "zip"],
        "preferido": "md",
        "nota": "El BIN va sin cabecera y el ZIP es lo mas comodo.",
    },
    "mastersystem": {
        "formatos": ["7z", "bin", "sms", "zip"],
        "preferido": "sms",
        "nota": "El SMS es el volcado del cartucho.",
    },
    "gamegear": {
        "formatos": ["7z", "bin", "gg", "zip"],
        "preferido": "gg",
        "nota": "El GG es el volcado del cartucho.",
    },
    "nes": {
        "formatos": ["7z", "nes", "unf", "unif", "zip"],
        "preferido": "nes",
        "nota": "El NES es el volcado del cartucho y el UNIF el formato universal.",
    },
    "gb": {
        "formatos": ["7z", "gb", "zip"],
        "preferido": "gb",
        "nota": "El GB es el volcado del cartucho.",
    },
    "gbc": {
        "formatos": ["7z", "gbc", "zip"],
        "preferido": "gbc",
        "nota": "El GBC es el volcado del cartucho.",
    },
    "gba": {
        "formatos": ["7z", "gba", "zip"],
        "preferido": "gba",
        "nota": "El GBA es el volcado del cartucho.",
    },
    "nds": {
        "formatos": ["7z", "bin", "nds", "zip"],
        "preferido": "nds",
        "nota": "El NDS es el volcado del cartucho.",
    },
    "3ds": {
        "formatos": ["3ds", "app", "axf", "cci", "cia", "cxi", "elf", "squashfs",
                       "zcci", "zcia", "zcxi"],
        "preferido": "3ds",
        "nota": "El 3DS es el volcado del cartucho y el CIA el contenido empaquetado.",
    },
    "vectrex": {
        "formatos": ["7z", "bin", "gam", "vec", "zip"],
        "preferido": "gam",
        "nota": "El GAM es el volcado del cartucho.",
    },
    "atari2600": {
        "formatos": ["7z", "a26", "bin", "zip"],
        "preferido": "a26",
        "nota": "El A26 es el volcado del cartucho.",
    },
    "atari5200": {
        "formatos": ["7z", "a52", "atr", "atx", "bin", "car", "cas", "cdm", "rom",
                       "xex", "xfd", "zip"],
        "preferido": "a52",
        "nota": "El A52 es el volcado del cartucho.",
    },
    "atari7800": {
        "formatos": ["7z", "a78", "bin", "zip"],
        "preferido": "a78",
        "nota": "El A78 es el volcado del cartucho.",
    },
    "atari800": {
        "formatos": ["7z", "a52", "atr", "atx", "bin", "car", "cas", "cdm", "m3u",
                       "rom", "xex", "xfd", "zip"],
        "preferido": "atr",
        "nota": "El ATR es el volcado de la disquetera.",
    },
    "atarist": {
        "formatos": ["7z", "dim", "ipf", "m3u", "msa", "st", "stx", "zip"],
        "preferido": "st",
        "nota": "El emulador Hatari usa el ST y el MSA.",
    },
    "colecovision": {
        "formatos": ["7z", "bin", "col", "rom", "zip"],
        "preferido": "bin",
        "nota": "El BIN es el volcado de la cartuchera.",
    },
    "intellivision": {
        "formatos": ["7z", "bin", "int", "rom", "zip"],
        "preferido": "bin",
        "nota": "El BIN es el volcado de la cartuchera.",
    },
    "virtualboy": {
        "formatos": ["7z", "vb", "zip"],
        "preferido": "vb",
        "nota": "El VB es el volcado del cartucho.",
    },
    "lynx": {
        "formatos": ["7z", "bll", "lnx", "lyx", "o", "zip"],
        "preferido": "lnx",
        "nota": "El LNX es el volcado del cartucho.",
    },
    "wswan": {
        "formatos": ["7z", "ws", "zip"],
        "preferido": "ws",
        "nota": "El WS es el volcado del cartucho.",
    },
    "wswanc": {
        "formatos": ["7z", "wsc", "zip"],
        "preferido": "wsc",
        "nota": "El WSC es el volcado del cartucho.",
    },
    "pokemini": {
        "formatos": ["7z", "min", "zip"],
        "preferido": "min",
        "nota": "El MIN es el volcado del cartucho.",
    },
    "gp32": {
        "formatos": ["7z", "smc", "zip"],
        "preferido": "smc",
        "nota": "El SMC es el volcado del cartucho.",
    },
    "ti99": {
        "formatos": ["7z", "rpk", "wav", "zip"],
        "preferido": "rpk",
        "nota": "El RPK lleva las cintas de audio al lado.",
    },
    "pcengine": {
        "formatos": ["7z", "bin", "pce", "zip"],
        "preferido": "pce",
        "nota": "El PCE es el volcado del cartucho.",
    },
    "amstradcpc": {
        "formatos": ["7z", "cdt", "dsk", "m3u", "sna", "tap", "voc", "zip"],
        "preferido": "dsk",
        "nota": "El DSK es el volcado de la disquetera.",
    },
    "msx1": {
        "formatos": ["7z", "cas", "dsk", "m3u", "mx1", "ogv", "openmsx", "rom", "zip"],
        "preferido": "rom",
        "nota": "El ROM es el volcado de la cartuchera.",
    },
    "msx2": {
        "formatos": ["7z", "cas", "dsk", "m3u", "mx2", "ogv", "openmsx", "rom", "zip"],
        "preferido": "rom",
        "nota": "El ROM es el volcado de la cartuchera.",
    },
    "zxspectrum": {
        "formatos": ["7z", "dsk", "rzx", "scl", "tap", "trd", "tzx", "z80", "zip"],
        "preferido": "tzx",
        "nota": "El TAP y el TZX son los volcados del casete.",
    },
    "c64": {
        "formatos": ["7z", "crt", "d64", "d71", "d81", "g64", "m3u", "nib", "prg",
                       "t64", "tap", "zip"],
        "preferido": "prg",
        "nota": "El PRG va con su CRT y el D64 es el volcado de la disquetera.",
    },
    "amiga500": {
        "formatos": ["adf", "adz", "dms", "dmz", "exe", "hdf", "ipf", "lha", "m3u",
                       "raw", "scp", "uae", "zip"],
        "preferido": "adf",
        "nota": "El ADF es la disquetera y el ADZ su version comprimida.",
    },
    "amiga1200": {
        "formatos": ["adf", "adz", "dms", "dmz", "exe", "hdf", "ipf", "lha", "m3u",
                       "raw", "scp", "uae", "zip"],
        "preferido": "adf",
        "nota": "El ADF es la disquetera y el ADZ su version comprimida.",
    },
    "apple2": {
        "formatos": ["2mg", "7z", "chd", "dfi", "do", "dsk", "edd", "hdv", "mfi",
                       "nib", "po", "rti", "wav", "woz", "zip"],
        "preferido": "dsk",
        "nota": "El DSK es el volcado de la disquetera.",
    },
    "apple2gs": {
        "formatos": ["7z", "do", "dsk", "edd", "mfi", "nib", "po", "rti", "wav", "woz",
                       "zip"],
        "preferido": "dsk",
        "nota": "El DSK es el volcado de la disquetera.",
    },
    "pc98": {
        "formatos": ["2hd", "88d", "98d", "cmd", "d88", "d98", "dup", "fdd", "fdi",
                       "hdd", "hdi", "hdm", "hdn", "m3u", "nhd", "tfd", "thd", "xdf",
                       "zip"],
        "preferido": "hdi",
        "nota": "El HDI y el HDM son los volcados de disco.",
    },
    "x68000": {
        "formatos": ["2hd", "7z", "88d", "cmd", "d88", "dim", "dup", "hdf", "hdm",
                       "img", "m3u", "xdf", "zip"],
        "preferido": "hdm",
        "nota": "El HDM y el HDF son los volcados de disco.",
    },
    # ── Arcade ──────────────────────────────────────────────────────────────
    "mame": {
        "formatos": ["7z", "chd", "zip"],
        "preferido": "zip",
        "nota": "El ZIP lleva el set de roms. El CHD es el disco: va en una carpeta con el mismo nombre que el ZIP.",
    },
    "fbneo": {
        "formatos": ["7z", "zip"],
        "preferido": "zip",
        "nota": "Solo admite el ZIP o el 7Z: el ROM en crudo no.",
    },
    "neogeo": {
        "formatos": ["7z", "zip"],
        "preferido": "zip",
        "nota": "Solo admite el ZIP o el 7Z: el ROM en crudo no.",
    },
    "naomi": {
        "formatos": ["7z", "bin", "dat", "lst", "zip"],
        "preferido": "zip",
        "nota": "El ZIP lleva el set de roms y el LST es el listado.",
    },
    "naomi2": {
        "formatos": ["7z", "zip"],
        "preferido": "zip",
        "nota": "Solo admite el ZIP o el 7Z.",
    },
    "atomiswave": {
        "formatos": ["7z", "bin", "dat", "lst", "zip"],
        "preferido": "zip",
        "nota": "El ZIP lleva el set de roms y el LST es el listado.",
    },
    "systemsp": {
        "formatos": ["7z", "bin", "dat", "lst", "zip"],
        "preferido": "zip",
        "nota": "El ZIP lleva el set de roms y el LST es el listado.",
    },
}


# ── Utilidades: disponibles o no ────────────────────────────────────────

def herramienta_disponible(nombre: str) -> bool:
    """Si la consola trae la utilidad que hace falta."""
    datos = HERRAMIENTAS.get(nombre)
    if datos is None:
        return False
    binario = datos.get("binario")
    if not binario:
        return True                       # la hace el propio manager
    return shutil.which(binario) is not None


def inventario_herramientas() -> list:
    """Todas las utilidades, con si estan en la consola ahora mismo."""
    out = []
    for nombre, datos in HERRAMIENTAS.items():
        item = dict(datos)
        item["id"] = nombre
        item["disponible"] = herramienta_disponible(nombre)
        out.append(item)
    return out


def herramienta_de_accion(id_accion: str) -> str:
    """Que utilidad hace falta para una conversion."""
    return HERRAMIENTA_ACCION.get(id_accion, "nativo")


def extension_de_accion(id_accion: str) -> str | None:
    """La extension que produce una conversion (``None`` si no deja fichero)."""
    if id_accion in EXTENSION_ACCION:
        return EXTENSION_ACCION[id_accion]
    return id_accion


# ── El mapa por sistema ─────────────────────────────────────────────────

def formatos_de_sistema(sistema: str | None, extensiones=None) -> list:
    """Los formatos que admite un sistema.

    ``extensiones`` son las que trae el `es_systems.cfg` de la consola: si
    estan, mandan sobre la tabla de aqui (que es el respaldo, y la que usan
    los sistemas personalizados).
    """
    if not sistema:
        return []
    slug = (sistema or "").strip().lower()
    if extensiones:
        return sorted({e.strip().lower().lstrip(".") for e in extensiones if e.strip()})
    datos = SISTEMAS.get(slug)
    if datos:
        return list(datos["formatos"])
    return []


def nota_de_sistema(sistema: str | None) -> str:
    """La nota del sistema (que formato se suele usar y que hay que saber)."""
    if not sistema:
        return ""
    datos = SISTEMAS.get((sistema or "").strip().lower())
    return (datos or {}).get("nota", "")


def _accion(id_accion: str, formatos: list, etiqueta: str) -> dict:
    """Prepara un boton de conversion, con la utilidad que hace falta."""
    from . import formats as _formats

    cap = _formats.CAPACIDADES.get(id_accion)
    if not cap:
        return {}
    ext = extension_de_accion(id_accion)
    herramienta = herramienta_de_accion(id_accion)
    tool = HERRAMIENTAS.get(herramienta, {})
    disponible = herramienta_disponible(herramienta)
    accion = {
        "id": id_accion,
        "label": cap["label"],
        "nota": cap["ayuda"],
        "herramienta": herramienta,
        "disponible": disponible,
        "admite": True,
    }
    if ext and ext not in formatos:
        # El sistema no admite este formato: no se ofrece, porque es un
        # trabajo que luego no sirve.
        accion["admite"] = False
        accion["motivo"] = "este sistema no admite el formato .%s" % ext
        return accion
    if not disponible:
        accion["falta"] = tool.get("nombre", herramienta)
        accion["motivo"] = "falta la utilidad %s" % accion["falta"]
    elif etiqueta:
        accion["motivo"] = ""
    return accion


def acciones_para(info, sistema: str | None = None, extensiones=None) -> list:
    """Las conversiones que admite un fichero **en su sistema**.

    Tres filtros:

    1. las que se pueden hacer desde el formato detectado;
    2. las que el sistema admite (si no lo admite, no se ofrece: es trabajo
       que luego no sirve);
    3. las compresiones que el sistema admite (ZIP, 7Z...): estas no dependen
       del formato del fichero sino del sistema.

    Cada accion lleva si se puede hacer y, si no, que falta.
    """
    from . import formats as _formats

    formatos = formatos_de_sistema(sistema, extensiones)
    if not formatos:
        # Sin datos del sistema: se ofrece lo de siempre (el catalogo por
        # formato), sin filtros.
        return _formats.acciones_de(info)

    acciones = []
    vistos = set()
    for id_accion in _formats.FORMAT_CATALOGUE.get(info.kind, ("", []))[1]:
        if id_accion in vistos:
            continue
        vistos.add(id_accion)
        accion = _accion(id_accion, formatos, "")
        if accion and accion["admite"]:
            acciones.append(accion)

    # Las compresiones: si el sistema admite .zip o .7z, se ofrecen. No
    # dependen del formato del fichero: un BIN de PlayStation 2 se puede
    # comprimir igual que una ISO.
    if info.kind != "zip":
        for id_comp in COMPRESIONES:
            if id_comp in vistos:
                continue
            ext = extension_de_accion(id_comp)
            if ext and ext not in formatos:
                continue
            vistos.add(id_comp)
            accion = _accion(id_comp, formatos, "compresion")
            if accion and accion["admite"]:
                acciones.append(accion)

    return acciones


def resumen_sistema(sistema: str | None, extensiones=None) -> dict:
    """Lo que la interfaz necesita saber de un sistema."""
    formatos = formatos_de_sistema(sistema, extensiones)
    slug = (sistema or "").strip().lower()
    datos = SISTEMAS.get(slug, {})
    return {
        "sistema": slug,
        "formatos": formatos,
        "preferido": datos.get("preferido", ""),
        "nota": datos.get("nota", ""),
        "compresiones": [c for c in COMPRESIONES
                         if extension_de_accion(c) in formatos],
    }
