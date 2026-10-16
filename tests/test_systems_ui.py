"""Tests de UI JS (extracción y validación de helpers puros)."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

def _helper_source():
    html = HTML.read_text(encoding="utf-8")
    # Extrae el bloque entre los marcadores
    m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?>>>[\s\S]*?<script>\s*(.*?)\s*</script>\s*<!-- <<< UI-HELPERS", html, re.S)
    if not m:
        m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?<script>(.*?)</script>[\s\S]*?<!-- <<< UI-HELPERS", html, re.S)
    assert m, "No se encontró bloque UI-HELPERS"
    return m.group(1)


def _run_node_eval(js: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    # eval script
    cmd = [node, "-e", js]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}\n{p.stdout}"
    return p.stdout.strip()


def test_cardcolor_deterministic_and_distinct():
    src = _helper_source()
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const names=['nes','psx','snes','neogeo','cps1','cps2','mame','gb','gba','master','sms','megadrive','atari2600','pc','dos'];\n"
        + "const c=names.map(cardColor);\n"
        + "const out={\n"
        + "  nes:cardColor('nes'),\n"
        + "  nes2:cardColor('nes'),\n"
        + "  psx:cardColor('psx'),\n"
        + "  c0:c[0],c1:c[1],\n"
        + "  distinct:(new Set(c)).size>=2\n"
        + "};\n"
        + "console.log(JSON.stringify(out));"
    )
    out = json.loads(_run_node_eval(js))
    assert out["nes"] == out["nes2"], "cardColor debe ser determinista"
    assert out["nes"] != out["psx"], "nes y psx deben dar colores distintos (umbral de prueba)"
    assert out["distinct"] is True, "Al menos 2 colores distintos entre nombres reales"


def test_cardcolor_accepts_object_with_name():
    src = _helper_source()
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "console.log(JSON.stringify(cardColor({name:'nes'})));"
    )
    out = _run_node_eval(js)
    assert out == _run_node_eval(
        "const console=global.console;\n" + src + "\nconsole.log(JSON.stringify(cardColor('nes')));"
    )


def test_filtersystems_case_insensitive_and_match_fullname():
    src = _helper_source()
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const list=[{name:'NES',fullname:'Nintendo Entertainment System'},{name:'psx',fullname:'PlayStation'}];\n"
        + "const ne=filterSystems(list,'ne').map(x=>x.name);\n"
        + "const play=filterSystems(list,'PLAY').map(x=>x.name);\n"
        + "console.log(JSON.stringify({ne,play}));"
    )
    out = json.loads(_run_node_eval(js))
    assert out["ne"] == ["NES"]
    assert out["play"] == ["psx"]


def test_sorts_name_az():
    src = _helper_source()
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const list=[{name:'zeta'},{name:'Alpha'},{name:'mId'},{name:'beta'}];\n"
        + "console.log(JSON.stringify(sortSystems(list,'name').map(x=>x.name)));"
    )
    out = json.loads(_run_node_eval(js))
    assert out == ["Alpha", "beta", "mId", "zeta"]


def test_sorts_roms_desc_and_tiebreak_name():
    src = _helper_source()
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const list=[{name:'a',rom_count:5},{name:'b',rom_count:10},{name:'c',rom_count:5}];\n"
        + "console.log(JSON.stringify(sortSystems(list,'roms').map(x=>({name:x.name,rom_count:x.rom_count}))));"
    )
    out = json.loads(_run_node_eval(js))
    assert out == [{"name": "b", "rom_count": 10}, {"name": "a", "rom_count": 5}, {"name": "c", "rom_count": 5}]
