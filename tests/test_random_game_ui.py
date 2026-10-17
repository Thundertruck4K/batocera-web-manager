# -*- coding: utf-8 -*-
"""Tests de UI de la tarjeta "Juego al azar" ampliada.

El helper puro `randomGameView(g)` convierte el juego (con sus metadatos ya
resueltos por el backend) en tres líneas listas para pintar: datos, uso y
sinopsis. Devuelve texto plano (se pinta con textContent), así que no hay
riesgo de HTML inyectado desde la gamelist.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _helper_source():
    m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?<script>(.*?)</script>[\s\S]*?<!-- <<< UI-HELPERS",
                  _html(), re.S)
    assert m, "No se encontró bloque UI-HELPERS"
    return m.group(1)


def _run_node_eval(js: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    p = subprocess.run([node, "-e", js], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}\n{p.stdout}"
    return p.stdout.strip()


def _view(game):
    js = ("const console=global.console;\n" + _helper_source() + "\n"
          + "console.log(JSON.stringify(randomGameView(" + json.dumps(game) + ")));\n")
    return json.loads(_run_node_eval(js))


FULL = {
    "system": "ps2", "system_name": "PlayStation 2", "name": "Area 51",
    "filename": "Area 51.iso", "subpath": "", "has_art": True,
    "year": "2005", "genre": "Disparos / 1ª persona", "publisher": "Midway",
    "players": "1-2", "desc": "Shooter en primera persona.",
    "playcount": 3, "gametime_s": 4200, "lastplayed": "2026-10-12",
}


def test_helper_exists():
    assert "function randomGameView" in _helper_source(), "falta randomGameView"


def test_facts_join_platform_year_genre():
    v = _view(FULL)
    assert "PlayStation 2" in v["facts"]
    assert "2005" in v["facts"]
    assert "Disparos" in v["facts"]


def test_facts_skip_missing_parts():
    v = _view({"system": "snes", "system_name": "Super Nintendo Entertainment System"})
    assert v["facts"] == "Super Nintendo Entertainment System"
    assert v["usage"] == ""
    assert v["desc"] == ""


def test_facts_fall_back_to_slug_without_friendly_name():
    v = _view({"system": "snes"})
    assert v["facts"] == "snes", "sin nombre amigable se muestra el slug"


def test_usage_has_count_time_and_last_date():
    v = _view(FULL)
    assert "3 veces" in v["usage"]
    assert "1,2 h" in v["usage"], "el tiempo se muestra en horas con coma"
    assert "12/10/2026" in v["usage"], "la fecha se muestra en formato español"


def test_usage_singular_and_minutes():
    v = _view({"system": "nes", "playcount": 1, "gametime_s": 2700})
    assert "1 vez" in v["usage"]
    assert "45 min" in v["usage"]


def test_usage_time_only_without_playcount():
    v = _view({"system": "nes", "gametime_s": 7200})
    assert "2,0 h" in v["usage"]


def test_usage_empty_without_any_usage_data():
    v = _view({"system": "nes", "playcount": 0, "gametime_s": 0})
    assert v["usage"] == ""


def test_desc_is_passed_through():
    v = _view(FULL)
    assert v["desc"] == "Shooter en primera persona."


def test_card_has_nodes_for_facts_usage_desc():
    h = _html()
    for node in ("dash-random-facts", "dash-random-usage", "dash-random-desc"):
        assert f'id="{node}"' in h, f"falta el nodo {node}"


def test_renderRandomGame_uses_view_and_textContent():
    m = re.search(r"function renderRandomGame\(g\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta renderRandomGame()"
    body = m.group(1)
    assert "randomGameView(" in body
    assert "textContent" in body, "se pinta como texto (la gamelist no es HTML de confianza)"
    for node in ("facts", "usage", "desc"):
        assert f"random-{node}" in body, f"renderRandomGame no pinta {node}"
