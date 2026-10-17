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


# ── Recuento de sistemas con ROMs ─────────────────────────────────────
# El banner del dashboard mostraba `systems_count`, que son los sistemas
# *creados a mano* (es_systems_*.cfg), no los que tienen ROMs.

def test_count_rom_systems_counts_systems_with_roms(appmod, tmp_path):
    s = _settings(appmod, tmp_path)
    for name in ("ps2", "snes", "dreamcast"):
        (tmp_path / "roms" / name).mkdir(parents=True)
    (tmp_path / "roms" / "ps2" / "juego.iso").write_bytes(b"x")
    (tmp_path / "roms" / "snes" / "juego.sfc").write_bytes(b"x")
    (tmp_path / "roms" / "dreamcast" / "juego.chd").write_bytes(b"x")

    assert appmod.count_rom_systems(s) == 3


def test_count_rom_systems_skips_empty_dirs(appmod, tmp_path):
    s = _settings(appmod, tmp_path)
    (tmp_path / "roms" / "ps2").mkdir(parents=True)
    (tmp_path / "roms" / "vacio").mkdir(parents=True)
    (tmp_path / "roms" / "ps2" / "juego.iso").write_bytes(b"x")

    assert appmod.count_rom_systems(s) == 1


def test_count_rom_systems_ignores_non_rom_files(appmod, tmp_path):
    """Una carpeta con solo gamelist/portadas/notas no es un sistema con ROMs."""
    s = _settings(appmod, tmp_path)
    sys_dir = tmp_path / "roms" / "ps2"
    (sys_dir / "images").mkdir(parents=True)
    (sys_dir / "gamelist.xml").write_text("<gameList/>", encoding="utf-8")
    (sys_dir / "images" / "juego.png").write_bytes(b"x")
    (sys_dir / "notas.txt").write_text("hola", encoding="utf-8")

    assert appmod.count_rom_systems(s) == 0


def test_count_rom_systems_counts_game_subdir(appmod, tmp_path):
    """Ports/motores guardan el juego en una subcarpeta: iortcw/main, pygame/pygun."""
    s = _settings(appmod, tmp_path)
    (tmp_path / "roms" / "iortcw" / "main").mkdir(parents=True)

    assert appmod.count_rom_systems(s) == 1


def test_count_rom_systems_ignores_media_and_asset_dirs(appmod, tmp_path):
    """`media/`, `images/`, `videos/` y `manuals/` son assets, no juegos."""
    s = _settings(appmod, tmp_path)
    sys_dir = tmp_path / "roms" / "ps2"
    for sub in ("media", "images", "videos", "manuals", ".data"):
        (sys_dir / sub).mkdir(parents=True)
    (sys_dir / "media" / "juego.mp4").write_bytes(b"x")
    (sys_dir / "_info.txt").write_text("x", encoding="utf-8")

    assert appmod.count_rom_systems(s) == 0


def test_count_rom_systems_without_roms_base_is_zero(appmod, tmp_path):
    s = _settings(appmod, tmp_path)
    assert appmod.count_rom_systems(s) == 0


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
