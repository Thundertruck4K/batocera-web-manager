"""Tests del panel ROMs & BIOS.

Cubren dos regresiones reales:
  1) el grid de sistemas debe seguir siendo multicolumna (las cabeceras de
     sección deben ocupar todo el ancho), y
  2) los helpers de filtrado deben existir una sola vez y estar conectados
     a los chips (una definición duplicada dejaba los filtros inertes).

Además validan la clasificación por tipo/fabricante (`_classify_system`),
que actúa de respaldo cuando el slug no aparece en los es_systems.cfg.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _region(start: str, end: str) -> str:
    src = _html()
    i = src.index(start)
    j = src.index(end, i)
    return src[i:j]


# ── Estructura del grid ───────────────────────────────────────────


def test_roms_grid_is_multicolumn():
    """El contenedor de sistemas debe ser un grid multicolumna, no una lista."""
    m = re.search(r'id="roms-systems-grid"[^>]*style="([^"]*)"', _html())
    assert m, "no se encontró #roms-systems-grid"
    style = m.group(1).replace(" ", "")
    assert "display:grid" in style, style
    assert "auto-fill" in style or "auto-fit" in style, style


def test_rom_type_header_spans_full_width():
    """Cada cabecera de tipo debe ocupar todo el ancho del grid.

    Si no lo hace, la sección cae en una sola celda del grid exterior y las
    tarjetas terminan apiladas en una única columna.
    """
    body = _region("function renderRomSystems", "function toggleRomTypeSection")
    header_ok = re.search(r"rom-type-header[^>]*grid-column:1/-1", body)
    section_ok = re.search(r"rom-type-section[^>]*grid-column:1/-1", body)
    assert header_ok or section_ok, (
        "la cabecera/sección de tipo necesita grid-column:1/-1 para que el "
        "grid multicolumna funcione"
    )


# ── Filtros (chips) ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "renderRomSystems",
        "toggleRomTypeSection",
        "populateRomFilters",
        "toggleRomTypeFilter",
        "toggleRomMfrFilter",
        "filterRomSystems",
        "romSystemCard",
    ],
)
def test_roms_helper_defined_once(name):
    """Cada helper debe existir exactamente una vez.

    Una segunda definición de `filterRomSystems` (sin filtros) sobrescribía
    la buena y dejaba los chips inertes.
    """
    count = len(re.findall(r"function\s+" + name + r"\s*\(", _html()))
    assert count == 1, f"{name} definido {count} veces (se esperaba 1)"


def test_roms_filter_state_declared():
    html = _html()
    for decl in ("_romCollapsedTypes", "_romTypeFilter", "_romMfrFilter"):
        assert re.search(r"(const|let|var)\s+" + decl + r"\b", html), (
            f"falta la declaración de {decl}"
        )


def test_roms_filter_chips_containers_present():
    html = _html()
    assert 'id="rom-type-chips"' in html
    assert 'id="rom-mfr-chips"' in html


# ── Clasificación por tipo / fabricante ───────────────────────────


@pytest.mark.parametrize(
    "slug,expected_type,expected_mfr",
    [
        ("mame", "Arcade", ""),
        ("neogeo", "Arcade", "SNK"),
        ("nes", "Consolas", "Nintendo"),
        ("snes", "Consolas", "Nintendo"),
        ("ps2", "Consolas", "Sony"),
        ("megadrive", "Consolas", "Sega"),
        ("atari2600", "Consolas", "Atari"),
        ("switch", "Portátiles", "Nintendo"),
        ("gba", "Portátiles", "Nintendo"),
        ("amiga1200", "Ordenadores", "Commodore"),
        ("zxspectrum", "Ordenadores", "Sinclair"),
    ],
)
def test_classify_system_known(appmod, slug, expected_type, expected_mfr):
    typ, mfr = appmod._classify_system(slug)
    assert typ == expected_type, f"{slug}: tipo {typ!r} != {expected_type!r}"
    assert mfr == expected_mfr, f"{slug}: fabricante {mfr!r} != {expected_mfr!r}"


def test_classify_system_no_substring_false_positive(appmod):
    """\"n64\" no debe colarse dentro de \"dragon64\"."""
    _typ, mfr = appmod._classify_system("dragon64")
    assert mfr != "Nintendo"


def test_classify_system_unknown_defaults_to_console(appmod):
    typ, _mfr = appmod._classify_system("slug-desconocido-xyz")
    assert typ == "Consolas"


def test_system_type_name_maps_hardware(appmod):
    assert appmod.system_type_name("console") == "Consolas"
    assert appmod.system_type_name("portable") == "Portátiles"
    assert appmod.system_type_name("computer") == "Ordenadores"
    assert appmod.system_type_name("arcade") == "Arcade"
    assert appmod.system_type_name("") == "Otros"
