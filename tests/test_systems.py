"""Tests de sistemas/ROMs: BIOS, logos y validación de rutas."""

import pytest


def _settings(appmod, tmp_path):
    s = dict(appmod.DEFAULT_SETTINGS)
    s["roms_base"] = str(tmp_path / "roms")
    s["themes_user"] = str(tmp_path / "themes")
    s["themes_sys"] = str(tmp_path / "themes_sys")
    return s


def test_get_rom_systems_has_bios_false_for_nobios_platform(appmod, tmp_path):
    """`nes` no requiere BIOS: no debe anunciarse como que sí."""
    s = _settings(appmod, tmp_path)
    (tmp_path / "roms" / "nes").mkdir(parents=True)

    result = appmod.get_rom_systems(s, fast=True)

    nes = next(r for r in result if r["name"] == "nes")
    assert nes["has_bios"] is False
    assert nes["bios_count"] == 0


def test_get_rom_systems_has_bios_true_for_bios_platform(appmod, tmp_path):
    s = _settings(appmod, tmp_path)
    (tmp_path / "roms" / "psx").mkdir(parents=True)

    result = appmod.get_rom_systems(s, fast=True)

    psx = next(r for r in result if r["name"] == "psx")
    assert psx["has_bios"] is True
    assert psx["bios_count"] > 0


def test_find_system_logo_searches_system_themes(appmod, tmp_path):
    """Los logos de los temas de sistema (/usr/share/...) también valen."""
    s = _settings(appmod, tmp_path)
    logo = tmp_path / "themes_sys" / "es-theme-carbon" / "snes" / "art" / "logo.png"
    logo.parent.mkdir(parents=True)
    logo.write_bytes(b"\x89PNG")

    found = appmod.find_system_logo(s, "snes", "es-theme-carbon")

    assert found is not None
    assert found.read_bytes() == b"\x89PNG"


def test_find_system_logo_prefers_user_theme(appmod, tmp_path):
    s = _settings(appmod, tmp_path)
    for base in ("themes", "themes_sys"):
        p = tmp_path / base / "t" / "snes" / "art" / "logo.png"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"\x89PNG-" + base.encode())

    found = appmod.find_system_logo(s, "snes", "t")

    assert found == (tmp_path / "themes" / "t" / "snes" / "art" / "logo.png").resolve()


def test_find_system_logo_rejects_traversal(appmod, tmp_path):
    """`system` con `..` no debe salir de la raíz de temas."""
    s = _settings(appmod, tmp_path)
    # themes/t/../../secret/art/logo.png  →  tmp/secret/art/logo.png
    secret = tmp_path / "secret" / "art" / "logo.png"
    secret.parent.mkdir(parents=True)
    secret.write_bytes(b"secret")

    found = appmod.find_system_logo(s, "../../secret", "t")

    assert found is None
