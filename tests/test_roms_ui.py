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


# ── /api/bios/missing (colección de BIOS faltantes) ───────────────


def _file(name, *, exists, md5_ok, mandatory=True, desc="BIOS"):
    return {
        "file": name,
        "desc": desc,
        "mandatory": mandatory,
        "exists": exists,
        "md5_ok": md5_ok,
        "expected_md5": None,
    }


def test_collect_missing_bios_ok_when_nothing_missing(appmod, monkeypatch):
    """Regresión: si un sistema tiene BIOS y ninguna falta, no debe reventar.

    El `append` quedó fuera del bucle y referenciaba variables no asignadas,
    lo que provocaba un cierre de conexión sin respuesta (ERR_EMPTY_RESPONSE).
    """
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("x.bin", exists=True, md5_ok=True)]},
    )
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    items = appmod.collect_missing_bios([{"name": "n64"}], Path("bios"))
    assert items == []


def test_collect_missing_bios_enriches_type_and_manufacturer(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("neogeo.zip", exists=False, md5_ok=None)]},
    )
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    items = appmod.collect_missing_bios([{"name": "neogeo"}], Path("bios"))
    assert len(items) == 1
    assert items[0]["type"] == "Arcade"
    assert items[0]["manufacturer"] == "SNK"
    assert items[0]["skip_key"] == "neogeo/neogeo.zip"


def test_collect_missing_bios_prefers_system_meta(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("z.bin", exists=False, md5_ok=None)]},
    )
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    usys = {"name": "zzz", "type": "Personalizada", "manufacturer": "Acme"}
    items = appmod.collect_missing_bios([usys], Path("bios"))
    assert items[0]["type"] == "Personalizada"
    assert items[0]["manufacturer"] == "Acme"


def test_collect_missing_bios_respects_skips(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("y.bin", exists=False, md5_ok=None)]},
    )
    monkeypatch.setattr(appmod, "_missing_bios_skipped", {"nes/y.bin"})
    assert appmod.collect_missing_bios([{"name": "nes"}], Path("bios")) == []


def test_collect_missing_bios_ignores_unknown_systems(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_check_bios_grouped", lambda slug, d: None)
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    assert appmod.collect_missing_bios([{"name": "desconocido"}], Path("bios")) == []


def test_collect_missing_bios_reports_bad_md5(appmod, monkeypatch):
    """Un fichero presente con MD5 incorrecto también cuenta como faltante."""
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("bad.bin", exists=True, md5_ok=False)]},
    )
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    items = appmod.collect_missing_bios([{"name": "nes"}], Path("bios"))
    assert len(items) == 1
    assert items[0]["exists"] is True and items[0]["md5_ok"] is False


def test_collect_missing_bios_survives_broken_system(appmod, monkeypatch):
    """Un sistema que falla no debe tumbar el listado entero."""

    def fake(slug, d):
        if slug == "roto":
            raise OSError("permiso denegado")
        return {"known": True, "files": [_file("ok.bin", exists=False, md5_ok=None)]}

    monkeypatch.setattr(appmod, "_check_bios_grouped", fake)
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    items = appmod.collect_missing_bios(
        [{"name": "roto"}, {"name": "nes"}], Path("bios"))
    assert [i["system"] for i in items] == ["nes"]


def test_collect_missing_bios_ignores_entry_without_name(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "_check_bios_grouped",
        lambda slug, d: {"known": True, "files": [_file("a.bin", exists=False, md5_ok=None)]})
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    assert appmod.collect_missing_bios([{}], Path("bios")) == []


# ── Blindaje del servidor (evita ERR_EMPTY_RESPONSE) ──────────────


def test_http_methods_are_guarded(appmod):
    """do_GET/POST/DELETE deben ir envueltos por `_safe_api`."""
    for name in ("do_GET", "do_POST", "do_DELETE"):
        fn = getattr(appmod.BatoceraHandler, name)
        assert getattr(fn, "_safe_api", False) is True, f"{name} no está blindado"


def test_safe_api_returns_json_500_on_exception(appmod):
    """Si el handler revienta, se responde 500 en JSON en vez de nada."""
    calls = []

    class Fake:
        def send_json(self, data, status=200):
            calls.append((data, status))

        def boom(self):
            raise RuntimeError("vaya")

    appmod._safe_api(lambda self: self.boom())(Fake())

    assert calls, "el wrapper no respondió"
    data, status = calls[0]
    assert status == 500
    assert data.get("ok") is False


# ── /api/rom-systems (resumen que alimenta los chips TIPO/FABRICANTE) ──


def _full_system(**over):
    base = {
        "name": "nes", "path": "/userdata/roms/nes",
        "rom_count": 120, "media_count": 8, "total_size": 1048576,
        "size_human": "1.0 MB", "has_gamelist": True,
        "roms": [{"file": "a.zip"}], "is_empty": False,
        "has_bios": True, "bios_count": 3, "has_logo": True,
        "type": "Consolas", "manufacturer": "Nintendo",
        "platform": "nes", "release": "1983",
        "fullname": "Nintendo Entertainment System",
    }
    base.update(over)
    return base


def test_rom_system_summary_keeps_filter_fields(appmod):
    """El resumen DEBE llevar type/manufacturer; si no, los chips salen vacíos.

    Regresión: el endpoint recortaba los campos y sólo aparecían 'Todos/Otros'.
    """
    s = appmod.rom_system_summary(_full_system())
    assert s["type"] == "Consolas"
    assert s["manufacturer"] == "Nintendo"
    assert s["platform"] == "nes"
    assert s["release"] == "1983"
    assert s["fullname"] == "Nintendo Entertainment System"


def test_rom_system_summary_drops_heavy_fields(appmod):
    s = appmod.rom_system_summary(_full_system())
    assert "roms" not in s
    assert "path" not in s
    assert "total_size" not in s


def test_rom_system_summary_defaults(appmod):
    s = appmod.rom_system_summary({
        "name": "zzz", "rom_count": 0, "media_count": 0, "size_human": "0 B",
        "is_empty": True, "has_gamelist": False, "has_bios": False, "bios_count": 0,
    })
    assert s["type"] == "Otros"
    assert s["manufacturer"] == ""
    assert s["fullname"] == "zzz"
    assert s["has_logo"] is False


def test_rom_systems_endpoint_uses_summary(appmod):
    """El endpoint debe serializar con `rom_system_summary` (no recortar a mano)."""
    src = Path(appmod.__file__).read_text(encoding="utf-8")
    assert "rom_system_summary(x) for x in systems" in src

