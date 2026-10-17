# -*- coding: utf-8 -*-
"""Tests de los metadatos de la tarjeta "Juego al azar" (backend).

La tarjeta mostraba solo imagen + nombre + slug del sistema. Ahora enriquece
con datos que ya existen en el `gamelist.xml` del juego elegido: plataforma
(nombre amigable), año, género, editor, jugadores, sinopsis y uso real
(veces jugado, tiempo, última vez).

Nada se inventa: si el ROM no está scrapeado, `read_game_meta` devuelve {}.
"""
from __future__ import annotations

from pathlib import Path

GAMELIST = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
  <game>
    <path>./Area 51.iso</path>
    <name>Area 51</name>
    <desc>Shooter en primera persona en la base secreta.</desc>
    <genre>Disparos / 1&#170; persona</genre>
    <publisher>Midway</publisher>
    <developer>Midway Studios</developer>
    <players>1-2</players>
    <releasedate>20050101T000000</releasedate>
    <playcount>3</playcount>
    <gametime>4200</gametime>
    <lastplayed>20261012T111243</lastplayed>
  </game>
  <game>
    <path>./otro.iso</path>
    <name>Otro</name>
  </game>
</gameList>
"""


def _setup(tmp_path: Path) -> Path:
    sys_dir = tmp_path / "ps2"
    sys_dir.mkdir(parents=True, exist_ok=True)
    sys_dir.joinpath("gamelist.xml").write_text(GAMELIST, encoding="utf-8")
    return tmp_path


# ── friendly_system_name ────────────────────────────────────────────────────

def test_friendly_system_name_known(appmod):
    assert appmod.friendly_system_name("ps2") == "PlayStation 2"


def test_friendly_system_name_unknown_falls_back_to_slug(appmod):
    assert appmod.friendly_system_name("sistema_raro") == "sistema_raro"


def test_friendly_system_name_maps_gamecube_slug(appmod):
    """El catálogo usa la clave corta `gc`; el slug de Batocera es `gamecube`."""
    assert appmod.friendly_system_name("gamecube") == "GameCube"


def test_friendly_system_name_maps_dreamcast_slug(appmod):
    assert appmod.friendly_system_name("dreamcast") == "Dreamcast"


def test_friendly_system_name_maps_pcengine_slug(appmod):
    assert appmod.friendly_system_name("pcengine") == "PC Engine"


def test_friendly_system_name_maps_atari800_slug(appmod):
    assert appmod.friendly_system_name("atari800") == "Atari 800"


# ── read_game_meta ──────────────────────────────────────────────────────────

def test_read_game_meta_returns_text_and_usage(appmod, tmp_path):
    base = _setup(tmp_path)

    meta = appmod.read_game_meta(base, "ps2", "Area 51.iso")

    assert meta["name"] == "Area 51"
    assert meta["year"] == "2005"
    assert "Disparos" in meta["genre"]
    assert meta["publisher"] == "Midway"
    assert meta["players"] == "1-2"
    assert "Shooter" in meta["desc"]
    assert meta["playcount"] == 3
    assert meta["gametime_s"] == 4200
    assert meta["lastplayed"] == "2026-10-12"


def test_read_game_meta_falls_back_to_developer(appmod, tmp_path):
    base = _setup(tmp_path)
    gl = base / "ps2" / "gamelist.xml"
    gl.write_text(
        GAMELIST.replace("<publisher>Midway</publisher>", ""), encoding="utf-8")

    meta = appmod.read_game_meta(base, "ps2", "Area 51.iso")

    assert meta["publisher"] == "Midway Studios", "sin publisher usa developer"


def test_read_game_meta_omits_missing_fields(appmod, tmp_path):
    base = _setup(tmp_path)

    meta = appmod.read_game_meta(base, "ps2", "otro.iso")

    assert meta["name"] == "Otro"
    assert "desc" not in meta
    assert "year" not in meta
    assert meta.get("playcount", 0) == 0


def test_read_game_meta_empty_when_rom_not_in_gamelist(appmod, tmp_path):
    base = _setup(tmp_path)
    assert appmod.read_game_meta(base, "ps2", "no-existe.iso") == {}


def test_read_game_meta_empty_without_gamelist(appmod, tmp_path):
    (tmp_path / "ps2").mkdir()
    assert appmod.read_game_meta(tmp_path, "ps2", "Area 51.iso") == {}


# ── pick_random_game enriquecido ────────────────────────────────────────────

def _rom_with_art(tmp_path: Path, system: str, filename: str) -> Path:
    sys_dir = tmp_path / system
    (sys_dir / "images").mkdir(parents=True, exist_ok=True)
    (sys_dir / filename).write_bytes(b"x")
    (sys_dir / "images" / (Path(filename).stem + "-image.png")).write_bytes(b"x")
    return tmp_path


def test_pick_random_game_includes_friendly_platform(appmod, tmp_path, monkeypatch):
    base = _setup(tmp_path)
    _rom_with_art(base, "ps2", "Area 51.iso")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    game = appmod.pick_random_game(base)

    assert game["system"] == "ps2"
    assert game["system_name"] == "PlayStation 2"


def test_pick_random_game_includes_text_meta(appmod, tmp_path, monkeypatch):
    base = _setup(tmp_path)
    _rom_with_art(base, "ps2", "Area 51.iso")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    game = appmod.pick_random_game(base)

    assert game["year"] == "2005"
    assert game["genre"].startswith("Disparos")
    assert game["playcount"] == 3


def test_pick_random_game_uses_gamelist_name(appmod, tmp_path, monkeypatch):
    """El nombre de la gamelist es más legible que el del fichero."""
    base = _setup(tmp_path)
    _rom_with_art(base, "ps2", "Area 51.iso")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    game = appmod.pick_random_game(base)

    assert game["name"] == "Area 51"
    assert game["filename"] == "Area 51.iso"


def test_pick_random_game_survives_without_gamelist(appmod, tmp_path, monkeypatch):
    base = _rom_with_art(tmp_path, "snes", "mario.zip")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    game = appmod.pick_random_game(base)

    assert game["system"] == "snes"
    assert game["system_name"] == "Super Nintendo Entertainment System"
    assert game["name"] == "mario", "sin gamelist cae al nombre del fichero"
    assert "desc" not in game
