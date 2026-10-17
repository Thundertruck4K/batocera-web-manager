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


# ─── C1: hero ──────────────────────────────────────────────────────────

def test_dashboard_hero_markup():
    h = _html()
    assert 'id="dash-hero"' in h
    assert 'id="dash-hero-stats"' in h
    assert "function renderHero(" in h


def test_hero_systems_counts_rom_systems_not_custom(appmod):
    """El banner debe contar los sistemas con ROMs, no los creados a mano.

    `systems_count` son los `es_systems_*.cfg` (pestaña "Sistemas Creados");
    el hero usa `rom_systems_count` (sistemas con ≥1 ROM) para no mostrar
    solo los 4 sistemas añadidos a mano.
    """
    h = _html()
    assert "rom_systems_count" in h, "el hero debe usar rom_systems_count"
    assert "rom_systems_count" in _app(), "/api/info debe exponerlo"
    # El hero no debe volver a caer en el recuento de sistemas personalizados.
    hero = h.split("function renderHero(", 1)[1].split("function ", 1)[0]
    assert "systems_count" not in hero or "rom_systems_count" in hero


# ─── C2: juego al azar ─────────────────────────────────────────────────

def test_random_game_card_markup():
    h = _html()
    assert 'id="dash-random-game"' in h
    assert "function loadRandomGame(" in h
    assert "function renderRandomGame(" in h
    assert "/api/random-game" in h


# ─── C3: analítica ─────────────────────────────────────────────────────

def test_playstats_markup():
    h = _html()
    assert 'id="dash-playstats"' in h
    assert 'id="dash-activity"' in h
    assert "function renderPlayStats(" in h


def test_activity_svg_path():
    h = _html()
    assert "polyline points=" in h


# ─── C4: monitoreo técnico conservado ──────────────────────────────────

def test_tecnico_conservado():
    h = _html()
    for anchor in ('id="dash-kpis"', 'id="dash-row1"', 'id="dash-row2"',
                   'id="dash-row-storage-fans"', 'id="dash-storage"', 'id="dash-row-fans"',
                   'id="dash-news"', 'id="dash-es-info"'):
        assert anchor in h, f"falta {anchor}"


