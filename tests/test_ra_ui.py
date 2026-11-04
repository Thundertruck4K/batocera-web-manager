"""Tests de la sección de Logros en la SPA.

Comprueban el código fuente del frontend: que la ruta exista, que la
sección ya no esté marcada como *Pronto* en el menú, que avise cuando no
hay cuenta configurada y que cada tarjeta use la carátula local con un
icono según el estado del juego.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"

NAV = SRC / "lib" / "nav.ts"
API = SRC / "lib" / "api.ts"
APP = SRC / "App.tsx"
PAGE = SRC / "pages" / "Achievements.tsx"
CARD = SRC / "components" / "achievements" / "AchievementCard.tsx"


def _read(path: Path) -> str:
    assert path.exists(), f"falta {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


# ── Ruta y menú ────────────────────────────────────────────────────────

def test_la_seccion_tiene_ruta():
    app = _read(APP)
    assert 'path="/retroachievements"' in app
    assert "AchievementsPage" in app


def test_el_menu_ya_no_marca_logros_como_pendiente():
    nav = _read(NAV)
    linea = next(l for l in nav.splitlines() if "'/retroachievements'" in l)
    assert "pending" not in linea, "la sección de logros ya está implementada"
    assert "Trophy" in linea


def test_la_seccion_llama_al_endpoint_nuevo():
    api = _read(API)
    assert "'/api/retroachievements/games'" in api


# ── Avisos ─────────────────────────────────────────────────────────────

def test_avisa_si_no_hay_cuenta_configurada():
    page = _read(PAGE)
    assert "!data.configured" in page
    assert "Configura tu cuenta de RetroAchievements" in page
    assert "navigate('/configuracion')" in page


def test_avisa_si_la_integracion_esta_desactivada():
    page = _read(PAGE)
    assert "!data.enabled" in page
    assert "RetroAchievements está desactivado" in page


def test_muestra_el_perfil_y_los_premios():
    page = _read(PAGE)
    assert "data?.profile" in page
    assert "data?.awards" in page


# ── Tarjetas ───────────────────────────────────────────────────────────

def test_la_tarjeta_usa_la_caratula_local():
    card = _read(CARD)
    assert "/api/rom-image/" in card
    assert "subpath" in card
    # y el icono de RA queda como respaldo
    assert "game.icon" in card


def test_la_tarjeta_tiene_un_icono_por_estado():
    card = _read(CARD)
    for icono in ("Trophy", "Medal", "Award", "Star", "Sparkles", "Lock"):
        assert icono in card, f"falta el icono {icono}"


def test_la_tarjeta_pinta_el_progreso():
    card = _read(CARD)
    assert "num_awarded" in card and "max_possible" in card
    assert "percent" in card


def test_la_pagina_ordena_los_juegos():
    page = _read(PAGE)
    assert "Mis logros" in page
    assert "% completado" in page
    assert "Logros del juego" in page
