#!/usr/bin/env python3
"""
Batocera System Manager Web — v1.2
Servidor HTTP puro (stdlib) — sin dependencias externas.
"""

import http.server, json, re, os, io, shutil, urllib.parse, hashlib
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from http import HTTPStatus

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HOST, PORT = "0.0.0.0", 5000

SETTINGS_FILE = Path("/userdata/system/batocera_manager_settings.json")
DEFAULT_SETTINGS = {
    "es_cfg_dir":    "/userdata/system/configs/emulationstation",
    "roms_base":     "/userdata/roms",
    "themes_user":   "/userdata/themes",
    "themes_sys":    "/usr/share/emulationstation/themes",
    "batocera_conf": "/userdata/system/batocera.conf",
    "python_path":   "/usr/lib/python3.12/site-packages/configgen/emulatorlauncher.py",
    "bios_dir":      "/userdata/bios",
    "app_path":      "/userdata/system/batocera_web/app.py",
    "server_port":   5000,
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
BIOS_DB = {
    "3do": [
        {"file":"panafz1.bin","md5":"f47264dd47fe30f73ab3c010015c155b","desc":"panafz1","mandatory":True},
        {"file":"panafz10.bin","md5":"51f2f43ae2f3508a14d9f56597e2d3ce","desc":"panafz10","mandatory":True},
        {"file":"goldstar.bin","md5":"8639fd5e549bd6238cfee79e3e749114","desc":"goldstar","mandatory":True},
    ],
    "adam": [
        {"file":"adam.zip","md5":None,"desc":"adam.zip","mandatory":True},
        {"file":"adam_ddp.zip","md5":None,"desc":"adam_ddp.zip","mandatory":True},
        {"file":"adam_fdc.zip","md5":None,"desc":"adam_fdc.zip","mandatory":True},
        {"file":"adam_kb.zip","md5":None,"desc":"adam_kb.zip","mandatory":True},
        {"file":"adam_prn.zip","md5":None,"desc":"adam_prn.zip","mandatory":True},
    ],
    "advision": [
        {"file":"advision.zip","md5":None,"desc":"advision.zip","mandatory":True},
    ],
    "amiga1200": [
        {"file":"amiga/kick39106.A1200","md5":"b7cc148386aa631136f510cd29e42fc3","desc":"kick39106.A1200","mandatory":True},
        {"file":"amiga/kick40068.A1200","md5":"646773759326fbac3b2311fd8c8793ee","desc":"kick40068.A1200","mandatory":True},
        {"file":"amiga/kick40068.A4000","md5":"9bdedde6a4f33555b4a270c8ca53297d","desc":"kick40068.A4000","mandatory":True},
        {"file":"amiga/amiga-os-300-a1200.rom","md5":"b7cc148386aa631136f510cd29e42fc3","desc":"amiga-os-300-a1200","mandatory":True},
        {"file":"amiga/amiga-os-310-a1200.rom","md5":"646773759326fbac3b2311fd8c8793ee","desc":"amiga-os-310-a1200","mandatory":True},
        {"file":"amiga/amiga-os-310-a3000.rom","md5":"413590e50098a056cfec418d3df0212d","desc":"amiga-os-310-a3000","mandatory":True},
        {"file":"amiga/amiga-os-310-a4000.rom","md5":"9bdedde6a4f33555b4a270c8ca53297d","desc":"amiga-os-310-a4000","mandatory":True},
        {"file":"amiga/amiga-os-310.rom","md5":"730888fb1bd9a3606d51f772ed136528","desc":"amiga-os-310","mandatory":True},
    ],
    "amiga500": [
        {"file":"amiga/kick33180.A500","md5":"85ad74194e87c08904327de1a9443b7a","desc":"kick33180.A500","mandatory":True},
        {"file":"amiga/kick37175.A500","md5":"dc10d7bdd1b6f450773dfb558477c230","desc":"kick37175.A500","mandatory":True},
        {"file":"amiga/kick34005.A500","md5":"82a21c1890cae844b3df741f2762d48d","desc":"kick34005.A500","mandatory":True},
        {"file":"amiga/kick37350.A600","md5":"465646c9b6729f77eea5314d1f057951","desc":"kick37350.A600","mandatory":True},
        {"file":"amiga/kick40063.A600","md5":"e40a5dfb3d017ba8779faba30cbd1c8e","desc":"kick40063.A600","mandatory":True},
        {"file":"amiga/amiga-os-120.rom","md5":"85ad74194e87c08904327de1a9443b7a","desc":"amiga-os-120","mandatory":True},
        {"file":"amiga/amiga-os-130.rom","md5":"82a21c1890cae844b3df741f2762d48d","desc":"amiga-os-130","mandatory":True},
        {"file":"amiga/amiga-os-204.rom","md5":"dc10d7bdd1b6f450773dfb558477c230","desc":"amiga-os-204","mandatory":True},
        {"file":"amiga/amiga-os-205.rom","md5":"465646c9b6729f77eea5314d1f057951","desc":"amiga-os-205","mandatory":True},
        {"file":"amiga/amiga-os-310-a600.rom","md5":"e40a5dfb3d017ba8779faba30cbd1c8e","desc":"amiga-os-310-a600","mandatory":True},
    ],
    "amigacd32": [
        {"file":"amiga/kick40060.CD32","md5":"5f8924d013dd57a89cf349f4cdedc6b1","desc":"kick40060.CD32","mandatory":True},
        {"file":"amiga/kick40060.CD32.ext","md5":"bb72565701b1b6faece07d68ea5da639","desc":"kick40060.CD32.ext","mandatory":True},
        {"file":"amiga/amiga-os-310-cd32.rom","md5":"5f8924d013dd57a89cf349f4cdedc6b1","desc":"amiga-os-310-cd32","mandatory":True},
        {"file":"amiga/amiga-ext-310-cd32.rom","md5":"bb72565701b1b6faece07d68ea5da639","desc":"amiga-ext-310-cd32","mandatory":True},
    ],
    "amigacdtv": [
        {"file":"amiga/kick34005.A500","md5":"82a21c1890cae844b3df741f2762d48d","desc":"kick34005.A500","mandatory":True},
        {"file":"amiga/kick34005.CDTV","md5":"89da1838a24460e4b93f4f0c5d92d48d","desc":"kick34005.CDTV","mandatory":True},
        {"file":"amiga/amiga-os-130.rom","md5":"82a21c1890cae844b3df741f2762d48d","desc":"amiga-os-130","mandatory":True},
        {"file":"amiga/amiga-ext-130-cdtv.rom","md5":"89da1838a24460e4b93f4f0c5d92d48d","desc":"amiga-ext-130-cdtv","mandatory":True},
    ],
    "apfm1000": [
        {"file":"apfm1000.zip","md5":None,"desc":"apfm1000.zip","mandatory":True},
    ],
    "apple2": [
        {"file":"apple2e.zip","md5":None,"desc":"apple2e.zip","mandatory":True},
        {"file":"apple2ee.zip","md5":None,"desc":"apple2ee.zip","mandatory":True},
        {"file":"apple2p.zip","md5":None,"desc":"apple2p.zip","mandatory":True},
        {"file":"a2diskiing.zip","md5":None,"desc":"a2diskiing.zip","mandatory":True},
        {"file":"a2cffa02.zip","md5":None,"desc":"a2cffa02.zip","mandatory":True},
        {"file":"votrsc01.zip","md5":None,"desc":"votrsc01.zip","mandatory":True},
        {"file":"votrsc01a.zip","md5":None,"desc":"votrsc01a.zip","mandatory":True},
        {"file":"d2fdc.zip","md5":None,"desc":"d2fdc.zip","mandatory":True},
    ],
    "apple2gs": [
        {"file":"apple2gs.zip","md5":None,"desc":"apple2gs.zip","mandatory":True},
    ],
    "archimedes": [
        {"file":"aa310.zip","md5":None,"desc":"aa310.zip","mandatory":True},
        {"file":"archimedes_keyboard.zip","md5":None,"desc":"archimedes_keyboard.zip","mandatory":True},
    ],
    "astrocade": [
        {"file":"astrocde.zip","md5":None,"desc":"astrocde.zip","mandatory":True},
    ],
    "atari5200": [
        {"file":"5200.rom","md5":"281f20ea4320404ec820fb7ec0693b38","desc":"5200","mandatory":True},
    ],
    "atari800": [
        {"file":"ATARIOSA.ROM","md5":"eb1f32f5d9f382db1bbfb8d7f9cb343a","desc":"ATARIOSA.ROM","mandatory":True},
        {"file":"ATARIOSB.ROM","md5":"4177f386a3bac989a981d3fe3388cb6c","desc":"ATARIOSB.ROM","mandatory":True},
        {"file":"ATARIXL.ROM","md5":"06daac977823773a3eea3422fd26a703","desc":"ATARIXL.ROM","mandatory":True},
        {"file":"ATARIBAS.ROM","md5":"0bac0c6a50104045d902df4503a4c30b","desc":"ATARIBAS.ROM","mandatory":True},
    ],
    "atarist": [
        {"file":"tos.img","md5":"c1c57ce48e8ee4135885cee9e63a68a2","desc":"tos.img","mandatory":True},
        {"file":"tos100fr.img","md5":"25789a649faff0a1176dc7d9b98105c0","desc":"tos100fr.img","mandatory":True},
        {"file":"tos100uk.img","md5":"c87a52c277f7952b41c639fc7bf0a43b","desc":"tos100uk.img","mandatory":True},
        {"file":"tos100us.img","md5":"d0f682ee6237497004339fb02172638b","desc":"tos100us.img","mandatory":True},
        {"file":"tos102de.img","md5":"a622cc35d8d78703905592dfaa4d2ccb","desc":"tos102de.img","mandatory":True},
        {"file":"tos102fr.img","md5":"d6521785627d20c51edc566808a6bf28","desc":"tos102fr.img","mandatory":True},
        {"file":"tos102uk.img","md5":"b2a8570de2e850c5acf81cb80512d9f6","desc":"tos102uk.img","mandatory":True},
        {"file":"tos104de.img","md5":"41b7dae4e24735f330b63ad923a0bfbc","desc":"tos104de.img","mandatory":True},
        {"file":"tos104es.img","md5":"143343f7b8e0b1162af206fe8f46b002","desc":"tos104es.img","mandatory":True},
        {"file":"tos104fr.img","md5":"0087e2707c57efa2106a0aa7576655c0","desc":"tos104fr.img","mandatory":True},
        {"file":"tos104uk.img","md5":"036c5ae4f885cbf62c9bed651c6c58a8","desc":"tos104uk.img","mandatory":True},
        {"file":"tos104us.img","md5":"736adb2dc835df4d323191fdc8926cc9","desc":"tos104us.img","mandatory":True},
        {"file":"tos106de.img","md5":"992bac38e01633a529121a2a65f0779e","desc":"tos106de.img","mandatory":True},
        {"file":"tos106es.img","md5":"30f69d70fe7c210300ed83f991b12de9","desc":"tos106es.img","mandatory":True},
        {"file":"tos106fr.img","md5":"bc7b224d0dc3f0cc14c8897db89c5787","desc":"tos106fr.img","mandatory":True},
        {"file":"tos106uk.img","md5":"6033f2b9364edfed321c6931a8181fd2","desc":"tos106uk.img","mandatory":True},
        {"file":"tos106us.img","md5":"a0982e760f9807d82667ff5a69e78f6b","desc":"tos106us.img","mandatory":True},
        {"file":"tos162de.img","md5":"94a75c1c65408d9f974b0463e15a3b11","desc":"tos162de.img","mandatory":True},
        {"file":"tos162fr.img","md5":"ed5fbaabe0219092df74c6c14cea3f8e","desc":"tos162fr.img","mandatory":True},
        {"file":"tos162uk.img","md5":"1cbc4f55295e469fc8cd72b7efdea1da","desc":"tos162uk.img","mandatory":True},
        {"file":"tos162us.img","md5":"febb00ba8784798293a7ae709a1dafcb","desc":"tos162us.img","mandatory":True},
        {"file":"tos205de.img","md5":"7aeabdc25f8134590e25643a405210ca","desc":"tos205de.img","mandatory":True},
        {"file":"tos205es.img","md5":"7449b131681f1dfe62ebed1392847057","desc":"tos205es.img","mandatory":True},
        {"file":"tos205fr.img","md5":"61b620ad951815a25cb37895c81a947c","desc":"tos205fr.img","mandatory":True},
        {"file":"tos205it.img","md5":"7e87d8fe7e24e0b4c55ad1b7955beae3","desc":"tos205it.img","mandatory":True},
        {"file":"tos205us.img","md5":"7cdd45b6aac66a21bfb357d9334e46db","desc":"tos205us.img","mandatory":True},
        {"file":"tos206de.img","md5":"0604dbb85928f0598d04144a8b554bbe","desc":"tos206de.img","mandatory":True},
        {"file":"tos206fr.img","md5":"b2873004a408b8db36321f98daafa251","desc":"tos206fr.img","mandatory":True},
        {"file":"tos206.img","md5":"4a0d4f282c3f2a0196681adf88862dd4","desc":"tos206.img","mandatory":True},
        {"file":"tos206uk.img","md5":"e690bec90d902024beed549d22150755","desc":"tos206uk.img","mandatory":True},
        {"file":"tos206us.img","md5":"c9093f27159e7d13ac0d1501a95e53d4","desc":"tos206us.img","mandatory":True},
        {"file":"tos306de.img","md5":"066f39a7ea5789d5afd59dd7b3104fa6","desc":"tos306de.img","mandatory":True},
        {"file":"tos306uk.img","md5":"dd1010ec566efbd71047d6c4919feba5","desc":"tos306uk.img","mandatory":True},
        {"file":"tos400.img","md5":"ed2647936ce4bd283c4d7dfd7ae09d1c","desc":"tos400.img","mandatory":True},
        {"file":"tos402.img","md5":"9e880168d0a004f7f5e852be758f39e4","desc":"tos402.img","mandatory":True},
        {"file":"tos404.img","md5":"e5ea0f216fb446f1c4a4f476bc5f03d4","desc":"tos404.img","mandatory":True},
    ],
    "atom": [
        {"file":"atom.zip","md5":None,"desc":"atom.zip","mandatory":True},
    ],
    "atomiswave": [
        {"file":"dc/awbios.zip","md5":"85254fbe320ca82a768ec2c26bb08def","desc":"awbios.zip","mandatory":True},
    ],
    "bbc": [
        {"file":"bbcb.zip","md5":None,"desc":"bbcb.zip","mandatory":True},
        {"file":"bbc_acorn8271.zip","md5":None,"desc":"bbc_acorn8271.zip","mandatory":True},
        {"file":"saa5050.zip","md5":None,"desc":"saa5050.zip","mandatory":True},
        {"file":"bbc_tube_80186.zip","md5":None,"desc":"bbc_tube_80186.zip","mandatory":True},
        {"file":"bbcm.zip","md5":None,"desc":"bbcm.zip","mandatory":True},
        {"file":"bbcmc.zip","md5":None,"desc":"bbcmc.zip","mandatory":True},
        {"file":"bbc_bitstik1.zip","md5":None,"desc":"bbc_bitstik1.zip","mandatory":True},
        {"file":"bbc_bitstik2.zip","md5":None,"desc":"bbc_bitstik2.zip","mandatory":True},
        {"file":"mame/samples/bbc.zip","md5":None,"desc":"bbc.zip","mandatory":True},
        {"file":"Acorn/basic2.rom","md5":"2cc67be4624df4dc66617742571a8e3d","desc":"basic2","mandatory":True},
        {"file":"BBCMicro/os12.rom","md5":"0a59a5ba15fe8557b5f7fee32bbd393a","desc":"os12","mandatory":True},
        {"file":"BBCMicro/dfs-2.26.rom","md5":"f083f49d6fe66344c650d7e74249cb96","desc":"dfs-2.26","mandatory":True},
    ],
    "beena": [
        {"file":"beena.zip","md5":None,"desc":"beena.zip","mandatory":True},
    ],
    "bk": [
        {"file":"bk/B11M_BOS.ROM","md5":"fe4627d1e3a1535874085050733263e7","desc":"B11M_BOS.ROM","mandatory":True},
        {"file":"bk/B11M_EXT.ROM","md5":"dc52f365d56fa1951f5d35b1101b9e3f","desc":"B11M_EXT.ROM","mandatory":True},
        {"file":"bk/BAS11M_0.ROM","md5":"946f6f23ded03c0e26187f0b3ca75993","desc":"BAS11M_0.ROM","mandatory":True},
        {"file":"bk/BAS11M_1.ROM","md5":"1e6637f32aa7d1de03510030cac40bcf","desc":"BAS11M_1.ROM","mandatory":True},
        {"file":"bk/DISK_327.ROM","md5":"5015228eeeb238e65da8edcd1b6dfac7","desc":"DISK_327.ROM","mandatory":True},
        {"file":"bk/BASIC10.ROM","md5":"3fa774326d75410a065659aea80252f0","desc":"BASIC10.ROM","mandatory":True},
        {"file":"bk/FOCAL10.ROM","md5":"5737f972e8638831ab71e9139abae052","desc":"FOCAL10.ROM","mandatory":True},
        {"file":"bk/MONIT10.ROM","md5":"95f8c41c6abf7640e35a6a03cecebd01","desc":"MONIT10.ROM","mandatory":True},
        {"file":"bk0010.zip","md5":None,"desc":"bk0010.zip","mandatory":True},
    ],
    "camplynx": [
        {"file":"lynx48k.zip","md5":None,"desc":"lynx48k.zip","mandatory":True},
        {"file":"lynx96k.zip","md5":None,"desc":"lynx96k.zip","mandatory":True},
        {"file":"lynx128k.zip","md5":None,"desc":"lynx128k.zip","mandatory":True},
    ],
    "cdi": [
        {"file":"cdimono1.zip","md5":None,"desc":"cdimono1.zip","mandatory":True},
    ],
    "cgenie": [
        {"file":"cgenie.zip","md5":None,"desc":"cgenie.zip","mandatory":True},
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
        {"file":"coco.zip","md5":None,"desc":"coco.zip","mandatory":True},
        {"file":"coco2.zip","md5":None,"desc":"coco2.zip","mandatory":True},
        {"file":"coco2b.zip","md5":None,"desc":"coco2b.zip","mandatory":True},
        {"file":"coco3.zip","md5":None,"desc":"coco3.zip","mandatory":True},
        {"file":"coco3p.zip","md5":None,"desc":"coco3p.zip","mandatory":True},
        {"file":"coco_fdc_v11.zip","md5":None,"desc":"coco_fdc_v11.zip","mandatory":True},
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
        {"file":"crvision.zip","md5":None,"desc":"crvision.zip","mandatory":True},
    ],
    "dragon64": [
        {"file":"dragon64.zip","md5":None,"desc":"dragon64.zip","mandatory":True},
        {"file":"dragon32.zip","md5":None,"desc":"dragon32.zip","mandatory":True},
        {"file":"xroar/d32.rom","md5":"3420b96031078a4ef408cad7bf21a33f","desc":"d32","mandatory":True},
        {"file":"xroar/d64_1.rom","md5":"5f0bee59710e55f5880e74890912ed78","desc":"d64_1","mandatory":True},
        {"file":"xroar/d64_2.rom","md5":"fd91edce7be5e7c2d88e46b76956a8aa","desc":"d64_2","mandatory":True},
        {"file":"xroar/ddos10.rom","md5":"1c965da49b6c5459b8353630aa1482e7","desc":"ddos10","mandatory":True},
    ],
    "dreamcast": [
        {"file":"dc/dc_boot.bin","md5":"e10c53c2f8b90bab96ead2d368858623","desc":"dc_boot","mandatory":True},
    ],
    "electron": [
        {"file":"electron.zip","md5":None,"desc":"electron.zip","mandatory":True},
        {"file":"electron64.zip","md5":None,"desc":"electron64.zip","mandatory":True},
        {"file":"electron_plus1.zip","md5":None,"desc":"electron_plus1.zip","mandatory":True},
        {"file":"electron_plus3.zip","md5":None,"desc":"electron_plus3.zip","mandatory":True},
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
        {"file":"ep64.zip","md5":"5ad3baaad3b5156d6b60b34229a676fb","desc":"ep64.zip","mandatory":True},
        {"file":"ep128.zip","md5":"f36f24cbb87745fbd2714e4df881db09","desc":"ep128.zip","mandatory":True},
        {"file":"ep64_exdos.zip","md5":"47258d03aec37bc24df5dbc5d50fc9f8","desc":"ep64_exdos.zip","mandatory":True},
    ],
    "fds": [
        {"file":"disksys.rom","md5":"ca30b50f880eb660a320674ed365ef7a","desc":"disksys","mandatory":True},
    ],
    "fm7": [
        {"file":"fm7.zip","md5":None,"desc":"fm7.zip","mandatory":True},
        {"file":"fm77av.zip","md5":None,"desc":"fm77av.zip","mandatory":True},
    ],
    "fmtowns": [
        {"file":"fmtowns/FMT_DIC.ROM","md5":"8fa4e553f28cfc0c30a0a1e589799942","desc":"FMT_DIC.ROM","mandatory":True},
        {"file":"fmtowns/FMT_DOS.ROM","md5":"0585b19930d4a7f4c71bcc8a33746588","desc":"FMT_DOS.ROM","mandatory":True},
        {"file":"fmtowns/FMT_F20.ROM","md5":"ac0c7021e9bf48ca84b51ab651169a88","desc":"FMT_F20.ROM","mandatory":True},
        {"file":"fmtowns/FMT_FNT.ROM","md5":"b91300e55b70227ce98b59c5f02fa8dd","desc":"FMT_FNT.ROM","mandatory":True},
        {"file":"fmtowns/FMT_SYS.ROM","md5":"86fb6f7280689259f0ca839dd3dd6cde","desc":"FMT_SYS.ROM","mandatory":True},
        {"file":"fmtmarty.zip","md5":None,"desc":"fmtmarty.zip","mandatory":True},
        {"file":"fmtowns.zip","md5":None,"desc":"fmtowns.zip","mandatory":True},
        {"file":"fmtownsux.zip","md5":None,"desc":"fmtownsux.zip","mandatory":True},
    ],
    "gamate": [
        {"file":"gamate.zip","md5":None,"desc":"gamate.zip","mandatory":True},
    ],
    "gamecom": [
        {"file":"gamecom.zip","md5":None,"desc":"gamecom.zip","mandatory":True},
    ],
    "gamecube": [
        {"file":"GC/EUR/IPL.bin","md5":"db92574caab77a7ec99d4605fd6f2450","desc":"IPL","mandatory":True},
        {"file":"GC/JAP/IPL.bin","md5":"b17148254a5799684c7d783206504926","desc":"IPL","mandatory":True},
        {"file":"GC/USA/IPL.bin","md5":"b17148254a5799684c7d783206504926","desc":"IPL","mandatory":True},
    ],
    "gamepock": [
        {"file":"gamepock.zip","md5":None,"desc":"gamepock.zip","mandatory":True},
    ],
    "gba": [
        {"file":"gba_bios.bin","md5":"a860e8c0b6d573d191e4ec7db1b1e4f6","desc":"gba_bios","mandatory":True},
        {"file":"gb_bios.bin","md5":"32fbbd84168d3482956eb3c5051637f5","desc":"gb_bios","mandatory":True},
        {"file":"gbc_bios.bin","md5":"dbfce9db9deaa2567f6a84fde55f9680","desc":"gbc_bios","mandatory":True},
        {"file":"sgb_bios.bin","md5":"d574d4f9c12f305074798f54c091a8b4","desc":"sgb_bios","mandatory":True},
    ],
    "gmaster": [
        {"file":"gmaster.zip","md5":None,"desc":"gmaster.zip","mandatory":True},
    ],
    "gp32": [
        {"file":"gp32.zip","md5":None,"desc":"gp32.zip","mandatory":True},
    ],
    "gsplus": [
        {"file":"ROM1","md5":"20a0334c447cb069a040ae5be1d938df","desc":"ROM1","mandatory":True},
    ],
    "hikaru": [
        {"file":"hikaru.zip","md5":"040f9b37a1f802d450379aaec106ec69","desc":"hikaru.zip","mandatory":True},
        {"file":"mie.zip","md5":"e95415b161121bef35ade12367138c63","desc":"mie.zip","mandatory":True},
        {"file":"jvs13551.zip","md5":"ee643e8c7369fe7feca610d4daa4a57c","desc":"jvs13551.zip","mandatory":True},
    ],
    "intellivision": [
        {"file":"exec.bin","md5":"62e761035cb657903761800f4437b8af","desc":"exec","mandatory":True},
        {"file":"grom.bin","md5":"0cd5946c6473e42e8e4c2137785e427f","desc":"grom","mandatory":True},
    ],
    "laser310": [
        {"file":"laser310.zip","md5":None,"desc":"laser310.zip","mandatory":True},
    ],
    "loopy": [
        {"file":"casloopy.zip","md5":"0e1d8dc0110ecf8201c0cef11ef4a858","desc":"casloopy.zip","mandatory":True},
    ],
    "lynx": [
        {"file":"lynxboot.img","md5":"fcd403db69f54290b51035d82f835e7b","desc":"lynxboot.img","mandatory":True},
    ],
    "macintosh": [
        {"file":"MacII.ROM","md5":"66223be1497460f1e60885eeb35e03cc","desc":"MacII.ROM","mandatory":True},
        {"file":"MacIIx.ROM","md5":"2a8a4c7f2a38e0ab0771f59a9a0f1ee4","desc":"MacIIx.ROM","mandatory":True},
        {"file":"mac128k.zip","md5":None,"desc":"mac128k.zip","mandatory":True},
        {"file":"mackbd_m0110.zip","md5":None,"desc":"mackbd_m0110.zip","mandatory":True},
        {"file":"mackbd_m0120.zip","md5":None,"desc":"mackbd_m0120.zip","mandatory":True},
        {"file":"mac512k.zip","md5":None,"desc":"mac512k.zip","mandatory":True},
        {"file":"macplus.zip","md5":None,"desc":"macplus.zip","mandatory":True},
        {"file":"macse.zip","md5":None,"desc":"macse.zip","mandatory":True},
        {"file":"macclasc.zip","md5":None,"desc":"macclasc.zip","mandatory":True},
        {"file":"mac2fdhd.zip","md5":None,"desc":"mac2fdhd.zip","mandatory":True},
        {"file":"nb_mdc824.zip","md5":None,"desc":"nb_mdc824.zip","mandatory":True},
        {"file":"maciix.zip","md5":None,"desc":"maciix.zip","mandatory":True},
        {"file":"maclc3.zip","md5":None,"desc":"maclc3.zip","mandatory":True},
        {"file":"mackbd_m0110a.zip","md5":None,"desc":"mackbd_m0110a.zip","mandatory":True},
        {"file":"nb_image.zip","md5":None,"desc":"nb_image.zip","mandatory":True},
        {"file":"egret.zip","md5":None,"desc":"egret.zip","mandatory":True},
        {"file":"adbmodem.zip","md5":None,"desc":"adbmodem.zip","mandatory":True},
        {"file":"macos3.img","md5":None,"desc":"macos3.img","mandatory":True},
        {"file":"macos608.img","md5":None,"desc":"macos608.img","mandatory":True},
        {"file":"macos701.img","md5":None,"desc":"macos701.img","mandatory":True},
        {"file":"macos75.img","md5":None,"desc":"macos75.img","mandatory":True},
        {"file":"mac608.chd","md5":None,"desc":"mac608.chd","mandatory":True},
        {"file":"mac701.chd","md5":None,"desc":"mac701.chd","mandatory":True},
        {"file":"mac755.chd","md5":None,"desc":"mac755.chd","mandatory":True},
    ],
    "mc10": [
        {"file":"mc10.zip","md5":None,"desc":"mc10.zip","mandatory":True},
        {"file":"alice.zip","md5":None,"desc":"alice.zip","mandatory":True},
        {"file":"xroar/mc10.rom","md5":"f29e94ff36577ffb6a787959e45bfe85","desc":"mc10","mandatory":True},
        {"file":"xroar/alice.rom","md5":"78af465c2f31cf4e05dec1efda77da01","desc":"alice","mandatory":True},
    ],
    "megadrive-msu": [
        {"file":"bios_CD_E.bin","md5":"e66fa1dc5820d254611fdcdba0662372","desc":"bios_CD_E","mandatory":True},
        {"file":"bios_CD_U.bin","md5":"854b9150240a198070150e4566ae1290","desc":"bios_CD_U","mandatory":True},
        {"file":"bios_CD_J.bin","md5":"278a9397d192149e84e820ac621a8edd","desc":"bios_CD_J","mandatory":True},
    ],
    "msx": [
        {"file":"MSX.ROM","md5":"364a1a579fe5cb8dba54519bcfcdac0d","desc":"MSX.ROM","mandatory":True},
    ],
    "msx1": [
        {"file":"openmsx/px-7_pbasic.rom","md5":"281809cafe63437fc4bffb3033fbd0db","desc":"px-7_pbasic","mandatory":True},
        {"file":"openmsx/px-7_basic-bios1.rom","md5":"9218f6dd89f7ba01e3090d44721b4260","desc":"px-7_basic-bios1","mandatory":True},
    ],
    "msx2": [
        {"file":"MSX2.ROM","md5":"ec3a01c91f24fbddcbcab0ad301bc9ef","desc":"MSX2.ROM","mandatory":True},
        {"file":"MSX2EXT.ROM","md5":"2183c2aff17cf4297bdb496de78c2e8a","desc":"MSX2EXT.ROM","mandatory":True},
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
        {"file":"openmsx/ide250.zip","md5":"afa4b5f2944334f84971af814a24bd5a","desc":"ide250.zip","mandatory":True},
        {"file":"openmsx/phc-70fd2_basickun.rom","md5":"2ce20986da024e9a0e271961c6bc9f01","desc":"phc-70fd2_basickun","mandatory":True},
        {"file":"openmsx/yrw801.rom","md5":"42af93619160ef2116416f74a6cb12f2","desc":"yrw801","mandatory":True},
    ],
    "mz2000": [
        {"file":"mz2000.zip","md5":None,"desc":"mz2000.zip","mandatory":True},
    ],
    "mz2500": [
        {"file":"mz2500.zip","md5":None,"desc":"mz2500.zip","mandatory":True},
    ],
    "mz700": [
        {"file":"mz700.zip","md5":None,"desc":"mz700.zip","mandatory":True},
    ],
    "mz800": [
        {"file":"mz800.zip","md5":None,"desc":"mz800.zip","mandatory":True},
    ],
    "mz80k": [
        {"file":"mz80k.zip","md5":None,"desc":"mz80k.zip","mandatory":True},
        {"file":"mz80kj.zip","md5":None,"desc":"mz80kj.zip","mandatory":True},
    ],
    "n64dd": [
        {"file":"64DD_IPL.bin","md5":"8d3d9f294b6e174bc7b1d2fd1c727530","desc":"64DD_IPL","mandatory":True},
    ],
    "naomi": [
        {"file":"dc/naomi.zip","md5":"eb4099aeb42ef089cfe94f8fe95e51f6","desc":"naomi.zip","mandatory":True},
    ],
    "naomi2": [
        {"file":"dc/naomi2.zip","md5":None,"desc":"naomi2.zip","mandatory":True},
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
        {"file":"neogeo.zip","md5":"dffb72f116d36d025068b23970a4f6df","desc":"neogeo.zip","mandatory":True},
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
        {"file":"pc6001.zip","md5":"2a13a60acf99a659144655b6c9e39b92","desc":"pc6001.zip","mandatory":True},
        {"file":"pc6001a.zip","md5":"8665e123c7d6b167677153f05a2f9c86","desc":"pc6001a.zip","mandatory":True},
        {"file":"pc6001mk2.zip","md5":"ec0fced1d7f242a823c6d6ebf9772045","desc":"pc6001mk2.zip","mandatory":True},
        {"file":"pc6001mk2sr.zip","md5":"bef7865bdc29009350e308935a8b2b17","desc":"pc6001mk2sr.zip","mandatory":True},
    ],
    "pc80": [
        {"file":"pc8001.zip","md5":None,"desc":"pc8001.zip","mandatory":True},
        {"file":"pc8001mk2sr.zip","md5":None,"desc":"pc8001mk2sr.zip","mandatory":True},
    ],
    "pc88": [
        {"file":"quasi88/N88.ROM","md5":"4f984e04a99d56c4cfe36115415d6eb8","desc":"N88.ROM","mandatory":True},
        {"file":"quasi88/N88SUB.ROM","md5":"793f86784e5608352a5d7f03f03e0858","desc":"N88SUB.ROM","mandatory":True},
        {"file":"quasi88/N88N.ROM","md5":"2ff07b8769367321128e03924af668a0","desc":"N88N.ROM","mandatory":True},
        {"file":"quasi88/N88KNJ1.ROM","md5":"d81c6d5d7ad1a4bbbd6ae22a01257603","desc":"N88KNJ1.ROM","mandatory":True},
        {"file":"quasi88/N88EXT0.ROM","md5":"d675a2ca186c6efcd6277b835de4c7e5","desc":"N88EXT0.ROM","mandatory":True},
        {"file":"quasi88/N88EXT1.ROM","md5":"e844534dfe5744b381444dbe61ef1b66","desc":"N88EXT1.ROM","mandatory":True},
        {"file":"quasi88/N88EXT2.ROM","md5":"6548fa45061274dee1ea8ae1e9e93910","desc":"N88EXT2.ROM","mandatory":True},
        {"file":"quasi88/N88EXT3.ROM","md5":"fc4b76a402ba501e6ba6de4b3e8b4273","desc":"N88EXT3.ROM","mandatory":True},
    ],
    "pc98": [
        {"file":"np2kai/BIOS.ROM","md5":"e246140dec5124c5e404869a84caefce","desc":"BIOS.ROM","mandatory":True},
        {"file":"np2kai/FONT.ROM","md5":"2af6179d7de4893ea0b705c00e9a98d6","desc":"FONT.ROM","mandatory":True},
        {"file":"np2kai/SOUND.ROM","md5":"caf90f22197aed6f14c471c21e64658d","desc":"SOUND.ROM","mandatory":True},
        {"file":"np2kai/ITF.ROM","md5":"e9fc3890963b12cf15d0a2eea5815b72","desc":"ITF.ROM","mandatory":True},
        {"file":"np2kai/font.bmp","md5":"7da1e5b7c482d4108d22a5b09631d967","desc":"font.bmp","mandatory":True},
    ],
    "pcengine": [
        {"file":"syscard3.pce","md5":"38179df8f4ac870017db21ebcbf53114","desc":"syscard3.pce","mandatory":True},
    ],
    "pcfx": [
        {"file":"pcfx.rom","md5":"08e36edbea28a017f79f8d4f7ff9b6d7","desc":"pcfx","mandatory":True},
    ],
    "pcw": [
        {"file":"pcw8256.zip","md5":None,"desc":"pcw8256.zip","mandatory":True},
        {"file":"pcw9512.zip","md5":None,"desc":"pcw9512.zip","mandatory":True},
    ],
    "ps2": [
        {"file":"ps2/ps2-0230a-20080220.bin","md5":"21038400dc633070a78ad53090c53017","desc":"ps2-0230a-20080220","mandatory":True},
    ],
    "ps3": [
        {"file":"PS3UPDAT.PUP","md5":"05fe32f5dc8c78acbcd84d36ee7fdc5b","desc":"PS3UPDAT.PUP","mandatory":True},
    ],
    "psvita": [
        {"file":"psvita/PSP2UPDAT.PUP","md5":"59dcf059d3328fb67be7e51f8aa33418","desc":"PSP2UPDAT.PUP","mandatory":True},
        {"file":"psvita/PSVUPDAT.PUP","md5":"f2c7b12fe85496ec88a0391b514d6e3b","desc":"PSVUPDAT.PUP","mandatory":True},
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
        {"file":"pv2000.zip","md5":None,"desc":"pv2000.zip","mandatory":True},
    ],
    "rx78": [
        {"file":"rx78.zip","md5":None,"desc":"rx78.zip","mandatory":True},
    ],
    "satellaview": [
        {"file":"BS-X.bin","md5":"96cf17bf589fcbfa6f8de2dc84f19fa2","desc":"BS-X","mandatory":True},
    ],
    "saturn": [
        {"file":"sega_101.bin","md5":"85ec9ca47d8f6807718151cbcca8b964","desc":"sega_101","mandatory":True},
        {"file":"mpr-17933.bin","md5":"3240872c70984b6cbfda1586cab68dbe","desc":"mpr-17933","mandatory":True},
        {"file":"mpr-18811-mx.ic1","md5":"255113ba943c92a54facd25a10fd780c","desc":"mpr-18811-mx.ic1","mandatory":True},
        {"file":"mpr-19367-mx.ic1","md5":"1cd19988d1d72a3e7caa0b73234c96b4","desc":"mpr-19367-mx.ic1","mandatory":True},
        {"file":"saturn_bios.bin","md5":"af5828fdff51384f99b3c4926be27762","desc":"saturn_bios","mandatory":True},
    ],
    "scummvm": [
        {"file":"scummvm/extra/MT32_PCM.ROM","md5":"89e42e386e82e0cacb4a2704a03706ca","desc":"MT32_PCM.ROM","mandatory":True},
        {"file":"scummvm/extra/MT32_CONTROL.ROM","md5":"5626206284b22c2734f3e9efefcd2675","desc":"MT32_CONTROL.ROM","mandatory":True},
    ],
    "scv": [
        {"file":"upd7801g.s01","md5":"635a978fd40db9a18ee44eff449fc126","desc":"upd7801g.s01","mandatory":True},
    ],
    "segaai": [
        {"file":"segaai.zip","md5":None,"desc":"segaai.zip","mandatory":True},
    ],
    "segacd": [
        {"file":"bios_CD_E.bin","md5":"e66fa1dc5820d254611fdcdba0662372","desc":"bios_CD_E","mandatory":True},
        {"file":"bios_CD_U.bin","md5":"854b9150240a198070150e4566ae1290","desc":"bios_CD_U","mandatory":True},
        {"file":"bios_CD_J.bin","md5":"278a9397d192149e84e820ac621a8edd","desc":"bios_CD_J","mandatory":True},
    ],
    "sgb": [
        {"file":"sgb_boot.bin","md5":"d574d4f9c12f305074798f54c091a8b4","desc":"sgb_boot","mandatory":True},
        {"file":"sgb2_boot.bin","md5":"e0430bca9925fb9882148fd2dc2418c1","desc":"sgb2_boot","mandatory":True},
        {"file":"SGB1.sfc","md5":"b15ddb15721c657d82c5bab6db982ee9","desc":"SGB1.sfc","mandatory":True},
        {"file":"SGB2.sfc","md5":"8ecd73eb4edf7ed7e81aef1be80031d5","desc":"SGB2.sfc","mandatory":True},
    ],
    "socrates": [
        {"file":"socrates.zip","md5":None,"desc":"socrates.zip","mandatory":True},
    ],
    "sufami": [
        {"file":"STBIOS.bin","md5":"d3a44ba7d42a74d3ac58cb9c14c6a5ca","desc":"STBIOS","mandatory":True},
    ],
    "supergrafx": [
        {"file":"syscard3.pce","md5":"38179df8f4ac870017db21ebcbf53114","desc":"syscard3.pce","mandatory":True},
    ],
    "supracan": [
        {"file":"supracan.zip","md5":"53c4343e062bb3b337370bbb58e64d16","desc":"supracan.zip","mandatory":True},
        {"file":"umc6650.zip","md5":"da6cebe6b22a91a34a67074adbbec3a3","desc":"umc6650.zip","mandatory":True},
    ],
    "ti99": [
        {"file":"ti99_4a.zip","md5":None,"desc":"ti99_4a.zip","mandatory":True},
        {"file":"ti99_speech.zip","md5":None,"desc":"ti99_speech.zip","mandatory":True},
    ],
    "triforce": [
        {"file":"saves/dolphin-emu/Triforce/segaboot.gcm","md5":"2ef01c0e93f7ee3a0a4b139aa14728b9","desc":"segaboot.gcm","mandatory":True},
    ],
    "trs80": [
        {"file":"trs80.zip","md5":None,"desc":"trs80.zip","mandatory":True},
        {"file":"trs80m3.zip","md5":None,"desc":"trs80m3.zip","mandatory":True},
        {"file":"trs80m4.zip","md5":None,"desc":"trs80m4.zip","mandatory":True},
        {"file":"trs80m4p.zip","md5":None,"desc":"trs80m4p.zip","mandatory":True},
    ],
    "tutor": [
        {"file":"tutor.zip","md5":None,"desc":"tutor.zip","mandatory":True},
    ],
    "tvc": [
        {"file":"ep128emu/roms/tvc22_sys.rom","md5":"8c54285f541930cde766069942bad0f2","desc":"tvc22_sys","mandatory":True},
        {"file":"ep128emu/roms/tvc22_ext.rom","md5":"5ce95a26ceed5bec73995d83568da9cf","desc":"tvc22_ext","mandatory":True},
        {"file":"ep128emu/roms/tvcfileio.rom","md5":"a2cf86ba8e7fc58b242137fe59036832","desc":"tvcfileio","mandatory":True},
        {"file":"ep128emu/roms/tvc_dos12d.rom","md5":"88dc7876d584f90e4106f91444ab23b7","desc":"tvc_dos12d","mandatory":True},
        {"file":"tvc64.zip","md5":None,"desc":"tvc64.zip","mandatory":True},
    ],
    "vectrex": [
        {"file":"vectrex.zip","md5":None,"desc":"vectrex.zip","mandatory":True},
    ],
    "vgmplay": [
        {"file":"qsound.zip","md5":None,"desc":"qsound.zip","mandatory":True},
        {"file":"ym2413.zip","md5":None,"desc":"ym2413.zip","mandatory":True},
        {"file":"ym2608.zip","md5":None,"desc":"ym2608.zip","mandatory":True},
    ],
    "videopacplus": [
        {"file":"g7400.bin","md5":"c500ff71236068e0dc0d0603d265ae76","desc":"g7400","mandatory":True},
        {"file":"jopac.bin","md5":"279008e4a0db2dc5f1c048853b033828","desc":"jopac","mandatory":True},
    ],
    "vis": [
        {"file":"vis.zip","md5":None,"desc":"vis.zip","mandatory":True},
    ],
    "vsmile": [
        {"file":"vsmile.zip","md5":None,"desc":"vsmile.zip","mandatory":True},
    ],
    "x1": [
        {"file":"xmil/IPLROM.X1","md5":"eeeea1cd29c6e0e8b094790ae969bfa7","desc":"IPLROM.X1","mandatory":True},
        {"file":"xmil/iplrom.x1t","md5":"56c28adcf1f3a2f87cf3d57c378013f5","desc":"iplrom.x1t","mandatory":True},
    ],
    "x68000": [
        {"file":"keropi/iplrom.dat","md5":"7fd4caabac1d9169e289f0f7bbf71d8e","desc":"iplrom.dat","mandatory":True},
        {"file":"keropi/cgrom.dat","md5":"cb0a5cfcf7247a7eab74bb2716260269","desc":"cgrom.dat","mandatory":True},
    ],
    "xbox": [
        {"file":"mcpx_1.0.bin","md5":"d49c52a4102f6df7bcf8d0617ac475ed","desc":"mcpx_1.0","mandatory":True},
        {"file":"Complex_4627.bin","md5":"39cee882148a87f93cb440b99dde3ceb","desc":"Complex_4627","mandatory":True},
    ],
    "xegs": [
        {"file":"xegs.zip","md5":None,"desc":"xegs.zip","mandatory":True},
    ],
    "zc210": [
        {"file":"zc210/zcdata.dat","md5":"033d7392985841027909c4c32b9f2076","desc":"zcdata.dat","mandatory":True},
        {"file":"zc210/sf2/default.sf2","md5":"39e5bc84ce9aac3a2d297d8aeb2a0d05","desc":"default.sf2","mandatory":True},
        {"file":"zc210/sf2/custom0.sf2","md5":"e0ba7a8634b12cfee4b6760a6f89051a","desc":"custom0.sf2","mandatory":True},
        {"file":"zc210/sf2/custom1.sf2","md5":"c1dc781c34cff8f9a023c0192754dc6c","desc":"custom1.sf2","mandatory":True},
        {"file":"zc210/sf2/custom2.sf2","md5":"144fcdbb6a30f1f916f6963006c2da97","desc":"custom2.sf2","mandatory":True},
        {"file":"zc210/sf2/custom3.sf2","md5":"134d217fb99c3be1e89cfaf8f28280d8","desc":"custom3.sf2","mandatory":True},
        {"file":"zc210/sf2/custom4.sf2","md5":"b37366199c6df9ee5316f031755aa821","desc":"custom4.sf2","mandatory":True},
        {"file":"zc210/sf2/custom5.sf2","md5":"64068b84eb88dc85b75148bbe9b393fb","desc":"custom5.sf2","mandatory":True},
        {"file":"zc210/sf2/custom6.sf2","md5":"1241986de5b1d00b02d34f1e6651a1d1","desc":"custom6.sf2","mandatory":True},
        {"file":"zc210/sf2/custom7.sf2","md5":"386db0d538f372a9f1af622d1e934abf","desc":"custom7.sf2","mandatory":True},
        {"file":"zc210/sf2/custom8.sf2","md5":"6f68e4baf89c8ee4623c19617319184b","desc":"custom8.sf2","mandatory":True},
        {"file":"zc210/sf2/custom9.sf2","md5":"2010e5b85f9e1d60685ccb3d84a17115","desc":"custom9.sf2","mandatory":True},
        {"file":"zcsf.sf2","md5":"e0ba7a8634b12cfee4b6760a6f89051a","desc":"zcsf.sf2","mandatory":True},
    ],
}

# Batocera platforms that need no BIOS files (explicitly acknowledged
# so the UI shows "no BIOS required" instead of "unknown system").
NOBIOS_PLATFORMS = {
    "3ds":[], "amiga":[], "amstradcpc":[], "arcade":[], "atari2600":[],
    "atari7800":[], "c64":[], "famicom":[], "fba":[], "gamegear":[],
    "gb":[], "gbc":[], "gc":[], "genesis":[], "jaguar":[], "mame":[],
    "mastersystem":[], "megacd":[], "megadrive":[], "n64":[], "nes":[],
    "ngp":[], "pc":[], "pce":[], "psp":[], "sega32x":[], "sg1000":[],
    "snes":[], "tg16":[], "virtualboy":[], "wii":[], "wiiu":[],
    "wonderswan":[], "wonderswancolor":[], "zxspectrum":[],
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
import threading, time
_rom_cache        = {}   # {roms_base: (timestamp, data)}
_rom_cache_lock   = threading.Lock()
ROM_CACHE_TTL     = 60   # segundos

# In-memory set of skipped missing BIOS entries (skip_key = "system/file")
_missing_bios_skipped = set()

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


def list_rom_folder(settings, system, subpath=""):
    """Lista el contenido de una carpeta dentro de un sistema, soportando subcarpetas anidadas.
    subpath es relativo a la raíz del sistema, ej: 'CPS1' o 'CPS1/bootlegs'.
    """
    roms_base = Path(settings["roms_base"]) / system
    target    = (roms_base / subpath) if subpath else roms_base
    target    = target.resolve()
    roms_base_resolved = roms_base.resolve()

    # Seguridad: evitar path traversal fuera del sistema
    try:
        target.relative_to(roms_base_resolved)
    except ValueError:
        return None  # intento de escape fuera del directorio del sistema

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


def get_rom_systems(settings, fast=False):
    roms_base = Path(settings["roms_base"])
    result = []
    if not roms_base.exists(): return result
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
        theme_dir = Path(settings["themes_user"]) / active_theme / name
        logo_paths = [theme_dir / "art" / "logo.png", theme_dir / "logo.png"]
        has_logo = any(p.exists() for p in logo_paths)
        result.append({
            "name":name,"path":str(sys_dir),
            "rom_count":len(roms),"media_count":media_count,
            "total_size":total_size,"size_human":human_size(total_size),
            "has_gamelist":gl.exists(),"roms":roms,
            "is_empty":len(roms)==0,
            "has_bios":_bios_key(name) in _BIOS_LOOKUP,
            "bios_count":len(_get_bios_entries(name)),
            "has_logo": has_logo,
        })
    return result

def check_bios(system_name, bios_dir):
    bios_path = Path(bios_dir)
    entries = _get_bios_entries(system_name)
    known = _bios_key(system_name) in _BIOS_LOOKUP
    if not known:
        return {"known": False, "files": []}
    results = []
    for b in entries:
        fpath  = bios_path / b["file"]
        exists = fpath.exists()
        md5_ok = None
        actual = None
        if exists:
            if b.get("md5"):
                actual = md5_file(fpath)
                md5_ok = (actual == b["md5"])
            else:
                md5_ok = True
        results.append({
            "file":b["file"],"desc":b["desc"],"mandatory":b["mandatory"],
            "exists":exists,"md5_ok":md5_ok,
            "expected_md5":b.get("md5"),"actual_md5":actual,
            "size":human_size(fpath.stat().st_size) if exists else None,
        })
    return {"known": True, "files": results}

def parse_multipart(environ, data):
    import email.parser, email.policy
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
import subprocess, struct, fcntl, socket as _socket

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
            idx, gname, gtemp, gutil, gmem_used, gmem_total, gpower = parts[:7]
            try:
                temp_val = round(float(gtemp), 1) if gtemp else None
            except Exception:
                temp_val = None
            try:
                util_val = int(gutil) if gutil else None
            except Exception:
                util_val = None
            try:
                mem_used_str = f"{int(gmem_used)//1024} MB" if gmem_used else None
            except Exception:
                mem_used_str = None
            try:
                mem_total_str = f"{int(gmem_total)//1024} MB" if gmem_total else None
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


def get_gpu_info():
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
    if nv_gpus:
        for g in nv_gpus:
            gpus.append(g)
            seen_names.add(g["name"])

    # 2. DRM sysfs (para AMD/Intel y NVIDIA si no se detectó via smi)
    drm = Path("/sys/class/drm")
    if drm.exists():
        for card in sorted(drm.glob("card[0-9]")):
            try:
                g = _gpu_from_drm(card)
                # Evitar duplicados si nvidia-smi ya lo encontró
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

def get_memory():
    info = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":")[0].strip(), line.split(":")[1].strip().split()[0]
            info[k] = int(v)
    except Exception: return {}
    total = info.get("MemTotal", 0)
    avail = info.get("MemAvailable", 0)
    free  = info.get("MemFree", 0)
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

def get_disk():
    partitions = []
    try:
        out = _run("df -k 2>/dev/null")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 6: continue
            fs, size, used, avail, pct, mount = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            # Solo particiones relevantes de Batocera
            if not any(m in mount for m in ["/userdata","/boot","/","/media","/share"]):
                if mount not in ["/","/boot"]: continue
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

def get_network():
    ifaces = []
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
                "rx":     fmt(rx_bytes),
                "tx":     fmt(tx_bytes),
                "rx_raw": rx_bytes,
                "tx_raw": tx_bytes,
            })
    except Exception: pass
    return ifaces

def get_es_status():
    pid = _run("pgrep -n emulationstation 2>/dev/null")
    if pid:
        return {"running": True, "pid": pid}
    return {"running": False}

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
        "network":get_network(),
        "processes": get_top_processes(),
    }


# ═══════════════════════════════════════════════════════════════
#  MÓDULO: AUTOSTART SERVICE MANAGER
# ═══════════════════════════════════════════════════════════════

CUSTOM_SH       = Path("/userdata/system/custom.sh")
SERVICE_MARKER  = "# [batocera-manager]"
SERVICE_TAG_END = "# [/batocera-manager]"

def get_service_cmd(settings):
    """Genera el comando de inicio según la ruta real del app.py."""
    app_path = Path(settings.get("app_path", "/userdata/system/batocera_web/app.py"))
    port     = settings.get("server_port", 5000)
    return f"python3 {app_path} --port {port}"

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

def get_process_status():
    """Verifica si el servidor está corriendo actualmente."""
    import subprocess
    try:
        r = subprocess.run(
            ["pgrep", "-f", "python3.*app.py"],
            capture_output=True, text=True, timeout=3)
        pids = [p.strip() for p in r.stdout.strip().splitlines() if p.strip()]
        if pids:
            # Obtener puerto desde netstat/ss
            port = None
            try:
                ss = subprocess.run(
                    ["ss", "-tlnp"],
                    capture_output=True, text=True, timeout=3)
                for line in ss.stdout.splitlines():
                    if "python" in line or any(pid in line for pid in pids):
                        import re as _re
                        m = _re.search(r':(\d{4,5})\s', line)
                        if m: port = int(m.group(1)); break
            except Exception: pass
            return {"running": True, "pids": pids, "port": port}
    except Exception: pass
    return {"running": False, "pids": [], "port": None}

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
import urllib.request as _ureq
import urllib.parse   as _uparse
import re as _re

SS_API   = "https://www.screenscraper.fr/api2"
SS_SOFTNAME = "batocera_manager"

def get_scraper_config(settings):
    """Lee credenciales de ScreenScraper desde batocera.conf."""
    conf_path = Path(settings.get("batocera_conf", "/userdata/system/batocera.conf"))
    cfg = {"ss_user":"","ss_password":"","ss_region":"wor","ss_lang":"es",
           "ss_image_type":"mixrbv1","ss_devid":"","ss_devpassword":"",
           "tgdb_apikey":"","igdb_client_id":"","igdb_client_secret":"",
           "scraper_source":"screenscraper"}
    if not conf_path.exists():
        return cfg
    try:
        for line in conf_path.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k == "global.scrapper.user":       cfg["ss_user"]       = v
            if k == "global.scrapper.password":   cfg["ss_password"]   = v
            if k == "global.scrapper.region":     cfg["ss_region"]     = v
            if k == "global.scrapper.lang":       cfg["ss_lang"]       = v
            if k == "global.scrapper.devid":      cfg["ss_devid"]      = v
            if k == "global.scrapper.devpassword":cfg["ss_devpassword"]= v
            if k == "global.tgdb.apikey":          cfg["tgdb_apikey"]        = v
            if k == "global.igdb.clientid":         cfg["igdb_client_id"]     = v
            if k == "global.igdb.clientsecret":     cfg["igdb_client_secret"] = v
            if k == "global.scraper.source":        cfg["scraper_source"]     = v
            if k == "global.scrapper.imageSource":cfg["ss_image_type"] = v
    except Exception:
        pass
    return cfg

def ss_search_game(rom_filename, system_name, ss_user, ss_pass, region="wor", lang="es", devid="", devpassword=""):
    """Busca un juego en ScreenScraper.fr por nombre de archivo."""
    if not ss_user or not ss_pass:
        return None, "Sin credenciales de ScreenScraper", {}

    import re as _re
    rom_stem = Path(rom_filename).stem
    # Quitar paréntesis, corchetes y su contenido
    clean_name = _re.sub(r"[([{][^)\]{}]*[)\]}]", "", rom_stem)
    # Separar CamelCase: "VirtuaFighter4Evo" => "Virtua Fighter 4 Evo"
    clean_name = _re.sub(r"([a-z])([A-Z])",   r"\1 \2", clean_name)
    clean_name = _re.sub(r"([A-Za-z])([0-9])",r"\1 \2", clean_name)
    clean_name = _re.sub(r"([0-9])([A-Za-z])",r"\1 \2", clean_name)
    clean_name = clean_name.replace("_"," ").replace("-"," ").replace("."," ")
    clean_name = _re.sub(r"\s+", " ", clean_name).strip()

    # Mapeo sistema Batocera → systemeid ScreenScraper
    SS_SYSTEMS = {
        "snes":9,"nes":3,"n64":14,"gba":12,"gb":9,"gbc":10,"nds":15,
        "megadrive":1,"genesis":1,"segacd":20,"sega32x":19,
        "psx":57,"ps2":58,"psp":61,"dreamcast":23,"saturn":22,
        "mame":75,"arcade":75,"atomiswave":53,"naomi":56,"naomi2":56,
        "neogeo":142,"neogeocd":70,
        "atari2600":26,"atari7800":43,"atari5200":40,"lynx":61,
        "pcengine":31,"amiga500":64,"amiga1200":64,"amigacd32":64,"c64":16,
        "gamecube":13,"wii":16,"wiiu":18,"3ds":17,"nds":15,
        "mastersystem":2,"gamegear":21,"sg1000":6,
        "xbox":32,"xbox360":33,"ps3":59,"ps4":60,"psp":61,
        "cps1":6,"cps2":7,"cps3":8,
    }
    sys_id = SS_SYSTEMS.get(system_name.lower(), 0)

    # Usar las credenciales del usuario como devid también
    # (cuenta personal puede actuar como dev para uso personal)
    params = {
        "devid":      devid      or "batocera_manager",
        "devpassword":devpassword or "batocera_manager",
        "softname":   SS_SOFTNAME,
        "output":     "json",
        "ssid":       ss_user,
        "sspassword": ss_pass,
        "systemeid":  str(sys_id),
        "romtype":    "rom",
        "romnom":     rom_filename,
        "recherche":  clean_name,
    }
    url = f"{SS_API}/jeuInfos.php?" + _uparse.urlencode(params)
    try:
        req = _ureq.Request(url, headers={
            "User-Agent": f"BatoceraManager/1.2 ({ss_user})"
        })
        with _ureq.urlopen(req, timeout=15) as r:
            raw  = r.read()
            data = json.loads(raw)
            hdr  = data.get("header",{})
            if hdr.get("success") == "true":
                jeu = data.get("response",{}).get("jeu")
                ssuser = data.get("response",{}).get("ssuser",{})
                quota  = {
                    "requeststoday":  ssuser.get("requeststoday",""),
                    "maxrequestsperday": ssuser.get("maxrequestsperday",""),
                    "maxthreads":     ssuser.get("maxthreads",""),
                    "level":          ssuser.get("niveau",""),
                }
                if jeu:
                    return jeu, None, quota
                return None, "Sin resultados para este ROM", quota
            else:
                msg = hdr.get("message","") or hdr.get("error","Sin resultados")
                return None, msg, {}
    except _ureq.HTTPError as e:
        body = ""
        try: body = e.read().decode(errors="replace")[:200]
        except Exception: pass
        return None, f"HTTP {e.code}: {body or e.reason}", {}
    except Exception as e:
        return None, str(e), {}

def ss_download_image(game_data, image_type, dest_path):
    """Descarga una imagen de ScreenScraper y la guarda."""
    # Mapeo tipo imagen a región de SS
    type_map = {
        "mixrbv1":"mixrbv1","mixrbv2":"mixrbv2",
        "images":"ss","screenshots":"ss",
        "boxart":"box-2D","named_boxarts":"box-2D",
        "named_logos":"wheel","wheels":"wheel",
        "fanart":"fanart",
    }
    ss_region = type_map.get(image_type, "ss")

    medias = game_data.get("medias", [])
    # Buscar imagen del tipo solicitado
    url = None
    for media in medias:
        mtype = media.get("type","")
        if mtype == ss_region or (ss_region in mtype):
            url = media.get("url","")
            break
    # Fallback: screenshot
    if not url:
        for media in medias:
            if media.get("type","") in ("ss","screenshot"):
                url = media.get("url","")
                break
    if not url:
        return False, "Sin imagen disponible en ScreenScraper"
    try:
        req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
        with _ureq.urlopen(req, timeout=15) as r:
            img_data = r.read()
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(img_data)
        return True, str(dest_path)
    except Exception as e:
        return False, str(e)

def ss_build_meta(game_data, region="wor", lang="es"):
    """Extrae metadatos de la respuesta de ScreenScraper."""
    def get_text(lst, preferred_region="wor", preferred_lang="es"):
        if not lst: return ""
        if isinstance(lst, str): return lst
        # Buscar por idioma preferido
        for item in lst:
            if isinstance(item, dict):
                if item.get("langue") == preferred_lang: return item.get("text","")
        # Fallback inglés o primero
        for item in lst:
            if isinstance(item, dict):
                if item.get("langue") in ("en","","wor"): return item.get("text","")
        if isinstance(lst[0], dict): return lst[0].get("text","")
        return str(lst[0])

    noms   = game_data.get("noms",[])
    name   = get_text(noms, region, lang) or game_data.get("romnom","")
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
    except: rating = ""
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
        try: year = str(_dt.datetime.utcfromtimestamp(ts).year)
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

def download_image_generic(url, dest_path):
    """Descarga cualquier imagen desde una URL y la guarda."""
    try:
        req = _ureq.Request(url, headers={"User-Agent":"BatoceraManager/1.0"})
        with _ureq.urlopen(req, timeout=15) as r:
            data = r.read()
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return True, str(dest_path)
    except Exception as e:
        return False, str(e)

# ─── HTTP Handler ─────────────────────────────────────────────────
class BatoceraHandler(http.server.BaseHTTPRequestHandler):

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
        self.send_header("Content-Length",len(body))
        self.end_headers(); self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length",0))
        return self.rfile.read(n) if n else b""

    def read_json(self):
        return json.loads(self.read_body() or b"{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_GET(self):
        path  = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        parts = [p for p in path.split("/") if p]
        s     = load_settings()
        if path == "/":
            self.send_html(render_index())
        elif path == "/api/info":
            self.send_json({"active_theme":detect_active_theme(s),
                "themes":list_themes(s),"systems_count":len(list_custom_systems(s)),
                "ext_presets":EXT_PRESETS,"platform_ids":PLATFORM_IDS,
                "hardware_types":HARDWARE_TYPES,"has_pil":HAS_PIL})
        elif path == "/api/systems":
            self.send_json(list_custom_systems(s))
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
            self.send_json([{
                "name":x["name"],"rom_count":x["rom_count"],
                "media_count":x["media_count"],"size_human":x["size_human"],
                "is_empty":x["is_empty"],"has_gamelist":x["has_gamelist"],
                "has_bios":x["has_bios"],"bios_count":x["bios_count"],
                "has_logo":x.get("has_logo",False),
            } for x in systems])
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
        elif path == "/api/rom-image-info":
            # Devuelve qué imágenes disponibles tiene un ROM
            if len(parts) >= 4:
                sys_name = urllib.parse.unquote(parts[2])
                rom_fn   = urllib.parse.unquote("/".join(parts[3:]))
                roms_base= Path(s["roms_base"]) / sys_name
                rom_stem = Path(rom_fn).stem
                found = []
                for mdir in ["images","named_boxarts","named_logos","screenshots",
                             "wheels","marquees","boxart","fanart","mixrbv1","mixrbv2"]:
                    for ext in [".png",".jpg",".jpeg",".webp"]:
                        p = roms_base / "media" / mdir / (rom_stem + ext)
                        if p.exists():
                            found.append({"dir":mdir,"file":p.name,"size":human_size(p.stat().st_size)})
                self.send_json({"ok":True,"images":found,"rom":rom_fn})
            else:
                self.send_json({"ok":False,"error":"Faltan parámetros"})
        elif path == "/api/scraper/config":
            self.send_json(get_scraper_config(s))
        elif path == "/api/bios/missing":
            bios_dir = Path(s.get("bios_dir","/userdata/bios"))
            # Only check systems the user actually has (ROM folders)
            user_systems = get_rom_systems_cached(s)
            items = []
            for usys in user_systems:
                name = usys["name"]
                entries = _get_bios_entries(name)
                if not entries:
                    continue  # no BIOS entries for this system
                for b in entries:
                    fpath = bios_dir / b["file"]
                    exists = fpath.exists()
                    md5_ok = None
                    if exists and b.get("md5"):
                        md5_ok = (md5_file(fpath) == b["md5"])
                    missing = not exists or md5_ok is False
                    if not missing:
                        continue
                    skip_key = f"{name}/{b['file']}"
                    if skip_key in _missing_bios_skipped:
                        continue
                    items.append({
                        "system": name,
                        "file": b["file"],
                        "desc": b["desc"],
                        "mandatory": b["mandatory"],
                        "md5": b.get("md5"),
                        "exists": exists,
                        "md5_ok": md5_ok,
                        "skip_key": skip_key,
                    })
            total = len(items)
            systems = {}
            for it in items:
                systems.setdefault(it["system"], []).append(it)
            self.send_json({"ok":True,"total_missing":total,"items":items,"systems":systems})
        elif path == "/api/bios/missing/skip":
            d = self.read_json()
            key = d.get("skip_key","")
            if key:
                _missing_bios_skipped.add(key)
            self.send_json({"ok":True})
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
        elif len(parts)==3 and parts[:2]==["api","system-logo"]:
            system = urllib.parse.unquote(parts[2])
            self._serve_system_logo(system, s)
        elif len(parts)==4 and parts[:2]==["api","rom-image"]:
            system   = urllib.parse.unquote(parts[2])
            filename = urllib.parse.unquote(parts[3])
            self._serve_rom_image(system, filename, s)
        else:
            self.send_json({"error":"Not found"},404)

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
        elif path == "/api/settings":
            data = self.read_json()
            current = load_settings()
            current.update({k:v for k,v in data.items() if k in DEFAULT_SETTINGS})
            save_settings_to_file(current)
            self.send_json({"ok":True})
        elif path == "/api/upload-logo":
            self._upload_logo(s)
        elif len(parts)==4 and parts[:2]==["api","rom-systems"] and parts[3]=="upload":
            system = urllib.parse.unquote(parts[2])
            self._upload_rom(system, s)
        elif path == "/api/bios/upload":
            self._upload_bios(s)
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
            import subprocess as _sp, sys as _sys
            kill_service()
            import time as _time; _time.sleep(1)
            d    = self.read_json()
            cmd  = d.get("cmd", get_service_cmd(load_settings()))
            try:
                _sp.Popen(cmd.split(), close_fds=True)
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
        else:
            self.send_json({"error":"Not found"},404)

    def do_DELETE(self):
        path  = urllib.parse.urlparse(self.path).path.rstrip("/")
        parts = [p for p in path.split("/") if p]
        s     = load_settings()
        if len(parts)==3 and parts[:2]==["api","system"]:
            name    = parts[2]
            systems = list_custom_systems(s)
            t = next((x for x in systems if x["name"]==name),None)
            if t:
                try: os.remove(t["file"]); self.send_json({"ok":True})
                except Exception as e: self.send_json({"ok":False,"error":str(e)})
            else: self.send_json({"ok":False,"error":"No encontrado"})
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
        elif re.search(r'\s', slug):           errors.append("Slug sin espacios")
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
                log.append(f"✔ CFG escrito: {cfg_path}")
            except Exception as e:
                self.send_json({"ok":False,"errors":[str(e)]}); return
            if d.get("create_roms_dir"):
                try: os.makedirs(d.get("rompath","").strip(), exist_ok=True); log.append("✔ Dir ROMs creado")
                except Exception as e: log.append(f"⚠ {e}")
            if d.get("batocera_conf_entry") and d.get("emulator") and d.get("core"):
                try:
                    with open(s["batocera_conf"],"a",encoding="utf-8") as f:
                        f.write(f"\n# {d.get('fullname','')}\n{slug}.emulator={d.get('emulator')}\n{slug}.core={d.get('core')}\n")
                    log.append("✔ batocera.conf actualizado")
                except Exception as e: log.append(f"⚠ {e}")
        log.append(f"\n✅ Sistema '{slug}' {'simulado' if dry else 'creado'}.")
        if not dry: log.append("   Reinicia EmulationStation para que aparezca.")
        self.send_json({"ok":True,"log":log,"xml":xml_str,"cfg_path":cfg_path})

    def _upload_logo(self, s):
        body = self.read_body()
        ct   = self.headers.get("Content-Type","")
        if "application/json" in ct:
            d    = json.loads(body or b"{}")
            slug = d.get("slug","unknown").strip()
            if not HAS_PIL:
                self.send_json({"ok":False,"error":"PIL no disponible"}); return
            theme    = detect_active_theme(s)
            dest_dir = Path(s["themes_user"]) / theme / slug / "art"
            dest_file= dest_dir / "logo.png"
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file.write_bytes(make_placeholder_png(slug.upper()))
                self.send_json({"ok":True,"path":str(dest_file),"placeholder":True})
            except Exception as e: self.send_json({"ok":False,"error":str(e)})
            return
        fields, files = parse_multipart({"CONTENT_TYPE":ct}, body)
        slug  = fields.get("slug","unknown").strip()
        theme = detect_active_theme(s)
        dest_dir  = Path(s["themes_user"]) / theme / slug / "art"
        dest_file = dest_dir / "logo.png"
        if "logo" not in files:
            self.send_json({"ok":False,"error":"No se recibió archivo"}); return
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
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
        roms_base= Path(s["roms_base"]) / system
        dest_dir = (roms_base / subpath) if subpath else roms_base
        # Seguridad: evitar path traversal
        try:
            dest_dir.resolve().relative_to(roms_base.resolve())
        except ValueError:
            self.send_json({"ok":False,"error":"Ruta inválida"}); return
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
        subpath  = fields.get("path","").strip().strip("/")
        if subpath:
            # Security: prevent path traversal
            dest_base = (bios_dir / subpath).resolve()
            try:
                dest_base.relative_to(bios_dir.resolve())
            except ValueError:
                self.send_json({"ok":False,"error":"Ruta inválida"}); return
        else:
            dest_base = bios_dir
        dest_base.mkdir(parents=True, exist_ok=True)
        saved = []
        for fdata in files.values():
            dest = dest_base / fdata["filename"]
            dest.write_bytes(fdata["data"])
            saved.append({"file":str(dest.relative_to(bios_dir)).replace("\\","/"),
                "size":human_size(len(fdata["data"])),
                "md5":hashlib.md5(fdata["data"]).hexdigest()})
        self.send_json({"ok":True,"saved":saved})

    def _rename_rom(self, s):
        d = self.read_json()
        system   = d.get("system","")
        subpath  = d.get("subpath","").strip().strip("/")
        old_name = d.get("old_name","")
        new_name = d.get("new_name","").strip()
        if not all([system, old_name, new_name]):
            self.send_json({"ok":False,"error":"Faltan parámetros"}); return
        roms_base = Path(s["roms_base"]) / system
        base_dir  = (roms_base / subpath) if subpath else roms_base
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
        cfg      = get_scraper_config(s)
        cfg.update({k:v for k,v in d.items() if k in (
            "ss_user","ss_password","ss_region","ss_lang","ss_devid","ss_devpassword",
            "tgdb_apikey","igdb_client_id","igdb_client_secret")})

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
            game, err, quota = ss_search_game(filename, system,
                                       cfg["ss_user"], cfg["ss_password"],
                                       cfg["ss_region"], cfg["ss_lang"],
                                       cfg.get("ss_devid",""), cfg.get("ss_devpassword",""))
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
        cfg      = get_scraper_config(s)
        cfg.update({k:v for k,v in d.items() if k in (
            "ss_user","ss_password","ss_region","ss_lang","ss_image_type","ss_devid","ss_devpassword",
            "tgdb_apikey","igdb_client_id","igdb_client_secret")})

        results   = {"images":[],"meta":False,"errors":[]}
        sys_root  = Path(s["roms_base"]) / system
        roms_base = (sys_root / subpath) if subpath else sys_root
        rom_stem  = Path(filename).stem

        if source == "thegamesdb":
            game_id = game.get("id")
            img_url, err = tgdb_get_image(game_id, cfg.get("tgdb_apikey","")) if game_id else (None,"Sin ID de juego")
            if img_url:
                dest = roms_base / "media" / "images" / (rom_stem + ".png")
                ok, msg = download_image_generic(img_url, dest)
                if ok: results["images"].append({"type":"boxart","path":str(dest)})
                else:  results["errors"].append(f"Imagen: {msg}")
            else:
                results["errors"].append(f"Imagen: {err}")
            if d.get("save_meta", True):
                meta = tgdb_build_meta(game, cfg.get("tgdb_apikey",""))
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if results["images"]:
                    meta["image_path"] = "./media/images/" + rom_stem + ".png"
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        elif source == "igdb":
            img_url = igdb_get_image_url(game)
            if img_url:
                dest = roms_base / "media" / "images" / (rom_stem + ".png")
                ok, msg = download_image_generic(img_url, dest)
                if ok: results["images"].append({"type":"cover","path":str(dest)})
                else:  results["errors"].append(f"Imagen: {msg}")
            else:
                results["errors"].append("Sin imagen de portada en IGDB")
            if d.get("save_meta", True):
                meta = igdb_build_meta(game)
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if results["images"]:
                    meta["image_path"] = "./media/images/" + rom_stem + ".png"
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        else:  # screenscraper
            img_types = d.get("img_types", [cfg.get("ss_image_type","mixrbv1")])
            if isinstance(img_types, str): img_types = [img_types]
            for itype in img_types:
                folder_map = {"mixrbv1":"mixrbv1","mixrbv2":"mixrbv2",
                              "ss":"screenshots","screenshot":"screenshots",
                              "box-2D":"named_boxarts","wheel":"named_logos","fanart":"fanart"}
                folder = folder_map.get(itype, itype)
                dest   = roms_base / "media" / folder / (rom_stem + ".png")
                ok, msg = ss_download_image(game, itype, dest)
                if ok: results["images"].append({"type":itype,"path":str(dest)})
                else:  results["errors"].append(f"Imagen {itype}: {msg}")
            if d.get("save_meta", True) and game:
                meta = ss_build_meta(game, cfg["ss_region"], cfg["ss_lang"])
                meta.update({"system":system,"subpath":subpath,"filename":filename})
                if results["images"]:
                    first_img = results["images"][0]["path"]
                    meta["image_path"] = "./media/" + "/".join(Path(first_img).parts[-2:])
                self._save_gamelist_entry(s, meta)
                results["meta"] = True

        self.send_json({"ok":True,"results":results})

    def _save_gamelist_entry(self, s, meta):
        """Guarda una entrada completa en gamelist.xml incluyendo imagen."""
        system   = meta.get("system","")
        filename = meta.get("filename","")
        sys_dir  = Path(s["roms_base"]) / system
        gl_path  = sys_dir / "gamelist.xml"
        if gl_path.exists():
            try: tree = ET.parse(gl_path); root = tree.getroot()
            except Exception: root = ET.Element("gameList")
        else:
            root = ET.Element("gameList")
        # Buscar entrada existente
        game = None
        for g in root.findall("game"):
            gpath = g.findtext("path","").lstrip("./")
            if gpath == filename or Path(gpath).name == filename:
                game = g; break
        if game is None:
            game = ET.SubElement(root,"game")
            ET.SubElement(game,"path").text = f"./{filename}"
        field_map = {
            "name":"name","desc":"desc","year":"releasedate",
            "publisher":"publisher","genre":"genre","rating":"rating",
            "image_path":"image",
        }
        for k, tag in field_map.items():
            val = meta.get(k,"")
            if not val: continue
            if tag == "releasedate" and len(val) == 4:
                val = val + "0101T000000"
            el = game.find(tag)
            if el is None: el = ET.SubElement(game, tag)
            el.text = val
        try:
            rough    = ET.tostring(root, encoding="unicode")
            reparsed = minidom.parseString(rough)
            lines    = reparsed.toprettyxml(indent="    ").split("\n")
            filtered = [l for l in lines if l.strip()]
            if filtered and filtered[0].startswith("<?xml"): filtered = filtered[1:]
            xml_out  = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(filtered)
            gl_path.write_text(xml_out, encoding="utf-8")
            invalidate_rom_cache()
        except Exception:
            pass

    def _scraper_system(self, s):
        """Scrapea todos los ROMs de un sistema usando la fuente seleccionada."""
        import time as _t
        d        = self.read_json()
        system   = d.get("system","")
        source   = d.get("source", "screenscraper")
        only_missing = d.get("only_missing", True)
        cfg      = get_scraper_config(s)
        cfg.update({k:v for k,v in d.items() if k in (
            "ss_user","ss_password","ss_region","ss_lang","ss_image_type","ss_devid","ss_devpassword",
            "tgdb_apikey","igdb_client_id","igdb_client_secret")})

        # Validar credenciales según fuente
        if source == "thegamesdb" and not cfg.get("tgdb_apikey"):
            self.send_json({"ok":False,"error":"Configura tu API Key de TheGamesDB"}); return
        if source == "igdb" and not (cfg.get("igdb_client_id") and cfg.get("igdb_client_secret")):
            self.send_json({"ok":False,"error":"Configura Client ID y Secret de IGDB (Twitch)"}); return
        if source == "screenscraper" and not (cfg.get("ss_user") and cfg.get("ss_password")):
            self.send_json({"ok":False,"error":"Configura usuario y contraseña de ScreenScraper"}); return

        all_sys  = get_rom_systems(s, fast=False)
        sys_data = next((x for x in all_sys if x["name"]==system), None)
        if not sys_data:
            self.send_json({"ok":False,"error":"Sistema no encontrado"}); return

        roms = [r for r in sys_data["roms"]
                if r["is_rom"] and r["ext"] not in ("dir",) and r["name"] not in ("images","media","videos")]
        if only_missing:
            roms = [r for r in roms if not r["has_image"]]

        results   = {"ok":0,"fail":0,"skip":0,"errors":[],"total":len(roms),"quota":{}}
        roms_base = Path(s["roms_base"]) / system
        img_type  = cfg.get("ss_image_type","mixrbv1")

        for rom in roms:
            rom_stem = Path(rom["filename"]).stem
            ok_img   = False
            meta     = {}
            err      = None

            if source == "thegamesdb":
                game, err = tgdb_search_game(rom["filename"], system, cfg.get("tgdb_apikey",""))
                if game:
                    meta = tgdb_build_meta(game, cfg.get("tgdb_apikey",""))
                    img_url, ierr = tgdb_get_image(game.get("id"), cfg.get("tgdb_apikey",""))
                    if img_url:
                        dest = roms_base / "media" / "images" / (rom_stem + ".png")
                        ok_img, _ = download_image_generic(img_url, dest)
                        if ok_img: meta["image_path"] = ("." + ("/" + subpath if subpath else "") + f"/media/images/{rom_stem}.png")
                _t.sleep(0.3)

            elif source == "igdb":
                game, err = igdb_search_game(rom["filename"], system,
                                            cfg.get("igdb_client_id",""), cfg.get("igdb_client_secret",""))
                if game:
                    meta = igdb_build_meta(game)
                    img_url = igdb_get_image_url(game)
                    if img_url:
                        dest = roms_base / "media" / "images" / (rom_stem + ".png")
                        ok_img, _ = download_image_generic(img_url, dest)
                        if ok_img: meta["image_path"] = ("." + ("/" + subpath if subpath else "") + f"/media/images/{rom_stem}.png")
                _t.sleep(0.3)

            else:  # screenscraper
                game, err, sq = ss_search_game(rom["filename"], system,
                                           cfg["ss_user"], cfg["ss_password"],
                                           cfg["ss_region"], cfg["ss_lang"],
                                           cfg.get("ss_devid",""), cfg.get("ss_devpassword",""))
                if game:
                    meta = ss_build_meta(game, cfg["ss_region"], cfg["ss_lang"])
                    folder_map = {"mixrbv1":"mixrbv1","mixrbv2":"mixrbv2","ss":"screenshots",
                                 "box-2D":"named_boxarts","wheel":"named_logos","fanart":"fanart"}
                    folder = folder_map.get(img_type, img_type)
                    dest   = roms_base / "media" / folder / (rom_stem + ".png")
                    ok_img, _ = ss_download_image(game, img_type, dest)
                    if ok_img: meta["image_path"] = f"./media/{folder}/{rom_stem}.png"
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
                continue

            meta.update({"system":system,"filename":rom["filename"]})
            self._save_gamelist_entry(s, meta)
            if ok_img:
                results["ok"] += 1
            else:
                results["fail"] += 1
                results["errors"].append(f"{rom['name']} (sin imagen)")

        self.send_json({"ok":True,"results":results})


    def _scraper_save_config(self, s):
        """Guarda credenciales de ScreenScraper en batocera.conf."""
        d     = self.read_json()
        lines = d.get("lines", [])  # [{key, val}, ...]
        conf  = Path(s.get("batocera_conf","/userdata/system/batocera.conf"))
        try:
            existing = conf.read_text(errors="replace") if conf.exists() else ""
            ex_lines = existing.splitlines()
            for item in lines:
                key, val = item.get("key",""), item.get("val","")
                if not key: continue
                replaced = False
                for i, line in enumerate(ex_lines):
                    if line.strip().startswith(key + "=") or line.strip() == key + "=":
                        ex_lines[i] = f"{key}={val}"
                        replaced = True; break
                if not replaced:
                    ex_lines.append(f"{key}={val}")
            conf.parent.mkdir(parents=True, exist_ok=True)
            conf.write_text("\n".join(ex_lines) + "\n", encoding="utf-8")
            self.send_json({"ok":True})
        except Exception as e:
            self.send_json({"ok":False,"error":str(e)})

    def _serve_rom_image(self, system, rom_filename, s):
        """Sirve imagen de un ROM leyendo la ruta real del gamelist.xml.
        Soporta ROMs dentro de subcarpetas via ?subpath=CPS1 en la query string.
        """
        query   = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        subpath = urllib.parse.unquote(query.get("subpath",[""])[0]).strip("/")
        roms_base = Path(s["roms_base"]) / system
        base_dir  = (roms_base / subpath) if subpath else roms_base
        try:
            base_dir.resolve().relative_to(roms_base.resolve())
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
        media_dirs = ["images","named_boxarts","named_logos","screenshots",
                      "wheels","marquees","boxart","fanart","mixrbv1","mixrbv2"]
        img_exts   = [".png",".jpg",".jpeg",".webp",".gif"]
        for search_base in ([base_dir, roms_base] if subpath else [roms_base]):
            for mdir in media_dirs:
                for ext in img_exts:
                    p = search_base / "media" / mdir / (rom_stem + ext)
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
        """Sirve el logo de un sistema desde el tema activo."""
        theme = detect_active_theme(s)
        logo_paths = [
            Path(s["themes_user"]) / theme / system / "art" / "logo.png",
            Path(s["themes_user"]) / theme / system / "logo.png",
        ]
        for p in logo_paths:
            try:
                p = p.resolve()
                base = Path(s["themes_user"]).resolve()
                p.relative_to(base)
                if p.exists():
                    self.send_response(200)
                    self.send_header("Content-Type","image/png")
                    self.send_header("Content-Length",p.stat().st_size)
                    self.send_header("Cache-Control","max-age=86400")
                    self.end_headers()
                    self.wfile.write(p.read_bytes())
                    return
            except Exception:
                continue
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

        rom_relpath = f"{subpath}/{filename}" if subpath else filename
        sys_dir  = Path(s["roms_base"]) / system
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
    import socket, sys as _sys
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
    print("  Batocera System Manager Web  v1.2")
    print(f"  PIL/Pillow: {'disponible' if HAS_PIL else 'no disponible'}")
    print(f"  -> http://localhost:{PORT}")
    print(f"  -> http://{local_ip}:{PORT}  (desde tu red)")
    print("="*55)
    server = http.server.ThreadingHTTPServer((HOST,PORT), BatoceraHandler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n  Servidor detenido."); server.server_close()
