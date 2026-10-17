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
    p = subprocess.run([node, "-e", js], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}\n{p.stdout}"
    return p.stdout.strip()


def _view(game):
    js = ("const console=global.console;\n" + _helper_source() + "\n"
          + "console.log(JSON.stringify(randomGameView(" + json.dumps(game) + ")));\n")
    return json.loads(_run_node_eval(js))


def _call(fn: str, game):
    """Ejecuta un helper puro del bloque UI-HELPERS con un juego dado."""
    js = ("const console=global.console;\n" + _helper_source() + "\n"
          + f"console.log(JSON.stringify({fn}(" + json.dumps(game) + ")));\n")
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


# ─── Chips del espacio 2 (sistema · año · tipo) ────────────────────────

def test_chips_helper_exists():
    assert "function randomGameChips" in _helper_source(), "falta randomGameChips"


def test_chips_one_per_field_with_kind():
    chips = _call("randomGameChips", FULL)
    assert [c["label"] for c in chips] == ["PlayStation 2", "2005", "Disparos / 1ª persona"]
    assert [c["kind"] for c in chips] == ["system", "year", "genre"]


def test_chips_skip_missing_fields():
    chips = _call("randomGameChips",
                  {"system": "snes", "system_name": "Super Nintendo Entertainment System"})
    assert [c["label"] for c in chips] == ["Super Nintendo Entertainment System"]
    assert chips[0]["kind"] == "system"


def test_chips_fall_back_to_slug():
    chips = _call("randomGameChips", {"system": "snes"})
    assert [c["label"] for c in chips] == ["snes"], "sin nombre amigable se muestra el slug"


def test_chips_empty_without_game():
    assert _call("randomGameChips", None) == []


# ─── Carátula vertical + wallpaper generado ────────────────────────────

def test_art_uses_cover_url_when_has_art():
    art = _call("randomGameArt", FULL)
    assert "/api/rom-image/ps2/Area%2051.iso" in art["url"]
    assert art["placeholder"] is False


def test_art_keeps_subpath_in_url():
    art = _call("randomGameArt", {**FULL, "system": "cps1", "filename": "foo.zip",
                                  "subpath": "CPS1"})
    assert art["url"].endswith("?subpath=CPS1")


def test_art_asks_for_wallpaper_without_art():
    art = _call("randomGameArt", {"system": "snes", "filename": "game.zip"})
    assert art["url"] == "", "sin arte no hay URL: se pinta el wallpaper"
    assert art["placeholder"] is True
    assert art["label"] == "game.zip", "el wallpaper lleva el nombre del juego"


def test_art_label_prefers_name_over_filename():
    art = _call("randomGameArt", {"system": "snes", "filename": "f.zip",
                                  "name": "Sonic", "has_art": False})
    assert art["label"] == "Sonic"


def test_card_has_wallpaper_and_cover_nodes():
    h = _html()
    for node in ("dash-random-media", "dash-random-ph", "dash-random-ph-name",
                 "dash-random-cover"):
        assert f'id="{node}"' in h, f"falta el nodo {node}"


def test_media_column_is_a_thumbnail():
    # La carátula acompaña a la info: una franja estrecha (~mitad de antes),
    # no media tarjeta. Sigue siendo vertical (2/3).
    css = _html()
    m = re.search(r"\.dash-random-body\{([^}]*)\}", css)
    assert m, "falta la regla .dash-random-body"
    cols = re.search(r"grid-template-columns:minmax\((\d+)px,\s*(\d+)px\)", m.group(1))
    assert cols, "la columna de imagen se define con minmax(<min>px, <max>px)"
    lo, hi = int(cols.group(1)), int(cols.group(2))
    assert hi <= 100, f"la carátula es una miniatura: {hi}px es demasiado ancha"
    assert 60 <= lo < hi, "la miniatura debe seguir viéndose"

    media = re.search(r"\.dash-random-media\{([^}]*)\}", css)
    assert media and "aspect-ratio:2/3" in media.group(1), "la imagen sigue siendo vertical"

    mob = re.search(r"@media \(max-width:760px\)\{([^\n]*)\}", css)
    assert mob and "dash-random-media" in mob.group(1), \
        "en móvil la miniatura no debe crecer a pantalla completa"


def test_renderRandomGame_falls_back_when_cover_fails():
    m = re.search(r"function renderRandomGame\(g\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta renderRandomGame()"
    body = m.group(1)
    assert "randomGameArt(" in body, "la imagen sale de randomGameArt()"
    assert "onerror" in body, "si la carátula no carga se pinta el wallpaper"
    assert "dash-random-ph" in body
