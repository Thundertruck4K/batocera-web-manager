#!/usr/bin/env python3
"""
Batocera System Manager Web — servidor HTTP puro (stdlib), sin dependencias.
"""

import hashlib
import http.server
import io
import json
import os
import random
import re
import shlex
import shutil
import time
import traceback
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from xml.dom import minidom

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HOST, PORT = "0.0.0.0", 5000
APP_VERSION = "1.4"   # única fuente: la portada y el banner la reciben de aquí

SETTINGS_FILE = Path("/userdata/system/batocera_manager_settings.json")

_BATOCERA_SYSTEMS_FILE = Path(__file__).parent / "batocera_systems.json"
_BATOCERA_SYSTEMS = {}
if _BATOCERA_SYSTEMS_FILE.exists():
    try:
        _BATOCERA_SYSTEMS = json.loads(_BATOCERA_SYSTEMS_FILE.read_text())
    except Exception: pass

def _detect_configgen_path(patterns=None):
    """Detecta `emulatorlauncher.py` de configgen sin fijar la versión de Python.

    En Batocera vive en `/usr/lib/python3.X/site-packages/configgen/`. Se
    devuelve la primera coincidencia existente; si no hay ninguna, el valor
    histórico como *fallback*.
    """
    import glob as _glob
    if patterns is None:
        patterns = [
            "/usr/lib/python3*/site-packages/configgen/emulatorlauncher.py",
            "/usr/lib/python3/dist-packages/configgen/emulatorlauncher.py",
            "/usr/local/lib/python3*/site-packages/configgen/emulatorlauncher.py",
        ]
    for pat in patterns:
        hits = sorted(_glob.glob(pat))
        if hits:
            return hits[0]
    return "/usr/lib/python3.12/site-packages/configgen/emulatorlauncher.py"


DEFAULT_SETTINGS = {
    "es_cfg_dir":    "/userdata/system/configs/emulationstation",
    "roms_base":     "/userdata/roms",
    "themes_user":   "/userdata/themes",
    "themes_sys":    "/usr/share/emulationstation/themes",
    "batocera_conf": "/userdata/system/batocera.conf",
    "python_path":   _detect_configgen_path(),
    "bios_dir":      "/userdata/bios",
    "app_path":      "/userdata/system/batocera_web/app.py",
    "server_port":   5000,
    # RetroAchievements (opcional): usuario + Web API Key (nunca la contraseña)
    "ra_user":       "",
    "ra_api_key":    "",
    "ra_enabled":    True,
}

PLATFORM_IDS = [
    "3do","3ds","amiga","amigacd32","amstradcpc","arcade","atari2600","atari7800",
    "atarist","c64","colecovision","dreamcast","famicom","fba","gb","gba","gbc",
    "gamegear","gc","genesis","intellivision","jaguar","lynx","mame","mastersystem",
    "megadrive","megacd","msx","msx2","n64","nds","neogeo","neogeocd","nes","ngp",
    "pc","pce","pcengine","pcfx","psp","ps2","ps3","psx","saturn","sega32x",
    "segacd","sg1000","snes","supergrafx","tg16","vectrex","virtualboy","wii",
    "wiiu","wonderswan","wonderswancolor","x68000","zxspectrum",
]
HARDWARE_TYPES = ["console","portable","computer","arcade","engine","fantasy","other"]
EXT_PRESETS = {
    "ROMs genéricos":  ".zip .7z .rar",
    "ISO / Disco":     ".iso .chd .cue .bin",
    "Nintendo Switch": ".nsp .xci",
    "GBA / NDS":       ".gba .nds .gb .gbc",
    "PlayStation":     ".pbp .pkg .iso .chd",
    "MAME":            ".zip .7z .chd",
    "PC Engine":       ".pce .cue .chd",
    "Arcade":          ".zip .7z",
}
ROM_EXTENSIONS = {
    ".zip",".7z",".rar",".iso",".chd",".cue",".bin",".img",
    ".smc",".sfc",".nes",".gb",".gbc",".gba",".n64",".z64",
    ".v64",".nds",".pce",".fds",".a26",".a78",".lnx",".ngp",
    ".psx",".pbp",".cso",".gcm",".wad",".wbfs",".nrg",".mdf",
    ".cdi",".gdi",".d64",".t64",".prg",".sc",".sg",".sms",
    ".md",".gen",".32x",".col",".m3u",".scummvm",".3ds",".cia",
    ".nsp",".xci",".ws",".wsc",".ngc",".dsk",".st",".adf",
}
FILTER_DIRS  = {"manuals","videos","images"}
FILTER_FILES = {"_info.txt"}
# Auto-generated from official batocera-systems script
# Auto-generated from official batocera-systems script
# https://github.com/batocera-linux/batocera.linux/blob/master/package/batocera/core/batocera-scripts/scripts/batocera-systems
# Generado: 108 sistemas con BIOS, 705 entradas, 35 sistemas sin BIOS


BIOS_DB = {
    "3do": [
        {"file":"panafz1.bin","md5":"f47264dd47fe30f73ab3c010015c155b","desc":"panafz1","mandatory":True},
        {"file":"panafz10.bin","md5":"51f2f43ae2f3508a14d9f56597e2d3ce","desc":"panafz10","mandatory":True},
        {"file":"goldstar.bin","md5":"8639fd5e549bd6238cfee79e3e749114","desc":"goldstar","mandatory":True},
    ],
    "adam": [
        {"file":"adam.zip","md5":None,"desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"01bba3bcd46d8a586dd6ec555accc133","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"feabe33e8f2dab88da1458b4d27f3faa","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"a720bc872a772ed471fac14e36ec8bcb","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"cf10b154f2e006a9740d7653cfc47cab","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"7916bb9635d502366326ec39aea5fc89","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"2c66f5911e5b42b8ebe113403548eee7","desc":"adam","mandatory":True},
        {"file":"adam.zip","md5":"4fe4f6800076ea3d897d4285653447bd","desc":"adam","mandatory":True},
        {"file":"adam_ddp.zip","md5":None,"desc":"adam_ddp","mandatory":True},
        {"file":"adam_ddp.zip","md5":"0423e9e9bf5036aa1e9d656b6a1f842c","desc":"adam_ddp","mandatory":True},
        {"file":"adam_fdc.zip","md5":None,"desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"ae12d0b83832b059cb6cb43029bbfdb3","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"4c38a7df1e645c8d9f417bf7165c46d0","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"afea14c826f3cfbc89b76725a4a41951","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"976d2a7d85319d9104bc9ec176fbfa9c","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"29569dc029e95e48907b3c81d636987f","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"a121855c20a638429bbfcf0448349515","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"e05ababa16e2d5cb92b678cb6e6e2004","desc":"adam_fdc","mandatory":True},
        {"file":"adam_fdc.zip","md5":"a1a2a353dea4b8769a2da733822abfdc","desc":"adam_fdc","mandatory":True},
        {"file":"adam_kb.zip","md5":None,"desc":"adam_kb","mandatory":True},
        {"file":"adam_kb.zip","md5":"d81e0b2bb6b98999541c5f40b489e88f","desc":"adam_kb","mandatory":True},
        {"file":"adam_prn.zip","md5":None,"desc":"adam_prn","mandatory":True},
        {"file":"adam_prn.zip","md5":"3cdf2fe48ac4224b56f26c03f6c68982","desc":"adam_prn","mandatory":True},
    ],
    "advision": [
        {"file":"advision.zip","md5":None,"desc":"advision","mandatory":True},
        {"file":"advision.zip","md5":"5729638bd856c475678467a353bd921c","desc":"advision","mandatory":True},
        {"file":"advision.zip","md5":"fc5e71445e4947a9d00eedbc66b13a8f","desc":"advision","mandatory":True},
    ],
    "amiga1200": [
        {"file":"amiga/kick39106.A1200","md5":"b7cc148386aa631136f510cd29e42fc3","desc":"kick39106","mandatory":True},
        {"file":"amiga/kick40068.A1200","md5":"646773759326fbac3b2311fd8c8793ee","desc":"kick40068","mandatory":True},
        {"file":"amiga/kick40068.A4000","md5":"9bdedde6a4f33555b4a270c8ca53297d","desc":"kick40068","mandatory":True},
        {"file":"amiga/amiga-os-300-a1200.rom","md5":"b7cc148386aa631136f510cd29e42fc3","desc":"amiga-os-300-a1200","mandatory":True},
        {"file":"amiga/amiga-os-310-a1200.rom","md5":"646773759326fbac3b2311fd8c8793ee","desc":"amiga-os-310-a1200","mandatory":True},
        {"file":"amiga/amiga-os-310-a3000.rom","md5":"413590e50098a056cfec418d3df0212d","desc":"amiga-os-310-a3000","mandatory":True},
        {"file":"amiga/amiga-os-310-a4000.rom","md5":"9bdedde6a4f33555b4a270c8ca53297d","desc":"amiga-os-310-a4000","mandatory":True},
        {"file":"amiga/amiga-os-310.rom","md5":"730888fb1bd9a3606d51f772ed136528","desc":"amiga-os-310","mandatory":True},
    ],
    "amiga500": [
        {"file":"amiga/kick33180.A500","md5":"85ad74194e87c08904327de1a9443b7a","desc":"kick33180","mandatory":True},
        {"file":"amiga/kick37175.A500","md5":"dc10d7bdd1b6f450773dfb558477c230","desc":"kick37175","mandatory":True},
        {"file":"amiga/kick34005.A500","md5":"82a21c1890cae844b3df741f2762d48d","desc":"kick34005","mandatory":True},
        {"file":"amiga/kick37350.A600","md5":"465646c9b6729f77eea5314d1f057951","desc":"kick37350","mandatory":True},
        {"file":"amiga/kick40063.A600","md5":"e40a5dfb3d017ba8779faba30cbd1c8e","desc":"kick40063","mandatory":True},
        {"file":"amiga/amiga-os-120.rom","md5":"85ad74194e87c08904327de1a9443b7a","desc":"amiga-os-120","mandatory":True},
        {"file":"amiga/amiga-os-130.rom","md5":"82a21c1890cae844b3df741f2762d48d","desc":"amiga-os-130","mandatory":True},
        {"file":"amiga/amiga-os-204.rom","md5":"dc10d7bdd1b6f450773dfb558477c230","desc":"amiga-os-204","mandatory":True},
        {"file":"amiga/amiga-os-205.rom","md5":"465646c9b6729f77eea5314d1f057951","desc":"amiga-os-205","mandatory":True},
        {"file":"amiga/amiga-os-310-a600.rom","md5":"e40a5dfb3d017ba8779faba30cbd1c8e","desc":"amiga-os-310-a600","mandatory":True},
    ],
    "amigacd32": [
        {"file":"amiga/kick40060.CD32","md5":"5f8924d013dd57a89cf349f4cdedc6b1","desc":"kick40060","mandatory":True},
        {"file":"amiga/kick40060.CD32.ext","md5":"bb72565701b1b6faece07d68ea5da639","desc":"kick40060.CD32","mandatory":True},
        {"file":"amiga/amiga-os-310-cd32.rom","md5":"5f8924d013dd57a89cf349f4cdedc6b1","desc":"amiga-os-310-cd32","mandatory":True},
        {"file":"amiga/amiga-ext-310-cd32.rom","md5":"bb72565701b1b6faece07d68ea5da639","desc":"amiga-ext-310-cd32","mandatory":True},
    ],
    "amigacdtv": [
        {"file":"amiga/kick34005.A500","md5":"82a21c1890cae844b3df741f2762d48d","desc":"kick34005","mandatory":True},
        {"file":"amiga/kick34005.CDTV","md5":"89da1838a24460e4b93f4f0c5d92d48d","desc":"kick34005","mandatory":True},
        {"file":"amiga/amiga-os-130.rom","md5":"82a21c1890cae844b3df741f2762d48d","desc":"amiga-os-130","mandatory":True},
        {"file":"amiga/amiga-ext-130-cdtv.rom","md5":"89da1838a24460e4b93f4f0c5d92d48d","desc":"amiga-ext-130-cdtv","mandatory":True},
    ],
    "apfm1000": [
        {"file":"apfm1000.zip","md5":None,"desc":"apfm1000","mandatory":True},
        {"file":"apfm1000.zip","md5":"1f4a976350202ee1e32c2b0477c3fc1b","desc":"apfm1000","mandatory":True},
        {"file":"apfm1000.zip","md5":"b325543b36d37edf3fc20761f00c7a37","desc":"apfm1000","mandatory":True},
        {"file":"apfm1000.zip","md5":"89a7cfa5469ce24773721d65b28f8544","desc":"apfm1000","mandatory":True},
    ],
    "apple2": [
        {"file":"apple2e.zip","md5":None,"desc":"apple2e","mandatory":True},
        {"file":"apple2e.zip","md5":"4431aea380185e3f509285540d7cb418","desc":"apple2e","mandatory":True},
        {"file":"apple2e.zip","md5":"e6d453d8738e6df4f73df8c8051df3e8","desc":"apple2e","mandatory":True},
        {"file":"apple2e.zip","md5":"72924019cf1719765e4fde35e59c1c7d","desc":"apple2e","mandatory":True},
        {"file":"apple2e.zip","md5":"0b150f4bfa090770a866cc5d214703f4","desc":"apple2e","mandatory":True},
        {"file":"apple2ee.zip","md5":None,"desc":"apple2ee","mandatory":True},
        {"file":"apple2ee.zip","md5":"b956c537e7b6b85ffa5c3493b1490d8a","desc":"apple2ee","mandatory":True},
        {"file":"apple2ee.zip","md5":"9123fff3442c0e688cc6816be88dd4ab","desc":"apple2ee","mandatory":True},
        {"file":"apple2ee.zip","md5":"6ac9338f6972eea01604f90d9a581f18","desc":"apple2ee","mandatory":True},
        {"file":"apple2ee.zip","md5":"6b11018a14668a7e3904319d2097dddc","desc":"apple2ee","mandatory":True},
        {"file":"apple2p.zip","md5":None,"desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"89ca5cd551ffad9a557652a97dcb6627","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"42333f24cd6e70696b212b042f3166aa","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"5de50bebc41e59ae4eb27be4c24b6814","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"56d9bb6730735a3b2bbcc75d1da7a8de","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"cb63c41c5e72b5fda54feb5490efdefb","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"8925b695ae0177dd3919dbea2f2f202b","desc":"apple2p","mandatory":True},
        {"file":"apple2p.zip","md5":"9ac0dc8c4d0002eb45b0b84be0bde5ec","desc":"apple2p","mandatory":True},
        {"file":"a2diskiing.zip","md5":None,"desc":"a2diskiing","mandatory":True},
        {"file":"a2diskiing.zip","md5":"2020aa1413ff77fe29353f3ee72dc295","desc":"a2diskiing","mandatory":True},
        {"file":"a2cffa02.zip","md5":None,"desc":"a2cffa02","mandatory":True},
        {"file":"a2cffa02.zip","md5":"80adbc2d79f347ec63f4b771ea32984d","desc":"a2cffa02","mandatory":True},
        {"file":"votrsc01.zip","md5":None,"desc":"votrsc01","mandatory":True},
        {"file":"votrsc01.zip","md5":"8ccf35a06f5e9a2131b0f42380ee5c15","desc":"votrsc01","mandatory":True},
        {"file":"votrsc01a.zip","md5":None,"desc":"votrsc01a","mandatory":True},
        {"file":"votrsc01a.zip","md5":"95b91e4a2fe7d6f13d353ba1827d37f9","desc":"votrsc01a","mandatory":True},
        {"file":"d2fdc.zip","md5":None,"desc":"d2fdc","mandatory":True},
        {"file":"d2fdc.zip","md5":"5f1be0c1cdff26f5956eef9643911886","desc":"d2fdc","mandatory":True},
    ],
    "apple2gs": [
        {"file":"apple2gs.zip","md5":None,"desc":"apple2gs","mandatory":True},
        {"file":"apple2gs.zip","md5":"b956c537e7b6b85ffa5c3493b1490d8a","desc":"apple2gs","mandatory":True},
        {"file":"apple2gs.zip","md5":"b9f94f5d1be27dafcb8fe619ca3f4d15","desc":"apple2gs","mandatory":True},
        {"file":"apple2gs.zip","md5":"e8e632aa592a61ef373b38af10ed54e1","desc":"apple2gs","mandatory":True},
        {"file":"apple2gs.zip","md5":"c9e0e059faec0393fc429131a3af4ee9","desc":"apple2gs","mandatory":True},
        {"file":"apple2gs.zip","md5":"68ff96a624237d233e8d4c701f660dd1","desc":"apple2gs","mandatory":True},
    ],
    "archimedes": [
        {"file":"aa310.zip","md5":None,"desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"374e4bcaa04cb98aad3b64a1555c3930","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"b0b6a83029b6f85bb044bfc46bf3f0f6","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"bf35bb799aa0278b7ee7719dd32f26bc","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"e41af081535aae930d68ee4cbd672513","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"7ecdccd760557ab0711edb37773faeb6","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"c43bad04862ea03146ff5bf7441a1a24","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"454c1977ad70a206f4f3a0bdca294d85","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"6850da7a70b198eaf6fde5be503fa5cd","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"84d305e248dab48a3a110af161dfb005","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"64d7f085e6afb149ebc2e7f919429a19","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"f7d0a9a4d1dae8eee057aa626b87715f","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"763b015d85c7d9d17e06d5babc0a9d32","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"b8fcd63c6a28d0c7034af2e6c5aff9a8","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"6265551c5d6336f7ddd9f3fc78ceba93","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"ca4379aeab4f7c7640c8ad34b27a9db6","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"358d3c9d2685c076f6a141c26d45520c","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"4ae429fbf23f8aa64ce2002cfb14c527","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"83d0f0738468fdf9f23c13eef22dbeea","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"636e4072c392916d2bf00865fee40984","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"252b1993fdb66cac522a0edbeffc3407","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"591f3bdd0f20a0a3d03c8748f2f75754","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"f77f4a409c78c8495fc3876cd4e7d97c","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"57d3a349407916f55129d6c8c0f56395","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"ee4aa1ea0eebf88c5f6cae6315ed11a1","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"a057124502e533ccd8865dc970cf7017","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"3c40d2821595a7334a46ea3b46a5421d","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"d1d51b8f603bba476d1f63bc5980040e","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"7b096a93cc5ada80bcfb5249bca33768","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"744e80abe4c6a845412f63a0f0b14e48","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"9dac78cba6034c427d00f78fa94ab63d","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"4c0b2e1fb29c8acd84e94d25c953173c","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"f6bf5f8908a19a9aacf733633b1cd5cf","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"eec46f5bd4cdb456b760b3cddf16a33c","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"980e3be0c851a59d0f4602f4a94b2eef","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"971a49d5c2dbb3fc01c17d1d5615781a","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"9ce06a4d2a8331bc5b7fadb967d74f4f","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"c74763f720c98e16dc3c6c421db21485","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"6f564c8917f04594bda7385f6de61061","desc":"aa310","mandatory":True},
        {"file":"aa310.zip","md5":"232a302efe19278d9df6ecbc8ea3dc6c","desc":"aa310","mandatory":True},
        {"file":"archimedes_keyboard.zip","md5":None,"desc":"archimedes_keyboard","mandatory":True},
        {"file":"archimedes_keyboard.zip","md5":"1a8617c1abe3e0729d20ce844e1e12a8","desc":"archimedes_keyboard","mandatory":True},
    ],
    "astrocade": [
        {"file":"astrocde.zip","md5":None,"desc":"astrocde","mandatory":True},
        {"file":"astrocde.zip","md5":"7d25a26e5c4841b364cfe6b1735eaf03","desc":"astrocde","mandatory":True},
    ],
    "atari5200": [
        {"file":"5200.rom","md5":"281f20ea4320404ec820fb7ec0693b38","desc":"5200","mandatory":True},
    ],
    "atari800": [
        {"file":"ATARIOSA.ROM","md5":"eb1f32f5d9f382db1bbfb8d7f9cb343a","desc":"ATARIOSA","mandatory":True},
        {"file":"ATARIOSB.ROM","md5":"4177f386a3bac989a981d3fe3388cb6c","desc":"ATARIOSB","mandatory":True},
        {"file":"ATARIXL.ROM","md5":"06daac977823773a3eea3422fd26a703","desc":"ATARIXL","mandatory":True},
        {"file":"ATARIBAS.ROM","md5":"0bac0c6a50104045d902df4503a4c30b","desc":"ATARIBAS","mandatory":True},
    ],
    "atarist": [
        {"file":"tos.img","md5":"c1c57ce48e8ee4135885cee9e63a68a2","desc":"tos","mandatory":True},
        {"file":"tos100fr.img","md5":"25789a649faff0a1176dc7d9b98105c0","desc":"tos100fr","mandatory":True},
        {"file":"tos100uk.img","md5":"c87a52c277f7952b41c639fc7bf0a43b","desc":"tos100uk","mandatory":True},
        {"file":"tos100us.img","md5":"d0f682ee6237497004339fb02172638b","desc":"tos100us","mandatory":True},
        {"file":"tos102de.img","md5":"a622cc35d8d78703905592dfaa4d2ccb","desc":"tos102de","mandatory":True},
        {"file":"tos102fr.img","md5":"d6521785627d20c51edc566808a6bf28","desc":"tos102fr","mandatory":True},
        {"file":"tos102uk.img","md5":"b2a8570de2e850c5acf81cb80512d9f6","desc":"tos102uk","mandatory":True},
        {"file":"tos104de.img","md5":"41b7dae4e24735f330b63ad923a0bfbc","desc":"tos104de","mandatory":True},
        {"file":"tos104es.img","md5":"143343f7b8e0b1162af206fe8f46b002","desc":"tos104es","mandatory":True},
        {"file":"tos104fr.img","md5":"0087e2707c57efa2106a0aa7576655c0","desc":"tos104fr","mandatory":True},
        {"file":"tos104uk.img","md5":"036c5ae4f885cbf62c9bed651c6c58a8","desc":"tos104uk","mandatory":True},
        {"file":"tos104us.img","md5":"736adb2dc835df4d323191fdc8926cc9","desc":"tos104us","mandatory":True},
        {"file":"tos106de.img","md5":"992bac38e01633a529121a2a65f0779e","desc":"tos106de","mandatory":True},
        {"file":"tos106es.img","md5":"30f69d70fe7c210300ed83f991b12de9","desc":"tos106es","mandatory":True},
        {"file":"tos106fr.img","md5":"bc7b224d0dc3f0cc14c8897db89c5787","desc":"tos106fr","mandatory":True},
        {"file":"tos106uk.img","md5":"6033f2b9364edfed321c6931a8181fd2","desc":"tos106uk","mandatory":True},
        {"file":"tos106us.img","md5":"a0982e760f9807d82667ff5a69e78f6b","desc":"tos106us","mandatory":True},
        {"file":"tos162de.img","md5":"94a75c1c65408d9f974b0463e15a3b11","desc":"tos162de","mandatory":True},
        {"file":"tos162fr.img","md5":"ed5fbaabe0219092df74c6c14cea3f8e","desc":"tos162fr","mandatory":True},
        {"file":"tos162uk.img","md5":"1cbc4f55295e469fc8cd72b7efdea1da","desc":"tos162uk","mandatory":True},
        {"file":"tos162us.img","md5":"febb00ba8784798293a7ae709a1dafcb","desc":"tos162us","mandatory":True},
        {"file":"tos205de.img","md5":"7aeabdc25f8134590e25643a405210ca","desc":"tos205de","mandatory":True},
        {"file":"tos205es.img","md5":"7449b131681f1dfe62ebed1392847057","desc":"tos205es","mandatory":True},
        {"file":"tos205fr.img","md5":"61b620ad951815a25cb37895c81a947c","desc":"tos205fr","mandatory":True},
        {"file":"tos205it.img","md5":"7e87d8fe7e24e0b4c55ad1b7955beae3","desc":"tos205it","mandatory":True},
        {"file":"tos205us.img","md5":"7cdd45b6aac66a21bfb357d9334e46db","desc":"tos205us","mandatory":True},
        {"file":"tos206de.img","md5":"0604dbb85928f0598d04144a8b554bbe","desc":"tos206de","mandatory":True},
        {"file":"tos206fr.img","md5":"b2873004a408b8db36321f98daafa251","desc":"tos206fr","mandatory":True},
        {"file":"tos206.img","md5":"4a0d4f282c3f2a0196681adf88862dd4","desc":"tos206","mandatory":True},
        {"file":"tos206uk.img","md5":"e690bec90d902024beed549d22150755","desc":"tos206uk","mandatory":True},
        {"file":"tos206us.img","md5":"c9093f27159e7d13ac0d1501a95e53d4","desc":"tos206us","mandatory":True},
        {"file":"tos306de.img","md5":"066f39a7ea5789d5afd59dd7b3104fa6","desc":"tos306de","mandatory":True},
        {"file":"tos306uk.img","md5":"dd1010ec566efbd71047d6c4919feba5","desc":"tos306uk","mandatory":True},
        {"file":"tos400.img","md5":"ed2647936ce4bd283c4d7dfd7ae09d1c","desc":"tos400","mandatory":True},
        {"file":"tos402.img","md5":"9e880168d0a004f7f5e852be758f39e4","desc":"tos402","mandatory":True},
        {"file":"tos404.img","md5":"e5ea0f216fb446f1c4a4f476bc5f03d4","desc":"tos404","mandatory":True},
    ],
    "atom": [
        {"file":"atom.zip","md5":None,"desc":"atom","mandatory":True},
        {"file":"atom.zip","md5":"b7b7f8a608339fa39d44a3bcfa2cc3f0","desc":"atom","mandatory":True},
        {"file":"atom.zip","md5":"baa26f458acf5745388177ffc7368124","desc":"atom","mandatory":True},
        {"file":"atom.zip","md5":"9627dfb5f8302db8dd5702dbf7c09f72","desc":"atom","mandatory":True},
    ],
    "atomiswave": [
        {"file":"dc/awbios.zip","md5":"85254fbe320ca82a768ec2c26bb08def","desc":"awbios","mandatory":True},
    ],
    "bbc": [
        {"file":"bbcb.zip","md5":None,"desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"521a197d3623682825f1042c1350feb4","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"2cc67be4624df4dc66617742571a8e3d","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"0cad3d0cf0d111aca2b158b9b605913f","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"46f920a170e88bab7faa96cf80b84324","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"0199bac73f1dbca291582834a3e61122","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"0a59a5ba15fe8557b5f7fee32bbd393a","desc":"bbcb","mandatory":True},
        {"file":"bbcb.zip","md5":"35e9ab10bcf016bd24b4c716add009b9","desc":"bbcb","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":None,"desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"803530149c274994fabc6d28cbe03679","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"5a3ddfae96178e025f27bf1f69bfa629","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"d636ffb7a80fc29b133d32e4250fbab6","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"5daed103918277e2065dd7e8d23e57a5","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"79b31feacab0b1ccddf358be5dfb6241","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"24458ace9566a01d255bca16b46a960d","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"6e9356d0a5e7fbabb386824ec370d6f3","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"990b8a9755af25452c85f23ceb344be4","desc":"bbc_acorn8271","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":"1d250b0242e447e9106e8bfd1f27ea84","desc":"bbc_acorn8271","mandatory":True},
        {"file":"saa5050.zip","md5":None,"desc":"saa5050","mandatory":True},
        {"file":"saa5050.zip","md5":"8b3c10a2317808ed94d6c6073b5b3327","desc":"saa5050","mandatory":True},
        {"file":"bbc_tube_80186.zip","md5":None,"desc":"bbc_tube_80186","mandatory":True},
        {"file":"bbc_tube_80186.zip","md5":"33d097349f12526584fcac21eccf3012","desc":"bbc_tube_80186","mandatory":True},
        {"file":"bbc_tube_80186.zip","md5":"e6e84221c29b5d31d07055039583c8e7","desc":"bbc_tube_80186","mandatory":True},
        {"file":"bbcm.zip","md5":None,"desc":"bbcm","mandatory":True},
        {"file":"bbcm.zip","md5":"b159012f9f301bab33316fd3bf55db79","desc":"bbcm","mandatory":True},
        {"file":"bbcm.zip","md5":"fed079c5e2c595b354529a8ea703b5fb","desc":"bbcm","mandatory":True},
        {"file":"bbcm.zip","md5":"ca0527f13f83bc95ef4b6833ee440afa","desc":"bbcm","mandatory":True},
        {"file":"bbcm.zip","md5":"ee9fc46252b7d7fe341b9c7f92575099","desc":"bbcm","mandatory":True},
        {"file":"bbcm.zip","md5":"3f3dd4614db30f6e383794731272076a","desc":"bbcm","mandatory":True},
        {"file":"bbcmc.zip","md5":None,"desc":"bbcmc","mandatory":True},
        {"file":"bbcmc.zip","md5":"55586a88477505d8fd28edfae646e2e3","desc":"bbcmc","mandatory":True},
        {"file":"bbcmc.zip","md5":"956bf71da840943050836ade2474ef7b","desc":"bbcmc","mandatory":True},
        {"file":"bbc_bitstik1.zip","md5":None,"desc":"bbc_bitstik1","mandatory":True},
        {"file":"bbc_bitstik1.zip","md5":"baf5cb5564ff6e6b4400243e7612f323","desc":"bbc_bitstik1","mandatory":True},
        {"file":"bbc_bitstik2.zip","md5":None,"desc":"bbc_bitstik2","mandatory":True},
        {"file":"bbc_bitstik2.zip","md5":"c196c145b3de630f85f625ca762e5504","desc":"bbc_bitstik2","mandatory":True},
        {"file":"mame/samples/bbc.zip","md5":None,"desc":"bbc","mandatory":True},
        {"file":"mame/samples/bbc.zip","md5":"9240120e32a59caabc6f5d462f87d683","desc":"bbc","mandatory":True},
        {"file":"mame/samples/bbc.zip","md5":"9d63bdc91cef4eda5e1a110e75c848fb","desc":"bbc","mandatory":True},
        {"file":"Acorn/basic2.rom","md5":"2cc67be4624df4dc66617742571a8e3d","desc":"basic2","mandatory":True},
        {"file":"BBCMicro/os12.rom","md5":"0a59a5ba15fe8557b5f7fee32bbd393a","desc":"os12","mandatory":True},
        {"file":"BBCMicro/dfs-2.26.rom","md5":"f083f49d6fe66344c650d7e74249cb96","desc":"dfs-2.26","mandatory":True},
    ],
    "beena": [
        {"file":"beena.zip","md5":None,"desc":"beena","mandatory":True},
    ],
    "bk": [
        {"file":"bk/B11M_BOS.ROM","md5":"fe4627d1e3a1535874085050733263e7","desc":"B11M_BOS","mandatory":True},
        {"file":"bk/B11M_EXT.ROM","md5":"dc52f365d56fa1951f5d35b1101b9e3f","desc":"B11M_EXT","mandatory":True},
        {"file":"bk/BAS11M_0.ROM","md5":"946f6f23ded03c0e26187f0b3ca75993","desc":"BAS11M_0","mandatory":True},
        {"file":"bk/BAS11M_1.ROM","md5":"1e6637f32aa7d1de03510030cac40bcf","desc":"BAS11M_1","mandatory":True},
        {"file":"bk/DISK_327.ROM","md5":"5015228eeeb238e65da8edcd1b6dfac7","desc":"DISK_327","mandatory":True},
        {"file":"bk/BASIC10.ROM","md5":"3fa774326d75410a065659aea80252f0","desc":"BASIC10","mandatory":True},
        {"file":"bk/FOCAL10.ROM","md5":"5737f972e8638831ab71e9139abae052","desc":"FOCAL10","mandatory":True},
        {"file":"bk/MONIT10.ROM","md5":"95f8c41c6abf7640e35a6a03cecebd01","desc":"MONIT10","mandatory":True},
        {"file":"bk0010.zip","md5":None,"desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"95f8c41c6abf7640e35a6a03cecebd01","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"eb9e1cf1c1b36a2dece89624bfc59323","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"93d2776ecf9abf49fb45f58ce3182143","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"4a4530347ee18c547a0563aca73cf43d","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"86fc2f7797a0333300159aa222c3ad3f","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"fb8875a62b9b02a66670dcefc270d441","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"c113a36e51f4557594817bc35a4b63b7","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"823d35a8c98f70d2d378a2c7568c3b23","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"1e6637f32aa7d1de03510030cac40bcf","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"dc52f365d56fa1951f5d35b1101b9e3f","desc":"bk0010","mandatory":True},
        {"file":"bk0010.zip","md5":"fe4627d1e3a1535874085050733263e7","desc":"bk0010","mandatory":True},
    ],
    "camplynx": [
        {"file":"lynx48k.zip","md5":None,"desc":"lynx48k","mandatory":True},
        {"file":"lynx48k.zip","md5":"b0ad5bf3070aea27b637e1998c81fa8c","desc":"lynx48k","mandatory":True},
        {"file":"lynx48k.zip","md5":"b665e10211bbdbfaf2defb32d5580892","desc":"lynx48k","mandatory":True},
        {"file":"lynx48k.zip","md5":"bc0760d8bf61c9683270266d259cd2ae","desc":"lynx48k","mandatory":True},
        {"file":"lynx48k.zip","md5":"dde90a794e5324002a9fd7f79cec3172","desc":"lynx48k","mandatory":True},
        {"file":"lynx96k.zip","md5":None,"desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"a0a8f136f69b5891d33993627a185697","desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"fcb706b3ba2ba61f6f7af1c28f420f94","desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"815afa653b61cbe70936b01aff700912","desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"3ccdb9dfe6018892383fcbb1a9167d76","desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"01a9770efdab17f089bbbbe53f5d69fa","desc":"lynx96k","mandatory":True},
        {"file":"lynx96k.zip","md5":"89ba52f683cd79638646874e965476b6","desc":"lynx96k","mandatory":True},
        {"file":"lynx128k.zip","md5":None,"desc":"lynx128k","mandatory":True},
        {"file":"lynx128k.zip","md5":"fcb706b3ba2ba61f6f7af1c28f420f94","desc":"lynx128k","mandatory":True},
        {"file":"lynx128k.zip","md5":"5017fe3a2ea47038ae61e2aeb4f43d65","desc":"lynx128k","mandatory":True},
        {"file":"lynx128k.zip","md5":"bf69d9538192f65571dbed43dc4a99bb","desc":"lynx128k","mandatory":True},
        {"file":"lynx128k.zip","md5":"f9f54913cdedb22bb8f0c549ad121379","desc":"lynx128k","mandatory":True},
    ],
    "cdi": [
        {"file":"cdimono1.zip","md5":None,"desc":"cdimono1","mandatory":True},
        {"file":"cdimono1.zip","md5":"2969341396aa61e0143dc2351aaa6ef6","desc":"cdimono1","mandatory":True},
        {"file":"cdimono1.zip","md5":"ac80a92c988ce07fbd6a8f21ded34cf1","desc":"cdimono1","mandatory":True},
        {"file":"cdimono1.zip","md5":"ac0d468be366779c9df633be98da250a","desc":"cdimono1","mandatory":True},
        {"file":"cdimono1.zip","md5":"3e59b8a9a423d3ecd612a32fe4e2d748","desc":"cdimono1","mandatory":True},
        {"file":"cdimono1.zip","md5":"3d20cf7550f1b723158b42a1fd5bac62","desc":"cdimono1","mandatory":True},
    ],
    "cgenie": [
        {"file":"cgenie.zip","md5":None,"desc":"cgenie","mandatory":True},
    ],
    "channelf": [
        {"file":"sl31253.bin","md5":"ac9804d4c0e9d07e33472e3726ed15c3","desc":"sl31253","mandatory":True},
        {"file":"sl31254.bin","md5":"da98f4bb3242ab80d76629021bb27585","desc":"sl31254","mandatory":True},
        {"file":"sl90025.bin","md5":"95d339631d867c8f1d15a5f2ec26069d","desc":"sl90025","mandatory":True},
    ],
    "chihiro": [
        {"file":"mcpx_1.0.bin","md5":"d49c52a4102f6df7bcf8d0617ac475ed","desc":"mcpx_1.0","mandatory":True},
        {"file":"cerbios.bin","md5":"f23d7e00ae8fbf88908ed1f9165f35eb","desc":"cerbios","mandatory":True},
    ],
    "coco": [
        {"file":"coco.zip","md5":None,"desc":"coco","mandatory":True},
        {"file":"coco.zip","md5":"a74f3d95b395dad7cdca19d560eeea74","desc":"coco","mandatory":True},
        {"file":"coco2.zip","md5":None,"desc":"coco2","mandatory":True},
        {"file":"coco2.zip","md5":"c933316c7d939532a13648850c1c2aa6","desc":"coco2","mandatory":True},
        {"file":"coco2.zip","md5":"21070aa0496142b886c562bf76d7c113","desc":"coco2","mandatory":True},
        {"file":"coco2b.zip","md5":None,"desc":"coco2b","mandatory":True},
        {"file":"coco2b.zip","md5":"c2fc43556eb6b7b25bdf5955bd9df825","desc":"coco2b","mandatory":True},
        {"file":"coco2.zip","md5":"21070aa0496142b886c562bf76d7c113","desc":"coco2","mandatory":True},
        {"file":"coco3.zip","md5":None,"desc":"coco3","mandatory":True},
        {"file":"coco3.zip","md5":"7233c6c429f3ce1c7392f28a933e0b6f","desc":"coco3","mandatory":True},
        {"file":"coco3p.zip","md5":None,"desc":"coco3p","mandatory":True},
        {"file":"coco3p.zip","md5":"4ae57e5a8e7494e5485446fefedb580b","desc":"coco3p","mandatory":True},
        {"file":"coco_fdc_v11.zip","md5":None,"desc":"coco_fdc_v11","mandatory":True},
        {"file":"coco_fdc_v11.zip","md5":"8cab28f4b7311b8df63c07bb3b59bfd5","desc":"coco_fdc_v11","mandatory":True},
        {"file":"xroar/bas10.rom","md5":"a74f3d95b395dad7cdca19d560eeea74","desc":"bas10","mandatory":True},
        {"file":"xroar/bas12.rom","md5":"c933316c7d939532a13648850c1c2aa6","desc":"bas12","mandatory":True},
        {"file":"xroar/bas13.rom","md5":"c2fc43556eb6b7b25bdf5955bd9df825","desc":"bas13","mandatory":True},
        {"file":"xroar/extbas11.rom","md5":"21070aa0496142b886c562bf76d7c113","desc":"extbas11","mandatory":True},
        {"file":"xroar/coco3.rom","md5":"7233c6c429f3ce1c7392f28a933e0b6f","desc":"coco3","mandatory":True},
        {"file":"xroar/coco3p.rom","md5":"4ae57e5a8e7494e5485446fefedb580b","desc":"coco3p","mandatory":True},
        {"file":"xroar/disk11.rom","md5":"8cab28f4b7311b8df63c07bb3b59bfd5","desc":"disk11","mandatory":True},
    ],
    "colecovision": [
        {"file":"colecovision.rom","md5":"2c66f5911e5b42b8ebe113403548eee7","desc":"colecovision","mandatory":True},
    ],
    "crvision": [
        {"file":"crvision.zip","md5":None,"desc":"crvision","mandatory":True},
        {"file":"crvision.zip","md5":"3b1ef759d8e3fb4071582efd33dd05f9","desc":"crvision","mandatory":True},
    ],
    "dragon64": [
        {"file":"dragon64.zip","md5":None,"desc":"dragon64","mandatory":True},
        {"file":"dragon64.zip","md5":"5f0bee59710e55f5880e74890912ed78","desc":"dragon64","mandatory":True},
        {"file":"dragon64.zip","md5":"fd91edce7be5e7c2d88e46b76956a8aa","desc":"dragon64","mandatory":True},
        {"file":"dragon32.zip","md5":None,"desc":"dragon32","mandatory":True},
        {"file":"dragon32.zip","md5":None,"desc":"dragon32","mandatory":True},
        {"file":"xroar/d32.rom","md5":"3420b96031078a4ef408cad7bf21a33f","desc":"d32","mandatory":True},
        {"file":"xroar/d64_1.rom","md5":"5f0bee59710e55f5880e74890912ed78","desc":"d64_1","mandatory":True},
        {"file":"xroar/d64_2.rom","md5":"fd91edce7be5e7c2d88e46b76956a8aa","desc":"d64_2","mandatory":True},
        {"file":"xroar/ddos10.rom","md5":"1c965da49b6c5459b8353630aa1482e7","desc":"ddos10","mandatory":True},
    ],
    "dreamcast": [
        {"file":"dc/dc_boot.bin","md5":"e10c53c2f8b90bab96ead2d368858623","desc":"dc_boot","mandatory":True},
    ],
    "electron": [
        {"file":"electron.zip","md5":None,"desc":"electron","mandatory":True},
        {"file":"electron.zip","md5":"4688a93aa298b9431c1788c9b90378c8","desc":"electron","mandatory":True},
        {"file":"electron64.zip","md5":None,"desc":"electron64","mandatory":True},
        {"file":"electron64.zip","md5":"2cc67be4624df4dc66617742571a8e3d","desc":"electron64","mandatory":True},
        {"file":"electron64.zip","md5":"df01cfe5894276de96bbd1c45b7e834c","desc":"electron64","mandatory":True},
        {"file":"electron_plus1.zip","md5":None,"desc":"electron_plus1","mandatory":True},
        {"file":"electron_plus1.zip","md5":"f3a39227b401a2ce8cdc7e4b7a860aaf","desc":"electron_plus1","mandatory":True},
        {"file":"electron_plus3.zip","md5":None,"desc":"electron_plus3","mandatory":True},
        {"file":"electron_plus3.zip","md5":"9aa334b4e8f6d7565e6323e0f77110de","desc":"electron_plus3","mandatory":True},
        {"file":"electron_plus3.zip","md5":"83e15ca501899b0d5b2ce3f5ef696069","desc":"electron_plus3","mandatory":True},
        {"file":"electron_plus3.zip","md5":"b60ee811f4b805638478acd5297b16e0","desc":"electron_plus3","mandatory":True},
        {"file":"electron_plus3.zip","md5":"62f5e1d3dae3a68d8fe4406a6f603dc3","desc":"electron_plus3","mandatory":True},
        {"file":"electron_plus3.zip","md5":"5c39baa89fe8a40a5167a53cc5ae7791","desc":"electron_plus3","mandatory":True},
    ],
    "enterprise": [
        {"file":"ep128emu/roms/exos21.rom","md5":"f36f24cbb87745fbd2714e4df881db09","desc":"exos21","mandatory":True},
        {"file":"ep128emu/roms/basic21.rom","md5":"e972fe42b398c9ff1d93ff014786aec6","desc":"basic21","mandatory":True},
        {"file":"ep128emu/roms/exdos13.rom","md5":"ddff70c014d1958dc75378b6c9aab6f8","desc":"exdos13","mandatory":True},
        {"file":"ep128emu/roms/epfileio.rom","md5":"a68ebcbc73a4d2178d755b7755bf18fe","desc":"epfileio","mandatory":True},
        {"file":"ep128emu/roms/exos20.rom","md5":"5ad3baaad3b5156d6b60b34229a676fb","desc":"exos20","mandatory":True},
        {"file":"ep128emu/roms/basic20.rom","md5":"8e18edce4a7acb2c33cc0ab18f988482","desc":"basic20","mandatory":True},
        {"file":"ep128emu/roms/exos24uk.rom","md5":"55af78f877a21ca45eb2df68a74fcc60","desc":"exos24uk","mandatory":True},
        {"file":"ep128emu/roms/hun.rom","md5":"22167938f142c222f40992839aa21a06","desc":"hun","mandatory":True},
        {"file":"ep128emu/roms/epd19hft.rom","md5":"12cfc9c7e48c8a16c2e09edbd926d467","desc":"epd19hft","mandatory":True},
        {"file":"ep128emu/roms/zt19hfnt.rom","md5":"653daaf7b9b29c2c4e577f489580f247","desc":"zt19hfnt","mandatory":True},
        {"file":"ep128emu/roms/brd.rom","md5":"6af0402906944fd134004b85097c8524","desc":"brd","mandatory":True},
        {"file":"ep128emu/roms/zt19uk.rom","md5":"228540b6be83ae2acd7569c8ff0f91d0","desc":"zt19uk","mandatory":True},
        {"file":"ep64.zip","md5":"5ad3baaad3b5156d6b60b34229a676fb","desc":"ep64","mandatory":True},
        {"file":"ep128.zip","md5":"f36f24cbb87745fbd2714e4df881db09","desc":"ep128","mandatory":True},
        {"file":"ep64_exdos.zip","md5":"47258d03aec37bc24df5dbc5d50fc9f8","desc":"ep64_exdos","mandatory":True},
    ],
    "fds": [
        {"file":"disksys.rom","md5":"ca30b50f880eb660a320674ed365ef7a","desc":"disksys","mandatory":True},
    ],
    "fm7": [
        {"file":"fm7.zip","md5":None,"desc":"fm7","mandatory":True},
        {"file":"fm7.zip","md5":"9f9b7d5615ecdbde2cd26e9306ffef13","desc":"fm7","mandatory":True},
        {"file":"fm7.zip","md5":"18a461ccaf7ef4e8ecad58cecd3a24b3","desc":"fm7","mandatory":True},
        {"file":"fm7.zip","md5":"6a5da0404b7ee338df9002cdcabc3068","desc":"fm7","mandatory":True},
        {"file":"fm7.zip","md5":"a330817f8f7ced752a7bcc8dfba8fd2e","desc":"fm7","mandatory":True},
        {"file":"fm7.zip","md5":"d19ed5923aaae2ec43dffe7a0daa80cb","desc":"fm7","mandatory":True},
        {"file":"fm77av.zip","md5":None,"desc":"fm77av","mandatory":True},
        {"file":"fm77av.zip","md5":"71c96a45b78e88a39cb94c1aabd23d8a","desc":"fm77av","mandatory":True},
        {"file":"fm77av.zip","md5":"e0f4c0ebee60aee83e863826e59ae1de","desc":"fm77av","mandatory":True},
        {"file":"fm77av.zip","md5":"ae945a6dfb642b0a5d0529737e8ee5cd","desc":"fm77av","mandatory":True},
        {"file":"fm77av.zip","md5":"fb83a1a9725c8432acef0c3ce89492e3","desc":"fm77av","mandatory":True},
        {"file":"fm77av.zip","md5":"7db27dede3e358017d518101850bccfa","desc":"fm77av","mandatory":True},
    ],
    "fmtowns": [
        {"file":"fmtowns/FMT_DIC.ROM","md5":"8fa4e553f28cfc0c30a0a1e589799942","desc":"FMT_DIC","mandatory":True},
        {"file":"fmtowns/FMT_DOS.ROM","md5":"0585b19930d4a7f4c71bcc8a33746588","desc":"FMT_DOS","mandatory":True},
        {"file":"fmtowns/FMT_F20.ROM","md5":"ac0c7021e9bf48ca84b51ab651169a88","desc":"FMT_F20","mandatory":True},
        {"file":"fmtowns/FMT_FNT.ROM","md5":"b91300e55b70227ce98b59c5f02fa8dd","desc":"FMT_FNT","mandatory":True},
        {"file":"fmtowns/FMT_SYS.ROM","md5":"86fb6f7280689259f0ca839dd3dd6cde","desc":"FMT_SYS","mandatory":True},
        {"file":"fmtmarty.zip","md5":None,"desc":"fmtmarty","mandatory":True},
        {"file":"fmtmarty.zip","md5":"6618519b2c104cf9b7e71a48381b44a9","desc":"fmtmarty","mandatory":True},
        {"file":"fmtmarty.zip","md5":"75a5c7afb4bc8221bab8cf24db417950","desc":"fmtmarty","mandatory":True},
        {"file":"fmtowns.zip","md5":None,"desc":"fmtowns","mandatory":True},
        {"file":"fmtowns.zip","md5":"34847786d7de94b5d1133c956ab1d75d","desc":"fmtowns","mandatory":True},
        {"file":"fmtowns.zip","md5":"0585b19930d4a7f4c71bcc8a33746588","desc":"fmtowns","mandatory":True},
        {"file":"fmtowns.zip","md5":"eb44f2093f51eb7159f03e170b13af76","desc":"fmtowns","mandatory":True},
        {"file":"fmtowns.zip","md5":"feaf8c5675151e00cfe3ad27673bff29","desc":"fmtowns","mandatory":True},
        {"file":"fmtownsux.zip","md5":None,"desc":"fmtownsux","mandatory":True},
        {"file":"fmtownsux.zip","md5":"8fa4e553f28cfc0c30a0a1e589799942","desc":"fmtownsux","mandatory":True},
        {"file":"fmtownsux.zip","md5":"03c8fac9a5f5f5f35fb5de5a5d0d018f","desc":"fmtownsux","mandatory":True},
        {"file":"fmtownsux.zip","md5":"b91300e55b70227ce98b59c5f02fa8dd","desc":"fmtownsux","mandatory":True},
        {"file":"fmtownsux.zip","md5":"90b5e01d42aaa93e8f4503a5e94e120b","desc":"fmtownsux","mandatory":True},
        {"file":"fmtownsux.zip","md5":"1a15f6c1b58ec7e5f850118610a787a7","desc":"fmtownsux","mandatory":True},
    ],
    "gamate": [
        {"file":"gamate.zip","md5":None,"desc":"gamate","mandatory":True},
        {"file":"gamate.zip","md5":"b411167df6dd563111729296f4c547f6","desc":"gamate","mandatory":True},
        {"file":"gamate.zip","md5":"ef67993a94503c4b7798b5901c7dda52","desc":"gamate","mandatory":True},
    ],
    "gamecom": [
        {"file":"gamecom.zip","md5":None,"desc":"gamecom","mandatory":True},
        {"file":"gamecom.zip","md5":"813364d4863b1d7b7b8fd6a97a416bcf","desc":"gamecom","mandatory":True},
        {"file":"gamecom.zip","md5":"f7bcefb6daf923c8e5ea2eb69f619efe","desc":"gamecom","mandatory":True},
    ],
    "gamecube": [
        {"file":"GC/EUR/IPL.bin","md5":"db92574caab77a7ec99d4605fd6f2450","desc":"IPL","mandatory":True},
        {"file":"GC/JAP/IPL.bin","md5":"b17148254a5799684c7d783206504926","desc":"IPL","mandatory":True},
        {"file":"GC/USA/IPL.bin","md5":"b17148254a5799684c7d783206504926","desc":"IPL","mandatory":True},
    ],
    "gamepock": [
        {"file":"gamepock.zip","md5":None,"desc":"gamepock","mandatory":True},
        {"file":"gamepock.zip","md5":"a0dd595eafb407a6a4b4ed800005a394","desc":"gamepock","mandatory":True},
    ],
    "gba": [
        {"file":"gba_bios.bin","md5":"a860e8c0b6d573d191e4ec7db1b1e4f6","desc":"gba_bios","mandatory":True},
        {"file":"gb_bios.bin","md5":"32fbbd84168d3482956eb3c5051637f5","desc":"gb_bios","mandatory":True},
        {"file":"gbc_bios.bin","md5":"dbfce9db9deaa2567f6a84fde55f9680","desc":"gbc_bios","mandatory":True},
        {"file":"sgb_bios.bin","md5":"d574d4f9c12f305074798f54c091a8b4","desc":"sgb_bios","mandatory":True},
    ],
    "gmaster": [
        {"file":"gmaster.zip","md5":None,"desc":"gmaster","mandatory":True},
        {"file":"gmaster.zip","md5":"6bff08b5e5f96de405cd56d5f04a08f8","desc":"gmaster","mandatory":True},
    ],
    "gp32": [
        {"file":"gp32.zip","md5":None,"desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"e64ad881b5e1d86547f2edc3034946d9","desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"f78092f15f6ffe15975901ee4e92c680","desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"19021cc891119c0872d46e87fc0ffe35","desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"1e4d3216719acea231b81dfcf6069aef","desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"cac4b56c0db80922cae75403faef40af","desc":"gp32","mandatory":True},
        {"file":"gp32.zip","md5":"d4af2bc352bdaf4972ea40902feda114","desc":"gp32","mandatory":True},
    ],
    "gsplus": [
        {"file":"ROM1","md5":"20a0334c447cb069a040ae5be1d938df","desc":"ROM1","mandatory":True},
    ],
    "hikaru": [
        {"file":"hikaru.zip","md5":"040f9b37a1f802d450379aaec106ec69","desc":"hikaru","mandatory":True},
        {"file":"mie.zip","md5":"e95415b161121bef35ade12367138c63","desc":"mie","mandatory":True},
        {"file":"jvs13551.zip","md5":"ee643e8c7369fe7feca610d4daa4a57c","desc":"jvs13551","mandatory":True},
    ],
    "intellivision": [
        {"file":"exec.bin","md5":"62e761035cb657903761800f4437b8af","desc":"exec","mandatory":True},
        {"file":"grom.bin","md5":"0cd5946c6473e42e8e4c2137785e427f","desc":"grom","mandatory":True},
    ],
    "laser310": [
        {"file":"laser310.zip","md5":None,"desc":"laser310","mandatory":True},
        {"file":"laser310.zip","md5":"42c8f9e6c2133ae0e953b89ccbbdb7e2","desc":"laser310","mandatory":True},
        {"file":"laser310.zip","md5":"f7e5d9a3eb2b57bf5f4e2a4565318a8f","desc":"laser310","mandatory":True},
    ],
    "loopy": [
        {"file":"casloopy.zip","md5":"0e1d8dc0110ecf8201c0cef11ef4a858","desc":"casloopy","mandatory":True},
        {"file":"casloopy.zip","md5":"d527e3ed1bf9bd0661154c202a65c5bd","desc":"casloopy","mandatory":True},
        {"file":"casloopy.zip","md5":"c0f1c899c9ca098663d046d60779711d","desc":"casloopy","mandatory":True},
    ],
    "lynx": [
        {"file":"lynxboot.img","md5":"fcd403db69f54290b51035d82f835e7b","desc":"lynxboot","mandatory":True},
    ],
    "macintosh": [
        {"file":"MacII.ROM","md5":"66223be1497460f1e60885eeb35e03cc","desc":"MacII","mandatory":True},
        {"file":"MacIIx.ROM","md5":"2a8a4c7f2a38e0ab0771f59a9a0f1ee4","desc":"MacIIx","mandatory":True},
        {"file":"mac128k.zip","md5":None,"desc":"mac128k","mandatory":True},
        {"file":"mac128k.zip","md5":"bc04a4252ee96826c1f41f927c145225","desc":"mac128k","mandatory":True},
        {"file":"mac128k.zip","md5":"409d8b9a04db15b7bfbbd5fcb931bf2e","desc":"mac128k","mandatory":True},
        {"file":"mackbd_m0110.zip","md5":None,"desc":"mackbd_m0110","mandatory":True},
        {"file":"mackbd_m0110.zip","md5":"9d09a9a51c9ef3ea5719e19db22e7901","desc":"mackbd_m0110","mandatory":True},
        {"file":"mackbd_m0120.zip","md5":None,"desc":"mackbd_m0120","mandatory":True},
        {"file":"mackbd_m0120.zip","md5":"9d09a9a51c9ef3ea5719e19db22e7901","desc":"mackbd_m0120","mandatory":True},
        {"file":"mac512k.zip","md5":None,"desc":"mac512k","mandatory":True},
        {"file":"mac512k.zip","md5":"b4118b89fa68a913a225f0cf9a751fae","desc":"mac512k","mandatory":True},
        {"file":"mac512k.zip","md5":"ab4e461833e98ef7106f24455a07769d","desc":"mac512k","mandatory":True},
        {"file":"macplus.zip","md5":None,"desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"1467a42dee57ac265d063b3f351189fc","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"25b1bf85b3b072d957499cef4d7e313f","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"cf7c3259844245a8967556fa40d81243","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"d5584762b43a9b1cb24a981f9b9b4198","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"f83069fd7ff1fb011958f819cbff4c88","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"875919e2544644cd628f44b5c11db036","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"efcefe8f11c10541a503d48a07878201","desc":"macplus","mandatory":True},
        {"file":"macplus.zip","md5":"f4b06da98500df0747a764dfbf1862b9","desc":"macplus","mandatory":True},
        {"file":"macse.zip","md5":None,"desc":"macse","mandatory":True},
        {"file":"macse.zip","md5":"9fb38bdcc0d53d9d380897ee53dc1322","desc":"macse","mandatory":True},
        {"file":"macclasc.zip","md5":None,"desc":"macclasc","mandatory":True},
        {"file":"macclasc.zip","md5":"c229bb677cb41b84b780c9e38a09173e","desc":"macclasc","mandatory":True},
        {"file":"mac2fdhd.zip","md5":None,"desc":"mac2fdhd","mandatory":True},
        {"file":"mac2fdhd.zip","md5":"2a8a4c7f2a38e0ab0771f59a9a0f1ee4","desc":"mac2fdhd","mandatory":True},
        {"file":"nb_mdc824.zip","md5":None,"desc":"nb_mdc824","mandatory":True},
        {"file":"nb_mdc824.zip","md5":"7500a6a958247ee6e092f08715f2fff8","desc":"nb_mdc824","mandatory":True},
        {"file":"maciix.zip","md5":None,"desc":"maciix","mandatory":True},
        {"file":"maciix.zip","md5":"2a8a4c7f2a38e0ab0771f59a9a0f1ee4","desc":"maciix","mandatory":True},
        {"file":"maclc3.zip","md5":None,"desc":"maclc3","mandatory":True},
        {"file":"maclc3.zip","md5":"fa16d49527c4e6e9c0d9e46904133d39","desc":"maclc3","mandatory":True},
        {"file":"mackbd_m0110a.zip","md5":None,"desc":"mackbd_m0110a","mandatory":True},
        {"file":"mackbd_m0110a.zip","md5":"9e8ea1552153c5e0f895e247e7d3ec1c","desc":"mackbd_m0110a","mandatory":True},
        {"file":"nb_image.zip","md5":None,"desc":"nb_image","mandatory":True},
        {"file":"nb_image.zip","md5":"93155ac7bad0fec36837252bb1e408f2","desc":"nb_image","mandatory":True},
        {"file":"egret.zip","md5":None,"desc":"egret","mandatory":True},
        {"file":"egret.zip","md5":"96665499f5cf2bb5b4aae6fdaf0a9fb5","desc":"egret","mandatory":True},
        {"file":"egret.zip","md5":"b955ecbdf6d2f979f3683dd1d6884643","desc":"egret","mandatory":True},
        {"file":"egret.zip","md5":"5035d321c5d5fa1eab5ce6bf986676e4","desc":"egret","mandatory":True},
        {"file":"adbmodem.zip","md5":None,"desc":"adbmodem","mandatory":True},
        {"file":"adbmodem.zip","md5":"862b8598cecdbc934658c4cb599a8142","desc":"adbmodem","mandatory":True},
        {"file":"macos3.img","md5":None,"desc":"macos3","mandatory":True},
        {"file":"macos608.img","md5":None,"desc":"macos608","mandatory":True},
        {"file":"macos701.img","md5":None,"desc":"macos701","mandatory":True},
        {"file":"macos75.img","md5":None,"desc":"macos75","mandatory":True},
        {"file":"mac608.chd","md5":None,"desc":"mac608","mandatory":True},
        {"file":"mac701.chd","md5":None,"desc":"mac701","mandatory":True},
        {"file":"mac755.chd","md5":None,"desc":"mac755","mandatory":True},
    ],
    "mc10": [
        {"file":"mc10.zip","md5":None,"desc":"mc10","mandatory":True},
        {"file":"mc10.zip","md5":"f29e94ff36577ffb6a787959e45bfe85","desc":"mc10","mandatory":True},
        {"file":"alice.zip","md5":None,"desc":"alice","mandatory":True},
        {"file":"alice.zip","md5":"78af465c2f31cf4e05dec1efda77da01","desc":"alice","mandatory":True},
        {"file":"xroar/mc10.rom","md5":"f29e94ff36577ffb6a787959e45bfe85","desc":"mc10","mandatory":True},
        {"file":"xroar/alice.rom","md5":"78af465c2f31cf4e05dec1efda77da01","desc":"alice","mandatory":True},
    ],
    "megadrive-msu": [
        {"file":"bios_CD_E.bin","md5":"e66fa1dc5820d254611fdcdba0662372","desc":"bios_CD_E","mandatory":True},
        {"file":"bios_CD_U.bin","md5":"854b9150240a198070150e4566ae1290","desc":"bios_CD_U","mandatory":True},
        {"file":"bios_CD_J.bin","md5":"278a9397d192149e84e820ac621a8edd","desc":"bios_CD_J","mandatory":True},
    ],
    "msx": [
        {"file":"MSX.ROM","md5":"364a1a579fe5cb8dba54519bcfcdac0d","desc":"MSX","mandatory":True},
    ],
    "msx1": [
        {"file":"openmsx/px-7_pbasic.rom","md5":"281809cafe63437fc4bffb3033fbd0db","desc":"px-7_pbasic","mandatory":True},
        {"file":"openmsx/px-7_basic-bios1.rom","md5":"9218f6dd89f7ba01e3090d44721b4260","desc":"px-7_basic-bios1","mandatory":True},
    ],
    "msx2": [
        {"file":"MSX2.ROM","md5":"ec3a01c91f24fbddcbcab0ad301bc9ef","desc":"MSX2","mandatory":True},
        {"file":"MSX2EXT.ROM","md5":"2183c2aff17cf4297bdb496de78c2e8a","desc":"MSX2EXT","mandatory":True},
    ],
    "msx2+": [
        {"file":"openmsx/fs-a1wsx_kanjifont.rom","md5":"acf53887c2d2783dc059a9b442c86b90","desc":"fs-a1wsx_kanjifont","mandatory":True},
        {"file":"openmsx/fs-a1wsx_basic-bios2p.rom","md5":"c5c26c3e8bc6c485424818057f0507b9","desc":"fs-a1wsx_basic-bios2p","mandatory":True},
        {"file":"openmsx/fs-a1wsx_fmbasic.rom","md5":"0c40e7db1c1fcc2405e4d0cdd215adb4","desc":"fs-a1wsx_fmbasic","mandatory":True},
        {"file":"openmsx/fs-a1wsx_msx2psub.rom","md5":"7c8243c71d8f143b2531f01afa6a05dc","desc":"fs-a1wsx_msx2psub","mandatory":True},
        {"file":"openmsx/fs-a1wsx_kanjibasic.rom","md5":"9dfdebfaa6b547222a40aab8bb2e29f8","desc":"fs-a1wsx_kanjibasic","mandatory":True},
        {"file":"openmsx/fs-a1wsx_disk.rom","md5":"00aa02b6077de40a0b51d71a3c3e1d5f","desc":"fs-a1wsx_disk","mandatory":True},
        {"file":"openmsx/fs-a1wsx_firmware.rom","md5":"fa8e7d4b999af058fe2864a5f2e014ec","desc":"fs-a1wsx_firmware","mandatory":True},
        {"file":"openmsx/phc-70fd2_basickun.rom","md5":"2ce20986da024e9a0e271961c6bc9f01","desc":"phc-70fd2_basickun","mandatory":True},
        {"file":"openmsx/yrw801.rom","md5":"42af93619160ef2116416f74a6cb12f2","desc":"yrw801","mandatory":True},
    ],
    "msxturbor": [
        {"file":"openmsx/fs-a1gt_firmware.rom","md5":"af17a344bcc177b97a4888c4c559f3ae","desc":"fs-a1gt_firmware","mandatory":True},
        {"file":"openmsx/fs-a1gt_kanjifont.rom","md5":"acf53887c2d2783dc059a9b442c86b90","desc":"fs-a1gt_kanjifont","mandatory":True},
        {"file":"openmsx/ide250.zip","md5":"afa4b5f2944334f84971af814a24bd5a","desc":"ide250","mandatory":True},
        {"file":"openmsx/phc-70fd2_basickun.rom","md5":"2ce20986da024e9a0e271961c6bc9f01","desc":"phc-70fd2_basickun","mandatory":True},
        {"file":"openmsx/yrw801.rom","md5":"42af93619160ef2116416f74a6cb12f2","desc":"yrw801","mandatory":True},
    ],
    "mz2000": [
        {"file":"mz2000.zip","md5":None,"desc":"mz2000","mandatory":True},
        {"file":"mz2000.zip","md5":"f8b599b75ad6ff3eeaeb58ccc0190684","desc":"mz2000","mandatory":True},
        {"file":"mz2000.zip","md5":"dea49b39998885631db16de1176e71b9","desc":"mz2000","mandatory":True},
    ],
    "mz2500": [
        {"file":"mz2500.zip","md5":None,"desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"714ddaf418ccf0018e4cc7e31694b3d8","desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"96f2fdff0deba58611ed4d67705b539d","desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"88cd64f7bdd23ca6ea57b173254ead82","desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"3d5d1f6ba9d1f04378891c35663bd3a8","desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"eea42ca607369a225dbd9d11ab48bfd0","desc":"mz2500","mandatory":True},
        {"file":"mz2500.zip","md5":"04843d14a8e2f69a7fcaff394a8cc012","desc":"mz2500","mandatory":True},
    ],
    "mz700": [
        {"file":"mz700.zip","md5":None,"desc":"mz700","mandatory":True},
        {"file":"mz700.zip","md5":"27990ced7cb97dd80356f517aa705010","desc":"mz700","mandatory":True},
        {"file":"mz700.zip","md5":"e9045d57e8574f3eb3f775c02369fbfe","desc":"mz700","mandatory":True},
    ],
    "mz800": [
        {"file":"mz800.zip","md5":None,"desc":"mz800","mandatory":True},
        {"file":"mz800.zip","md5":"7d3909267b3f3e6ce7aa999de0ded226","desc":"mz800","mandatory":True},
    ],
    "mz80k": [
        {"file":"mz80k.zip","md5":None,"desc":"mz80k","mandatory":True},
        {"file":"mz80k.zip","md5":"5db7707d120c835751899b0d1df5ad39","desc":"mz80k","mandatory":True},
        {"file":"mz80k.zip","md5":"3380dff179941e96851cfee7156e31de","desc":"mz80k","mandatory":True},
        {"file":"mz80kj.zip","md5":None,"desc":"mz80kj","mandatory":True},
        {"file":"mz80kj.zip","md5":"e5413f1a0d94726156dcae7d63f8f35f","desc":"mz80kj","mandatory":True},
        {"file":"mz80kj.zip","md5":"4138784bdd2e2cbacd6c55eff195b2ac","desc":"mz80kj","mandatory":True},
    ],
    "n64dd": [
        {"file":"64DD_IPL.bin","md5":"8d3d9f294b6e174bc7b1d2fd1c727530","desc":"64DD_IPL","mandatory":True},
    ],
    "naomi": [
        {"file":"dc/naomi.zip","md5":"eb4099aeb42ef089cfe94f8fe95e51f6","desc":"naomi","mandatory":True},
    ],
    "naomi2": [
        {"file":"dc/naomi2.zip","md5":None,"desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"728bfe038ce280872057e365ebfc0fee","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"baf83367044924067e09856ba164aa6f","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"6f8ad6e3ab04c8ae1cbcaa652b91cf4e","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"f3f39513484df216d9979f6ae7577942","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"ab046e62c51d67fb89eade2b8d5f6a8d","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"096a5217ff6e6c6cafe65a03336760ab","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"659d579ba9aef5b025d87323044e83f4","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"cbe0984d03d73869c23da5a3dd2ce207","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"b624ec7b3b90fdf3be103cdfb1679d1d","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"a9d82db14b823a5a57885bea1a998eb7","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"3b1315be24dc8d17f4fa18f3bfc5fe5c","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"0143cf852cb2a8a41f217bc688f62105","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"8b88c1f5a06e9b560e887c3b9f879237","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"b49702e4fadb3b5f9143a3d20afd04b5","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"ecadb008179ca1e6f4fe3fa091ab5df2","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"edeed38a9795e062a9af28c3eba22040","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"14e6bffff0d4dff6a5a547e7c43680ff","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"689d2228b00fb59781f82af6e8ecdb78","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"8373a11106c1c2fc21ac839f75ea488f","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"7eecfb8e8f82b47ffab92a0c5528100e","desc":"naomi2","mandatory":True},
        {"file":"dc/naomi2.zip","md5":"960ece0dc22a7c5ff81c812a2993e7cc","desc":"naomi2","mandatory":True},
    ],
    "nds": [
        {"file":"firmware.bin","md5":None,"desc":"firmware","mandatory":True},
        {"file":"bios7.bin","md5":"df692a80a5b1bc90728bc3dfc76cd948","desc":"bios7","mandatory":True},
        {"file":"bios9.bin","md5":"a392174eb3e572fed6447e956bde4b25","desc":"bios9","mandatory":True},
        {"file":"dsi_bios7.bin","md5":"559dae4ea78eb9d67702c56c1d791e81","desc":"dsi_bios7","mandatory":True},
        {"file":"dsi_bios9.bin","md5":"87b665fce118f76251271c3732532777","desc":"dsi_bios9","mandatory":True},
        {"file":"dsi_firmware.bin","md5":None,"desc":"dsi_firmware","mandatory":True},
        {"file":"dsi_nand.bin","md5":None,"desc":"dsi_nand","mandatory":True},
    ],
    "neogeo": [
        {"file":"neogeo.zip","md5":"dffb72f116d36d025068b23970a4f6df","desc":"neogeo","mandatory":True},
    ],
    "neogeocd": [
        {"file":"neocd/neocd_f.rom","md5":"8834880c33164ccbe6476b559f3e37de","desc":"neocd_f","mandatory":True},
        {"file":"neocd/neocd_sf.rom","md5":"043d76d5f0ef836500700c34faef774d","desc":"neocd_sf","mandatory":True},
        {"file":"neocd/neocd_t.rom","md5":"de3cf45d227ad44645b22aa83b49f450","desc":"neocd_t","mandatory":True},
        {"file":"neocd/neocd_st.rom","md5":"f6325a33c6d63ea4b9162a3fa8c32727","desc":"neocd_st","mandatory":True},
        {"file":"neocd/neocd_z.rom","md5":"11526d58d4c524daef7d5d677dc6b004","desc":"neocd_z","mandatory":True},
        {"file":"neocd/neocd_sz.rom","md5":"971ee8a36fb72da57aed01758f0a37f5","desc":"neocd_sz","mandatory":True},
        {"file":"neocd/front-sp1.bin","md5":"5c2366f25ff92d71788468ca492ebeca","desc":"front-sp1","mandatory":True},
        {"file":"neocd/top-sp1.bin","md5":"122aee210324c72e8a11116e6ef9c0d0","desc":"top-sp1","mandatory":True},
        {"file":"neocd/neocd.bin","md5":"f39572af7584cb5b3f70ae8cc848aba2","desc":"neocd","mandatory":True},
        {"file":"neocd/uni-bioscd.rom","md5":"08ca8b2dba6662e8024f9e789711c6fc","desc":"uni-bioscd","mandatory":True},
    ],
    "odyssey2": [
        {"file":"o2rom.bin","md5":"562d5ebf9e030a40d6fabfc2f33139fd","desc":"o2rom","mandatory":True},
        {"file":"c52.bin","md5":"f1071cdb0b6b10dde94d3bc8a6146387","desc":"c52","mandatory":True},
    ],
    "oricatmos": [
        {"file":"Oric/basic11.rom","md5":"a330779c42ad7d0c4ac6ef9e92788ec6","desc":"basic11","mandatory":True},
        {"file":"Oric/colour.rom","md5":"c888b36bf0fc222c3585c3fabe556d21","desc":"colour","mandatory":True},
    ],
    "pc60": [
        {"file":"pc6001.zip","md5":"2a13a60acf99a659144655b6c9e39b92","desc":"pc6001","mandatory":True},
        {"file":"pc6001.zip","md5":"9153f89e83f94f5d1cfe0a4e75d03372","desc":"pc6001","mandatory":True},
        {"file":"pc6001.zip","md5":"240738391e23f9b0337ab122df8ed7c0","desc":"pc6001","mandatory":True},
        {"file":"pc6001a.zip","md5":"8665e123c7d6b167677153f05a2f9c86","desc":"pc6001a","mandatory":True},
        {"file":"pc6001a.zip","md5":"7a740d0745e32e171115122442af909c","desc":"pc6001a","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"ec0fced1d7f242a823c6d6ebf9772045","desc":"pc6001mk2","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"808a4172c0e9cf2adf7c44fc8c549151","desc":"pc6001mk2","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"21f8cf17035d05e3b6b792f43246b1c0","desc":"pc6001mk2","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"638ea8e59a73fa4d8c6a6153b500dab9","desc":"pc6001mk2","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"8b2e909ba293170e462057ba932ff57c","desc":"pc6001mk2","mandatory":True},
        {"file":"pc6001mk2sr.zip","md5":"bef7865bdc29009350e308935a8b2b17","desc":"pc6001mk2sr","mandatory":True},
        {"file":"pc6001mk2sr.zip","md5":"7eca26109db4c664826018a0d2e1d0d7","desc":"pc6001mk2sr","mandatory":True},
        {"file":"pc6001mk2sr.zip","md5":"9d61f3cbd47c4a281c5241c4f1d80919","desc":"pc6001mk2sr","mandatory":True},
    ],
    "pc80": [
        {"file":"pc8001.zip","md5":None,"desc":"pc8001","mandatory":True},
        {"file":"pc8001.zip","md5":"f374db2869f7f44356ede51e94b4c5b6","desc":"pc8001","mandatory":True},
        {"file":"pc8001.zip","md5":"f1f6109541a89b626d4faf3f92ce5d75","desc":"pc8001","mandatory":True},
        {"file":"pc8001.zip","md5":"36a73378118eb9a610d50a8b5098c404","desc":"pc8001","mandatory":True},
        {"file":"pc8001.zip","md5":"cd428f9ee8ff9f84c60beb7a8a0ef628","desc":"pc8001","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":None,"desc":"pc8001mk2sr","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":"f0f4a4c18bc76134e1fa85ddb91d04ed","desc":"pc8001mk2sr","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":"aced63c7fece13a1b075ea2cde93929b","desc":"pc8001mk2sr","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":"a1ff399365f5e3aa0607b6f34e313a51","desc":"pc8001mk2sr","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":"018073063b1ae83a2e8a3ca127df78e5","desc":"pc8001mk2sr","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":"d81c6d5d7ad1a4bbbd6ae22a01257603","desc":"pc8001mk2sr","mandatory":True},
    ],
    "pc88": [
        {"file":"quasi88/N88.ROM","md5":"4f984e04a99d56c4cfe36115415d6eb8","desc":"N88","mandatory":True},
        {"file":"quasi88/N88SUB.ROM","md5":"793f86784e5608352a5d7f03f03e0858","desc":"N88SUB","mandatory":True},
        {"file":"quasi88/N88N.ROM","md5":"2ff07b8769367321128e03924af668a0","desc":"N88N","mandatory":True},
        {"file":"quasi88/N88KNJ1.ROM","md5":"d81c6d5d7ad1a4bbbd6ae22a01257603","desc":"N88KNJ1","mandatory":True},
        {"file":"quasi88/N88EXT0.ROM","md5":"d675a2ca186c6efcd6277b835de4c7e5","desc":"N88EXT0","mandatory":True},
        {"file":"quasi88/N88EXT1.ROM","md5":"e844534dfe5744b381444dbe61ef1b66","desc":"N88EXT1","mandatory":True},
        {"file":"quasi88/N88EXT2.ROM","md5":"6548fa45061274dee1ea8ae1e9e93910","desc":"N88EXT2","mandatory":True},
        {"file":"quasi88/N88EXT3.ROM","md5":"fc4b76a402ba501e6ba6de4b3e8b4273","desc":"N88EXT3","mandatory":True},
    ],
    "pc98": [
        {"file":"np2kai/BIOS.ROM","md5":"e246140dec5124c5e404869a84caefce","desc":"BIOS","mandatory":True},
        {"file":"np2kai/FONT.ROM","md5":"2af6179d7de4893ea0b705c00e9a98d6","desc":"FONT","mandatory":True},
        {"file":"np2kai/SOUND.ROM","md5":"caf90f22197aed6f14c471c21e64658d","desc":"SOUND","mandatory":True},
        {"file":"np2kai/ITF.ROM","md5":"e9fc3890963b12cf15d0a2eea5815b72","desc":"ITF","mandatory":True},
        {"file":"np2kai/font.bmp","md5":"7da1e5b7c482d4108d22a5b09631d967","desc":"font","mandatory":True},
    ],
    "pcengine": [
        {"file":"syscard3.pce","md5":"38179df8f4ac870017db21ebcbf53114","desc":"syscard3","mandatory":True},
    ],
    "pcfx": [
        {"file":"pcfx.rom","md5":"08e36edbea28a017f79f8d4f7ff9b6d7","desc":"pcfx","mandatory":True},
    ],
    "pcw": [
        {"file":"pcw8256.zip","md5":None,"desc":"pcw8256","mandatory":True},
        {"file":"pcw8256.zip","md5":"a846b928562ca8281bc279f41b475a06","desc":"pcw8256","mandatory":True},
        {"file":"pcw8256.zip","md5":"cefe4b0b7c701c1a80130e3390b007f5","desc":"pcw8256","mandatory":True},
        {"file":"pcw9512.zip","md5":None,"desc":"pcw9512","mandatory":True},
        {"file":"pcw9512.zip","md5":"b664af93987d575b0248832832c61505","desc":"pcw9512","mandatory":True},
    ],
    "ps2": [
        {"file":"ps2/ps2-0230a-20080220.bin","md5":"21038400dc633070a78ad53090c53017","desc":"ps2-0230a-20080220","mandatory":True},
    ],
    "ps3": [
        {"file":"PS3UPDAT.PUP","md5":"05fe32f5dc8c78acbcd84d36ee7fdc5b","desc":"PS3UPDAT","mandatory":True},
    ],
    "psvita": [
        {"file":"psvita/PSP2UPDAT.PUP","md5":"59dcf059d3328fb67be7e51f8aa33418","desc":"PSP2UPDAT","mandatory":True},
        {"file":"psvita/PSVUPDAT.PUP","md5":"f2c7b12fe85496ec88a0391b514d6e3b","desc":"PSVUPDAT","mandatory":True},
    ],
    "psx": [
        {"file":"psxonpsp660.bin","md5":"c53ca5908936d412331790f4426c6c33","desc":"psxonpsp660","mandatory":True},
        {"file":"scph101.bin","md5":"6e3735ff4c7dc899ee98981385f6f3d0","desc":"scph101","mandatory":True},
        {"file":"scph1001.bin","md5":"dc2b9bf8da62ec93e868cfd29f0d067d","desc":"scph1001","mandatory":True},
        {"file":"scph5500.bin","md5":"8dd7d5296a650fac7319bce665a6a53c","desc":"scph5500","mandatory":True},
        {"file":"scph5501.bin","md5":"490f666e1afb15b7362b406ed1cea246","desc":"scph5501","mandatory":True},
        {"file":"scph5502.bin","md5":"32736f17079d0b2b7024407c39bd3050","desc":"scph5502","mandatory":True},
        {"file":"scph7001.bin","md5":"1e68c231d0896b7eadcad1d7d8e76129","desc":"scph7001","mandatory":True},
    ],
    "pv2000": [
        {"file":"pv2000.zip","md5":None,"desc":"pv2000","mandatory":True},
    ],
    "rx78": [
        {"file":"rx78.zip","md5":None,"desc":"rx78","mandatory":True},
        {"file":"rx78.zip","md5":"f613b15c4b965013e4827d2ad79c7080","desc":"rx78","mandatory":True},
    ],
    "satellaview": [
        {"file":"BS-X.bin","md5":"96cf17bf589fcbfa6f8de2dc84f19fa2","desc":"BS-X","mandatory":True},
    ],
    "saturn": [
        {"file":"sega_101.bin","md5":"85ec9ca47d8f6807718151cbcca8b964","desc":"sega_101","mandatory":True},
        {"file":"mpr-17933.bin","md5":"3240872c70984b6cbfda1586cab68dbe","desc":"mpr-17933","mandatory":True},
        {"file":"mpr-18811-mx.ic1","md5":"255113ba943c92a54facd25a10fd780c","desc":"mpr-18811-mx","mandatory":True},
        {"file":"mpr-19367-mx.ic1","md5":"1cd19988d1d72a3e7caa0b73234c96b4","desc":"mpr-19367-mx","mandatory":True},
        {"file":"saturn_bios.bin","md5":"af5828fdff51384f99b3c4926be27762","desc":"saturn_bios","mandatory":True},
    ],
    "scummvm": [
        {"file":"scummvm/extra/MT32_PCM.ROM","md5":"89e42e386e82e0cacb4a2704a03706ca","desc":"MT32_PCM","mandatory":True},
        {"file":"scummvm/extra/MT32_CONTROL.ROM","md5":"5626206284b22c2734f3e9efefcd2675","desc":"MT32_CONTROL","mandatory":True},
    ],
    "scv": [
        {"file":"upd7801g.s01","md5":"635a978fd40db9a18ee44eff449fc126","desc":"upd7801g","mandatory":True},
    ],
    "segaai": [
        {"file":"segaai.zip","md5":None,"desc":"segaai","mandatory":True},
    ],
    "segacd": [
        {"file":"bios_CD_E.bin","md5":"e66fa1dc5820d254611fdcdba0662372","desc":"bios_CD_E","mandatory":True},
        {"file":"bios_CD_U.bin","md5":"854b9150240a198070150e4566ae1290","desc":"bios_CD_U","mandatory":True},
        {"file":"bios_CD_J.bin","md5":"278a9397d192149e84e820ac621a8edd","desc":"bios_CD_J","mandatory":True},
    ],
    "sgb": [
        {"file":"sgb_boot.bin","md5":"d574d4f9c12f305074798f54c091a8b4","desc":"sgb_boot","mandatory":True},
        {"file":"sgb2_boot.bin","md5":"e0430bca9925fb9882148fd2dc2418c1","desc":"sgb2_boot","mandatory":True},
        {"file":"SGB1.sfc","md5":"b15ddb15721c657d82c5bab6db982ee9","desc":"SGB1","mandatory":True},
        {"file":"SGB2.sfc","md5":"8ecd73eb4edf7ed7e81aef1be80031d5","desc":"SGB2","mandatory":True},
    ],
    "socrates": [
        {"file":"socrates.zip","md5":None,"desc":"socrates","mandatory":True},
        {"file":"socrates.zip","md5":"0efac0c2cc168c0d495e1c4e04ea9f5a","desc":"socrates","mandatory":True},
        {"file":"socrates.zip","md5":"99af124aa300ecd44f5dc9d5a2599778","desc":"socrates","mandatory":True},
        {"file":"socrates.zip","md5":"7046c2b27f51c9a5d33b4d6103f29acf","desc":"socrates","mandatory":True},
        {"file":"socrates.zip","md5":"6878302c362321eeee7e40d285cf7d30","desc":"socrates","mandatory":True},
        {"file":"socrates.zip","md5":"31c29c57e3d3e6788ba5817eaaa8b17a","desc":"socrates","mandatory":True},
    ],
    "sufami": [
        {"file":"STBIOS.bin","md5":"d3a44ba7d42a74d3ac58cb9c14c6a5ca","desc":"STBIOS","mandatory":True},
    ],
    "supergrafx": [
        {"file":"syscard3.pce","md5":"38179df8f4ac870017db21ebcbf53114","desc":"syscard3","mandatory":True},
    ],
    "supracan": [
        {"file":"supracan.zip","md5":"53c4343e062bb3b337370bbb58e64d16","desc":"supracan","mandatory":True},
        {"file":"umc6650.zip","md5":"da6cebe6b22a91a34a67074adbbec3a3","desc":"umc6650","mandatory":True},
    ],
    "ti99": [
        {"file":"ti99_4a.zip","md5":None,"desc":"ti99_4a","mandatory":True},
        {"file":"ti99_4a.zip","md5":"9bb51dfab49b9a7cf832cc1fb6f203e6","desc":"ti99_4a","mandatory":True},
        {"file":"ti99_4a.zip","md5":"7f1864c3dac31c86e2ae6ce43ccead07","desc":"ti99_4a","mandatory":True},
        {"file":"ti99_4a.zip","md5":"a1f77a07243a334e13509a89bff944f2","desc":"ti99_4a","mandatory":True},
        {"file":"ti99_4a.zip","md5":"6f495eef767b3f2821a2ec32d0047891","desc":"ti99_4a","mandatory":True},
        {"file":"ti99_4a.zip","md5":"0dcb961cf84c69b2171a565427c7c6c7","desc":"ti99_4a","mandatory":True},
        {"file":"ti99_speech.zip","md5":None,"desc":"ti99_speech","mandatory":True},
        {"file":"ti99_speech.zip","md5":"491c1195f6345cb6b725096b69d81ec9","desc":"ti99_speech","mandatory":True},
        {"file":"ti99_speech.zip","md5":"206daf498ac5d0141de1d47d38afd899","desc":"ti99_speech","mandatory":True},
    ],
    "triforce": [
        {"file":"saves/dolphin-emu/Triforce/segaboot.gcm","md5":"2ef01c0e93f7ee3a0a4b139aa14728b9","desc":"segaboot","mandatory":True},
    ],
    "trs80": [
        {"file":"trs80.zip","md5":None,"desc":"trs80","mandatory":True},
        {"file":"trs80.zip","md5":None,"desc":"trs80","mandatory":True},
        {"file":"trs80m3.zip","md5":None,"desc":"trs80m3","mandatory":True},
        {"file":"trs80m4.zip","md5":None,"desc":"trs80m4","mandatory":True},
        {"file":"trs80m4.zip","md5":None,"desc":"trs80m4","mandatory":True},
        {"file":"trs80m4p.zip","md5":None,"desc":"trs80m4p","mandatory":True},
    ],
    "tutor": [
        {"file":"tutor.zip","md5":None,"desc":"tutor","mandatory":True},
        {"file":"tutor.zip","md5":"196ba41dd1184fe754390534cc273116","desc":"tutor","mandatory":True},
        {"file":"tutor.zip","md5":"5770834c10946ac2c3617504ba530884","desc":"tutor","mandatory":True},
    ],
    "tvc": [
        {"file":"ep128emu/roms/tvc22_sys.rom","md5":"8c54285f541930cde766069942bad0f2","desc":"tvc22_sys","mandatory":True},
        {"file":"ep128emu/roms/tvc22_ext.rom","md5":"5ce95a26ceed5bec73995d83568da9cf","desc":"tvc22_ext","mandatory":True},
        {"file":"ep128emu/roms/tvcfileio.rom","md5":"a2cf86ba8e7fc58b242137fe59036832","desc":"tvcfileio","mandatory":True},
        {"file":"ep128emu/roms/tvc_dos12d.rom","md5":"88dc7876d584f90e4106f91444ab23b7","desc":"tvc_dos12d","mandatory":True},
        {"file":"tvc64.zip","md5":None,"desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"bed323c85b629e7ccdd318ef8a21904b","desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"be6a66ccdd3bf87992678138f3971090","desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"c451c518138f855257ac05673532e162","desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"d3ea34ee3ed3d0c7ae3001bd0d9a4ae9","desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"198182b80de1f1c54904870ae0639471","desc":"tvc64","mandatory":True},
        {"file":"tvc64.zip","md5":"5ce95a26ceed5bec73995d83568da9cf","desc":"tvc64","mandatory":True},
    ],
    "vectrex": [
        {"file":"vectrex.zip","md5":None,"desc":"vectrex","mandatory":True},
        {"file":"vectrex.zip","md5":"ab082fa8c8e632dd68589a8c7741388f","desc":"vectrex","mandatory":True},
        {"file":"vectrex.zip","md5":"a9c238473229912eb757ff3dfe6f4631","desc":"vectrex","mandatory":True},
    ],
    "vgmplay": [
        {"file":"qsound.zip","md5":None,"desc":"qsound","mandatory":True},
        {"file":"qsound.zip","md5":"108b113a596e800a02fece73f784eeb0","desc":"qsound","mandatory":True},
        {"file":"ym2413.zip","md5":None,"desc":"ym2413","mandatory":True},
        {"file":"ym2413.zip","md5":"96c11a92992bdff7f7e9d98a52621e1f","desc":"ym2413","mandatory":True},
        {"file":"ym2608.zip","md5":None,"desc":"ym2608","mandatory":True},
        {"file":"ym2608.zip","md5":"8740932cda05e518a9955f1d08d6786f","desc":"ym2608","mandatory":True},
    ],
    "videopacplus": [
        {"file":"g7400.bin","md5":"c500ff71236068e0dc0d0603d265ae76","desc":"g7400","mandatory":True},
        {"file":"jopac.bin","md5":"279008e4a0db2dc5f1c048853b033828","desc":"jopac","mandatory":True},
    ],
    "vis": [
        {"file":"vis.zip","md5":None,"desc":"vis","mandatory":True},
        {"file":"vis.zip","md5":"ebf432d3b09f694db1c62018eb2ab471","desc":"vis","mandatory":True},
        {"file":"vis.zip","md5":"758f8fec271fbf526bb22b36e88f154b","desc":"vis","mandatory":True},
    ],
    "vsmile": [
        {"file":"vsmile.zip","md5":None,"desc":"vsmile","mandatory":True},
        {"file":"vsmile.zip","md5":"851ff77a89ec3f4f2793eb4aede30e5f","desc":"vsmile","mandatory":True},
        {"file":"vsmile.zip","md5":"f41fcc19ebe1e90fa359cd0df6293fab","desc":"vsmile","mandatory":True},
        {"file":"vsmile.zip","md5":"11e59253c578c8f16ea2375ec398e4e9","desc":"vsmile","mandatory":True},
    ],
    "x1": [
        {"file":"xmil/IPLROM.X1","md5":"eeeea1cd29c6e0e8b094790ae969bfa7","desc":"IPLROM","mandatory":True},
        {"file":"xmil/iplrom.x1t","md5":"56c28adcf1f3a2f87cf3d57c378013f5","desc":"iplrom","mandatory":True},
    ],
    "x68000": [
        {"file":"keropi/iplrom.dat","md5":"7fd4caabac1d9169e289f0f7bbf71d8e","desc":"iplrom","mandatory":True},
        {"file":"keropi/cgrom.dat","md5":"cb0a5cfcf7247a7eab74bb2716260269","desc":"cgrom","mandatory":True},
    ],
    "xbox": [
        {"file":"mcpx_1.0.bin","md5":"d49c52a4102f6df7bcf8d0617ac475ed","desc":"mcpx_1.0","mandatory":True},
        {"file":"Complex_4627.bin","md5":"39cee882148a87f93cb440b99dde3ceb","desc":"Complex_4627","mandatory":True},
    ],
    "xegs": [
        {"file":"xegs.zip","md5":None,"desc":"xegs","mandatory":True},
        {"file":"xegs.zip","md5":"42cbd989802c17d0ac3731d33270d835","desc":"xegs","mandatory":True},
    ],
    "zc210": [
        {"file":"zc210/zcdata.dat","md5":"033d7392985841027909c4c32b9f2076","desc":"zcdata","mandatory":True},
        {"file":"zc210/sf2/default.sf2","md5":"39e5bc84ce9aac3a2d297d8aeb2a0d05","desc":"default","mandatory":True},
        {"file":"zc210/sf2/custom0.sf2","md5":"e0ba7a8634b12cfee4b6760a6f89051a","desc":"custom0","mandatory":True},
        {"file":"zc210/sf2/custom1.sf2","md5":"c1dc781c34cff8f9a023c0192754dc6c","desc":"custom1","mandatory":True},
        {"file":"zc210/sf2/custom2.sf2","md5":"144fcdbb6a30f1f916f6963006c2da97","desc":"custom2","mandatory":True},
        {"file":"zc210/sf2/custom3.sf2","md5":"134d217fb99c3be1e89cfaf8f28280d8","desc":"custom3","mandatory":True},
        {"file":"zc210/sf2/custom4.sf2","md5":"b37366199c6df9ee5316f031755aa821","desc":"custom4","mandatory":True},
        {"file":"zc210/sf2/custom5.sf2","md5":"64068b84eb88dc85b75148bbe9b393fb","desc":"custom5","mandatory":True},
        {"file":"zc210/sf2/custom6.sf2","md5":"1241986de5b1d00b02d34f1e6651a1d1","desc":"custom6","mandatory":True},
        {"file":"zc210/sf2/custom7.sf2","md5":"386db0d538f372a9f1af622d1e934abf","desc":"custom7","mandatory":True},
        {"file":"zc210/sf2/custom8.sf2","md5":"6f68e4baf89c8ee4623c19617319184b","desc":"custom8","mandatory":True},
        {"file":"zc210/sf2/custom9.sf2","md5":"2010e5b85f9e1d60685ccb3d84a17115","desc":"custom9","mandatory":True},
        {"file":"zcsf.sf2","md5":"e0ba7a8634b12cfee4b6760a6f89051a","desc":"zcsf","mandatory":True},
    ],
}


NOBIOS_PLATFORMS = {
    "3ds":[],
    "amiga":[],
    "amstradcpc":[],
    "arcade":[],
    "atari2600":[],
    "atari7800":[],
    "c64":[],
    "famicom":[],
    "fba":[],
    "gamegear":[],
    "gb":[],
    "gbc":[],
    "gc":[],
    "genesis":[],
    "jaguar":[],
    "mame":[],
    "mastersystem":[],
    "megacd":[],
    "megadrive":[],
    "n64":[],
    "nes":[],
    "ngp":[],
    "pc":[],
    "pce":[],
    "psp":[],
    "sega32x":[],
    "sg1000":[],
    "snes":[],
    "tg16":[],
    "virtualboy":[],
    "wii":[],
    "wiiu":[],
    "wonderswan":[],
    "wonderswancolor":[],
    "zxspectrum":[],
}

# Combined case-insensitive lookup
_BIOS_LOOKUP = {}
for k, v in BIOS_DB.items():
    _BIOS_LOOKUP[k.strip().lower()] = v
for k, v in NOBIOS_PLATFORMS.items():
    _BIOS_LOOKUP[k.strip().lower()] = v

def _bios_key(slug):
    return slug.strip().lower() if slug else ""

def _get_bios_entries(slug):
    return _BIOS_LOOKUP.get(_bios_key(slug), [])

# ─── Cache ───────────────────────────────────────────────────────
import threading

_rom_cache        = {}   # {roms_base: (timestamp, data)}
_rom_cache_lock   = threading.Lock()
ROM_CACHE_TTL     = 60   # segundos

# Set of skipped missing BIOS entries (skip_key = "system/file"). Persistido en disco.
_missing_bios_skipped = set()

def _bios_skip_file():
    """Ruta del fichero de skips. Derivada de SETTINGS_FILE (monkeypatcheable en tests)."""
    return SETTINGS_FILE.parent / "batocera_manager_bios_skipped.json"

def load_bios_skipped():
    """Carga los skips persistidos. Tolera ausencia o fichero corrupto."""
    global _missing_bios_skipped
    f = _bios_skip_file()
    try:
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                _missing_bios_skipped = {str(x) for x in data}
    except Exception:
        pass
    return _missing_bios_skipped

def _save_bios_skipped():
    f = _bios_skip_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(sorted(_missing_bios_skipped), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(f)
    except Exception:
        pass

def set_bios_skipped(key):
    """Marca un skip y lo persiste."""
    if not key:
        return
    _missing_bios_skipped.add(key)
    _save_bios_skipped()

def unset_bios_skipped(key):
    """Quita un skip y persiste el cambio."""
    _missing_bios_skipped.discard(key)
    _save_bios_skipped()

load_bios_skipped()


def get_rom_systems_cached(settings):
    key   = settings["roms_base"]
    now   = time.time()
    with _rom_cache_lock:
        if key in _rom_cache:
            ts, data = _rom_cache[key]
            if now - ts < ROM_CACHE_TTL:
                return data
    data = get_rom_systems(settings, fast=True)
    with _rom_cache_lock:
        _rom_cache[key] = (now, data)
    return data

def invalidate_rom_cache():
    with _rom_cache_lock:
        _rom_cache.clear()


def count_rom_systems(settings):
    """Nº de sistemas de `roms_base` con al menos un juego.

    Recorre solo el primer nivel de cada sistema y corta al primer juego: no
    usa el escaneo completo (`get_rom_systems`), que suma el tamaño de todos
    los ficheros y tarda segundos. Mismas reglas que aquel:

    - un fichero con extensión de ROM (`ROM_EXTENSIONS`) cuenta;
    - una subcarpeta cuenta (ports/motores guardan el juego dentro, p. ej.
      `iortcw/main`, `pygame/pygun`), salvo `media/` y los filtrados
      (`images/`, `videos/`, `manuals/`);
    - `gamelist.xml`, los ficheros ocultos y `FILTER_FILES` no cuentan.
    """
    base = Path(settings["roms_base"])
    if not base.is_dir():
        return 0
    try:
        system_dirs = [d for d in base.iterdir() if d.is_dir()]
    except Exception:
        return 0
    total = 0
    for sys_dir in system_dirs:
        try:
            for item in sys_dir.iterdir():
                name = item.name
                if name.startswith(".") or name == "gamelist.xml":
                    continue
                if name in FILTER_FILES:
                    continue
                if item.is_dir():
                    if name == "media" or name.lower() in FILTER_DIRS:
                        continue
                elif item.suffix.lower() not in ROM_EXTENSIONS:
                    continue
                total += 1
                break
        except Exception:
            continue
    return total

# ─── Helpers ─────────────────────────────────────────────────────
def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings_to_file(data):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def human_size(n):
    for u in ["B","KB","MB","GB","TB"]:
        if abs(n) < 1024: return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"

def md5_file(path):
    h = hashlib.md5()
    try:
        with open(path,"rb") as f:
            while chunk := f.read(65536): h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def crc32_file(path):
    """CRC-32 de un archivo (formato SS: 8 dígitos hexadecimales en mayúsculas)."""
    h = 0
    try:
        with open(path,"rb") as f:
            while chunk := f.read(65536):
                h = zlib.crc32(chunk, h)
        return format(h & 0xffffffff, "08X")
    except Exception:
        return None

# Mapeo tipo de imagen (UI / ScreenScraper) -> (carpeta, sufijo) según Batocera
# (equivale a getSaveAsPath() de batocera-emulationstation)
SS_MEDIA_LAYOUT = {
    "image":       ("images", "-image"),
    "images":      ("images", "-image"),
    "ss":          ("images", "-image"),
    "screenshot":  ("images", "-image"),
    "mixrbv1":     ("images", "-image"),
    "mixrbv2":     ("images", "-image"),
    "box-2D":      ("images", "-image"),
    "box-3D":      ("images", "-box"),
    "box-2D-back": ("images", "-boxback"),
    "wheel":       ("images", "-wheel"),
    "marquee":     ("images", "-marquee"),
    "fanart":      ("images", "-fanart"),
    "titleshot":   ("images", "-titleshot"),
    "maps":        ("images", "-map"),
    "map":         ("images", "-map"),
    "cartridge":   ("images", "-cartridge"),
    "video":       ("videos", "-video"),
    "manuel":      ("manuals", "-manual"),
    "manual":      ("manuals", "-manual"),
}

def batocera_media_path(system_dir, rom_stem, media_type, ext=".png"):
    """Devuelve (ruta_destino, ruta_relativa_gamelist) estilo Batocera.
    Ej: images/Game-name-image.png  →  ./images/Game-name-image.png
    """
    folder, suffix = SS_MEDIA_LAYOUT.get(media_type, ("images","-image"))
    if ext and not ext.startswith("."):
        ext = "." + ext
    rel  = f"{folder}/{rom_stem}{suffix}{ext}"
    return Path(system_dir) / rel, "./" + rel

def is_gamelist_image_type(media_type):
    """True si el tipo produce el arte principal (`images/<stem>-image`).

    EmulationStation muestra `<image>` del gamelist; solo los tipos cuyo sufijo
    es `-image` (box-2D, ss, mixrbv…) deben rellenarlo, nunca wheel/fanart/video.
    """
    return SS_MEDIA_LAYOUT.get(media_type, ("images", "-image"))[1] == "-image"

def get_system_extensions(system, settings, builtin_path=None):
    """Extensiones permitidas para un sistema según es_systems.cfg.

    Semántica de EmulationStation/Batocera: si un `es_systems_*.cfg` de usuario
    define el sistema, **reemplaza** por completo la definición integrada (no se
    unen). Solo si no hay definición de usuario se usa la integrada.
    """
    def _exts_from(path):
        out = set()
        try:
            for s in ET.parse(path).findall(".//system"):
                if s.findtext("name", "") == system:
                    ext = (s.findtext("extension", "") or "").strip()
                    out |= {e.strip().lower() for e in ext.split() if e.strip()}
        except Exception:
            pass
        return out

    custom = set()
    cfg_dir = Path(settings.get("es_cfg_dir", "/userdata/system/configs/emulationstation"))
    if cfg_dir.is_dir():
        for f in sorted(cfg_dir.glob("es_systems_*.cfg")):
            custom |= _exts_from(f)
    if custom:
        return custom
    builtin = Path(builtin_path or "/usr/share/emulationstation/es_systems.cfg")
    if builtin.is_file():
        return _exts_from(builtin)
    return set()

def prettify_xml(elem):
    rough    = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough)
    lines    = reparsed.toprettyxml(indent="    ").split("\n")
    filtered = [l for l in lines if l.strip()]
    if filtered and filtered[0].startswith("<?xml"):
        filtered = filtered[1:]
    return "\n".join(filtered)

def build_xml(d, settings):
    root   = ET.Element("systemList")
    sys_el = ET.SubElement(root, "system")
    def add(tag, val):
        if val and str(val).strip():
            ET.SubElement(sys_el, tag).text = str(val).strip()
    add("fullname",     d.get("fullname"))
    add("name",         d.get("name"))
    add("manufacturer", d.get("manufacturer"))
    add("release",      d.get("release"))
    add("hardware",     d.get("hardware"))
    add("path",         d.get("rompath"))
    add("extension",    d.get("extensions"))
    py = settings.get("python_path", DEFAULT_SETTINGS["python_path"])
    ET.SubElement(sys_el,"command").text = (
        f"python3 {py} %CONTROLLERSCONFIG% -system %SYSTEM% -rom %ROM%")
    add("platform",    d.get("platform"))
    add("theme",       d.get("theme"))
    add("description", d.get("description"))
    emul = (d.get("emulator") or "").strip()
    core = (d.get("core") or "").strip()
    if emul and core:
        emuls    = ET.SubElement(sys_el,"emulators")
        emul_el  = ET.SubElement(emuls,"emulator", name=emul)
        cores_el = ET.SubElement(emul_el,"cores")
        c = ET.SubElement(cores_el,"core")
        c.text = core; c.set("default","true")
        for ec in (d.get("extra_cores") or "").split(","):
            if ec.strip(): ET.SubElement(cores_el,"core").text = ec.strip()
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + prettify_xml(root)

def detect_active_theme(settings):
    for p in [Path(settings["es_cfg_dir"])/"es_settings.cfg",
              Path("/usr/share/emulationstation/es_settings.cfg")]:
        if p.exists():
            try:
                for elem in ET.parse(p).iter("string"):
                    if elem.get("name") == "ThemeSet":
                        return elem.get("value","es-theme-carbon")
            except Exception: pass
    return "es-theme-carbon"

def find_system_logo(settings, system, theme=None):
    """Ruta del logo de un sistema en el tema activo (usuario o sistema), o None.

    Busca en temas de usuario (/userdata/themes) y de sistema
    (/usr/share/emulationstation/themes) y confina el resultado a esas raíces
    para evitar path traversal vía `system`.
    """
    if theme is None:
        theme = detect_active_theme(settings)
    for base in (settings.get("themes_user"), settings.get("themes_sys")):
        if not base:
            continue
        base_r = Path(base).resolve()
        for cand in (base_r / theme / system / "art" / "logo.png",
                     base_r / theme / system / "logo.png"):
            try:
                cand_r = cand.resolve()
                cand_r.relative_to(base_r)   # rechaza `..` fuera de la raíz
                if cand_r.exists():
                    return cand_r
            except Exception:
                continue
    return None

def list_themes(settings):
    themes = []
    for base in [settings["themes_user"], settings["themes_sys"]]:
        p = Path(base)
        if p.exists():
            for d in sorted(p.iterdir()):
                if d.is_dir() and d.name not in themes:
                    themes.append(d.name)
    return themes or ["es-theme-carbon","es-theme-minimal"]

def list_custom_systems(settings):
    systems = []
    d = Path(settings["es_cfg_dir"])
    if not d.exists(): return systems
    for f in sorted(d.glob("es_systems_*.cfg")):
        try:
            for s in ET.parse(f).findall(".//system"):
                systems.append({
                    "name":     s.findtext("name",""),
                    "fullname": s.findtext("fullname",""),
                    "path":     s.findtext("path",""),
                    "theme":    s.findtext("theme",""),
                    "hardware": s.findtext("hardware",""),
                    "file":     str(f), "filename": f.name,
                })
        except Exception: pass
    return systems

def delete_custom_system(name, settings):
    """Elimina SOLO el `<system>` `name` de sus `es_systems_*.cfg`.

    Un .cfg puede contener varios sistemas: antes se borraba el fichero entero
    y se perdían los demás. Si tras la operación no queda ningún sistema, el
    fichero sí se elimina.

    Devuelve (ok, info) donde info puede contener "error", "file_deleted" y
    "removed_systems".
    """
    systems = list_custom_systems(settings)
    t = next((x for x in systems if x["name"] == name), None)
    if not t:
        return False, {"error": "No encontrado"}
    cfg_path = Path(t["file"])
    try:
        tree = ET.parse(cfg_path)
        root = tree.getroot()
        removed = 0
        for parent in root.iter():
            for child in list(parent):
                if child.tag == "system" and child.findtext("name", "") == name:
                    parent.remove(child)
                    removed += 1
        if not removed:
            return False, {"error": "No encontrado"}
        if root.findall(".//system"):
            cfg_path.write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n' + prettify_xml(root),
                encoding="utf-8",
            )
            mark_es_restart_pending()
            invalidate_system_meta()
            return True, {"file_deleted": False, "removed_systems": removed}
        cfg_path.unlink()
        mark_es_restart_pending()
        invalidate_system_meta()
        return True, {"file_deleted": True, "removed_systems": removed}
    except Exception as e:
        return False, {"error": str(e)}

def get_custom_system_detail(name, settings):
    d = Path(settings["es_cfg_dir"])
    if not d.exists(): return None
    for f in d.glob("es_systems_*.cfg"):
        try:
            for s in ET.parse(f).findall(".//system"):
                if s.findtext("name","") != name: continue
                detail = {
                    "name":        s.findtext("name",""),
                    "fullname":    s.findtext("fullname",""),
                    "manufacturer":s.findtext("manufacturer",""),
                    "release":     s.findtext("release",""),
                    "hardware":    s.findtext("hardware",""),
                    "path":        s.findtext("path",""),
                    "extension":   s.findtext("extension",""),
                    "platform":    s.findtext("platform",""),
                    "theme":       s.findtext("theme",""),
                    "description": s.findtext("description",""),
                    "file":        str(f), "filename": f.name,
                }
                emul = s.find(".//emulator")
                if emul is not None:
                    detail["emulator"] = emul.get("name","")
                    cores = emul.findall(".//core")
                    core_list = []
                    for c in cores:
                        txt = (c.text or "").strip()
                        if txt: core_list.append(txt)
                    if core_list:
                        detail["core"] = core_list[0]
                        detail["extra_cores"] = ",".join(core_list[1:]) if len(core_list)>1 else ""
                return detail
        except Exception: pass
    return None


# ─── Seguridad: validación de rutas y valores ──────────────────────
_CONF_VALUE_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


def is_safe_component(name):
    """True si `name` es un único componente de ruta seguro.

    Rechaza vacío, ".", "..", separadores ("/", chr(92)) y NUL, de modo que al
    unirlo a un directorio no pueda escapar de él.
    """
    if not name or name in (".", ".."):
        return False
    return not ("/" in name or chr(92) in name or chr(0) in name)


def safe_path_under(base, *parts):
    """Une `parts` a `base` garantizando que el resultado queda dentro de `base`.

    Lanza ValueError si algún componente intenta salir (path traversal).
    """
    base_r = Path(base).resolve()
    target_r = base_r.joinpath(*parts).resolve()
    try:
        target_r.relative_to(base_r)
    except ValueError:
        raise ValueError("ruta fuera del directorio permitido")
    return target_r


def system_dir(settings, system):
    """Devuelve <roms_base>/<system> validando que `system` sea un componente seguro."""
    if not is_safe_component(system):
        raise ValueError("nombre de sistema inválido")
    return safe_path_under(settings["roms_base"], system)


def confine_to_base(base, candidate):
    """Resuelve `candidate` (absoluto, o relativo a `base`) y exige que quede dentro de `base`.

    Lanza ValueError si la ruta resultante sale de `base` (path traversal).
    """
    base_r = Path(base).resolve()
    cand = Path(candidate)
    target = cand if cand.is_absolute() else base_r / cand
    target_r = target.resolve()
    try:
        target_r.relative_to(base_r)
    except ValueError:
        raise ValueError("ruta fuera de la base permitida")
    return target_r


def sanitize_conf_value(value):
    """Valida un valor de batocera.conf (emulator/core).

    Rechaza saltos de línea, espacios y metacaracteres para impedir la inyección
    de directivas en el fichero de configuración.
    """
    value = (value or "").strip()
    if not value or not _CONF_VALUE_RE.match(value):
        raise ValueError("valor de configuración inválido")
    return value


def sanitize_comment_text(value):
    """Colapsa espacios y saltos de línea para insertar texto seguro en un comentario."""
    return " ".join((value or "").split())


def xml_looks_safe(text):
    """True si `text` (str o bytes) no contiene DOCTYPE ni ENTITY (mitiga XXE / billion laughs)."""
    if isinstance(text, (bytes, bytearray)):
        low = bytes(text).lower()
        return b"<!doctype" not in low and b"<!entity" not in low
    low = (text or "").lower()
    return "<!doctype" not in low and "<!entity" not in low


def parse_content_length(value):
    """Convierte el header Content-Length a entero no negativo (0 si ausente o inválido)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, n)


# Límite del cuerpo HTTP aceptado (subidas de ROM/BIOS): 512 MiB
MAX_BODY_BYTES = 512 * 1024 * 1024


def list_rom_folder(settings, system, subpath=""):
    """Lista el contenido de una carpeta dentro de un sistema, soportando subcarpetas anidadas.
    subpath es relativo a la raíz del sistema, ej: 'CPS1' o 'CPS1/bootlegs'.
    """
    try:
        roms_base = system_dir(settings, system)
        target    = safe_path_under(roms_base, subpath) if subpath else roms_base
    except ValueError:
        return None  # sistema o subruta inválidos (path traversal)

    if not target.exists() or not target.is_dir():
        return None

    items, media_count, total_size = [], 0, 0
    try:
        entries = sorted(target.iterdir())
    except PermissionError:
        entries = []

    for item in entries:
        if item.name == "media" and item.is_dir():
            try: media_count = sum(1 for _ in item.iterdir() if _.is_file())
            except Exception: media_count = 0
            continue
        if item.name.startswith(".") or item.name == "gamelist.xml":
            continue
        if item.name in FILTER_FILES:
            continue
        if item.is_dir() and item.name.lower() in FILTER_DIRS:
            continue
        if item.is_file():
            sz = item.stat().st_size
            total_size += sz
            items.append({
                "name": item.stem, "filename": item.name,
                "ext": item.suffix.lower(), "size": sz,
                "size_human": human_size(sz),
                "is_rom": item.suffix.lower() in ROM_EXTENSIONS,
                "is_dir": False,
                "desc":"","rating":"","genre":"","publisher":"","year":"",
                "has_image": False, "has_video": False,
            })
        elif item.is_dir():
            # Para carpetas, contar ROMs dentro (sin recursión profunda, solo 1er nivel)
            try:
                child_count = sum(1 for f in item.iterdir()
                                  if f.is_file() and not f.name.startswith(".")
                                  and f.name != "gamelist.xml")
                child_has_subdirs = any(f.is_dir() and f.name != "media"
                                        and f.name.lower() not in FILTER_DIRS
                                        for f in item.iterdir())
            except Exception:
                child_count, child_has_subdirs = 0, False
            sz = 0
            try:
                sz = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
            except Exception:
                pass
            total_size += sz
            items.append({
                "name": item.name, "filename": item.name,
                "ext": "dir", "size": sz, "size_human": human_size(sz),
                "is_rom": False, "is_dir": True,
                "child_count": child_count,
                "has_subdirs": child_has_subdirs,
                "desc":"","rating":"","genre":"","publisher":"","year":"",
                "has_image": False, "has_video": False,
            })

    # Gamelist: buscar en la carpeta actual (algunos sistemas tienen gamelist por subcarpeta)
    gl = target / "gamelist.xml"
    if gl.exists():
        try:
            tree = ET.parse(gl)
            gdata = {}
            for game in tree.findall(".//game"):
                fn = game.findtext("path","").lstrip("./")
                gdata[fn] = {
                    "desc":      game.findtext("desc",""),
                    "rating":    game.findtext("rating",""),
                    "genre":     game.findtext("genre",""),
                    "publisher": game.findtext("publisher",""),
                    "year":      (game.findtext("releasedate","") or "")[:4],
                    "has_image": bool(game.findtext("image","")),
                    "has_video": bool(game.findtext("video","")),
                }
            for it in items:
                if it["is_dir"]: continue
                meta = gdata.get(it["filename"], gdata.get(it["name"], {}))
                if meta: it.update(meta)
        except Exception:
            pass

    # Breadcrumb: partes del path para navegación
    breadcrumb = [system] + ([p for p in subpath.split("/") if p] if subpath else [])

    return {
        "system": system,
        "subpath": subpath,
        "breadcrumb": breadcrumb,
        "items": items,
        "item_count": len(items),
        "media_count": media_count,
        "total_size": total_size,
        "size_human": human_size(total_size),
        "has_gamelist": gl.exists(),
        "is_empty": len(items) == 0,
    }


# ─── Analítica de juego (dashboard) ──────────────────────────────────
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]

# Preferencia de arte, de mayor a menor (arte de usuario primero). Cada par es
# (carpeta, sufijo): con sufijo "" busca "<stem>.<ext>"; si no "<stem><sufijo>.<ext>".
USER_ART_PREFERENCE = [
    ("media/images", ""),
    ("images",       "-image"),
    ("mixrbv2",      "-mixrbv2"),
    ("mixrbv1",      "-mixrbv1"),
    ("fanart",       "-fanart"),
    ("screenshots",  "-titleshot"),
    ("named_boxarts", "-box"),
    ("boxart",       "-box"),
    ("images",       "-box"),
    ("wheels",       "-wheel"),
    ("images",       "-wheel"),
    ("marquees",     "-marquee"),
    ("images",       "-marquee"),
]


def find_user_art(roms_base, system, rom_relpath):
    """Lista de imágenes candidatas para un ROM, arte de usuario primero.

    `rom_relpath` admite subcarpeta (p. ej. "CPS1/foo.zip"). Devuelve list[Path]
    de archivos existentes ordenados por USER_ART_PREFERENCE; si no hay arte de
    usuario, incluye el `<image>` del gamelist.xml. Nunca lanza.
    """
    try:
        sys_dir = Path(roms_base) / system
        stem = Path(rom_relpath).stem
    except Exception:
        return []
    if not sys_dir.is_dir():
        return []

    bases = []
    sub = Path(rom_relpath).parent
    if str(sub) not in (".", ""):
        bases.append(sys_dir / sub)
    bases.append(sys_dir)

    out, seen = [], set()
    for base in bases:
        for mdir, suf in USER_ART_PREFERENCE:
            for ext in IMAGE_EXTS:
                p = base / mdir / (stem + suf + ext)
                if p.exists() and p not in seen:
                    seen.add(p)
                    out.append(p)

    if not out:
        gl = sys_dir / "gamelist.xml"
        if gl.exists():
            try:
                tree = ET.parse(gl)
                for game in tree.findall(".//game"):
                    gpath = (game.findtext("path", "") or "").lstrip("./")
                    if gpath == rom_relpath or Path(gpath).stem == stem:
                        img = (game.findtext("image", "") or "").lstrip("./")
                        if img:
                            p = sys_dir / img
                            if p.exists():
                                out.append(p)
                        break
            except Exception:
                pass
    return out


def _parse_es_date(value):
    """Convierte 'YYYYMMDDTHHMMSS' de EmulationStation a 'YYYY-MM-DD', o ''."""
    value = (value or "").strip()
    if len(value) >= 8 and value[:8].isdigit():
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
    return ""


def _int_text(value):
    """Entero de un campo de texto; 0 si viene vacío o no es numérico."""
    try:
        return int((value or "").strip() or 0)
    except (ValueError, AttributeError):
        return 0


def collect_play_stats(roms_base, systems=None):
    """Agrega estadísticas de juego desde los `gamelist.xml` de `roms_base`.

    `systems`: lista de slugs a incluir; None = todos los subdirectorios.
    Devuelve ok/updated/has_playtime/totals/top_games/by_system/activity.
    Nunca lanza: entradas ilegibles se saltan.
    """
    result = {
        "ok": True,
        "updated": time.time(),
        "has_playtime": False,
        "totals": {"games": 0, "playcount": 0, "playtime_s": 0, "systems": 0},
        "top_games": [],
        "by_system": [],
        "activity": [],
    }
    base = Path(roms_base)
    if not base.is_dir():
        return result
    if systems is None:
        try:
            systems = [d.name for d in sorted(base.iterdir()) if d.is_dir()]
        except Exception:
            systems = []

    activity: dict[str, int] = {}
    top, per_sys = [], []
    total_games = total_playcount = total_playtime = 0

    for sys_name in systems:
        gl = base / sys_name / "gamelist.xml"
        if not gl.exists():
            continue
        try:
            tree = ET.parse(gl)
        except Exception:
            continue
        sys_playcount = sys_playtime = sys_games = 0
        for game in tree.findall(".//game"):
            pc = _int_text(game.findtext("playcount", "0"))
            # ES escribe el tiempo en <gametime>; <playtime> lo usan otras herramientas.
            pt = _int_text(game.findtext("gametime", "")) or \
                 _int_text(game.findtext("playtime", "0"))
            if pc <= 0 and pt <= 0:
                continue
            gpath = (game.findtext("path", "") or "").lstrip("./")
            name = game.findtext("name", "") or Path(gpath).stem
            lastplayed = _parse_es_date(game.findtext("lastplayed", ""))
            sys_games += 1
            sys_playcount += pc
            sys_playtime += pt
            if lastplayed:
                activity[lastplayed] = activity.get(lastplayed, 0) + 1
            art = find_user_art(roms_base, sys_name, gpath)
            top.append({
                "system": sys_name, "name": name, "path": gpath,
                "playcount": pc, "lastplayed": lastplayed, "playtime_s": pt,
                "image": str(art[0]) if art else "",
            })
        if sys_games:
            per_sys.append({"system": sys_name, "playcount": sys_playcount,
                            "playtime_s": sys_playtime, "games": sys_games})
        total_games += sys_games
        total_playcount += sys_playcount
        total_playtime += sys_playtime

    top.sort(key=lambda g: (g["playcount"], g["playtime_s"]), reverse=True)
    per_sys.sort(key=lambda x: (x["playcount"], x["playtime_s"]), reverse=True)
    result["totals"] = {"games": total_games, "playcount": total_playcount,
                        "playtime_s": total_playtime, "systems": len(per_sys)}
    result["has_playtime"] = total_playtime > 0
    result["top_games"] = top[:10]
    result["by_system"] = per_sys
    result["activity"] = [{"date": d, "count": c} for d, c in sorted(activity.items())]
    return result


# El catálogo usa claves cortas para algunos sistemas; el slug de Batocera no
# siempre coincide (gamecube vs gc). Alias explícitos: no se inventan nombres,
# se reutiliza el que ya está en `batocera_systems.json`.
SYSTEM_SLUG_ALIASES = {
    "gamecube": "gc",
    "dreamcast": "dc",
    "pcengine": "pce",
    "atari800": "atari-800",
}


def friendly_system_name(slug):
    """Nombre legible de un sistema desde `batocera_systems.json` (o el slug)."""
    info = _BATOCERA_SYSTEMS.get(slug) or {}
    if not info.get("n"):
        info = _BATOCERA_SYSTEMS.get(SYSTEM_SLUG_ALIASES.get(slug, "")) or {}
    return info.get("n") or slug


def read_game_meta(roms_base, system, filename, subpath=""):
    """Metadatos de un ROM leídos de `roms/<system>/gamelist.xml`.

    Devuelve solo lo que existe: `{}` si el ROM no está en la gamelist o su
    entrada no tiene texto. Nunca lanza.

    Claves: name, desc, genre, publisher (cae a developer), players, year,
    playcount, gametime_s y lastplayed (YYYY-MM-DD).
    """
    gl = Path(roms_base) / system / "gamelist.xml"
    if not gl.exists():
        return {}
    try:
        root = ET.parse(gl).getroot()
    except Exception:
        return {}
    rel = f"{subpath}/{filename}" if subpath else filename
    game = None
    for g in root.findall("game"):
        gpath = (g.findtext("path", "") or "").lstrip("./")
        if gpath == rel or (not subpath and Path(gpath).name == filename):
            game = g
            break
    if game is None:
        return {}

    def txt(tag):
        return (game.findtext(tag, "") or "").strip()

    meta = {}
    for tag in ("name", "desc", "genre", "players"):
        val = txt(tag)
        if val:
            meta[tag] = val
    publisher = txt("publisher") or txt("developer")
    if publisher:
        meta["publisher"] = publisher
    year = _parse_es_date(txt("releasedate"))[:4]
    if year:
        meta["year"] = year
    playcount = _int_text(txt("playcount"))
    if playcount:
        meta["playcount"] = playcount
    # ES escribe el tiempo en <gametime>; <playtime> es de otras herramientas.
    gametime = _int_text(txt("gametime")) or _int_text(txt("playtime"))
    if gametime:
        meta["gametime_s"] = gametime
    lastplayed = _parse_es_date(txt("lastplayed"))
    if lastplayed:
        meta["lastplayed"] = lastplayed
    return meta


def pick_random_game(roms_base, systems=None):
    """Elige un juego al azar, prefiriendo los que tienen arte disponible.

    Enriquece el resultado con el nombre amigable de la plataforma y con los
    metadatos que ya existan en la gamelist del sistema elegido.

    Si ningún juego tiene arte devuelve igualmente uno (con `has_art=False`):
    la tarjeta pinta entonces el wallpaper generado, así que no hace falta
    dejar el panel vacío.

    Devuelve {"system","system_name","name","filename","subpath","has_art",...}
    o None.
    """
    base = Path(roms_base)
    if not base.is_dir():
        return None
    if systems is None:
        try:
            systems = [d.name for d in sorted(base.iterdir()) if d.is_dir()]
        except Exception:
            return None

    with_art, any_rom = [], []
    for sys_name in systems:
        sys_dir = base / sys_name
        if not sys_dir.is_dir():
            continue
        try:
            entries = sorted(sys_dir.iterdir())
        except Exception:
            continue
        for item in entries:
            if not item.is_file():
                continue
            if item.name.startswith(".") or item.name in FILTER_FILES:
                continue
            if item.suffix.lower() not in ROM_EXTENSIONS:
                continue
            entry = {"system": sys_name, "name": item.stem,
                     "filename": item.name, "subpath": "",
                     "has_art": False}
            any_rom.append(entry)
            if find_user_art(roms_base, sys_name, item.name):
                with_art.append({**entry, "has_art": True})
    pool = with_art or any_rom
    if not pool:
        return None
    game = random.choice(pool)
    game["system_name"] = friendly_system_name(game["system"])
    game.update(read_game_meta(roms_base, game["system"], game["filename"],
                               game["subpath"]))
    return game


_HARDWARE_TYPE_NAMES = {
    "arcade": "Arcade",
    "console": "Consolas",
    "portable": "Portátiles",
    "computer": "Ordenadores",
    "engine": "Otros",
    "fantasy": "Otros",
    "other": "Otros",
}


def system_type_name(hardware):
    """Convierte el campo `hardware` de Batocera en una categoría amigable."""
    return _HARDWARE_TYPE_NAMES.get((hardware or "").strip().lower(), "Otros")


_SYSTEM_META_CACHE = {"ts": 0, "data": {}}


def load_system_meta(settings):
    """Lee manufacturer/hardware/platform/release/fullname de los es_systems.cfg.

    Combina los cfg de usuario (custom) con el oficial de Batocera
    (/usr/share/emulationstation/es_systems.cfg). Los custom tienen prioridad.
    Devuelve {slug: {fullname, manufacturer, hardware, platform, release}}.
    """
    now = time.time()
    if now - _SYSTEM_META_CACHE["ts"] < 300 and _SYSTEM_META_CACHE["data"]:
        return _SYSTEM_META_CACHE["data"]

    meta = {}
    cfg_dir = Path(settings.get("es_cfg_dir", "/userdata/system/configs/emulationstation"))
    files = []
    builtin = Path("/usr/share/emulationstation/es_systems.cfg")
    if builtin.is_file():
        files.append(builtin)  # primero: base
    if cfg_dir.is_dir():
        files += sorted(cfg_dir.glob("es_systems_*.cfg"))  # después: override

    for f in files:
        try:
            for s in ET.parse(f).findall(".//system"):
                name = (s.findtext("name") or "").strip()
                if not name:
                    continue
                meta[name] = {
                    "fullname": (s.findtext("fullname") or "").strip() or name,
                    "manufacturer": (s.findtext("manufacturer") or "").strip(),
                    "hardware": (s.findtext("hardware") or "").strip(),
                    "platform": (s.findtext("platform") or "").strip(),
                    "release": (s.findtext("release") or "").strip()[:4],
                }
        except Exception:
            continue

    _SYSTEM_META_CACHE["ts"] = now
    _SYSTEM_META_CACHE["data"] = meta
    return meta


def invalidate_system_meta():
    _SYSTEM_META_CACHE["ts"] = 0
    _SYSTEM_META_CACHE["data"] = {}



# Clasificacion heuristica por nombre de carpeta (fallback cuando no hay
# metadata en es_systems.cfg). Devuelve (tipo, fabricante).
_MFR_RULES = [
    ("nintendo", "Nintendo"), ("gameboy", "Nintendo"), ("game boy", "Nintendo"),
    ("gamecube", "Nintendo"), ("virtualboy", "Nintendo"), ("virtual boy", "Nintendo"),
    ("wonderswan", "Nintendo"), ("wswan", "Nintendo"), ("gameandwatch", "Nintendo"),
    ("game and watch", "Nintendo"), ("n64", "Nintendo"), ("nes", "Nintendo"),
    ("snes", "Nintendo"), ("gb", "Nintendo"), ("gba", "Nintendo"), ("gbc", "Nintendo"),
    ("nds", "Nintendo"), ("3ds", "Nintendo"), ("switch", "Nintendo"), ("wii", "Nintendo"),
    ("fds", "Nintendo"), ("satellaview", "Nintendo"), ("sufami", "Nintendo"),
    ("sgb", "Nintendo"), ("gamecom", "Nintendo"), ("pokemini", "Nintendo"),
    ("gamepock", "Nintendo"), ("game master", "Nintendo"),
    ("sega", "Sega"), ("genesis", "Sega"), ("megadrive", "Sega"),
    ("mastersystem", "Sega"), ("gamegear", "Sega"), ("saturn", "Sega"),
    ("dreamcast", "Sega"), ("sega32x", "Sega"), ("segacd", "Sega"), ("sg1000", "Sega"),
    ("pico", "Sega"), ("naomi", "Sega"), ("atomiswave", "Sega"), ("model2", "Sega"),
    ("model3", "Sega"), ("hikaru", "Sega"), ("chihiro", "Sega"), ("systemsp", "Sega"),
    ("system16", "Sega"), ("megacd", "Sega"), ("segaai", "Sega"),
    ("sony", "Sony"), ("playstation", "Sony"), ("psx", "Sony"), ("ps1", "Sony"),
    ("ps2", "Sony"), ("ps3", "Sony"), ("ps4", "Sony"), ("psp", "Sony"),
    ("psvita", "Sony"), ("ps5", "Sony"), ("vita", "Sony"),
    ("atari", "Atari"),
    ("nec", "NEC"), ("pcengine", "NEC"), ("pce", "NEC"), ("turbografx", "NEC"),
    ("supergrafx", "NEC"), ("pcfx", "NEC"), ("tg16", "NEC"),
    ("snk", "SNK"), ("neogeo", "SNK"), ("ngp", "SNK"), ("ngpc", "SNK"),
    ("microsoft", "Microsoft"), ("xbox", "Microsoft"), ("xbox360", "Microsoft"),
    ("commodore", "Commodore"), ("c64", "Commodore"), ("amiga", "Commodore"),
    ("vic20", "Commodore"), ("c128", "Commodore"), ("c16", "Commodore"),
    ("plus4", "Commodore"), ("pet", "Commodore"), ("amstrad", "Amstrad"),
    ("cpc", "Amstrad"), ("gx4000", "Amstrad"), ("apple", "Apple"),
    ("macintosh", "Apple"), ("apple2", "Apple"), ("appleiigs", "Apple"),
    ("sharp", "Sharp"), ("x68000", "Sharp"), ("x1", "Sharp"),
    ("sinclair", "Sinclair"), ("spectrum", "Sinclair"), ("zx", "Sinclair"),
    ("zx81", "Sinclair"), ("philips", "Philips"), ("cdi", "Philips"),
    ("mattel", "Mattel"), ("intellivision", "Mattel"), ("coleco", "Coleco"),
    ("colecovision", "Coleco"), ("bandai", "Bandai"), ("wonderswan", "Bandai"),
    ("wswan", "Bandai"), ("casio", "Casio"), ("pv1000", "Casio"),
    ("pv2000", "Casio"), ("epoch", "Epoch"), ("fairchild", "Fairchild"),
    ("channelf", "Fairchild"), ("magnavox", "Magnavox"), ("odyssey", "Magnavox"),
    ("rca", "RCA"), ("studio2", "RCA"), ("texas", "Texas Instruments"),
    ("ti99", "Texas Instruments"), ("ti-99", "Texas Instruments"),
    ("tomy", "Tomy"), ("tutor", "Tomy"), ("vectrex", "GCE"), ("gce", "GCE"),
    ("3do", "Panasonic"), ("jaguar", "Atari"), ("lynx", "Atari"),
    ("dreamcast", "Sega"), ("saturn", "Sega"), ("virtualboy", "Nintendo"),
    ("ngp", "SNK"), ("ngpc", "SNK"), ("gamegear", "Sega"),
    ("colecovision", "Coleco"), ("intellivision", "Mattel"),
    ("odyssey", "Magnavox"), ("channelf", "Fairchild"),
    ("entex", "Entex"), ("advision", "Entex"), ("adventurevision", "Entex"),
    ("acorn", "Acorn"), ("bbc", "Acorn"), ("archimedes", "Acorn"),
    ("coco", "Tandy"), ("enterprise", "Enterprise"), ("samcoupe", "MGT"),
    ("oricatmos", "Tangerine"), ("oric", "Tangerine"), ("gp32", "GamePark"),
    ("arduboy", "Arduboy"), ("gamecom", "Tiger"), ("pokemini", "Nintendo"),
    ("astrocade", "Bally"), ("astrocde", "Bally"), ("vectrex", "GCE"),
    ("odyssey2", "Magnavox"), ("channelf", "Fairchild"), ("ti99", "Texas Instruments"),
    ("microsoft", "Microsoft"), ("dos", "Microsoft"), ("windows", "Microsoft"),
]
_MFR_RULES.sort(key=lambda x: -len(x[0]))


def _classify_system(slug):
    """Clasificacion heuristica (tipo, fabricante) a partir del nombre de carpeta."""
    s = (slug or "").lower().replace("-", "").replace("_", "").replace(" ", "")
    # fabricante: primero coincidencia exacta/prefijo, luego subcadena solo
    # para palabras largas (evita falsos positivos como "n64" en "dragon64")
    mfr = ""
    norm = s
    # 1) exacta
    for kw, name in _MFR_RULES:
        k = kw.replace("-", "").replace("_", "").replace(" ", "")
        if norm == k:
            mfr = name
            break
    # 2) prefijo
    if not mfr:
        for kw, name in sorted(_MFR_RULES, key=lambda x: -len(x[0])):
            k = kw.replace("-", "").replace("_", "").replace(" ", "")
            if norm.startswith(k):
                mfr = name
                break
    # 3) subcadena (solo palabras de >= 4 letras)
    if not mfr:
        for kw, name in sorted(_MFR_RULES, key=lambda x: -len(x[0])):
            k = kw.replace("-", "").replace("_", "").replace(" ", "")
            if len(k) >= 4 and k in norm:
                mfr = name
                break
    # tipo
    arcade_kw = ["arcade", "mame", "fbneo", "neogeo", "cps", "cave", "gaelco",
                 "atomiswave", "naomi", "model2", "model3", "hikaru", "chihiro",
                 "namco", "systemsp", "system16", "taito", "igs", "pgm", "daphne",
                 "singe", "demul", "flycast", "konami", "cannonball", "zinc",
                 "lindbergh", "triforce", "stv", "irem", "toaplan", "technos",
                 "midway", "williams", "bally", "capcom"]
    portable_kw = ["gb", "gba", "gbc", "nds", "3ds", "switch", "gamegear", "lynx",
                   "gameboy", "ngp", "wonderswan", "wswan", "virtualboy", "pokemon",
                   "gamecom", "gp32", "ngage", "psp", "vita", "psvita", "gamepock",
                   "supervision", "gameandwatch", "lcd", "pokemini", "arduboy",
                   "lowresnx", "tic80", "tic80", "pico8", "pico", "uzebox", "wasm4",
                   "gameboy", "gameboyadvance", "gameboycolor", "nintendods",
                   "nintendo3ds", "nintendoswitch", "gamegear", "atarilynx",
                   "neogeopocket", "wonderswan", "virtualboy", "gamecom", "gp32",
                   "ngage", "playstationportable", "playstationvita", "gamepocketcomputer",
                   "supervision", "gameandwatch", "pokemini", "arduboy", "lowresnx",
                   "tic80", "pico8", "uzebox", "wasm4", "gamate", "game master",
                   "gameandwatch", "lcdgames", "gamecom"]
    computer_kw = ["pc", "dos", "windows", "mac", "amiga", "atarist", "c64", "zx",
                   "spectrum", "msx", "apple", "pc88", "pc98", "x68000", "sharp",
                   "thomson", "oric", "bbc", "amstrad", "cpc", "ti99", "coco", "dragon",
                   "enterprise", "samcoupe", "zx81", "z80", "tandy", "trs80", "mc10",
                   "c128", "c16", "plus4", "pet", "vic20", "vic", "commodore",
                   "apple2", "appleiigs", "macintosh", "msx", "pcw", "x1", "thomson",
                   "oric", "bbc", "archimedes", "acorn", "samcoupe", "enterprise",
                   "dragon", "tandy", "trs80", "z80", "spectrum", "zx", "cpc",
                   "amstrad", "ti99", "coco", "c20", "c128", "vic20", "pet", "c64",
                   "c16", "plus4", "commodore", "apple2", "appleiigs", "macintosh",
                   "apple", "msx", "dos", "windows", "linux", "unix", "mac", "amiga",
                   "atari st", "atarist", "msx1", "msx2", "msxturbor", "pc88", "pc98",
                   "pc60", "pc80", "x68000", "sharp", "x1", "thomson", "oric",
                   "bbc", "archimedes", "acorn", "samcoupe", "enterprise", "dragon",
                   "tandy", "trs80", "z80", "spectrum", "zx", "cpc", "amstrad", "ti99",
                   "ti99", "coco", "c20", "c128", "vic20", "pet", "c64", "c16",
                   "plus4", "commodore", "apple2", "appleiigs", "macintosh", "apple",
                   "msx", "dos", "windows", "linux", "unix", "mac", "amiga", "atari st", "atarist", "pc", "ti994a", "ti-99"]
    # pcengine/pce/pcfx are consoles, not computers
    if any(k in s for k in ("pcengine", "pce", "pcfx", "pc-98", "pc98", "pc-88",
                            "pc88", "pc-60", "pc60", "pc-80", "pc80", "pcw")):
        if any(k in s for k in ("pcengine", "pce", "pcfx")):
            typ = "Consolas"
        else:
            typ = "Ordenadores"
    else:
        for kw in sorted(arcade_kw, key=len, reverse=True):
            if kw in s:
                typ = "Arcade"
                break
        else:
            for kw in sorted(portable_kw, key=len, reverse=True):
                if kw in s:
                    typ = "Portátiles"
                    break
            else:
                for kw in sorted(computer_kw, key=len, reverse=True):
                    if kw in s:
                        typ = "Ordenadores"
                        break
                else:
                    typ = "Consolas"
    return typ, mfr


def collect_missing_bios(user_systems, bios_dir):
    """Recopila las BIOS faltantes de los sistemas del usuario.

    Cada elemento lleva `type`/`manufacturer` (de la metadata del sistema o,
    si falta, deducidos del slug) para alimentar los filtros de la interfaz.
    """
    items = []
    for usys in user_systems:
        name = usys.get("name")
        if not name:
            continue
        try:
            info = _check_bios_grouped(name, bios_dir)
        except Exception as e:
            # Un sistema problemático (permisos, fichero que desaparece…) no
            # debe tumbar la lista entera de BIOS faltantes.
            print(f"  aviso: no se pudo revisar las BIOS de '{name}': {e}")
            continue
        if info is None or not info["files"]:
            continue
        _t, _m = _classify_system(name)
        for b in info["files"]:
            missing = not b["exists"] or b["md5_ok"] is False
            if not missing:
                continue
            skip_key = f"{name}/{b['file']}"
            if skip_key in _missing_bios_skipped:
                continue
            items.append({
                "system": name,
                "type": usys.get("type") or _t,
                "manufacturer": usys.get("manufacturer") or _m,
                "file": b["file"],
                "desc": b["desc"],
                "mandatory": b["mandatory"],
                "md5": b.get("expected_md5"),
                "exists": b["exists"],
                "md5_ok": b["md5_ok"],
                "skip_key": skip_key,
            })
    return items


def get_rom_systems(settings, fast=False):
    roms_base = Path(settings["roms_base"])
    result = []
    if not roms_base.exists(): return result
    _meta = load_system_meta(settings)
    try: dirs = sorted(roms_base.iterdir())
    except Exception: return result
    active_theme = detect_active_theme(settings)
    for sys_dir in dirs:
        if not sys_dir.is_dir(): continue
        name = sys_dir.name
        roms, media_count, total_size = [], 0, 0
        try:
            for item in sorted(sys_dir.iterdir()):
                if item.name == "media" and item.is_dir():
                    try: media_count = sum(1 for _ in item.iterdir() if _.is_file())
                    except Exception: media_count = 0
                    continue
                if item.name.startswith(".") or item.name == "gamelist.xml": continue
                if item.name in FILTER_FILES: continue
                if item.is_dir() and item.name.lower() in FILTER_DIRS: continue
                if item.is_file():
                    sz = item.stat().st_size; total_size += sz
                    roms.append({"name":item.stem,"filename":item.name,
                        "ext":item.suffix.lower(),"size":sz,
                        "size_human":human_size(sz),
                        "is_rom":item.suffix.lower() in ROM_EXTENSIONS,
                        "desc":"","rating":"","genre":"","publisher":"","year":"",
                        "has_image":False,"has_video":False})
                elif item.is_dir():
                    sz = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    total_size += sz
                    roms.append({"name":item.name,"filename":item.name,"ext":"dir",
                        "size":sz,"size_human":human_size(sz),"is_rom":True,
                        "desc":"","rating":"","genre":"","publisher":"","year":"",
                        "has_image":False,"has_video":False})
        except PermissionError: pass
        # Gamelist (solo si no es modo rapido)
        gl = sys_dir / "gamelist.xml"
        if gl.exists() and not fast:
            try:
                tree = ET.parse(gl)
                gdata = {}
                for game in tree.findall(".//game"):
                    fn = game.findtext("path","").lstrip("./")
                    gdata[fn] = {
                        "desc":      game.findtext("desc",""),
                        "rating":    game.findtext("rating",""),
                        "genre":     game.findtext("genre",""),
                        "publisher": game.findtext("publisher",""),
                        "year":      (game.findtext("releasedate","") or "")[:4],
                        "has_image": bool(game.findtext("image","")),
                        "has_video": bool(game.findtext("video","")),
                    }
                for rom in roms:
                    meta = gdata.get(rom["filename"], gdata.get(rom["name"], {}))
                    if meta: rom.update(meta)
            except Exception: pass
        has_logo = find_system_logo(settings, name, active_theme) is not None
        meta = _meta.get(name, {})
        hw = (meta.get("hardware") or "").strip()
        mfr = (meta.get("manufacturer") or "").strip()
        if not hw or not mfr:
            h2, m2 = _classify_system(name)
            if not hw:
                hw = h2
            if not mfr:
                mfr = m2
        result.append({
            "name":name,"path":str(sys_dir),
            "rom_count":len(roms),"media_count":media_count,
            "total_size":total_size,"size_human":human_size(total_size),
            "has_gamelist":gl.exists(),"roms":roms,
            "is_empty":len(roms)==0,
            "has_bios":bool(_get_bios_entries(name)),
            "bios_count":len(_get_bios_entries(name)),
            "has_logo": has_logo,
            "type": system_type_name(hw) if hw.lower() in ("arcade","console","portable","computer","engine","fantasy","other","") else hw,
            "manufacturer": mfr,
            "platform": meta.get("platform", "") or "",
            "release": meta.get("release", "") or "",
            "fullname": meta.get("fullname", "") or name,
        })
    return result


def rom_system_summary(x):
    """Resumen de un sistema para el listado del panel ROMs & BIOS.

    Incluye `type`/`manufacturer` (y platform/release/fullname) porque son los
    campos que alimentan los chips de filtrado de la interfaz.
    """
    return {
        "name": x["name"],
        "rom_count": x["rom_count"],
        "media_count": x["media_count"],
        "size_human": x["size_human"],
        "is_empty": x["is_empty"],
        "has_gamelist": x["has_gamelist"],
        "has_bios": x["has_bios"],
        "bios_count": x["bios_count"],
        "has_logo": x.get("has_logo", False),
        "type": x.get("type") or "Otros",
        "manufacturer": x.get("manufacturer") or "",
        "platform": x.get("platform") or "",
        "release": x.get("release") or "",
        "fullname": x.get("fullname") or x["name"],
    }


def _check_bios_grouped(slug, bios_dir):
    """Helper: returns grouped BIOS info for a single slug, or None if unknown."""
    raw = _get_bios_entries(slug)
    if not raw:
        # slug known but no BIOS entries → system without BIOS
        if _bios_key(slug) in _BIOS_LOOKUP:
            return {"known":True,"files":[]}
        return None
    by_file = {}
    for b in raw:
        fn = b["file"]
        if fn not in by_file:
            by_file[fn] = {"desc":b["desc"],"mandatory":b["mandatory"],"md5s":[]}
        md5 = b.get("md5")
        if md5:
            by_file[fn]["md5s"].append(md5)
    results = []
    for fn, info in by_file.items():
        fpath = Path(bios_dir) / fn
        exists = fpath.exists()
        md5_ok = None
        actual = None
        if exists:
            if info["md5s"]:
                actual = md5_file(fpath)
                md5_ok = (actual in info["md5s"])
            else:
                md5_ok = True
        results.append({
            "file":fn,"desc":info["desc"],"mandatory":info["mandatory"],
            "exists":exists,"md5_ok":md5_ok,
            "expected_md5":info["md5s"][0] if info["md5s"] else None,
            "actual_md5":actual,
            "size":human_size(fpath.stat().st_size) if exists else None,
            "valid_md5s":info["md5s"],
        })
    return {"known":True,"files":results}

def check_bios(system_name, bios_dir):
    info = _check_bios_grouped(system_name, bios_dir)
    if info is None:
        return {"known": False, "files": []}
    # remove valid_md5s from per-system response to keep it clean
    for f in info["files"]:
        f.pop("valid_md5s", None)
    return info


# ─── Asistente de BIOS faltantes (legal-primero) ───────────────────────
MAX_BIOS_DOWNLOAD = 64 * 1024 * 1024  # 64 MiB


def _bios_urlopen(url, timeout=30):
    """Indirección sobre urllib para poder simular la red en los tests."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "BatoceraManager/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_BIOS_DOWNLOAD + 1)


def github_bios_search_url(filename):
    """URL de búsqueda de código en GitHub para localizar un archivo BIOS.

    La app solo enlaza a la búsqueda; no descarga ni aloja nada por su cuenta.
    """
    q = urllib.parse.quote(str(filename))
    return f"https://github.com/search?q={q}&type=code"


def download_bios_from_url(bios_dir, filename, url, expected_md5s=None, timeout=30):
    """Descarga un BIOS desde una URL que EL USUARIO proporciona.

    Solo `http`/`https`; valida la ruta con `safe_path_under` (respeta
    subcarpetas) y limita el tamaño a MAX_BIOS_DOWNLOAD. Nunca lanza.
    Devuelve {ok, error?, dest, size, md5, md5_valid}.
    """
    filename = (filename or "").strip()
    url = (url or "").strip()
    if not filename or not url:
        return {"ok": False, "error": "Faltan 'file' o 'url'"}
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        return {"ok": False, "error": "Solo se permiten URLs http/https"}
    try:
        dest = safe_path_under(Path(bios_dir), filename)
    except ValueError:
        return {"ok": False, "error": "Ruta de BIOS inválida"}
    try:
        data = _bios_urlopen(url, timeout)
    except Exception as e:
        return {"ok": False, "error": f"No se pudo descargar: {e}"}
    if len(data) > MAX_BIOS_DOWNLOAD:
        return {"ok": False, "error": "Archivo demasiado grande"}
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    except Exception as e:
        return {"ok": False, "error": f"No se pudo guardar: {e}"}
    md5_val = hashlib.md5(data).hexdigest()
    return {
        "ok": True,
        "dest": str(dest),
        "size": human_size(len(data)),
        "md5": md5_val,
        "md5_valid": (md5_val in expected_md5s) if expected_md5s else None,
    }

def parse_multipart(environ, data):
    import email.parser
    import email.policy
    ct = environ.get("CONTENT_TYPE","")
    if "boundary=" not in ct: return {}, {}
    raw = b"Content-Type: " + ct.encode() + b"\r\n\r\n" + data
    msg = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(raw)
    fields, files = {}, {}
    for part in msg.get_payload():
        disp = part.get("Content-Disposition","")
        nm   = re.search(r'name="([^"]+)"', disp)
        fn   = re.search(r'filename="([^"]+)"', disp)
        if not nm: continue
        key     = nm.group(1)
        payload = part.get_payload(decode=True)
        if fn:   files[key]  = {"filename":fn.group(1),"data":payload}
        else:    fields[key] = payload.decode("utf-8",errors="replace") if payload else ""
    return fields, files

def make_placeholder_png(text):
    size = (400,100)
    img  = Image.new("RGBA", size, (20,20,35,255))
    draw = ImageDraw.Draw(img)
    font = None
    for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(fp):
            try: font = ImageFont.truetype(fp,36); break
            except Exception: pass
    if not font: font = ImageFont.load_default()
    bbox = draw.textbbox((0,0),text,font=font)
    tw,th = bbox[2]-bbox[0],bbox[3]-bbox[1]
    x,y = (size[0]-tw)//2,(size[1]-th)//2
    draw.text((x+2,y+2),text,font=font,fill=(0,80,180,160))
    draw.text((x,y),text,font=font,fill=(80,180,255,255))
    draw.rectangle([0,0,size[0]-1,size[1]-1],outline=(0,100,220,200),width=3)
    buf = io.BytesIO(); img.save(buf,"PNG"); return buf.getvalue()


# ═══════════════════════════════════════════════════════════════
#  MÓDULO: DASHBOARD — System Monitor
# ═══════════════════════════════════════════════════════════════
import subprocess


def _read_file(path, default=""):
    try: return Path(path).read_text().strip()
    except Exception: return default

def _run(cmd, default=""):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
        return r.stdout.strip()
    except Exception: return default

def get_batocera_version():
    for p in ["/usr/share/batocera/batocera.version",
              "/etc/batocera-release",
              "/usr/share/batocera/system.version"]:
        v = _read_file(p)
        if v: return v
    v = _run("batocera-info 2>/dev/null | head -1")
    return v or "desconocida"

def get_cpu_info():
    model = ""
    cores = 0
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if "model name" in line and not model:
                model = line.split(":")[1].strip()
            if line.startswith("processor"):
                cores += 1
    except Exception: pass
    return model or "Desconocido", cores or 1

def get_cpu_usage():
    """Calcula % CPU comparando dos lecturas de /proc/stat con 0.2s de diferencia."""
    import time
    def read_stat():
        line = Path("/proc/stat").read_text().splitlines()[0]
        vals = list(map(int, line.split()[1:]))
        idle = vals[3]
        total = sum(vals)
        return idle, total
    try:
        i1, t1 = read_stat()
        time.sleep(0.2)
        i2, t2 = read_stat()
        diff_total = t2 - t1
        diff_idle  = i2 - i1
        if diff_total == 0: return 0.0
        return round((1 - diff_idle / diff_total) * 100, 1)
    except Exception: return 0.0

def get_cpu_temp():
    """Lee temperatura CPU desde múltiples fuentes."""
    # Fuente 1: thermal zones
    for tz in sorted(Path("/sys/class/thermal").glob("thermal_zone*")):
        try:
            ttype = (tz / "type").read_text().strip()
            temp  = int((tz / "temp").read_text().strip()) / 1000
            if temp > 0 and temp < 120:
                return temp, ttype
        except Exception: pass
    # Fuente 2: hwmon
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        for tf in hwmon.glob("temp*_input"):
            try:
                temp = int(tf.read_text().strip()) / 1000
                if 0 < temp < 120:
                    label_f = tf.parent / tf.name.replace("_input","_label")
                    label = label_f.read_text().strip() if label_f.exists() else "CPU"
                    return temp, label
            except Exception: pass
    # Fuente 3: k10temp / coretemp via sensors
    out = _run("cat /sys/class/hwmon/hwmon*/temp1_input 2>/dev/null | head -1")
    if out:
        try: return int(out)/1000, "CPU"
        except Exception: pass
    return None, "N/A"

def get_fans(hwmon_root=None):
    """Lee ventiladores desde sysfs hwmon (fan*_input).

    Retorna una lista de ventiladores con RPM, label, flags de fallo/alarma
    y estado derivado: ok / stopped / fault.
    """
    fans = []
    root = Path(hwmon_root) if hwmon_root else Path("/sys/class/hwmon")
    for hwmon in sorted(root.glob("hwmon*")):
        hw_name = _read_file(hwmon / "name")
        for fanf in sorted(hwmon.glob("fan*_input")):
            base = fanf.name.replace("_input", "")   # p.ej. fan1
            m = re.search(r"fan(\d+)", base)
            idx = m.group(1) if m else base.replace("fan", "")
            try:
                rpm = int(fanf.read_text().strip())
            except Exception:
                rpm = 0
            label = _read_file(hwmon / (base + "_label")) or (hw_name and f"{hw_name} #{idx}") or f"Ventilador {idx}"
            fault = _read_file(hwmon / (base + "_fault"), "0")
            alarm = _read_file(hwmon / (base + "_alarm"), "0")
            mn    = _read_file(hwmon / (base + "_min"), None)
            try:
                min_rpm = int(mn) if mn else None
            except (TypeError, ValueError):
                min_rpm = None

            if fault and fault != "0":
                status = "fault"
            elif rpm == 0 or (min_rpm and rpm < min_rpm):
                status = "stopped"
            else:
                status = "ok"

            fans.append({
                "name":   hw_name,
                "index":  idx,
                "label":  label,
                "rpm":    rpm,
                "min":    min_rpm,
                "fault":  bool(fault and fault != "0"),
                "alarm":  bool(alarm and alarm != "0"),
                "status": status,
            })
    return fans

def _gpu_from_drm(card):
    """Extrae info de una GPU desde una entrada /sys/class/drm/cardN."""
    dev = card / "device"
    vendor_id = _read_file(dev / "vendor")
    device_id = _read_file(dev / "device")
    vendor_name = {"0x10de":"NVIDIA","0x1002":"AMD","0x8086":"Intel"}.get(vendor_id, "GPU")
    is_nvidia = vendor_id == "0x10de"

    # Nombre
    name = f"{vendor_name} [{device_id}]"
    uevent = _read_file(dev / "uevent")
    for line in uevent.splitlines():
        if "DRIVER=" in line:
            name = f"{vendor_name} ({line.split('=')[1]})"

    # Temperatura desde hwmon bajo la tarjeta
    temp = None
    for hwmon in sorted((dev / "hwmon").glob("hwmon*") if (dev/"hwmon").exists() else []):
        for tf in sorted(hwmon.glob("temp*_input")):
            try:
                t = int(tf.read_text().strip()) / 1000
                if 0 < t < 120:
                    temp = round(t, 1)
                    break
            except Exception: pass
        if temp: break

    # VRAM desde sysfs (nouveau/amdgpu)
    mem_used  = _read_file(dev / "mem_info_vram_used",  None)
    mem_total = _read_file(dev / "mem_info_vram_total", None)
    if mem_used and mem_total:
        try:
            mem_used  = f"{int(mem_used)//1048576} MB"
            mem_total = f"{int(mem_total)//1048576} MB"
        except Exception:
            mem_used = mem_total = None

    # Uso GPU
    util = None
    busy = _read_file(dev / "gpu_busy_percent", None)
    if busy:
        try: util = int(busy)
        except Exception: pass

    return {"name": name, "temp": temp, "util": util,
            "mem_used": mem_used, "mem_total": mem_total,
            "vendor": vendor_name, "is_nvidia": is_nvidia}


def _gpu_from_nvidia_smi():
    """Intenta leer datos de todas las GPUs NVIDIA via nvidia-smi."""
    try:
        out = _run(
            "nvidia-smi --query-gpu=index,name,temperature.gpu,"
            "utilization.gpu,memory.used,memory.total,power.draw "
            "--format=csv,noheader,nounits 2>/dev/null"
        )
        if not out:
            return None
        gpus = []
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 7:
                continue
            _idx, gname, gtemp, gutil, gmem_used, gmem_total, gpower = parts[:7]
            try:
                temp_val = round(float(gtemp), 1) if gtemp else None
            except Exception:
                temp_val = None
            try:
                util_val = int(gutil) if gutil else None
            except Exception:
                util_val = None
            try:
                mem_used_str = f"{int(gmem_used)} MB" if gmem_used else None
            except Exception:
                mem_used_str = None
            try:
                mem_total_str = f"{int(gmem_total)} MB" if gmem_total else None
            except Exception:
                mem_total_str = None
            try:
                power_str = f"{round(float(gpower))} W" if gpower else None
            except Exception:
                power_str = None
            gpus.append({
                "name": gname,
                "temp": temp_val,
                "util": util_val,
                "mem_used": mem_used_str,
                "mem_total": mem_total_str,
                "power": power_str,
                "vendor": "NVIDIA",
                "is_nvidia": True,
            })
        return gpus if gpus else None
    except Exception:
        return None


def get_gpu_info(drm_root=None):
    """Detecta todas las GPUs del sistema (iGPU + dGPU NVIDIA/AMD).
    Para NVIDIA intenta nvidia-smi primero, fallback a sysfs.
    """
    result = {"available": False, "name": "N/A", "temp": None,
               "util": None, "mem_used": None, "mem_total": None,
               "power": None, "gpus": []}

    gpus = []
    seen_names = set()

    # 1. nvidia-smi (datos más completos para NVIDIA)
    nv_gpus = _gpu_from_nvidia_smi()
    has_nvidia = bool(nv_gpus)
    if nv_gpus:
        for g in nv_gpus:
            gpus.append(g)
            seen_names.add(g["name"])

    # 2. DRM sysfs (para AMD/Intel y NVIDIA si no se detectó via smi)
    drm = Path(drm_root) if drm_root else Path("/sys/class/drm")
    if drm.exists():
        for card in sorted(drm.glob("card[0-9]")):
            try:
                g = _gpu_from_drm(card)
                # Evitar duplicados si nvidia-smi ya la encontró
                if g.get("is_nvidia") and has_nvidia:
                    continue
                if g["name"] in seen_names:
                    continue
                # Completar power desde hwmon general (solo si no lo trajo smi)
                if g.get("power") is None:
                    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
                        pf = hwmon / "power1_average"
                        if pf.exists():
                            try:
                                g["power"] = f"{int(pf.read_text().strip())//1000000} W"
                            except Exception:
                                pass
                            break
                seen_names.add(g["name"])
                gpus.append(g)
            except Exception:
                pass

    if not gpus:
        return result

    result["available"] = True
    result["gpus"] = gpus
    # Backward compat: primer GPU como principal
    primary = gpus[0]
    result["name"] = primary["name"]
    result["temp"] = primary["temp"]
    result["util"] = primary["util"]
    result["mem_used"] = primary["mem_used"]
    result["mem_total"] = primary["mem_total"]
    result["power"] = primary.get("power")
    return result

def get_memory(meminfo_path=None):
    info = {}
    src = Path(meminfo_path) if meminfo_path else Path("/proc/meminfo")
    try:
        lines = src.read_text().splitlines()
    except Exception:
        return {}
    for line in lines:
        try:
            k, v = line.split(":")[0].strip(), line.split(":")[1].strip().split()[0]
            info[k] = int(v)
        except Exception:
            continue
    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", 0)
    used  = total - avail
    swap_total = info.get("SwapTotal", 0)
    swap_free  = info.get("SwapFree", 0)
    def kb2mb(kb): return round(kb / 1024, 1)
    return {
        "total_mb":      kb2mb(total),
        "used_mb":       kb2mb(used),
        "free_mb":       kb2mb(avail),
        "used_pct":      round(used / total * 100, 1) if total else 0,
        "swap_total_mb": kb2mb(swap_total),
        "swap_used_mb":  kb2mb(swap_total - swap_free),
    }

_disk_cache = {"data": [], "day": None, "updated": None}

def _compute_disk():
    partitions = []
    skip_fs = ("tmpfs", "none", "overlay", "devtmpfs", "squashfs")
    skip_mounts = ("/boot", "/RESTORE", "/media/RESTORE")
    try:
        out = _run("df -k 2>/dev/null")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 6: continue
            fs, size, used, avail, pct, mount = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            # Solo particiones reales: excluye pseudo-fs (tmpfs/overlay/loop)
            if fs in skip_fs: continue
            if fs.startswith("/dev/loop"): continue
            # Excluye particiones del sistema que no aportan (boot, restore)
            if mount in skip_mounts: continue
            if any(mount.startswith(m + "/") for m in skip_mounts): continue
            # Cualquier montaje cuya carpeta final sea RESTORE (p. ej. /media/RESTORE)
            if mount.rsplit("/", 1)[-1].upper() == "RESTORE": continue
            try:
                partitions.append({
                    "fs":     fs,
                    "mount":  mount,
                    "size_gb":  round(int(size)/1024/1024, 1),
                    "used_gb":  round(int(used)/1024/1024, 1),
                    "free_gb":  round(int(avail)/1024/1024, 1),
                    "pct":    int(pct.replace("%","")),
                })
            except Exception: pass
    except Exception: pass
    return partitions

def get_disk():
    """Devuelve el estado del disco actualizado una sola vez al día (a las 18:00).

    Antes de las 18:00 sirve los datos de ayer a las 18:00; después de las 18:00
    recalcula y cachea para el resto del día.
    """
    now_ts = time.time()
    lt     = time.localtime(now_ts)
    today_1800 = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 18, 0, 0, 0, 0, -1))
    target = today_1800 if now_ts >= today_1800 else today_1800 - 86400
    day    = time.strftime("%Y-%m-%d", time.localtime(target))
    if _disk_cache["day"] != day:
        _disk_cache["data"]    = _compute_disk()
        _disk_cache["day"]     = day
        _disk_cache["updated"] = time.strftime("%Y-%m-%d %H:%M", time.localtime())
    return _disk_cache["data"]

_skip_diskio = ("loop", "ram", "fd", "sr", "zram", "dm-", "md")

def _read_diskstats():
    """Lee contadores de I/O de /proc/diskstats por dispositivo."""
    stats = {}
    try:
        for line in Path("/proc/diskstats").read_text().splitlines():
            f = line.split()
            if len(f) < 14: continue
            name = f[2]
            if name.startswith(_skip_diskio): continue
            stats[name] = {
                "reads":  int(f[3]), "rsect": int(f[5]), "rms": int(f[6]),
                "writes": int(f[7]), "wsect": int(f[9]), "wms": int(f[10]),
                "busy":   int(f[12]),
            }
    except Exception: pass
    return stats

_diskio_cache = {"prev": {}, "ts": None}

def get_disk_io():
    """Tasas de I/O de disco en vivo (KB/s lect/esc y % busy) por dispositivo."""
    now = time.time()
    cur = _read_diskstats()
    out = []
    prev, prev_ts = _diskio_cache["prev"], _diskio_cache["ts"]
    if prev and prev_ts:
        dt = max(0.001, now - prev_ts)
        for name, c in cur.items():
            p = prev.get(name)
            if not p: continue
            r_kbs = max(0, (c["rsect"] - p["rsect"]) * 512 / 1024 / dt)
            w_kbs = max(0, (c["wsect"] - p["wsect"]) * 512 / 1024 / dt)
            busy  = min(100, max(0, (c["busy"] - p["busy"]) / (dt * 1000) * 100))
            out.append({"device": name, "r_kbs": round(r_kbs, 1),
                        "w_kbs": round(w_kbs, 1), "busy": round(busy, 1)})
        out.sort(key=lambda x: x["r_kbs"] + x["w_kbs"], reverse=True)
    _diskio_cache["prev"] = cur
    _diskio_cache["ts"]   = now
    return out

def get_battery(power_supply_root=None):
    """Estado de batería y alimentación (laptop) desde /sys/class/power_supply."""
    out = {"available": False, "ac": False}
    root = Path(power_supply_root) if power_supply_root else Path("/sys/class/power_supply")
    try:
        for d in root.iterdir():
            if _read_file(d / "type") == "Mains":
                out["ac"] = _read_file(d / "online") == "1"
        for d in root.iterdir():
            if _read_file(d / "type") != "Battery":
                continue
            def num(f, d=d):
                try: return int(_read_file(d / f))
                except Exception: return None
            cap  = num("capacity") or 0
            vnow = num("voltage_now") or 0
            v    = vnow / 1e6  # V
            enow, efull, edes = num("energy_now"), num("energy_full"), num("energy_full_design")
            cnow, cfull, cdes = num("charge_now"), num("charge_full"), num("charge_full_design")
            pnow, cur = num("power_now"), num("current_now")
            # Energía en Wh: energy_* µWh; si falta, charge_* µAh * voltaje(V) / 1e6
            enow_wh  = enow / 1e6 if enow is not None else (cnow * v / 1e6 if cnow is not None else None)
            efull_wh = efull / 1e6 if efull is not None else (cfull * v / 1e6 if cfull is not None else None)
            edes_wh  = edes / 1e6 if edes is not None else (cdes * v / 1e6 if cdes is not None else None)
            # Potencia en W: power_now µW; si falta, current_now µA * voltaje
            pw = pnow / 1e6 if pnow is not None else (cur * v / 1e6 if cur is not None else None)
            out.update({
                "available": True,
                "name": d.name,
                "capacity": cap,
                "status": _read_file(d / "status"),
                "energy_now_wh": round(enow_wh, 1) if enow_wh is not None else None,
                "energy_full_wh": round(efull_wh, 1) if efull_wh is not None else None,
                "design_wh": round(edes_wh, 1) if edes_wh is not None else None,
                "power_w": round(pw, 1) if pw is not None else None,
                "voltage_v": round(v, 1) if v else None,
                "cycle": num("cycle_count"),
            })
            p, e = out.get("power_w"), out.get("energy_now_wh")
            if p and e:
                st = out.get("status")
                if st == "Discharging":
                    h = e / p
                    out["time_left"] = f"{int(h)}h {int((h % 1) * 60)}m"
                elif st == "Charging" and out.get("energy_full_wh"):
                    h = max(0, out["energy_full_wh"] - e) / p
                    out["time_full"] = f"{int(h)}h {int((h % 1) * 60)}m"
    except Exception:
        pass
    return out

# ── Noticias de emulación (RSS, portal en español) ──
import urllib.request as _nreq

NEWS_FEEDS = [
    # Actualizaciones oficiales de Batocera (releases de GitHub, Atom)
    {"name": "Batocera", "url": "https://github.com/batocera-linux/batocera.linux/releases.atom", "filter": False},
]
# Filtro de relevancia: emulación / retro / videojuegos en español
NEWS_KEYWORDS = (
    "emula", "emulación", "emulador", "rom", "roms", "retro", "mame", "arcade",
    "homebrew", "nintendo", "playstation", "xbox", "sega", "steam", "switch",
    "game boy", "gameboy", "consola", "consolas", "videojuego", "videojuegos",
    "juego", "juegos", "remake", "remaster", "retroarch", "gamer", "gaming",
    "indie", "pcsx", "dolphin", "cemu", "rpcs3", "yuzu", "ryujinx", "recreativa",
    "wii", "gamecube", "n64", "snes", "megadrive", "genesis",
)
_news_cache = {"ts": 0, "data": []}

def _news_strip_html(raw):
    try:
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:160] + ("…" if len(text) > 160 else "")
    except Exception:
        return ""

def _news_parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return 0
    # RFC 2822 (RSS)
    try:
        import email.utils
        dt = email.utils.parsedate_to_datetime(raw)
        return int(dt.timestamp())
    except Exception:
        pass
    # ISO 8601 (Atom, p. ej. "2026-05-29T06:02:43Z")
    try:
        from datetime import datetime, timezone
        s = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return 0

def _fetch_feed(url, timeout=8):
    req = _nreq.Request(url, headers={"User-Agent": "Mozilla/5.0 (BatoceraManager; en emulacion)"})
    with _nreq.urlopen(req, timeout=timeout) as r:
        return r.read()

def _parse_rss_feed(data, source):
    """Parsea RSS 2.0 o Atom y devuelve lista de {title,link,desc,img,src,ts}."""
    items = []
    if not xml_looks_safe(data):
        return items
    try:
        root = ET.fromstring(data)
    except Exception:
        return items
    ns = {"media": "http://search.yahoo.com/mrss/", "atom": "http://www.w3.org/2005/Atom"}
    tag = root.tag.split("}")[-1].lower()
    if tag == "feed":
        # ── Atom (p. ej. GitHub releases) ──
        for it in root.iterfind("atom:entry", namespaces=ns) or root.iterfind("{http://www.w3.org/2005/Atom}entry"):
            try:
                title = (it.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
                link_el = it.find("{http://www.w3.org/2005/Atom}link")
                link = (link_el.get("href") if link_el is not None else "") or ""
                link = link.strip()
                if not title or not link:
                    continue
                desc = _news_strip_html(it.findtext("{http://www.w3.org/2005/Atom}content")
                                       or it.findtext("{http://www.w3.org/2005/Atom}summary") or "")
                pub = _news_parse_date(it.findtext("{http://www.w3.org/2005/Atom}updated")
                                       or it.findtext("{http://www.w3.org/2005/Atom}published") or "")
                items.append({"title": title, "link": link, "desc": desc,
                              "img": "", "src": source, "ts": pub})
            except Exception:
                continue
        return items

    # ── RSS 2.0 ──
    ch = root.find("channel")
    src = ch if ch is not None else root
    for it in src.iterfind("item"):
        try:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            if not title or not link:
                continue
            desc = _news_strip_html(it.findtext("description") or "")
            pub = _news_parse_date(it.findtext("pubDate") or "")
            img = ""
            enc = it.find("enclosure")
            if enc is not None and (enc.get("type") or "").startswith("image"):
                img = enc.get("url") or ""
            if not img:
                mc = it.find("media:content", namespaces=ns)
                if mc is None:
                    mc = it.find("media:thumbnail", namespaces=ns)
                if mc is not None:
                    img = mc.get("url") or mc.get("medium") or ""
            if img.startswith("//"):
                img = "https:" + img
            items.append({"title": title, "link": link, "desc": desc,
                          "img": img, "src": source, "ts": pub})
        except Exception:
            continue
    return items

def get_news():
    """Actualizaciones de Batocera (releases de GitHub), cacheadas 30 min."""
    now = time.time()
    if now - _news_cache["ts"] > 1800:
        items, seen = [], set()
        for f in NEWS_FEEDS:
            try:
                for it in _parse_rss_feed(_fetch_feed(f["url"]), f["name"]):
                    key = (it["link"] or "").split("#")[0].rstrip("/").lower()
                    if key and key in seen:
                        continue
                    if key:
                        seen.add(key)
                    items.append(it)
            except Exception:
                continue
        # Dedup por título normalizado
        seen_t, dedup = set(), []
        for it in items:
            tk = re.sub(r"[^a-z0-9]+", "", (it["title"] or "").lower())
            if tk in seen_t:
                continue
            seen_t.add(tk)
            dedup.append(it)
        dedup.sort(key=lambda x: x["ts"], reverse=True)
        _news_cache["data"] = dedup[:8]
        _news_cache["ts"] = now
    return _news_cache["data"]


# ═══════════════════════════════════════════════════════════════
#  MÓDULO: RETROACHIEVEMENTS (récords personales)
# ═══════════════════════════════════════════════════════════════

RA_API_BASE  = "https://retroachievements.org/API"
RA_CACHE_TTL = 600
_ra_cache    = {"ts": 0, "data": None, "user": ""}


def _ra_urlopen(url, timeout=10):
    """Indirección sobre urllib para poder simular la red en los tests."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "BatoceraManager/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _ra_get(settings, endpoint, params=None, timeout=10):
    """GET a la Web API de RetroAchievements. Devuelve dict/list o None.

    Autenticación por query string: `z`=usuario, `y`=Web API Key, `u`=usuario.
    Nunca lanza: si faltan credenciales o hay cualquier error devuelve None.
    """
    user = (settings.get("ra_user") or "").strip()
    key  = (settings.get("ra_api_key") or "").strip()
    if not user or not key:
        return None
    query = {"z": user, "y": key, "u": user}
    if params:
        query.update({k: v for k, v in params.items() if v is not None})
    url = f"{RA_API_BASE}/{endpoint}?" + urllib.parse.urlencode(query)
    try:
        return json.loads(_ra_urlopen(url, timeout))
    except Exception:
        return None


def _ra_absolute(path):
    """Convierte un path relativo de RA ('/Badge/x.png') en URL absoluta."""
    if not path:
        return ""
    path = str(path)
    if path.startswith("http"):
        return path
    return "https://retroachievements.org" + path


def ra_profile(settings):
    """Perfil del usuario (o None si no está disponible)."""
    data = _ra_get(settings, "API_GetUserProfile.php")
    if not isinstance(data, dict) or not data:
        return None
    return {
        "user": data.get("User") or settings.get("ra_user", ""),
        "avatar": _ra_absolute(data.get("UserPic")),
        "points": data.get("TotalPoints", 0),
        "true_points": data.get("TotalTruePoints", 0),
        "softcore_points": data.get("TotalSoftcorePoints", 0),
        "member_since": data.get("MemberSince") or "",
        "motto": data.get("Motto") or "",
        "rich_presence": data.get("RichPresenceMsg") or "",
        "last_game_id": data.get("LastGameID"),
    }


def ra_recent_achievements(settings, minutes=10080, limit=12):
    """Logros recientes (por defecto 7 días). Lista (posiblemente vacía)."""
    data = _ra_get(settings, "API_GetUserRecentAchievements.php", {"m": minutes})
    if not isinstance(data, list):
        return []
    out = []
    for a in data[:limit]:
        if not isinstance(a, dict):
            continue
        badge = a.get("BadgeURL") or (
            f"/Badge/{a['BadgeName']}.png" if a.get("BadgeName") else "")
        out.append({
            "title": a.get("Title") or "",
            "desc": a.get("Description") or "",
            "points": a.get("Points", 0),
            "true_ratio": a.get("TrueRatio", 0),
            "hardcore": bool(a.get("HardcoreMode")),
            "game": a.get("GameTitle") or "",
            "game_id": a.get("GameID"),
            "console": a.get("ConsoleName") or "",
            "date": a.get("Date") or "",
            "badge": _ra_absolute(badge),
        })
    return out


def ra_completion(settings, count=20):
    """Progreso de finalización por juego (lista, posiblemente vacía)."""
    data = _ra_get(settings, "API_GetUserCompletionProgress.php", {"c": count})
    if not isinstance(data, dict):
        return []
    out = []
    for g in (data.get("Results") or []):
        if not isinstance(g, dict):
            continue
        maxp = g.get("MaxPossible") or 0
        num  = g.get("NumAwarded") or 0
        out.append({
            "game_id": g.get("GameID"),
            "title": g.get("Title") or "",
            "console": g.get("ConsoleName") or "",
            "icon": _ra_absolute(g.get("ImageIcon")),
            "num_awarded": num,
            "max_possible": maxp,
            "hardcore": bool(g.get("NumAwardedHardcore")),
            "percent": round(num / maxp * 100, 1) if maxp else 0.0,
            "award_kind": g.get("HighestAwardKind") or "",
            "award_date": g.get("HighestAwardDate") or "",
        })
    return out


def ra_awards(settings):
    """Resumen de premios (o None si no está disponible)."""
    data = _ra_get(settings, "API_GetUserAwards.php")
    if not isinstance(data, dict) or not data:
        return None
    return {
        "total": data.get("TotalAwardsCount", 0),
        "mastery": data.get("MasteryAwardsCount", 0),
        "completion": data.get("CompletionAwardsCount", 0),
        "beaten_hardcore": data.get("BeatenHardcoreAwardsCount", 0),
        "beaten_softcore": data.get("BeatenSoftcoreAwardsCount", 0),
        "events": data.get("EventAwardsCount", 0),
    }


def ra_test(settings):
    """Prueba de conexión: informa si las credenciales funcionan y si está activo.

    Distingue `configured` (hay usuario + key) de `enabled` (además el
    interruptor está activo). Así "Probar conexión" no puede decir "correcto"
    mientras el Dashboard está desactivado.
    """
    user = (settings.get("ra_user") or "").strip()
    key  = (settings.get("ra_api_key") or "").strip()
    profile = ra_profile(settings) if (user and key) else None
    return {
        "ok": profile is not None,
        "configured": bool(user and key),
        "enabled": bool(settings.get("ra_enabled", True)) and bool(user and key),
        "user": (profile or {}).get("user", ""),
    }


def get_retroachievements(settings, force=False):
    """Resumen combinado de RetroAchievements, cacheado RA_CACHE_TTL segundos.

    - `configured`: hay usuario + Web API Key.
    - `enabled`: además el interruptor está activo (si no, no se toca la red).
    - `ok`: la API respondió.
    """
    user    = (settings.get("ra_user") or "").strip()
    key     = (settings.get("ra_api_key") or "").strip()
    enabled = bool(settings.get("ra_enabled", True))
    if not user or not key:
        return {"ok": False, "configured": False, "enabled": False, "updated": None,
                "profile": None, "recent": [], "completion": [], "awards": None}
    if not enabled:
        return {"ok": False, "configured": True, "enabled": False, "updated": None,
                "profile": None, "recent": [], "completion": [], "awards": None}

    now = time.time()
    fresh = (not force
             and _ra_cache["data"] is not None
             and _ra_cache.get("user") == user
             and (now - _ra_cache["ts"]) < RA_CACHE_TTL)
    if fresh:
        return _ra_cache["data"]

    profile = ra_profile(settings)
    data = {
        "ok": profile is not None,
        "configured": True,
        "enabled": True,
        "updated": now,
        "profile": profile,
        "recent": ra_recent_achievements(settings),
        "completion": ra_completion(settings),
        "awards": ra_awards(settings),
    }
    if profile is not None:
        _ra_cache.update({"ts": now, "data": data, "user": user})
    return data




def get_uptime():
    try:
        secs = float(Path("/proc/uptime").read_text().split()[0])
        d = int(secs // 86400); secs %= 86400
        h = int(secs // 3600);  secs %= 3600
        m = int(secs // 60)
        parts = []
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        parts.append(f"{m}m")
        return " ".join(parts)
    except Exception: return "N/A"

def _ipv4_map():
    """Mapa {interfaz: IPv4} leyendo todas las interfaces en una sola llamada.

    Usa `ip -4 -o addr show` (iproute2). Devuelve {} si `ip` no está
    disponible (p. ej. fuera de Linux) o no hay direcciones.
    """
    out = _run("ip -4 -o addr show 2>/dev/null")
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if "inet" not in parts:
            continue
        i = parts.index("inet")
        # formato: "2: eth0    inet 192.168.1.5/24 brd ... scope global eth0"
        if i < 2 or i + 1 >= len(parts):
            continue
        result.setdefault(parts[1], parts[i + 1].split("/")[0])
    return result


def get_network():
    ifaces = []
    ip_map = _ipv4_map()
    try:
        lines = Path("/proc/net/dev").read_text().splitlines()[2:]
        for line in lines:
            parts = line.split()
            if len(parts) < 10: continue
            iface = parts[0].rstrip(":")
            if iface == "lo": continue
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])
            def fmt(b):
                if b > 1073741824: return f"{b/1073741824:.1f} GB"
                if b > 1048576:    return f"{b/1048576:.1f} MB"
                if b > 1024:       return f"{b/1024:.1f} KB"
                return f"{b} B"
            ifaces.append({
                "iface":  iface,
                "ip":     ip_map.get(iface),
                "rx":     fmt(rx_bytes),
                "tx":     fmt(tx_bytes),
                "rx_raw": rx_bytes,
                "tx_raw": tx_bytes,
            })
    except Exception: pass
    return ifaces

def _es_listen_port(pid):
    """Puerto TCP (el mayor) que está en LISTEN el proceso `pid`.

    Lee `/proc/net/tcp{,6}` y los descriptores de `/proc/<pid>/fd` de forma
    directa, sin invocar subprocesos. Devuelve None si no hay dato
    (sin `/proc`, sin permisos o sin socket de servicio escuchando).
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    inode_port = {}
    for proc_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(proc_file).read_text().splitlines()[1:]
        except Exception:
            continue
        for line in lines:
            parts = line.split()
            # 0A = TCP_LISTEN · col.1 = "IP:puerto" en hex · col.9 = inode
            if len(parts) < 10 or parts[3] != "0A":
                continue
            try:
                inode_port[int(parts[9])] = int(parts[1].rsplit(":", 1)[1], 16)
            except (ValueError, IndexError):
                continue
    if not inode_port:
        return None
    ports = set()
    try:
        for fd in Path(f"/proc/{pid}/fd").iterdir():
            try:
                target = os.readlink(str(fd))
            except OSError:
                continue
            m = re.match(r"socket:\[(\d+)\]", target)
            if m:
                port = inode_port.get(int(m.group(1)))
                if port:
                    ports.add(port)
    except OSError:
        return None
    return max(ports) if ports else None


_es_restart_pending = False

def mark_es_restart_pending(flag=True):
    """Marca que EmulationStation debe recargar los cambios de es_systems."""
    global _es_restart_pending
    _es_restart_pending = bool(flag)

def restart_emulationstation():
    """Reinicia EmulationStation vía batocera-es-swissknife.

    `--restart` hace `kill -9` del proceso de ES; el wrapper
    `emulationstation-standalone` (un bucle) lo relanza solo, sin tocar X ni
    openbox. Tarda milisegundos: es seguro llamarlo desde un handler HTTP.

    Se invoca desde el botón manual del dashboard y, automáticamente, tras un
    scrapeo que guardó metadatos (ver `reload_es_after_scrape`).

    Devuelve (ok, info).
    """
    import subprocess as _sp
    try:
        p = _sp.run(["batocera-es-swissknife", "--restart"],
                    capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return False, {"error": "batocera-es-swissknife no está disponible"}
    except _sp.TimeoutExpired:
        return False, {"error": "Reinicio de ES agotado (timeout)"}
    except Exception as e:
        return False, {"error": str(e)}
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "error desconocido").strip()[:500]
        return False, {"error": msg}
    mark_es_restart_pending(False)
    return True, {"ok": True}

def reload_es_after_scrape(meta_saved=True):
    """Recarga EmulationStation tras escribir metadatos en la gamelist.

    ES lee las gamelists al arrancar y las mantiene en memoria: la imagen sí
    aparece en la TV (autodetecta la carpeta `images/`), pero el texto no se
    relee hasta que ES se reinicia. Por eso, tras un scrapeo que guardó
    metadatos, hay que recargarlo.

    Nunca lanza: si el reinicio falla, el scrapeo ya se completó igual.
    Devuelve {"ok", "reloaded", "error"?}.
    """
    if not meta_saved:
        return {"ok": True, "reloaded": False}
    try:
        ok, info = restart_emulationstation()
    except Exception as e:  # pragma: no cover - defensivo
        return {"ok": False, "reloaded": False, "error": str(e)}
    if ok:
        return {"ok": True, "reloaded": True}
    return {"ok": False, "reloaded": False,
            "error": (info or {}).get("error", "error desconocido")}

def get_es_status():
    # `comm` se trunca a 15 chars ("emulationstatio"), por eso -f (cmdline completa)
    pid = _run("pgrep -f -n emulationstation 2>/dev/null")
    if pid:
        return {"running": True, "pid": pid, "port": _es_listen_port(pid),
                "restart_pending": _es_restart_pending}
    return {"running": False, "port": None, "restart_pending": _es_restart_pending}

def get_top_processes():
    procs = []
    try:
        out = _run("ps aux --sort=-%cpu 2>/dev/null || ps -eo user,pid,pcpu,pmem,comm --sort=-pcpu 2>/dev/null")
        lines = out.splitlines()
        for line in lines[1:9]:
            parts = line.split(None, 10)
            if len(parts) >= 5:
                procs.append({
                    "user":  parts[0],
                    "pid":   parts[1],
                    "cpu":   parts[2],
                    "mem":   parts[3],
                    "cmd":   parts[10].split("/")[-1][:30] if len(parts)>10 else parts[4][:30],
                })
    except Exception: pass
    return procs

def get_dashboard():
    cpu_model, cpu_cores = get_cpu_info()
    cpu_temp, temp_label = get_cpu_temp()
    return {
        "batocera_version": get_batocera_version(),
        "uptime":           get_uptime(),
        "es":               get_es_status(),
        "cpu": {
            "model":    cpu_model,
            "cores":    cpu_cores,
            "usage":    get_cpu_usage(),
            "temp":     cpu_temp,
            "temp_src": temp_label,
        },
"gpu":    get_gpu_info(),
        "memory": get_memory(),
        "disk":   get_disk(),
        "disk_updated": _disk_cache.get("updated"),
        "disk_io": get_disk_io(),
        "battery": get_battery(),
        "network":get_network(),
        "processes": get_top_processes(),
        "fans":   get_fans(),
    }


# ═══════════════════════════════════════════════════════════════
#  MÓDULO: AUTOSTART SERVICE MANAGER
# ═══════════════════════════════════════════════════════════════

CUSTOM_SH       = Path("/userdata/system/custom.sh")
SERVICE_MARKER  = "# [batocera-manager]"
SERVICE_TAG_END = "# [/batocera-manager]"

def get_service_cmd(settings):
    """Genera el comando de inicio según la ruta real del app.py (seguro para shell)."""
    app_path = str(settings.get("app_path", "/userdata/system/batocera_web/app.py"))
    try:
        port = int(settings.get("server_port", 5000))
    except (TypeError, ValueError):
        port = 5000
    if not (1 <= port <= 65535):
        port = 5000
    return f"python3 {shlex.quote(app_path)} --port {port}"

def get_autostart_status(settings):
    """Lee custom.sh y detecta si el servicio está registrado."""
    if not CUSTOM_SH.exists():
        return {"registered": False, "cmd": None, "line": None}
    content = CUSTOM_SH.read_text(errors="replace")
    if SERVICE_MARKER not in content:
        return {"registered": False, "cmd": None, "line": None}
    # Extraer el bloque
    try:
        start = content.index(SERVICE_MARKER)
        end   = content.index(SERVICE_TAG_END) + len(SERVICE_TAG_END)
        block = content[start:end]
        # Extraer línea de comando
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return {"registered": True, "cmd": line, "block": block}
    except ValueError:
        pass
    return {"registered": True, "cmd": None, "block": ""}

def _read_proc_cmdline(pid):
    """Devuelve /proc/<pid>/cmdline como texto (cadena vacía si no se puede)."""
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
    except OSError:
        return ""

def _port_from_cmdline(cmdline):
    """Extrae el puerto de `--port N` o `--port=N` de una línea de comandos.

    `cmdline` es el contenido de /proc/<pid>/cmdline (argumentos separados por
    bytes nulos). Devuelve None si no hay --port o si el valor no es un puerto
    válido (1-65535).
    """
    args = [a for a in (cmdline or "").split("\0") if a]
    for i, arg in enumerate(args):
        if arg.startswith("--port="):
            value = arg.split("=", 1)[1]
        elif arg == "--port" and i + 1 < len(args):
            value = args[i + 1]
        else:
            continue
        try:
            port = int(value)
        except ValueError:
            return None
        return port if 1 <= port <= 65535 else None
    return None

def get_process_status():
    """Verifica si el servidor está corriendo y en qué puerto escucha.

    El puerto se lee del propio manager: primero de su línea de comandos
    (`--port N`) y, si no aparece ahí, del socket en LISTEN de ese mismo PID
    (`_es_listen_port`). Antes se buscaba «el primer python» en la salida de
    `ss -tlnp`: cualquier otro servicio escrito en Python que escuchara en
    otro puerto (wsdd, por ejemplo) salía como si fuera el puerto del manager,
    aunque su línea de comandos dijera 5000.
    """
    pids = _run('pgrep -f "python3.*app.py"').split()
    if not pids:
        return {"running": False, "pids": [], "port": None}

    port = None
    for pid in pids:
        port = _port_from_cmdline(_read_proc_cmdline(pid))
        if port:
            break
    if not port:
        for pid in pids:
            port = _es_listen_port(pid)
            if port:
                break
    return {"running": True, "pids": pids, "port": port}

def install_autostart(cmd):
    """Instala o actualiza el bloque de autostart en custom.sh."""
    block = f"{SERVICE_MARKER}\n{cmd} &\n{SERVICE_TAG_END}\n"
    if CUSTOM_SH.exists():
        content = CUSTOM_SH.read_text(errors="replace")
        if SERVICE_MARKER in content:
            # Reemplazar bloque existente
            try:
                start = content.index(SERVICE_MARKER)
                end   = content.index(SERVICE_TAG_END) + len(SERVICE_TAG_END) + 1
                content = content[:start] + block + content[end:]
            except ValueError:
                content += "\n" + block
        else:
            content += "\n" + block
    else:
        content = "#!/bin/bash\n" + block
    CUSTOM_SH.write_text(content, encoding="utf-8")
    CUSTOM_SH.chmod(0o755)

def remove_autostart():
    """Elimina el bloque de autostart de custom.sh."""
    if not CUSTOM_SH.exists():
        return False
    content = CUSTOM_SH.read_text(errors="replace")
    if SERVICE_MARKER not in content:
        return False
    try:
        start = content.index(SERVICE_MARKER)
        end   = content.index(SERVICE_TAG_END) + len(SERVICE_TAG_END)
        # Quitar también el \n previo si existe
        if start > 0 and content[start-1] == "\n":
            start -= 1
        content = content[:start] + content[end:]
        CUSTOM_SH.write_text(content.rstrip() + "\n", encoding="utf-8")
        return True
    except ValueError:
        return False

def kill_service():
    """Mata el proceso del servidor."""
    import subprocess
    try:
        r = subprocess.run(["pkill", "-f", "python3.*app.py"],
                           capture_output=True, timeout=5)
        return r.returncode in (0, 1)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  MÓDULO: SCRAPER — ScreenScraper.fr API
# ═══════════════════════════════════════════════════════════════
import re as _re
import urllib.parse as _uparse
import urllib.request as _ureq

# Endpoint correcto: el host de ScreenScraper expone `api2` (con `apiv2` -> 404).
SS_API   = "https://api.screenscraper.fr/api2"
SS_SOFTNAME = "batocera_manager"

# ScreenScraper exige credenciales de desarrollador (devid/devpassword) en cada
# petición. Batocera NO las guarda en batocera.conf: van incrustadas en el
# binario de EmulationStation. Se detectan de ahí y, como último recurso, se
# usan las oficiales que Batocera distribuye.
SS_DEV_FALLBACK = ("batoceralinux", "omvIrirRPuY")
ES_BINARY_CANDIDATES = (
    "/usr/bin/emulationstation",
    "/usr/bin/batocera-es-launcher",
)

def _find_es_marker(data: bytes, name: bytes) -> str:
    """Extrae el valor de `name=<valor>` dentro de un binario (p.ej. b'devid')."""
    m = _re.search(name + rb"=([A-Za-z0-9_.\-]+)", data)
    return m.group(1).decode("ascii", "ignore") if m else ""

def detect_ss_dev_credentials(paths=None, settings=None):
    """Devuelve (devid, devpassword) leídos del binario de EmulationStation.

    Solo detecta: si no encuentra los marcadores devuelve ("", ""). La ruta del
    binario puede indicarse en `settings["es_binary"]`.
    """
    if paths is None:
        configured = (settings or {}).get("es_binary")
        paths = [configured] if configured else list(ES_BINARY_CANDIDATES)
    devid = devpassword = ""
    for p in paths:
        try:
            data = Path(p).read_bytes()
        except Exception:
            continue
        devid       = devid or _find_es_marker(data, b"devid")
        devpassword = devpassword or _find_es_marker(data, b"devpassword")
        if devid and devpassword:
            break
    return devid, devpassword

def get_scraper_config(settings):
    """Lee credenciales de ScreenScraper desde batocera.conf."""
    conf_path = Path(settings.get("batocera_conf", "/userdata/system/batocera.conf"))
    cfg = {"ss_user":"","ss_password":"","ss_devid":"","ss_devpassword":"",
           "ss_region":"wor","ss_lang":"es",
           "ss_image_type":"mixrbv1",
           "tgdb_apikey":"","igdb_client_id":"","igdb_client_secret":"",
           "scraper_source":"screenscraper"}
    if not conf_path.exists():
        return _apply_ss_dev_credentials(cfg, settings)
    try:
        for line in conf_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k == "global.scrapper.user":        cfg["ss_user"]        = v
            if k == "global.scrapper.password":    cfg["ss_password"]    = v
            if k == "global.scrapper.devid":       cfg["ss_devid"]       = v
            if k == "global.scrapper.devpassword": cfg["ss_devpassword"] = v
            if k == "global.scrapper.region":
                cfg["ss_region"] = {"world":"wor","mundial":"wor","europa":"eu",
                                    "usa":"us","japon":"jp"}.get(v.strip().lower(), v)
            if k == "global.scrapper.lang":       cfg["ss_lang"]       = v
            if k == "global.tgdb.apikey":          cfg["tgdb_apikey"]        = v
            if k == "global.igdb.clientid":         cfg["igdb_client_id"]     = v
            if k == "global.igdb.clientsecret":     cfg["igdb_client_secret"] = v
            if k == "global.scraper.source":        cfg["scraper_source"]     = v
            if k == "global.scrapper.imageSource":cfg["ss_image_type"] = v
    except Exception:
        pass
    return _apply_ss_dev_credentials(cfg, settings)

def _apply_ss_dev_credentials(cfg, settings):
    """Rellena devid/devpassword si falta alguno.

    Orden: batocera.conf -> binario de EmulationStation -> oficiales de Batocera.
    """
    if not (cfg["ss_devid"] and cfg["ss_devpassword"]):
        det_id, det_pass = detect_ss_dev_credentials(settings=settings)
        cfg["ss_devid"]       = cfg["ss_devid"] or det_id
        cfg["ss_devpassword"] = cfg["ss_devpassword"] or det_pass
    if not cfg["ss_devid"]:
        cfg["ss_devid"], cfg["ss_devpassword"] = SS_DEV_FALLBACK
    elif not cfg["ss_devpassword"]:
        cfg["ss_devpassword"] = SS_DEV_FALLBACK[1]
    return cfg

# Claves de batocera.conf que el scraper puede escribir. El front-end envía
# justo estas (`global.scrapper.*`), que es lo que lee `get_scraper_config`.
SCRAPER_CONF_KEYS = (
    "global.scrapper.user", "global.scrapper.password",
    "global.scrapper.devid", "global.scrapper.devpassword",
    "global.scrapper.region", "global.scrapper.lang",
    "global.scrapper.imageSource", "global.scrapper.style",
    "global.scraper.source",
    "global.tgdb.apikey",
    "global.igdb.clientid", "global.igdb.clientsecret",
)

def resolve_scraper_creds(settings, client_data):
    """Credenciales efectivas: config del servidor como base, cliente por encima.

    Así el devid detectado en el servidor llega al scrape aunque el formulario
    del navegador no lo traiga.
    """
    cfg = get_scraper_config(settings)
    for k in ("ss_user", "ss_password", "ss_devid", "ss_devpassword",
              "ss_region", "ss_lang", "ss_image_type",
              "tgdb_apikey", "igdb_client_id", "igdb_client_secret"):
        val = (client_data or {}).get(k)
        if val:
            cfg[k] = val
    return cfg

def save_scraper_config(conf_path, lines):
    """Escribe credenciales del scraper en batocera.conf. Devuelve (ok, error).

    Solo acepta claves de SCRAPER_CONF_KEYS para no escribir basura.
    """
    conf_path = Path(conf_path)
    try:
        text = conf_path.read_text(errors="replace") if conf_path.exists() else ""
        conf_lines = text.splitlines()
        for item in lines or []:
            key = (item or {}).get("key", "")
            val = (item or {}).get("val", "")
            if not key or key not in SCRAPER_CONF_KEYS:
                continue
            replaced = False
            for i, line in enumerate(conf_lines):
                stripped = line.strip()
                if stripped.startswith(key + "=") or stripped == key + "=":
                    conf_lines[i] = f"{key}={val}"
                    replaced = True
                    break
            if not replaced:
                conf_lines.append(f"{key}={val}")
        conf_path.parent.mkdir(parents=True, exist_ok=True)
        conf_path.write_text("\n".join(conf_lines) + "\n", encoding="utf-8")
        return True, ""
    except Exception as e:
        return False, str(e)

# Mapeo sistema Batocera → systemeid ScreenScraper
# (basado en screenscraper_platformid_map de batocera-emulationstation)
SS_SYSTEMS = {
    "3do":29,"amiga":64,"amiga500":64,"amiga1200":64,"amigacd32":130,
    "amstradcpc":65,"apple2":86,"arcade":75,"mame":75,
    "atari2600":26,"atari5200":40,"atari7800":41,"atari800":43,"atarixe":43,
    "atarist":42,"atarijaguar":27,"atarijaguarcd":171,"lynx":28,
    "bbc":37,"bbcmicro":37,"colecovision":48,"c64":66,"commodore64":66,"vic20":73,
    "plus4":99,"c16":99,"intellivision":115,"xbox":32,"xbox360":33,
    "msx":113,"msx2":116,"msx2plus":117,"msxturbor":118,
    "neogeo":142,"neogeocd":70,"neogeopocket":25,"ngp":25,
    "neogeopocketcolor":82,"ngpc":82,
    "3ds":17,"n64":14,"nds":15,"fds":106,"famicom":3,"nes":3,"snes":4,
    "gb":9,"gba":12,"gbc":10,"gamecube":13,"gc":13,"wii":16,"wiiu":18,
    "virtualboy":11,"gameandwatch":52,"pc":135,"scummvm":123,
    "sega32x":19,"segacd":20,"megacd":20,"dreamcast":23,"gamegear":21,
    "genesis":1,"megadrive":1,"mastersystem":2,"saturn":22,"sg1000":109,
    "x68000":79,"pc88":221,"pc98":208,
    "psx":57,"ps2":58,"ps3":59,"ps4":60,"psp":61,"psvita":62,
    "tg16":31,"pcengine":31,"tgcd":114,"supergrafx":105,
    "wonderswan":45,"wonderswancolor":46,"zxspectrum":76,
    "odyssey2":104,"videopac":104,"vectrex":102,"coco":144,"tandy":144,
    "dragon32":91,"gp32":101,"atomiswave":53,"naomi":56,"naomi2":56,
    "pcfx":72,"model3":55,"daphne":49,"pico8":234,"supergb":127,
    "satellaview":107,"sufami":108,"zx81":77,"ti99":205,"watara":207,
    "pokemini":211,"gx4000":87,"cdi":133,"philipscdi":133,
    "scv":67,"cassettevision":300,"triforce":0,"sonic":0,
}

# ScreenScraper devuelve JSON malformado: añade una barra invertida espuria en las
# URLs que ecoa (p.ej. `softname=batocera\_manager`, cuando nosotros enviamos
# `softname=batocera_manager`). Ese `\_` no es un escape JSON válido y
# `json.loads` estricto aborta con `Invalid \escape`, descartando la respuesta.
# Se elimina la barra espuria (recupera el valor que realmente pedimos).
_SS_INVALID_ESCAPE = _re.compile(rb'\\(?!(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))(.)?',
                                 _re.DOTALL)

def ss_parse_json(payload):
    """Parsea la respuesta de ScreenScraper, saneando escapes inválidos.

    Sólo se sanea si el parseo estricto falla, para no alterar respuestas
    correctas. Acepta bytes o str; si el saneado no basta, propaga el error.
    """
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", "replace")
    try:
        return json.loads(payload)
    except ValueError:
        cleaned = _SS_INVALID_ESCAPE.sub(lambda m: m.group(1) or b"",
                                         payload.encode("utf-8", "replace"))
        return json.loads(cleaned.decode("utf-8", "replace"))

def _ss_fetch_json(url, timeout=20):
    """GET JSON a ScreenScraper devolviendo (data, error_msg, quota)."""
    try:
        req = _ureq.Request(url, headers={
            "User-Agent": "BatoceraManager/1.2",
            "Accept": "application/json",
        })
        with _ureq.urlopen(req, timeout=timeout) as r:
            return ss_parse_json(r.read()), None, {}
    except _ureq.HTTPError as e:
        body = ""
        try: body = e.read().decode(errors="replace")[:200]
        except Exception: pass
        return None, f"HTTP {e.code}: {body or e.reason}", {}
    except Exception as e:
        return None, str(e), {}

def _ss_quota(data):
    """Extrae la cuota del usuario de una respuesta SS."""
    ssuser = (data or {}).get("response",{}).get("ssuser",{}) or {}
    return {
        "requeststoday":    ssuser.get("requeststoday",""),
        "maxrequestsperday":ssuser.get("maxrequestsperday",""),
        "maxthreads":       ssuser.get("maxthreads",""),
        "level":            ssuser.get("niveau",""),
    }

def _ss_parse_jeu(data):
    """Devuelve el primer 'jeu' de una respuesta SS o None."""
    resp = (data or {}).get("response",{}) or {}
    jeu = resp.get("jeu")
    if jeu:
        return jeu
    if isinstance(resp.get("jeux"), list) and resp["jeux"]:
        return resp["jeux"][0]
    return None

def ss_search_game(rom_filename, system_name, ss_user, ss_pass,
                   region="wor", lang="es", rom_path=None,
                   devid="", devpassword=""):
    """Busca un juego en ScreenScraper.fr replicando el formato de Batocera:
    jeuInfos.php + md5/crc/romtaille/systemeid, con fallback a jeuRecherche.php."""
    if not ss_user or not ss_pass:
        return None, "Sin credenciales de ScreenScraper", {}
    if not devid or not devpassword:
        return None, ("ScreenScraper necesita devid/devpassword de desarrollador "
                      "(campos opcionales en la pestaña Configuración del scraper)"), {}

    sys_id = SS_SYSTEMS.get(system_name.lower(), 0)
    base = {
        "devid":       devid,
        "devpassword": devpassword,
        "softname":    SS_SOFTNAME,
        "output":      "json",
        "ssid":        ss_user,
        "sspassword":  ss_pass,
        "systemeid":   str(sys_id),
    }

    # Hash/tamaño igual que Batocera: md5+crc si el archivo es <= 128 MB, tamaño siempre
    size = 0
    md5v = crcv = None
    if rom_path:
        try:
            size = Path(rom_path).stat().st_size
        except Exception:
            size = 0
        if 0 < size <= 131072 * 1024:
            md5v = md5_file(rom_path)
            crcv = crc32_file(rom_path)

    has_crc = bool(crcv)
    # ScreenScraper exige `systemeid` válido si no hay CRC. Si el sistema no
    # está mapeado (sys_id=0) y no podemos aportar CRC, la petición a
    # jeuInfos.php está condenada al HTTP 400: la saltamos y vamos directo a
    # la búsqueda por nombre (jeuRecherche.php), que sí funciona sin systemeid.
    skip_jeuinfos = (sys_id == 0 and not has_crc)

    data = err = quota = None
    if not skip_jeuinfos:
        params = dict(base)
        params["romtype"]   = "rom"
        params["romnom"]    = rom_filename
        params["romtaille"] = str(size)
        if md5v:
            params["md5"] = md5v.upper()
        if crcv:
            params["crc"] = crcv

        data, err, _ = _ss_fetch_json(f"{SS_API}/jeuInfos.php?" + _uparse.urlencode(params))
        quota = _ss_quota(data) if data else {}
        if data is None:
            # No abortamos: caemos al fallback por nombre (útil cuando el
            # sistema no está mapeado o el archivo no se localiza).
            data = None
        else:
            hdr = data.get("header", {}) or {}
            if hdr.get("success") == "true":
                jeu = _ss_parse_jeu(data)
                if jeu:
                    return jeu, None, quota
            elif hdr.get("success") is False:
                msg = hdr.get("message", "") or hdr.get("error", "Sin resultados")
                # Si el motivo es el systemeid obligatorio, seguimos al fallback
                if "systemeid" not in str(msg).lower():
                    return None, msg, quota

    # Fallback por nombre limpio (jeuRecherche.php)
    clean = _clean_rom_name(rom_filename)
    if not clean:
        return None, (err or "Sin resultados para este ROM"), (quota or {})
    p2 = {k: v for k, v in base.items()}
    p2["recherche"] = clean
    p2["systemeid"] = str(sys_id)
    data2, err2, _ = _ss_fetch_json(f"{SS_API}/jeuRecherche.php?" + _uparse.urlencode(p2))
    if data2 is None:
        return None, (err2 or err or "Sin resultados"), (quota or {})
    hdr2 = data2.get("header", {}) or {}
    quota2 = _ss_quota(data2)
    if hdr2.get("success") == "true":
        jeu = _ss_parse_jeu(data2)
        if jeu:
            return jeu, None, quota2
        return None, "Sin resultados para este ROM", quota2
    msg2 = hdr2.get("message", "") or hdr2.get("error", "Sin resultados")
    return None, msg2, (quota2 or quota or {})

def ss_media_url(game_data, image_type, region="wor"):
    """Devuelve (url, extension) del mejor medio SS para el tipo solicitado,
    replicando la preferencia de región de Batocera (region → wor → us → eu → jp)."""
    ss_region = image_type
    medias = game_data.get("medias", []) or []
    cands  = [m for m in medias if m.get("type","") == ss_region]
    if not cands:
        cands = [m for m in medias if ss_region in m.get("type","")]
    if not cands:
        return None, None
    region = (region or "wor").lower()
    chosen = None
    for reg in [region, "wor", "us", "eu", "jp", "ss", "cus", ""]:
        for m in cands:
            if (m.get("region","") or "").lower() == reg:
                chosen = m
                break
        if chosen:
            break
    if not chosen:
        chosen = cands[0]
    url = (chosen.get("url","") or "").replace("#screenscraper#", "https://www.screenscraper.fr/")
    ext = (chosen.get("format","") or "").lstrip(".").lower()
    if ext == "jpeg":
        ext = "jpg"
    return url, ("." + ext if ext else "")

def ss_download_image(game_data, image_type, dest_path, region="wor"):
    """Descarga una imagen de ScreenScraper y la guarda."""
    url, _ext = ss_media_url(game_data, image_type, region)
    if not url:
        return False, "Sin imagen disponible en ScreenScraper"
    ok, msg = download_image_generic(url, dest_path, referer_for=url)
    return ok, msg

def ss_build_meta(game_data, region="wor", lang="es"):
    """Extrae metadatos de la respuesta de ScreenScraper."""
    def get_text(lst, preferred_region="wor", preferred_lang="es", key="langue"):
        """Extrae `text` del primer elemento cuyo `key` coincide con el preferido.

        `synopsis`/`genres` indexan por `langue`; `noms` indexa por `region`.
        """
        if not lst: return ""
        if isinstance(lst, str): return lst
        preferred = preferred_lang if key == "langue" else preferred_region
        for item in lst:
            if isinstance(item, dict) and item.get(key) == preferred:
                return item.get("text","")
        # Fallback: inglés, región mundial o vacío
        for item in lst:
            if isinstance(item, dict) and item.get(key) in ("en","","wor","us"):
                return item.get("text","")
        if isinstance(lst[0], dict): return lst[0].get("text","")
        return str(lst[0])

    noms   = game_data.get("noms",[])
    name   = get_text(noms, region, lang, key="region") or game_data.get("romnom","")
    synops = game_data.get("synopsis",[])
    desc   = get_text(synops, region, lang)
    genres = game_data.get("genres",[])
    genre  = get_text(genres[0].get("noms",[]) if genres else [], region, lang) if genres else ""
    date   = game_data.get("dates",{})
    year   = ""
    if isinstance(date, dict):
        d = date.get(region) or date.get("wor") or date.get("us","")
        year = d[:4] if d else ""
    elif isinstance(date, list):
        for di in date:
            if isinstance(di, dict) and di.get("region") in (region,"wor","us"):
                year = (di.get("text",""))[:4]; break
    editeur = game_data.get("editeur",{})
    publisher = editeur.get("text","") if isinstance(editeur,dict) else str(editeur)
    rating_val = game_data.get("note","")
    try:    rating = str(round(float(rating_val)/20, 2)) if rating_val else ""
    except (TypeError, ValueError): rating = ""
    return {
        "name":      name,
        "desc":      desc,
        "genre":     genre,
        "year":      year,
        "publisher": publisher,
        "rating":    rating,
    }


# ═══════════════════════════════════════════════════════════════
#  FUENTES ALTERNATIVAS DE SCRAPING: TheGamesDB + IGDB
# ═══════════════════════════════════════════════════════════════

TGDB_API = "https://api.thegamesdb.net/v1"

# Mapeo sistema Batocera -> platform id de TheGamesDB
TGDB_PLATFORMS = {
    "snes":6,"nes":7,"n64":3,"gba":5,"gb":4,"gbc":41,"nds":8,
    "megadrive":36,"genesis":18,"segacd":21,"sega32x":33,
    "psx":10,"ps2":11,"psp":13,"dreamcast":16,"saturn":17,
    "mame":23,"arcade":23,"neogeo":24,
    "atari2600":22,"atari7800":27,"atari5200":26,"lynx":4924,
    "pcengine":34,"amiga500":4911,"amiga1200":4911,"c64":40,
    "gamecube":2,"wii":9,"wiiu":38,"3ds":4912,
    "mastersystem":35,"gamegear":20,"sg1000":4949,
    "xbox":14,"xbox360":15,"ps3":12,
}

# Mapeo sistema Batocera -> platform id de IGDB (consultado dinámicamente, pero cache de los comunes)
IGDB_PLATFORMS = {
    "snes":19,"nes":18,"n64":4,"gba":24,"gb":33,"gbc":22,"nds":20,
    "megadrive":29,"genesis":29,"segacd":78,"sega32x":30,
    "psx":7,"ps2":8,"psp":38,"dreamcast":23,"saturn":32,
    "mame":52,"arcade":52,"neogeo":80,
    "atari2600":59,"atari7800":60,"lynx":61,
    "pcengine":128,"amiga500":16,"c64":15,
    "gamecube":21,"wii":5,"wiiu":41,"3ds":37,
    "mastersystem":64,"gamegear":35,
    "xbox":11,"xbox360":12,"ps3":9,
}

def tgdb_search_game(rom_filename, system_name, api_key, clean_name=None):
    """Busca un juego en TheGamesDB."""
    if not api_key:
        return None, "Falta API Key de TheGamesDB"
    if not clean_name:
        clean_name = _clean_rom_name(rom_filename)
    platform_id = TGDB_PLATFORMS.get(system_name.lower())
    params = {"apikey": api_key, "name": clean_name, "fields": "players,publishers,genres,overview"}
    if platform_id:
        params["filter[platform]"] = str(platform_id)
    url = f"{TGDB_API}/Games/ByGameName?" + _uparse.urlencode(params)
    try:
        req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
        with _ureq.urlopen(req, timeout=12) as r:
            data  = json.loads(r.read())
            games = data.get("data", {}).get("games", [])
            if not games:
                return None, "Sin resultados en TheGamesDB"
            return games[0], None
    except _ureq.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, str(e)

def tgdb_get_image(game_id, api_key):
    """Obtiene la URL de boxart/imagen de un juego TGDB."""
    params = {"apikey": api_key, "games_id": str(game_id)}
    url = f"{TGDB_API}/Games/Images?" + _uparse.urlencode(params)
    try:
        req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
        with _ureq.urlopen(req, timeout=12) as r:
            data    = json.loads(r.read())
            base    = data.get("data", {}).get("base_url", {}).get("original", "")
            images  = data.get("data", {}).get("images", {}).get(str(game_id), [])
            # Priorizar boxart frontal
            for img in images:
                if img.get("type") == "boxart" and img.get("side") == "front":
                    return base + img.get("filename",""), None
            if images:
                return base + images[0].get("filename",""), None
            return None, "Sin imágenes disponibles"
    except Exception as e:
        return None, str(e)

_tgdb_genres_cache    = {}
_tgdb_publishers_cache = {}

def tgdb_resolve_genres(genre_ids, api_key):
    """Resuelve IDs de género a nombres, con cache en memoria."""
    if not genre_ids:
        return ""
    global _tgdb_genres_cache
    if not _tgdb_genres_cache:
        try:
            url = f"{TGDB_API}/Genres?" + _uparse.urlencode({"apikey": api_key})
            req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
            with _ureq.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                genres = data.get("data", {}).get("genres", {})
                _tgdb_genres_cache = {int(k): v.get("name","") for k, v in genres.items()}
        except Exception:
            return ""
    names = [_tgdb_genres_cache.get(gid, "") for gid in genre_ids[:2]]
    return ", ".join(n for n in names if n)

def tgdb_resolve_publisher(publisher_ids, api_key):
    """Resuelve el primer ID de publisher a nombre, con cache en memoria."""
    if not publisher_ids:
        return ""
    global _tgdb_publishers_cache
    if not _tgdb_publishers_cache:
        try:
            url = f"{TGDB_API}/Publishers?" + _uparse.urlencode({"apikey": api_key})
            req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
            with _ureq.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                pubs = data.get("data", {}).get("publishers", {})
                _tgdb_publishers_cache = {int(k): v.get("name","") for k, v in pubs.items()}
        except Exception:
            return ""
    return _tgdb_publishers_cache.get(publisher_ids[0], "")

def tgdb_build_meta(game, api_key=None):
    """Extrae metadatos de la respuesta TGDB, resolviendo genre/publisher si hay api_key."""
    overview = game.get("overview","") or ""
    genre_ids = game.get("genres", []) or []
    pub_ids   = game.get("publishers", []) or []
    genre     = tgdb_resolve_genres(genre_ids, api_key) if api_key else ""
    publisher = tgdb_resolve_publisher(pub_ids, api_key) if api_key else ""
    return {
        "name":      game.get("game_title",""),
        "desc":      overview,
        "genre":     genre,
        "year":      (game.get("release_date","") or "")[:4],
        "publisher": publisher,
        "rating":    "",   # TGDB no tiene rating de usuario en este endpoint
    }

# ── IGDB (requiere OAuth de Twitch) ──
_igdb_token_cache = {"token": None, "expires": 0}

def igdb_get_token(client_id, client_secret):
    """Obtiene un token OAuth de Twitch para IGDB (cache en memoria)."""
    import time as _t
    if _igdb_token_cache["token"] and _t.time() < _igdb_token_cache["expires"]:
        return _igdb_token_cache["token"], None
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    url = "https://id.twitch.tv/oauth2/token?" + _uparse.urlencode(params)
    try:
        req = _ureq.Request(url, data=b"", method="POST")
        with _ureq.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            token = data.get("access_token")
            ttl   = data.get("expires_in", 3600)
            _igdb_token_cache["token"]   = token
            _igdb_token_cache["expires"] = _t.time() + ttl - 60
            return token, None
    except _ureq.HTTPError as e:
        return None, f"HTTP {e.code}: credenciales Twitch inválidas"
    except Exception as e:
        return None, str(e)

def igdb_search_game(rom_filename, system_name, client_id, client_secret, clean_name=None):
    """Busca un juego en IGDB."""
    if not client_id or not client_secret:
        return None, "Faltan Client ID / Secret de Twitch para IGDB"
    token, err = igdb_get_token(client_id, client_secret)
    if not token:
        return None, err
    if not clean_name:
        clean_name = _clean_rom_name(rom_filename)
    platform_id = IGDB_PLATFORMS.get(system_name.lower())
    fields_str = "name,summary,rating,first_release_date,genres.name,involved_companies.company.name,cover.url,platforms"
    where_clause = f"where platforms = ({platform_id});" if platform_id else ""
    body = f'search "{clean_name}"; fields {fields_str}; {where_clause} limit 5;'
    try:
        req = _ureq.Request("https://api.igdb.com/v4/games",
                            data=body.encode(),
                            headers={
                                "Client-ID": client_id,
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "text/plain",
                            }, method="POST")
        with _ureq.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
            if not data:
                return None, "Sin resultados en IGDB"
            return data[0], None
    except _ureq.HTTPError as e:
        body_err = ""
        try: body_err = e.read().decode(errors="replace")[:150]
        except Exception: pass
        return None, f"HTTP {e.code}: {body_err or e.reason}"
    except Exception as e:
        return None, str(e)

def igdb_build_meta(game):
    """Extrae metadatos de la respuesta IGDB."""
    import datetime as _dt
    year = ""
    ts = game.get("first_release_date")
    if ts:
        try: year = str(_dt.datetime.fromtimestamp(ts, _dt.timezone.utc).year)
        except Exception: pass
    genres = game.get("genres", [])
    genre  = ", ".join(g.get("name","") for g in genres[:2]) if genres else ""
    companies = game.get("involved_companies", [])
    publisher = ""
    if companies:
        c = companies[0].get("company",{})
        publisher = c.get("name","") if isinstance(c, dict) else ""
    rating = game.get("rating","")
    try: rating_norm = str(round(float(rating)/100, 2)) if rating else ""
    except Exception: rating_norm = ""
    return {
        "name":      game.get("name",""),
        "desc":      game.get("summary",""),
        "genre":     genre,
        "year":      year,
        "publisher": publisher,
        "rating":    rating_norm,
    }

def igdb_get_image_url(game):
    """Construye la URL de imagen IGDB (cover art)."""
    cover = game.get("cover", {})
    url = cover.get("url","") if isinstance(cover, dict) else ""
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    # Reemplazar tamaño thumb por cover_big
    url = url.replace("t_thumb", "t_cover_big")
    return url

def _clean_rom_name(rom_filename):
    """Limpia el nombre de archivo ROM para búsqueda en cualquier API."""
    rom_stem = Path(rom_filename).stem
    clean = _re.sub(r"[([{][^)\]{}]*[)\]}]", "", rom_stem)
    clean = _re.sub(r"([a-z])([A-Z])",   r"\1 \2", clean)
    clean = _re.sub(r"([A-Za-z])([0-9])",r"\1 \2", clean)
    clean = _re.sub(r"([0-9])([A-Za-z])",r"\1 \2", clean)
    clean = clean.replace("_"," ").replace("-"," ").replace("."," ")
    return _re.sub(r"\s+", " ", clean).strip()

def download_image_generic(url, dest_path, referer_for=None):
    """Descarga cualquier imagen desde una URL y la guarda.
    referer_for: URL origen para enviar cabecera Referer (requerido por ScreenScraper)."""
    try:
        headers = {"User-Agent":"BatoceraManager/1.0"}
        if referer_for and "screenscraper" in str(referer_for):
            headers["Referer"] = "https://www.screenscraper.fr/gameinfos.php"
        req = _ureq.Request(url, headers=headers)
        with _ureq.urlopen(req, timeout=20) as r:
            data = r.read()
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return True, str(dest_path)
    except Exception as e:
        return False, str(e)

# ─── Scraper standalone helpers (reusable sync + background) ──────
def save_gamelist_entry(roms_base, meta):
    """Guarda una entrada completa en gamelist.xml incluyendo imagen.
    Soporta ROMs en subcarpetas (meta['subpath'])."""
    system   = meta.get("system","")
    filename = meta.get("filename","")
    subpath  = str(meta.get("subpath","") or "").strip("/")
    sys_dir  = Path(roms_base) / system
    gl_path  = sys_dir / "gamelist.xml"
    rom_relpath = f"{subpath}/{filename}" if subpath else filename
    if gl_path.exists():
        try: tree = ET.parse(gl_path); root = tree.getroot()
        except Exception: root = ET.Element("gameList")
    else:
        root = ET.Element("gameList")
    game = None
    for g in root.findall("game"):
        gpath = g.findtext("path","").lstrip("./")
        if gpath == rom_relpath or Path(gpath).name == filename:
            game = g; break
    if game is None:
        game = ET.SubElement(root,"game")
        ET.SubElement(game,"path").text = f"./{rom_relpath}"
    field_map = {
        "name":"name","desc":"desc","year":"releasedate",
        "publisher":"publisher","genre":"genre","rating":"rating",
        "image_path":"image",
    }
    for k, tag in field_map.items():
        val = meta.get(k,"")
        if val is None: val = ""
        if not val: continue
        if tag == "releasedate" and len(val) == 4:
            val = val + "0101T000000"
        el = game.find(tag)
        if el is None: el = ET.SubElement(game, tag)
        el.text = val
    ET.indent(root, space="    ")
    xml_out = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
    try:
        gl_path.write_text(xml_out, encoding="utf-8")
        invalidate_rom_cache()
    except Exception as e:
        log_message = f"Error guardando gamelist: {e}"
        print(f"  {log_message}")
        raise

def do_scrape_system(settings, system, source, creds, options, progress_cb=None):
    """Scrapea todos los ROMs de un sistema. Reusable desde sync y background."""
    import time as _t
    all_sys  = get_rom_systems(settings, fast=False)
    sys_data = next((x for x in all_sys if x["name"]==system), None)
    if not sys_data:
        return {"ok":0,"fail":0,"skip":0,"errors":[f"Sistema '{system}' no encontrado"],"total":0,"quota":{}}
    roms_base = Path(settings["roms_base"])
    sys_root  = roms_base / system
    only_missing = options.get("only_missing", True)
    img_type = options.get("ss_image_type","mixrbv1")
    region   = creds.get("ss_region","wor")
    lang     = creds.get("ss_lang","es")
    roms = [r for r in sys_data["roms"]
            if r["is_rom"] and r["ext"] not in ("dir",)
            and r["name"] not in ("images","media","videos","manuals")]
    if only_missing:
        roms = [r for r in roms if not r["has_image"]]
    results = {"ok":0,"fail":0,"skip":0,"errors":[],"total":len(roms),
               "quota":{},"meta_saved":0}
    for idx, rom in enumerate(roms):
        rom_stem = Path(rom["filename"]).stem
        rom_abspath = sys_root / rom["filename"]
        ok_img   = False
        meta     = {}
        err      = None
        if source == "thegamesdb":
            game, err = tgdb_search_game(rom["filename"], system, creds.get("tgdb_apikey",""))
            if game:
                meta = tgdb_build_meta(game, creds.get("tgdb_apikey",""))
                img_url, _ierr = tgdb_get_image(game.get("id"), creds.get("tgdb_apikey",""))
                if img_url:
                    dest, rel = batocera_media_path(sys_root, rom_stem, "image", ".jpg")
                    ok_img, _ = download_image_generic(img_url, dest)
                    if ok_img:
                        meta["image_path"] = rel
            _t.sleep(0.3)
        elif source == "igdb":
            game, err = igdb_search_game(rom["filename"], system,
                                         creds.get("igdb_client_id",""), creds.get("igdb_client_secret",""))
            if game:
                meta = igdb_build_meta(game)
                img_url = igdb_get_image_url(game)
                if img_url:
                    dest, rel = batocera_media_path(sys_root, rom_stem, "image", ".jpg")
                    ok_img, _ = download_image_generic(img_url, dest)
                    if ok_img:
                        meta["image_path"] = rel
            _t.sleep(0.3)
        else:  # screenscraper
            game, err, sq = ss_search_game(rom["filename"], system,
                                        creds.get("ss_user",""), creds.get("ss_password",""),
                                        region, lang, rom_path=str(rom_abspath),
                                        devid=creds.get("ss_devid",""),
                                        devpassword=creds.get("ss_devpassword",""))
            if game:
                meta = ss_build_meta(game, region, lang)
                url, ext = ss_media_url(game, img_type, region)
                if url:
                    dest, rel = batocera_media_path(sys_root, rom_stem, img_type, ext)
                    ok_img, _ = download_image_generic(url, dest, referer_for=url)
                    if ok_img:
                        meta["image_path"] = rel
            if sq:
                results["quota"] = sq
            if "429" in str(err) or "quota" in str(err or "").lower():
                _t.sleep(5)
            else:
                try:
                    maxthreads = int(sq.get("maxthreads", 1) or 1)
                    delay = max(1.0 / maxthreads, 0.5)
                except Exception:
                    delay = 1.0
                _t.sleep(delay)
        if not game:
            results["fail"] += 1
            results["errors"].append(f"{rom['name']}: {(err or 'Sin resultados')[:80]}")
            if progress_cb:
                progress_cb(system, rom["name"], idx+1, len(roms), results, err)
            continue
        meta.update({"system":system,"filename":rom["filename"]})
        save_gamelist_entry(settings["roms_base"], meta)
        results["meta_saved"] += 1
        if ok_img:
            results["ok"] += 1
        else:
            results["fail"] += 1
            results["errors"].append(f"{rom['name']} (sin imagen)")
        if progress_cb:
            progress_cb(system, rom["name"], idx+1, len(roms), results)
    return results

# ─── Scraper Batch Queue ────────────────────────────────────────────
import uuid as _uuid

_scraper_jobs = {}
_scraper_jobs_lock = threading.Lock()
_scraper_worker_thread = None
_scraper_start_lock    = threading.Lock()

def _start_batch_worker():
    """Garantiza un único worker de batch.

    La comprobación y el arranque van dentro del mismo lock: dos peticiones
    HTTP concurrentes podían ver el thread no vivo y lanzar dos workers
    (race condition clásica de "check-then-act").
    """
    global _scraper_worker_thread
    with _scraper_start_lock:
        if _scraper_worker_thread and _scraper_worker_thread.is_alive():
            return _scraper_worker_thread
        def worker():
            while True:
                job = None
                with _scraper_jobs_lock:
                    for j in _scraper_jobs.values():
                        if j["status"] == "pending":
                            j["status"] = "running"
                            job = j
                            break
                if job:
                    try:
                        _process_batch_job(job)
                    except Exception as e:
                        with _scraper_jobs_lock:
                            job["status"] = "failed"
                            job["error"] = str(e)
                else:
                    time.sleep(1)
        _scraper_worker_thread = threading.Thread(target=worker, daemon=True)
        _scraper_worker_thread.start()
        return _scraper_worker_thread

def _batch_progress(systems_done, total_systems, current, total):
    """Porcentaje global del lote.

    Combina los sistemas ya terminados con la fracción del sistema en curso,
    para que la barra avance ROM a ROM en vez de saltar de 0 a 100 al cerrar
    cada sistema. Se limita a 99 mientras queden sistemas: el 100 se reserva
    para "completado".
    """
    if total_systems <= 0:
        return 0
    frac = (current / total) if total else 0.0
    done = min(systems_done + frac, total_systems)
    return min(99, int(done / total_systems * 100))


def _partial_counts(partial):
    """Solo los contadores del sistema en curso (sin la lista de errores)."""
    if not partial:
        return {}
    return {"ok": partial.get("ok", 0), "fail": partial.get("fail", 0),
            "skip": partial.get("skip", 0)}


def _process_batch_job(job):
    def progress_cb(system, rom_name, current, total, partial, err=None):
        with _scraper_jobs_lock:
            job["current_system"] = system
            job["current_rom"] = rom_name
            job["progress_raw"] = [current, total]
            job["partial"] = _partial_counts(partial)
            job["systems_done"] = _sys_done
            job["progress"] = _batch_progress(_sys_done, total_systems, current, total)
    _sys_done = 0
    total_systems = len(job["systems"])
    for sys_name in job["systems"]:
        with _scraper_jobs_lock:
            if job["status"] == "cancelled":
                return
            job["current_system"] = sys_name
            job["current_rom"] = ""
            job["progress_raw"] = [0, 0]
            job["partial"] = {}
        # Credentials are already in job["creds"] with keys matching do_scrape_system
        result = do_scrape_system(job["settings"], sys_name, job["source"],
                                  job["creds"], job["options"], progress_cb)
        _sys_done += 1
        with _scraper_jobs_lock:
            job["systems_result"][sys_name] = result
            job["systems_done"] = _sys_done
            job["progress_raw"] = [0, 0]
            job["partial"] = {}
            if result["quota"]:
                job["quota"] = result["quota"]
            # Aggregate
            agg = job["aggregated"]
            agg["ok"] += result["ok"]
            agg["fail"] += result["fail"]
            agg["skip"] += result.get("skip",0)
            agg["total"] += result["total"]
            agg["meta_saved"] = agg.get("meta_saved", 0) + result.get("meta_saved", 0)
            agg["errors"].extend(result["errors"][:50])  # cap at 50 errors
            job["progress"] = _batch_progress(_sys_done, total_systems, 0, 0)
    with _scraper_jobs_lock:
        job["status"] = "completed"
        job["progress"] = 100
        meta_saved_total = job["aggregated"].get("meta_saved", 0)
    # ES mantiene las gamelists en memoria: recargarlo al terminar para que los
    # textos aparezcan en la TV. Fuera del lock: el reinicio puede tardar y no
    # debe bloquear el sondeo de progreso del front-end.
    if meta_saved_total > 0:
        es_reload = reload_es_after_scrape(True)
        with _scraper_jobs_lock:
            job["es_reload"] = es_reload

# ─── HTTP Handler ─────────────────────────────────────────────────

def _safe_api(fn):
    """Blinda un método HTTP para que nunca cierre la conexión sin respuesta.

    Sin esto, cualquier excepción no controlada aborta el handler y el
    navegador recibe una respuesta vacía (`net::ERR_EMPTY_RESPONSE`) sin pista
    del motivo. Ahora se devuelve un 500 en JSON y el traceback va a la consola.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception:
            traceback.print_exc()
            try:
                self.send_json({"ok": False, "error": "error interno del servidor"}, 500)
            except Exception:
                pass
    wrapper._safe_api = True
    wrapper.__name__ = getattr(fn, "__name__", "handler")
    return wrapper


class BatoceraHandler(http.server.BaseHTTPRequestHandler):

    def log_request(self, code='-', size='-'):
        # El dashboard hace polling cada pocos segundos (fans, ES, dashboard);
        # no queremos que cada petición correcta inunde la consola. Solo se
        # registran los errores (4xx/5xx) y las excepciones.
        try:
            status = int(code)
        except (ValueError, TypeError):
            status = 0
        if status >= 400 or status == 0:
            super().log_request(code, size)

    def log_message(self, format, *args):
        print(f"  {self.address_string()} — {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Connection","close")
        self.end_headers(); self.wfile.write(body)

    def send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Cache-Control","no-cache, no-store, must-revalidate")
        self.send_header("Pragma","no-cache")
        self.send_header("Expires","0")
        self.send_header("Content-Length",len(body))
        self.end_headers(); self.wfile.write(body)

    def read_body(self):
        n = parse_content_length(self.headers.get("Content-Length", 0))
        if n <= 0:
            return b""
        if n > MAX_BODY_BYTES:
            return b""   # rechazar cuerpos desmesurados (evita agotar memoria)
        return self.rfile.read(n)

    def read_json(self):
        return json.loads(self.read_body() or b"{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    @_safe_api
    def do_GET(self):
        path  = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        parts = [p for p in path.split("/") if p]
        s     = load_settings()
        if path == "/":
            self.send_html(render_index())
        elif path == "/api/info":
            self.send_json({"active_theme":detect_active_theme(s),
                "themes":list_themes(s),"systems_count":len(list_custom_systems(s)),
                "rom_systems_count":count_rom_systems(s),
                "ext_presets":EXT_PRESETS,"platform_ids":PLATFORM_IDS,
                "hardware_types":HARDWARE_TYPES,"has_pil":HAS_PIL})
        elif path == "/api/systems":
            self.send_json(list_custom_systems(s))
        elif path == "/api/batocera-systems":
            self.send_json({"ok":True,"count":len(_BATOCERA_SYSTEMS),"systems":_BATOCERA_SYSTEMS})
        elif path == "/api/themes":
            self.send_json({"active":detect_active_theme(s),"list":list_themes(s)})
        elif path == "/api/settings":
            self.send_json(s)
        elif len(parts)==3 and parts[:2]==["api","system"] and path.endswith("/xml"):
            name = parts[2]
            systems = list_custom_systems(s)
            t = next((x for x in systems if x["name"]==name),None)
            if t:
                try: self.send_json({"ok":True,"xml":Path(t["file"]).read_text()})
                except Exception as e: self.send_json({"ok":False,"error":str(e)})
            else: self.send_json({"ok":False,"error":"No encontrado"})
        # ROM monitor
        elif path == "/api/rom-systems":
            systems = get_rom_systems_cached(s)
            self.send_json([rom_system_summary(x) for x in systems])
        elif len(parts)==3 and parts[:2]==["api","rom-systems"]:
            name = urllib.parse.unquote(parts[2])
            # Detalle: escanear solo ese sistema con gamelist completa
            roms_base = Path(s["roms_base"]) / name
            if not roms_base.exists():
                self.send_json({"ok":False,"error":"No encontrado"}); return
            # Reusar get_rom_systems filtrando
            all_sys = get_rom_systems(s, fast=False)
            t = next((x for x in all_sys if x["name"]==name), None)
            if t: self.send_json({"ok":True,"system":t})
            else: self.send_json({"ok":False,"error":"No encontrado"})
        elif len(parts)==4 and parts[:2]==["api","system"] and parts[3]=="detail":
            name = parts[2]
            det = get_custom_system_detail(name, s)
            if det: self.send_json({"ok":True,"system":det})
            else: self.send_json({"ok":False,"error":"No encontrado"})
        elif len(parts)==4 and parts[:2]==["api","rom-systems"] and parts[3]=="bios":
            name = urllib.parse.unquote(parts[2])
            self.send_json({"ok":True,"system":name,
                "bios":check_bios(name, s.get("bios_dir","/userdata/bios"))})
        elif len(parts)>=3 and parts[:2]==["api","rom-folder"]:
            name = urllib.parse.unquote(parts[2])
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            subpath = urllib.parse.unquote(query.get("path",[""])[0])
            folder = list_rom_folder(s, name, subpath)
            if folder is None:
                self.send_json({"ok":False,"error":"Carpeta no encontrada o acceso inválido"})
            else:
                self.send_json({"ok":True,"folder":folder})
        elif path == "/api/dashboard":
            self.send_json(get_dashboard())
        elif path == "/api/game-stats":
            self.send_json(collect_play_stats(s["roms_base"]))
        elif path == "/api/random-game":
            self.send_json({"ok": True, "game": pick_random_game(s["roms_base"])})
        elif path == "/api/retroachievements":
            self.send_json(get_retroachievements(s))
        elif path == "/api/retroachievements/test":
            self.send_json(ra_test(s))
        elif path == "/api/es/status":
            self.send_json(get_es_status())
        elif path == "/api/fans":
            self.send_json({"ok": True, "ts": time.time(), "fans": get_fans()})
        elif path == "/api/news":
            self.send_json({"ok": True, "ts": time.time(), "news": get_news()})
        elif path == "/api/rom-image-info":
            # Devuelve qué imágenes disponibles tiene un ROM
            if len(parts) >= 4:
                sys_name = urllib.parse.unquote(parts[2])
                rom_fn   = urllib.parse.unquote("/".join(parts[3:]))
                roms_base= Path(s["roms_base"]) / sys_name
                rom_stem = Path(rom_fn).stem
                found = []
                bato_suffixes = ["-image","-thumb","-box","-wheel","-marquee","-fanart",
                                 "-boxback","-titleshot","-map","-cartridge","-bezel"]
                for mdir in ["images","named_boxarts","named_logos","screenshots",
                             "wheels","marquees","boxart","fanart","mixrbv1","mixrbv2"]:
                    for ext in [".png",".jpg",".jpeg",".webp"]:
                        p = roms_base / "media" / mdir / (rom_stem + ext)
                        if p.exists():
                            found.append({"dir":mdir,"file":p.name,"size":human_size(p.stat().st_size)})
                        for suf in bato_suffixes:
                            p = roms_base / mdir / (rom_stem + suf + ext)
                            if p.exists():
                                found.append({"dir":mdir,"file":p.name,"size":human_size(p.stat().st_size)})
                self.send_json({"ok":True,"images":found,"rom":rom_fn})
            else:
                self.send_json({"ok":False,"error":"Faltan parámetros"})
        elif path == "/api/scraper/config":
            self.send_json(get_scraper_config(s))
        elif path == "/api/scraper/batch":
            self._scraper_batch_list(s)
        elif len(parts)==4 and parts[:3]==["api","scraper","batch"]:
            self._scraper_batch_detail(parts[3], s)
        elif path == "/api/bios/all":
            bios_dir = Path(s.get("bios_dir","/userdata/bios"))
            all_systems = {}
            for slug in sorted(_BIOS_LOOKUP.keys()):
                info = _check_bios_grouped(slug, bios_dir)
                if info is not None:
                    all_systems[slug] = info
            self.send_json({"ok":True,"systems":all_systems})
        elif path == "/api/bios/missing":
            bios_dir = Path(s.get("bios_dir","/userdata/bios"))
            user_systems = get_rom_systems_cached(s)
            items = collect_missing_bios(user_systems, bios_dir)
            total = len(items)
            systems = {}
            for it in items:
                systems.setdefault(it["system"], []).append(it)
            self.send_json({"ok":True,"total_missing":total,"items":items,"systems":systems})
        elif path == "/api/service/read-sh":
            try:
                txt = CUSTOM_SH.read_text(errors="replace") if CUSTOM_SH.exists() else "(no existe)"
                self.send_json({"ok":True,"content":txt})
            except Exception as e:
                self.send_json({"ok":False,"error":str(e)})
        elif path == "/api/service/status":
            s2 = load_settings()
            self.send_json({
                "autostart":  get_autostart_status(s2),
                "process":    get_process_status(),
                "custom_sh":  str(CUSTOM_SH),
                "exists":     CUSTOM_SH.exists(),
                "cmd_current": get_service_cmd(s2),
            })
        elif path == "/favicon.ico":
            self.send_response(204); self.end_headers()
        elif len(parts)==3 and parts[:2]==["api","system-logo"]:
            system = urllib.parse.unquote(parts[2])
            self._serve_system_logo(system, s)
        elif len(parts)==4 and parts[:2]==["api","rom-image"]:
            system   = urllib.parse.unquote(parts[2])
            filename = urllib.parse.unquote(parts[3])
            self._serve_rom_image(system, filename, s)
        else:
            self.send_json({"error":"Not found"},404)

    @_safe_api
    def do_POST(self):
        path  = urllib.parse.urlparse(self.path).path.rstrip("/")
        parts = [p for p in path.split("/") if p]
        s     = load_settings()
        if path == "/api/preview":
            d = self.read_json()
            try: self.send_json({"ok":True,"xml":build_xml(d,s)})
            except Exception as e: self.send_json({"ok":False,"error":str(e)})
        elif path == "/api/create":
            self._create_system(s)
        elif path == "/api/update":
            self._update_system(s)
        elif path == "/api/settings":
            data = self.read_json()
            current = load_settings()
            current.update({k:v for k,v in data.items() if k in DEFAULT_SETTINGS})
            save_settings_to_file(current)
            if any(k.startswith("ra_") for k in data):
                _ra_cache.update({"ts": 0, "data": None, "user": ""})
            self.send_json({"ok":True})
        elif path == "/api/es/restart":
            ok, info = restart_emulationstation()
            self.send_json({"ok": ok, **info})
        elif path == "/api/upload-logo":
            self._upload_logo(s)
        elif len(parts)==4 and parts[:2]==["api","rom-systems"] and parts[3]=="upload":
            system = urllib.parse.unquote(parts[2])
            self._upload_rom(system, s)
        elif path == "/api/bios/upload":
            self._upload_bios(s)
        elif path == "/api/bios/fetch":
            d = self.read_json()
            fname  = (d.get("file") or "").strip()
            url    = (d.get("url") or "").strip()
            system = (d.get("system") or "").strip()
            if not fname or not url:
                self.send_json({"ok": False, "error": "Faltan 'file' o 'url'"}); return
            expected = [b["md5"] for b in _get_bios_entries(system)
                        if b.get("file") == fname and b.get("md5")]
            result = download_bios_from_url(
                s.get("bios_dir", "/userdata/bios"), fname, url, expected)
            self.send_json(result)
        elif path == "/api/bios/missing/skip":
            d = self.read_json()
            key = d.get("skip_key","")
            if key:
                set_bios_skipped(key)
            self.send_json({"ok":True, "skipped": sorted(_missing_bios_skipped)})
        elif path == "/api/bios/missing/unskip":
            d = self.read_json()
            key = d.get("skip_key","")
            if key:
                unset_bios_skipped(key)
            self.send_json({"ok":True, "skipped": sorted(_missing_bios_skipped)})
        elif path == "/api/bios/missing/skipped":
            self.send_json({"ok":True, "skipped": sorted(_missing_bios_skipped)})
        elif path == "/api/rom/rename":
            self._rename_rom(s)
        elif path == "/api/service/install":
            d   = self.read_json()
            cmd = d.get("cmd", "").strip() or get_service_cmd(load_settings())
            try:
                install_autostart(cmd)
                self.send_json({"ok":True, "cmd":cmd, "file":str(CUSTOM_SH)})
            except Exception as e:
                self.send_json({"ok":False,"error":str(e)})
        elif path == "/api/service/remove":
            ok = remove_autostart()
            self.send_json({"ok":True,"removed":ok})
        elif path == "/api/service/kill":
            ok = kill_service()
            self.send_json({"ok":True,"killed":ok})
        elif path == "/api/service/restart":
            import subprocess as _sp
            kill_service()
            import time as _time; _time.sleep(1)
            d    = self.read_json()
            cmd  = d.get("cmd", get_service_cmd(load_settings()))
            try:
                _sp.Popen(shlex.split(cmd), close_fds=True)
                self.send_json({"ok":True, "cmd":cmd})
            except Exception as e:
                self.send_json({"ok":False,"error":str(e)})
        elif path == "/api/rom/update-meta":
            self._update_rom_meta(s)
        elif path == "/api/scraper/search":
            self._scraper_search(s)
        elif path == "/api/scraper/download":
            self._scraper_download(s)
        elif path == "/api/scraper/scrape-system":
            self._scraper_system(s)
        elif path == "/api/scraper/save-config":
            self._scraper_save_config(s)
        elif path == "/api/scraper/batch":
            self._scraper_batch_create(s)
        else:
            self.send_json({"error":"Not found"},404)

    @_safe_api
    def do_DELETE(self):
        path  = urllib.parse.urlparse(self.path).path.rstrip("/")
        parts = [p for p in path.split("/") if p]
        s     = load_settings()
        if len(parts)==3 and parts[:2]==["api","system"]:
            name = urllib.parse.unquote(parts[2])
            ok, info = delete_custom_system(name, s)
            self.send_json({"ok": ok, **info})
        elif len(parts)>=3 and parts[:2]==["api","rom"]:
            system   = parts[2]
            filename = urllib.parse.unquote("/".join(parts[3:])) if len(parts)>3 else ""
            if not filename:
                self.send_json({"ok":False,"error":"Falta filename"}); return
            base = Path(s["roms_base"]).resolve()
            target = (base / system / filename).resolve()
            try:
                target.relative_to(base / system)
            except ValueError:
                self.send_json({"ok":False,"error":"Acceso denegado"}); return
            if not target.exists():
                self.send_json({"ok":False,"error":"No encontrado"}); return
            try:
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                self.send_json({"ok":True})
            except Exception as e: self.send_json({"ok":False,"error":str(e)})
        elif len(parts)==4 and parts[:3]==["api","scraper","batch"]:
            self._scraper_batch_cancel(parts[3], s)
        else:
            self.send_json({"error":"Not found"},404)

    # ── Métodos internos ──────────────────────────────────────────
    def _create_system(self, s):
        d    = self.read_json()
        log  = []
        slug = (d.get("name") or "").strip()
        errors = []
        if not d.get("fullname","").strip():   errors.append("Nombre completo requerido")
        if not slug:                           errors.append("Slug requerido")
        elif not is_safe_component(slug):      errors.append("Slug inválido (sin espacios ni separadores)")
        if not d.get("rompath","").strip():    errors.append("Ruta de ROMs requerida")
        if not d.get("extensions","").strip(): errors.append("Extensiones requeridas")
        if errors:
            self.send_json({"ok":False,"errors":errors}); return
        dry      = bool(d.get("dry_run"))
        cfg_dir  = s["es_cfg_dir"]
        cfg_path = os.path.join(cfg_dir, f"es_systems_{slug}.cfg")
        xml_str  = build_xml(d, s)
        if dry:
            log.append(f"[SIMULACIÓN] CFG se escribiría en: {cfg_path}")
            log.append("[SIMULACIÓN] No se modificó ningún archivo.")
        else:
            try:
                os.makedirs(cfg_dir, exist_ok=True)
                with open(cfg_path,"w",encoding="utf-8") as f: f.write(xml_str)
                mark_es_restart_pending()
                invalidate_system_meta()
                log.append(f"✔ CFG escrito: {cfg_path}")
            except Exception as e:
                self.send_json({"ok":False,"errors":[str(e)]}); return
            if d.get("create_roms_dir"):
                try:
                    os.makedirs(confine_to_base(s["roms_base"], d.get("rompath","").strip()), exist_ok=True)
                    log.append("✔ Dir ROMs creado")
                except ValueError: log.append("⚠ Ruta de ROMs fuera de la base permitida; no se creó")
                except Exception as e: log.append(f"⚠ {e}")
            if d.get("batocera_conf_entry") and d.get("emulator") and d.get("core"):
                try:
                    emu     = sanitize_conf_value(d.get("emulator"))
                    core    = sanitize_conf_value(d.get("core"))
                    comment = sanitize_comment_text(d.get("fullname",""))
                    with open(s["batocera_conf"],"a",encoding="utf-8") as f:
                        f.write(f"\n# {comment}\n{slug}.emulator={emu}\n{slug}.core={core}\n")
                    log.append("✔ batocera.conf actualizado")
                except ValueError as e: log.append(f"⚠ Valor inválido para batocera.conf: {e}")
                except Exception as e: log.append(f"⚠ {e}")
        log.append(f"\n✅ Sistema '{slug}' {'simulado' if dry else 'creado'}.")
        if not dry: log.append("   Reinicia EmulationStation para que aparezca.")
        self.send_json({"ok":True,"log":log,"xml":xml_str,"cfg_path":cfg_path})

    def _update_system(self, s):
        d    = self.read_json()
        old  = (d.get("old_name") or "").strip()
        slug = (d.get("name") or "").strip()
        log  = []
        errors = []
        if not d.get("fullname","").strip():   errors.append("Nombre completo requerido")
        if not old:                            errors.append("Sistema original requerido")
        if not slug:                           errors.append("Slug requerido")
        elif not is_safe_component(slug):      errors.append("Slug inválido (sin espacios ni separadores)")
        if old and not is_safe_component(old): errors.append("Sistema original inválido")
        if not d.get("rompath","").strip():    errors.append("Ruta de ROMs requerida")
        if not d.get("extensions","").strip(): errors.append("Extensiones requeridas")
        if errors:
            self.send_json({"ok":False,"errors":errors}); return
        cfg_dir  = s["es_cfg_dir"]
        old_cfg  = os.path.join(cfg_dir, f"es_systems_{old}.cfg")
        new_cfg  = os.path.join(cfg_dir, f"es_systems_{slug}.cfg")
        if old != slug and os.path.exists(new_cfg):
            self.send_json({"ok":False,"errors":[f"El slug '{slug}' ya existe"]}); return
        xml_str = build_xml(d, s)
        dry = bool(d.get("dry_run"))
        if dry:
            log.append(f"[SIMULACIÓN] CFG se {'crearía' if old!=slug else 'reescribiría'} en: {new_cfg}")
            if old != slug: log.append(f"[SIMULACIÓN] Se eliminaría: {old_cfg}")
            log.append("[SIMULACIÓN] No se modificó ningún archivo.")
        else:
            try:
                os.makedirs(cfg_dir, exist_ok=True)
                with open(new_cfg, "w", encoding="utf-8") as f: f.write(xml_str)
                mark_es_restart_pending()
                log.append(f"✔ CFG escrito: {new_cfg}")
                if old != slug and os.path.exists(old_cfg):
                    os.remove(old_cfg)
                    log.append(f"✔ CFG antiguo eliminado: {old_cfg}")
            except Exception as e:
                self.send_json({"ok":False,"errors":[str(e)]}); return
            if d.get("create_roms_dir"):
                try:
                    os.makedirs(confine_to_base(s["roms_base"], d.get("rompath","").strip()), exist_ok=True)
                    log.append("✔ Dir ROMs creado")
                except ValueError: log.append("⚠ Ruta de ROMs fuera de la base permitida; no se creó")
                except Exception as e: log.append(f"⚠ {e}")
            if d.get("batocera_conf_entry") and d.get("emulator") and d.get("core"):
                try:
                    emu     = sanitize_conf_value(d.get("emulator"))
                    core    = sanitize_conf_value(d.get("core"))
                    comment = sanitize_comment_text(d.get("fullname",""))
                    with open(s["batocera_conf"],"a",encoding="utf-8") as f:
                        f.write(f"\n# {comment}\n{slug}.emulator={emu}\n{slug}.core={core}\n")
                    log.append("✔ batocera.conf actualizado")
                except ValueError as e: log.append(f"⚠ Valor inválido para batocera.conf: {e}")
                except Exception as e: log.append(f"⚠ {e}")
        log.append(f"\n✅ Sistema '{slug}' {'simulado' if dry else 'actualizado'}.")
        if not dry: log.append("   Reinicia EmulationStation para que los cambios tengan efecto.")
        self.send_json({"ok":True,"log":log,"xml":xml_str,"cfg_path":new_cfg})

    def _upload_logo(self, s):
        body = self.read_body()
        ct   = self.headers.get("Content-Type","")
        if "application/json" in ct:
            d    = json.loads(body or b"{}")
            slug = (d.get("slug") or "").strip()
            if not is_safe_component(slug):
                self.send_json({"ok":False,"error":"Slug inválido"}); return
            if not HAS_PIL:
                self.send_json({"ok":False,"error":"PIL no disponible"}); return
            try:
                dest_file = safe_path_under(s["themes_user"], detect_active_theme(s), slug, "art", "logo.png")
            except ValueError:
                self.send_json({"ok":False,"error":"Ruta inválida"}); return
            try:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_bytes(make_placeholder_png(slug.upper()))
                self.send_json({"ok":True,"path":str(dest_file),"placeholder":True})
            except Exception as e: self.send_json({"ok":False,"error":str(e)})
            return
        fields, files = parse_multipart({"CONTENT_TYPE":ct}, body)
        slug  = (fields.get("slug") or "").strip()
        if not is_safe_component(slug):
            self.send_json({"ok":False,"error":"Slug inválido"}); return
        try:
            dest_file = safe_path_under(s["themes_user"], detect_active_theme(s), slug, "art", "logo.png")
        except ValueError:
            self.send_json({"ok":False,"error":"Ruta inválida"}); return
        if "logo" not in files:
            self.send_json({"ok":False,"error":"No se recibió archivo"}); return
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            img_data = files["logo"]["data"]
            if HAS_PIL:
                img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                img.save(str(dest_file),"PNG")
            else: dest_file.write_bytes(img_data)
            self.send_json({"ok":True,"path":str(dest_file)})
        except Exception as e: self.send_json({"ok":False,"error":str(e)})

    def _upload_rom(self, system, s):
        body = self.read_body()
        ct   = self.headers.get("Content-Type","")
        fields, files = parse_multipart({"CONTENT_TYPE":ct}, body)
        if not files:
            self.send_json({"ok":False,"error":"No se recibió archivo"}); return
        subpath  = fields.get("subpath","").strip().strip("/")
        try:
            roms_base = system_dir(s, system)
            dest_dir  = safe_path_under(roms_base, subpath) if subpath else roms_base
        except ValueError:
            self.send_json({"ok":False,"error":"Ruta inválida"}); return
        # Validar extensiones soportadas por el sistema (si las conocemos)
        allowed = get_system_extensions(system, s)
        rejected = []
        if allowed:
            kept = {}
            for k, fdata in files.items():
                ext = Path(fdata["filename"]).suffix.lower()
                if ext in allowed:
                    kept[k] = fdata
                else:
                    rejected.append({"file":fdata["filename"],
                                     "error":f"Extensión no permitida para {system} (permitidas: {', '.join(sorted(allowed))})"})
            files = kept
        if rejected:
            self.send_json({"ok":False,"error":"Archivos rechazados","rejected":rejected}); return
        # Validar nombres de archivo (sin separadores ni "..")
        bad = [f["filename"] for f in files.values() if not is_safe_component(f["filename"])]
        if bad:
            self.send_json({"ok":False,"error":"Nombre de archivo inválido",
                            "rejected":[{"file":b,"error":"nombre inseguro"} for b in bad]}); return
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for fdata in files.values():
            dest = dest_dir / fdata["filename"]
            dest.write_bytes(fdata["data"])
            saved.append({"file":fdata["filename"],"size":human_size(len(fdata["data"]))})
        invalidate_rom_cache()
        self.send_json({"ok":True,"saved":saved})

    def _upload_bios(self, s):
        body = self.read_body()
        ct   = self.headers.get("Content-Type","")
        fields, files = parse_multipart({"CONTENT_TYPE":ct}, body)
        if not files:
            self.send_json({"ok":False,"error":"No se recibió archivo"}); return
        bios_dir = Path(s.get("bios_dir","/userdata/bios"))
        target_system = fields.get("system","").strip()
        target_file   = fields.get("file","").strip()
        bios_dir.mkdir(parents=True, exist_ok=True)
        # La referencia 'file' de la BD incluye subcarpetas (neocd/neocd_f.rom...)
        # → se respeta para dejar el BIOS donde Batocera lo espera.
        if target_file:
            try:
                safe_path_under(bios_dir, target_file)
            except ValueError:
                self.send_json({"ok":False,"error":"Ruta BIOS inválida"}); return
        saved = []
        for fdata in files.values():
            if target_file:
                dest = bios_dir / target_file
            else:
                if not is_safe_component(fdata["filename"]):
                    self.send_json({"ok":False,"error":"Nombre de archivo inválido"}); return
                dest = bios_dir / fdata["filename"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(fdata["data"])
            md5_val = hashlib.md5(fdata["data"]).hexdigest()
            entry = {"file":fdata["filename"],
                "dest":str(dest),
                "size":human_size(len(fdata["data"])),
                "md5":md5_val}
            # Validate MD5 if system + file were provided
            if target_system and target_file:
                valid_md5s = []
                raw = _get_bios_entries(target_system)
                for b in raw:
                    if b["file"] == target_file and b.get("md5"):
                        valid_md5s.append(b["md5"])
                if valid_md5s:
                    entry["md5_valid"] = md5_val in valid_md5s
                    entry["valid_md5s"] = valid_md5s
                else:
                    entry["md5_valid"] = None  # no reference to compare
            saved.append(entry)
        self.send_json({"ok":True,"saved":saved})

    def _rename_rom(self, s):
        d = self.read_json()
        system   = d.get("system","")
        subpath  = d.get("subpath","").strip().strip("/")
        old_name = d.get("old_name","")
        new_name = d.get("new_name","").strip()
        if not all([system, old_name, new_name]):
            self.send_json({"ok":False,"error":"Faltan parámetros"}); return
        if not (is_safe_component(old_name) and is_safe_component(new_name)):
            self.send_json({"ok":False,"error":"Nombre inválido"}); return
        try:
            roms_base = system_dir(s, system)
            base_dir  = safe_path_under(roms_base, subpath) if subpath else roms_base
        except ValueError:
            self.send_json({"ok":False,"error":"Ruta inválida"}); return
        src  = base_dir / old_name
        dest = base_dir / new_name
        if not src.exists():
            self.send_json({"ok":False,"error":"Archivo no encontrado"}); return
        if dest.exists():
            self.send_json({"ok":False,"error":"Ya existe ese nombre"}); return
        try: src.rename(dest); invalidate_rom_cache(); self.send_json({"ok":True})
        except Exception as e: self.send_json({"ok":False,"error":str(e)})



    def _scraper_search(self, s):
        """Busca un juego usando la fuente seleccionada (ScreenScraper/TGDB/IGDB)."""
        d        = self.read_json()
        filename = d.get("filename","")
        system   = d.get("system","")
        subpath  = d.get("subpath","").strip().strip("/")
        source   = d.get("source", "screenscraper")
        cfg      = resolve_scraper_creds(s, d)

        if source == "thegamesdb":
            game, err = tgdb_search_game(filename, system, cfg.get("tgdb_apikey",""))
            if game:
                meta = tgdb_build_meta(game, cfg.get("tgdb_apikey",""))
                self.send_json({"ok":True,"game":game,"meta":meta,
                               "img_types":["boxart"],"cfg":cfg,"source":"thegamesdb"})
            else:
                self.send_json({"ok":False,"error":err or "Sin resultados"})

        elif source == "igdb":
            game, err = igdb_search_game(filename, system,
                                        cfg.get("igdb_client_id",""),
                                        cfg.get("igdb_client_secret",""))
            if game:
                meta = igdb_build_meta(game)
                self.send_json({"ok":True,"game":game,"meta":meta,
                               "img_types":["cover"],"cfg":cfg,"source":"igdb"})
            else:
                self.send_json({"ok":False,"error":err or "Sin resultados"})

        else:  # screenscraper (default)
            rom_path = None
            try:
                p = Path(s["roms_base"]) / system
                if subpath: p = p / subpath
                rom_path = str(p / filename)
            except Exception:
                rom_path = None
            game, err, quota = ss_search_game(filename, system,
                                       cfg["ss_user"], cfg["ss_password"],
                                       cfg["ss_region"], cfg["ss_lang"],
                                       rom_path=rom_path,
                                       devid=cfg.get("ss_devid",""),
                                       devpassword=cfg.get("ss_devpassword",""))
            if game:
                meta    = ss_build_meta(game, cfg["ss_region"], cfg["ss_lang"])
                medias  = game.get("medias",[])
                img_types = list({m.get("type","") for m in medias
                                 if m.get("type","") in
                                 ("mixrbv1","mixrbv2","ss","box-2D","wheel","fanart","screenshot")})
                self.send_json({"ok":True,"game":game,"meta":meta,
                               "img_types":img_types,"cfg":cfg,"source":"screenscraper",
                               "quota":quota})
            else:
                self.send_json({"ok":False,"error":err or "Sin resultados","quota":quota})

    def _scraper_download(self, s):
        """Descarga imagen y/o metadatos del juego para un ROM (fuente seleccionable)."""
        d        = self.read_json()
        system   = d.get("system","")
        subpath  = d.get("subpath","").strip().strip("/")
        filename = d.get("filename","")
        game     = d.get("game",{})
        source   = d.get("source", "screenscraper")
        cfg      = resolve_scraper_creds(s, d)

        results   = {"images":[],"meta":False,"errors":[]}
        if not (is_safe_component(system) and is_safe_component(filename)):
            self.send_json({"ok":False,"error":"Nombre inválido"}); return
        try:
            sys_root  = system_dir(s, system)
        except ValueError:
            self.send_json({"ok":False,"error":"Ruta inválida"}); return
        rom_stem  = Path(filename).stem
        image_rel = None

        if source == "thegamesdb":
            game_id = game.get("id")
            img_url, err = tgdb_get_image(game_id, cfg.get("tgdb_apikey","")) if game_id else (None,"Sin ID de juego")
            if img_url:
                dest, rel = batocera_media_path(sys_root, rom_stem, "image", ".jpg")
                ok, msg = download_image_generic(img_url, dest)
                if ok:
                    results["images"].append({"type":"boxart","path":str(dest)})
                    image_rel = rel
                else:  results["errors"].append(f"Imagen: {msg}")
            else:
                results["errors"].append(f"Imagen: {err}")
            if d.get("save_meta", True):
                meta = tgdb_build_meta(game, cfg.get("tgdb_apikey",""))
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if image_rel:
                    meta["image_path"] = image_rel
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        elif source == "igdb":
            img_url = igdb_get_image_url(game)
            if img_url:
                dest, rel = batocera_media_path(sys_root, rom_stem, "image", ".jpg")
                ok, msg = download_image_generic(img_url, dest)
                if ok:
                    results["images"].append({"type":"cover","path":str(dest)})
                    image_rel = rel
                else:  results["errors"].append(f"Imagen: {msg}")
            else:
                results["errors"].append("Sin imagen de portada en IGDB")
            if d.get("save_meta", True):
                meta = igdb_build_meta(game)
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if image_rel:
                    meta["image_path"] = image_rel
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        else:  # screenscraper
            img_types = d.get("img_types", [cfg.get("ss_image_type","mixrbv1")])
            if isinstance(img_types, str): img_types = [img_types]
            for itype in img_types:
                url, ext = ss_media_url(game, itype, cfg.get("ss_region","wor"))
                if not url:
                    results["errors"].append(f"Imagen {itype}: sin disponibilidad en ScreenScraper")
                    continue
                dest, rel = batocera_media_path(sys_root, rom_stem, itype, ext or ".png")
                ok, msg = download_image_generic(url, dest, referer_for=url)
                if ok:
                    results["images"].append({"type":itype,"path":str(dest)})
                    if is_gamelist_image_type(itype) and image_rel is None:
                        image_rel = rel
                else:
                    results["errors"].append(f"Imagen {itype}: {msg}")
            if d.get("save_meta", True) and game:
                meta = ss_build_meta(game, cfg["ss_region"], cfg["ss_lang"])
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if image_rel:
                    meta["image_path"] = image_rel
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        # ES lee las gamelists al arrancar: recargarlo para que el texto
        # recién guardado se vea en la TV.
        results["es_reload"] = reload_es_after_scrape(bool(results.get("meta")))
        self.send_json({"ok":True,"results":results})

    def _save_gamelist_entry(self, s, meta):
        save_gamelist_entry(s["roms_base"], meta)

    def _scraper_system(self, s):
        d = self.read_json()
        system = d.get("system","")
        source = d.get("source", "screenscraper")
        cfg = resolve_scraper_creds(s, d)
        if source == "thegamesdb" and not cfg.get("tgdb_apikey"):
            self.send_json({"ok":False,"error":"Configura tu API Key de TheGamesDB"}); return
        if source == "igdb" and not (cfg.get("igdb_client_id") and cfg.get("igdb_client_secret")):
            self.send_json({"ok":False,"error":"Configura Client ID y Secret de IGDB (Twitch)"}); return
        if source == "screenscraper" and not (cfg.get("ss_user") and cfg.get("ss_password")):
            self.send_json({"ok":False,"error":"Configura usuario y contraseña de ScreenScraper"}); return
        results = do_scrape_system(s, system, source, cfg, d)
        results["es_reload"] = reload_es_after_scrape(results.get("meta_saved", 0) > 0)
        self.send_json({"ok":True,"results":results})


    def _scraper_save_config(self, s):
        """Guarda credenciales de ScreenScraper en batocera.conf."""
        d     = self.read_json()
        lines = d.get("lines", [])  # [{key, val}, ...]
        conf  = Path(s.get("batocera_conf","/userdata/system/batocera.conf"))
        ok, err = save_scraper_config(conf, lines)
        if ok:
            self.send_json({"ok":True})
        else:
            self.send_json({"ok":False,"error":err})

    # ── Scraper batch ─────────────────────────────────────────────
    def _scraper_batch_create(self, s):
        d = self.read_json()
        systems = d.get("systems", [])
        if not systems:
            self.send_json({"ok":False,"error":"Selecciona al menos un sistema"}); return
        source = d.get("source", "screenscraper")
        creds = resolve_scraper_creds(s, d)
        # Validate
        if source == "thegamesdb" and not creds.get("tgdb_apikey"):
            self.send_json({"ok":False,"error":"Configura tu API Key de TheGamesDB"}); return
        if source == "igdb" and not (creds.get("igdb_client_id") and creds.get("igdb_client_secret")):
            self.send_json({"ok":False,"error":"Configura Client ID y Secret de IGDB"}); return
        if source == "screenscraper" and not (creds.get("ss_user") and creds.get("ss_password")):
            self.send_json({"ok":False,"error":"Configura usuario y contraseña de ScreenScraper"}); return
        job_id = str(_uuid.uuid4())[:8]
        job = {
            "id": job_id,
            "systems": systems,
            "source": source,
            "creds": creds,
            "options": {k:v for k,v in d.items() if k in ("only_missing","ss_image_type","ss_region","ss_lang")},
            "settings": s,
            "status": "pending",
            "progress": 0,
            "current_system": "",
            "current_rom": "",
            "progress_raw": [0, 0],
            "partial": {},
            "systems_done": 0,
            "systems_result": {},
            "aggregated": {"ok":0,"fail":0,"skip":0,"total":0,"errors":[],
                           "meta_saved":0},
            "quota": {},
            "created_at": time.time(),
            "error": None,
        }
        with _scraper_jobs_lock:
            _scraper_jobs[job_id] = job
        _start_batch_worker()
        self.send_json({"ok":True,"job_id":job_id})

    def _scraper_batch_list(self, s):
        with _scraper_jobs_lock:
            jobs = []
            for jid, j in sorted(_scraper_jobs.items(),
                                 key=lambda x: x[1].get("created_at",0), reverse=True):
                jobs.append({
                    "id": j["id"],
                    "systems": j["systems"],
                    "source": j["source"],
                    "status": j["status"],
                    "progress": j["progress"],
                    "current_system": j["current_system"],
                    "current_rom": j["current_rom"],
                    "progress_raw": j.get("progress_raw", [0, 0]),
                    "partial": j.get("partial", {}),
                    "systems_done": j["systems_done"],
                    "aggregated": j["aggregated"],
                    "created_at": j["created_at"],
                    "error": j.get("error"),
                    "es_reload": j.get("es_reload"),
                })
        self.send_json({"ok":True,"jobs":jobs})

    def _scraper_batch_detail(self, job_id, s):
        with _scraper_jobs_lock:
            j = _scraper_jobs.get(job_id)
            if not j:
                self.send_json({"ok":False,"error":"Job no encontrado"}); return
            detail = {
                "id": j["id"],
                "systems": j["systems"],
                "source": j["source"],
                "status": j["status"],
                "progress": j["progress"],
                "current_system": j["current_system"],
                "current_rom": j["current_rom"],
                "progress_raw": j.get("progress_raw", [0, 0]),
                "partial": j.get("partial", {}),
                "systems_done": j["systems_done"],
                "systems_result": j["systems_result"],
                "aggregated": j["aggregated"],
                "quota": j["quota"],
                "created_at": j["created_at"],
                "error": j.get("error"),
                "options": j["options"],
                "es_reload": j.get("es_reload"),
            }
        self.send_json({"ok":True,"job":detail})

    def _scraper_batch_cancel(self, job_id, s):
        with _scraper_jobs_lock:
            j = _scraper_jobs.get(job_id)
            if not j:
                self.send_json({"ok":False,"error":"Job no encontrado"}); return
            if j["status"] in ("pending","running"):
                j["status"] = "cancelled"
        self.send_json({"ok":True})

    def _serve_rom_image(self, system, rom_filename, s):
        """Sirve imagen de un ROM leyendo la ruta real del gamelist.xml.
        Soporta ROMs dentro de subcarpetas via ?subpath=CPS1 en la query string.
        """
        query   = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        subpath = urllib.parse.unquote(query.get("subpath",[""])[0]).strip("/")
        try:
            roms_base = system_dir(s, system)
            base_dir  = safe_path_under(roms_base, subpath) if subpath else roms_base
        except ValueError:
            self.send_json({"error":"Acceso denegado"},403)
            return
        rom_stem  = Path(rom_filename).stem
        # Path relativo completo del ROM dentro del sistema (para matchear gamelist)
        rom_relpath = f"{subpath}/{rom_filename}" if subpath else rom_filename
        candidates = []

        # 1. Leer ruta real desde gamelist.xml (siempre en la raíz del sistema)
        gl = roms_base / "gamelist.xml"
        if gl.exists():
            try:
                tree = ET.parse(gl)
                for game in tree.findall(".//game"):
                    gpath = game.findtext("path","").lstrip("./")
                    if gpath == rom_relpath or gpath == rom_filename or Path(gpath).stem == rom_stem:
                        img_tag = game.findtext("image","")
                        if img_tag:
                            img_clean = img_tag.lstrip("./")
                            p = roms_base / img_clean
                            if p.exists():
                                candidates.insert(0, p)
                            p2 = Path(img_tag) if img_tag.startswith("/") else None
                            if p2 and p2.exists():
                                candidates.insert(0, p2)
                        break
            except Exception:
                pass

        # 2. Fallback: buscar por stem en carpetas de media, tanto en la raíz como en la subcarpeta
        #    (media/<dir>/<stem>.<ext> estilo antiguo + Batocera: images/<stem>-<sufijo>.<ext>)
        media_dirs = ["images","named_boxarts","named_logos","screenshots",
                      "wheels","marquees","boxart","fanart","mixrbv1","mixrbv2"]
        img_exts   = [".png",".jpg",".jpeg",".webp",".gif"]
        bato_suffixes = ["-image","-thumb","-box","-wheel","-marquee","-fanart",
                         "-boxback","-titleshot","-map","-cartridge","-bezel"]
        for search_base in ([base_dir, roms_base] if subpath else [roms_base]):
            for mdir in media_dirs:
                for ext in img_exts:
                    p = search_base / "media" / mdir / (rom_stem + ext)
                    if p.exists():
                        candidates.append(p)
                    for suf in bato_suffixes:
                        p = search_base / mdir / (rom_stem + suf + ext)
                        if p.exists():
                            candidates.append(p)

        # 3. Servir la primera imagen encontrada
        for img_path in candidates:
            try:
                data = img_path.read_bytes()
                ext  = img_path.suffix.lower().lstrip(".")
                ct   = {"png":"image/png","jpg":"image/jpeg","jpeg":"image/jpeg",
                        "webp":"image/webp","gif":"image/gif"}.get(ext,"image/jpeg")
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", len(data))
                self.send_header("Cache-Control","max-age=300")
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception:
                continue

        # 4. Sin imagen — devolver 404 JSON
        self.send_json({"error":"Sin imagen"},404)

    def _serve_system_logo(self, system, s):
        """Sirve el logo de un sistema desde el tema activo (usuario o sistema)."""
        p = find_system_logo(s, system)
        if p is not None:
            try:
                self.send_response(200)
                self.send_header("Content-Type","image/png")
                self.send_header("Content-Length",p.stat().st_size)
                self.send_header("Cache-Control","max-age=86400")
                self.end_headers()
                self.wfile.write(p.read_bytes())
                return
            except Exception:
                pass
        self.send_response(204)
        self.end_headers()

    def _update_rom_meta(self, s):
        """Actualiza o crea entrada en gamelist.xml con los nuevos metadatos.
        Soporta ROMs dentro de subcarpetas via el campo 'subpath' en el JSON.
        """
        d        = self.read_json()
        system   = d.get("system","")
        subpath  = d.get("subpath","").strip().strip("/")
        filename = d.get("filename","")
        if not system or not filename:
            self.send_json({"ok":False,"error":"Faltan parámetros"}); return
        if not (is_safe_component(system) and is_safe_component(filename)):
            self.send_json({"ok":False,"error":"Nombre inválido"}); return

        try:
            sys_dir = system_dir(s, system)
        except ValueError:
            self.send_json({"ok":False,"error":"Sistema inválido"}); return
        rom_relpath = f"{subpath}/{filename}" if subpath else filename
        gl_path  = sys_dir / "gamelist.xml"

        # Leer o crear gamelist (siempre uno solo en la raíz del sistema)
        if gl_path.exists():
            try: tree = ET.parse(gl_path); root = tree.getroot()
            except Exception: root = ET.Element("gameList")
        else:
            root = ET.Element("gameList")

        # Buscar entrada existente por path relativo completo
        game = None
        for g in root.findall("game"):
            gpath = g.findtext("path","").lstrip("./")
            if gpath == rom_relpath or (not subpath and Path(gpath).name == filename):
                game = g; break

        if game is None:
            game = ET.SubElement(root, "game")
            ET.SubElement(game, "path").text = f"./{rom_relpath}"

        # Actualizar campos
        fields_map = {
            "name":"name","desc":"desc","year":"releasedate",
            "publisher":"publisher","genre":"genre","rating":"rating",
        }
        for key, tag in fields_map.items():
            val = d.get(key,"").strip()
            el  = game.find(tag)
            if val:
                if el is None: el = ET.SubElement(game, tag)
                # Año: convertir a formato YYYYMMDDTHHMMSS si es solo año
                if tag == "releasedate" and len(val) == 4:
                    val = val + "0101T000000"
                el.text = val
            elif el is not None and not val:
                game.remove(el)

        # Guardar con formato bonito
        try:
            rough    = ET.tostring(root, encoding="unicode")
            reparsed = minidom.parseString(rough)
            lines    = reparsed.toprettyxml(indent="    ").split("\n")
            filtered = [l for l in lines if l.strip()]
            if filtered and filtered[0].startswith("<?xml"): filtered = filtered[1:]
            xml_out  = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(filtered)
            gl_path.write_text(xml_out, encoding="utf-8")
            invalidate_rom_cache()
            self.send_json({"ok":True})
        except Exception as e:
            self.send_json({"ok":False,"error":str(e)})

# ─── Render HTML ──────────────────────────────────────────────────
def render_index():
    s = load_settings()
    active_theme = detect_active_theme(s)
    tpl = Path(__file__).parent / "templates" / "index.html"
    if tpl.exists():
        html = tpl.read_text(encoding="utf-8")
        html = html.replace("{{app_version}}", APP_VERSION)
        html = html.replace("{{active_theme}}", active_theme)
        html = html.replace("{{themes_user}}",  s.get("themes_user",""))
        html = html.replace("{{platform_opts}}",
            "\n".join(f'<option value="{p}">{p}</option>' for p in PLATFORM_IDS))
        html = html.replace("{{hardware_opts}}",
            "\n".join(f'<option value="{h}">{h}</option>' for h in HARDWARE_TYPES))
        html = html.replace("{{ext_preset_opts}}",
            "\n".join(f'<option value="{v}">{k}</option>' for k,v in EXT_PRESETS.items()))
        html = html.replace("{{has_pil}}", "true" if HAS_PIL else "false")
        return html
    return "<h1>Error: templates/index.html no encontrado</h1>"

# ─── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import socket
    import sys as _sys
    # Soporte --port <N>
    if "--port" in _sys.argv:
        idx = _sys.argv.index("--port")
        if idx+1 < len(_sys.argv):
            try: PORT = int(_sys.argv[idx+1])
            except ValueError: pass
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8",80)); local_ip = sock.getsockname()[0]; sock.close()
    except Exception: local_ip = "127.0.0.1"
    print("="*55)
    print(f"  Batocera System Manager Web  v{APP_VERSION}")
    print(f"  PIL/Pillow: {'disponible' if HAS_PIL else 'no disponible'}")
    print(f"  -> http://localhost:{PORT}")
    print(f"  -> http://{local_ip}:{PORT}  (desde tu red)")
    print("="*55)
    server = http.server.ThreadingHTTPServer((HOST,PORT), BatoceraHandler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n  Servidor detenido."); server.server_close()
