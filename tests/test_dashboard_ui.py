"""Tests de la página de control (dashboard) de la SPA.

Tres cosas se-arreglaron:

- La tarjeta *Sistemas* mostraba `systems_count` (los sistemas **personalizados**
  que gestiona el manager) en vez de los sistemas con juegos de la biblioteca.
- La tarjeta *Juegos* mostraba el total del `gamelist.xml` (los juegos
  catalogados) en vez de los juegos que hay de verdad en el disco.
- La tarjeta *Juego al azar* se quedaba vacía hasta que se pulsaba «Girar»: al
  cargar la app se pide ya un juego, con su carátula y sus metadatos.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
DASH = SRC / "pages" / "Dashboard.tsx"
CARD = SRC / "components" / "dashboard" / "RandomGameCard.tsx"
API = SRC / "lib" / "api.ts"
TYPES = SRC / "lib" / "types.ts"
APP = ROOT / "app.py"


def _read(path: Path) -> str:
    assert path.exists(), f"falta {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _bloque(src: str, inicio: str) -> str:
    """Trozo de código desde `inicio` hasta la siguiente exportación."""
    i = src.index(inicio)
    resto = src[i:]
    import re
    m = re.search(r"\nexport ", resto[len(inicio):])
    if m:
        return resto[: len(inicio) + m.start()]
    return resto


# ── La tarjeta de sistemas ─────────────────────────────────────────────

def test_la_tarjeta_de_sistemas_enseña_los_sistemas_con_juegos():
    src = _read(DASH)
    tarjeta = src.split('label="Sistemas"', 1)[1].split("/>", 1)[0]
    assert "rom_systems_count" in tarjeta, \
        "el número grande debe ser los sistemas con juegos, no los personalizados"
    assert "systems_count" not in tarjeta.split("rom_systems_count")[0], \
        "los personalizados van en el texto de apoyo, no en el número"


def test_el_backend_expone_el_recuento_del_disco():
    src = _read(APP)
    assert '"disk_games_count":disco["games"]' in src
    assert '"disk_systems_count":disco["systems"]' in src


def test_el_tipo_de_la_info_declara_los_nuevos_campos():
    types = _read(TYPES)
    assert "disk_games_count: number" in types
    assert "disk_systems_count: number" in types


# ── La tarjeta de juegos ───────────────────────────────────────────────

def test_la_tarjeta_de_juegos_usa_el_total_del_disco():
    src = _read(DASH)
    tarjeta = src.split('label="Juegos"', 1)[1].split("/>", 1)[0]
    assert "disk_games_count" in tarjeta, \
        "el total de juegos es el que hay en el disco, no el del gamelist"


# ── La tarjeta de juego al azar ────────────────────────────────────────

def test_el_dashboard_pide_un_juego_al_azar_al_cargar():
    src = _read(DASH)
    assert "useEffect(" in src, "la carga inicial va en un efecto"
    efecto = src.split("useEffect(", 1)[1].split("}, [])", 1)[0]
    assert "api.randomGame()" in efecto, "al montar se pide un juego al azar"
    assert "setRandomGame(" in efecto


def test_el_boton_de_girar_sigue_estando():
    card = _read(CARD)
    assert "onRoll" in card, "el botón «Girar» sigue ahí"
    assert "Girar" in card
    assert "Girando…" in card


def test_la_tarjeta_avisa_si_no_hay_juegos():
    card = _read(CARD)
    assert "No hay juegos en la biblioteca todavía." in card


def test_la_tarjeta_muestra_los_metadatos_del_juego():
    card = _read(CARD)
    for campo in ("game.name", "game.system_name", "game.meta?.desc",
                  "game.meta?.genre", "game.meta?.year", "game.meta?.publisher"):
        assert campo in card, f"falta {campo}"


# ── La lista de ROMs ───────────────────────────────────────────────────

def test_la_lista_de_roms_no_tiene_seccion_de_otros_ficheros():
    """El backend ya deja fuera lo que no es juego: la sección sobra."""
    src = _read(SRC / "components" / "scraper" / "RomFolderView.tsx")
    assert "Otros ficheros" not in src
    assert "const others" not in src
