"""Tests de estructura del landing y del dashboard rediseñado.

Comprueban que `templates/index.html` y `app.py` contienen los enganches
esperados (marcado, funciones JS y endpoints). No ejecutan el JS.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"
APP = ROOT / "app.py"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _app() -> str:
    return APP.read_text(encoding="utf-8")


# ─── A4: endpoints ─────────────────────────────────────────────────────

def test_endpoints_declared():
    src = _app()
    assert '"/api/game-stats"' in src
    assert '"/api/random-game"' in src
    assert "collect_play_stats(" in src
    assert "pick_random_game(" in src


# ─── B1: overlay de landing ────────────────────────────────────────────

def test_landing_overlay_markup():
    h = _html()
    assert 'id="landing"' in h
    assert 'class="landing-ring' in h
    assert 'onclick="dismissLanding()"' in h
    assert 'id="landing-never"' in h
    assert "@keyframes" in h
    assert ".landing.hidden" in h


# ─── B2: JS del landing ────────────────────────────────────────────────

def test_landing_js_wiring():
    h = _html()
    assert "function initLanding(" in h
    assert "function dismissLanding(" in h
    assert "function loadLandingFacts(" in h
    assert "bcm_landing_skip" in h
    assert "/api/bios/missing" in h


# ─── B3: boot ──────────────────────────────────────────────────────────

def test_boot_calls_init_landing_without_blocking():
    h = _html()
    assert "initLanding();" in h
    assert h.index("initLanding();") < h.index("init();")

