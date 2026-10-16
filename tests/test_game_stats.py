"""Tests de la analítica de juego del dashboard (backend).

Cubren:
- `find_user_art`: priorizar el arte de usuario (media del usuario) sobre el scraped.
- `collect_play_stats`: agregar playcount/lastplayed/playtime desde gamelist.xml.
- `pick_random_game`: elegir un juego al azar entre los que tienen arte.
"""
from __future__ import annotations

from pathlib import Path


# ─── A1: find_user_art ─────────────────────────────────────────────────

def test_find_user_art_prefers_user_media(appmod, tmp_path):
    sys_dir = tmp_path / "snes"
    (sys_dir / "media" / "images").mkdir(parents=True)
    (sys_dir / "images").mkdir(parents=True)
    (sys_dir / "mixrbv2").mkdir(parents=True)
    (sys_dir / "media" / "images" / "game.png").write_bytes(b"x")
    (sys_dir / "images" / "game-image.png").write_bytes(b"x")
    (sys_dir / "mixrbv2" / "game-mixrbv2.png").write_bytes(b"x")
    (sys_dir / "gamelist.xml").write_text(
        "<gameList><game><path>./game.zip</path>"
        "<image>./images/game-image.png</image></game></gameList>",
        encoding="utf-8",
    )

    art = appmod.find_user_art(tmp_path, "snes", "game.zip")
    names = [p.name for p in art]
    assert names[0] == "game.png", "media/images debe ganar"
    assert names.index("game-image.png") < names.index("game-mixrbv2.png")


def test_find_user_art_falls_back_to_gamelist_image(appmod, tmp_path):
    sys_dir = tmp_path / "nes"
    sys_dir.mkdir()
    (sys_dir / "art.png").write_bytes(b"x")
    (sys_dir / "gamelist.xml").write_text(
        "<gameList><game><path>./mario.zip</path>"
        "<image>./art.png</image></game></gameList>",
        encoding="utf-8",
    )

    art = appmod.find_user_art(tmp_path, "nes", "mario.zip")
    assert [p.name for p in art] == ["art.png"]


def test_find_user_art_empty_when_nothing(appmod, tmp_path):
    (tmp_path / "gg").mkdir()
    assert appmod.find_user_art(tmp_path, "gg", "sonic.zip") == []


# ─── A2: collect_play_stats ────────────────────────────────────────────

def _write_gamelist(sys_dir: Path, games: list[tuple]) -> None:
    sys_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path, name, playcount, lastplayed, playtime in games:
        rows.append(
            "<game>"
            f"<path>./{path}</path><name>{name}</name>"
            f"<playcount>{playcount}</playcount>"
            f"<lastplayed>{lastplayed}</lastplayed>"
            f"<playtime>{playtime}</playtime>"
            "</game>"
        )
    sys_dir.joinpath("gamelist.xml").write_text(
        "<gameList>" + "".join(rows) + "</gameList>", encoding="utf-8"
    )


def test_collect_play_stats_aggregates(appmod, tmp_path):
    _write_gamelist(tmp_path / "snes", [
        ("gameA.zip", "Game A", 5, "20261010T120000", 3600),
        ("gameB.zip", "Game B", 2, "", 0),
    ])
    _write_gamelist(tmp_path / "nes", [
        ("gameC.zip", "Game C", 1, "20261001T090000", 0),
    ])

    s = appmod.collect_play_stats(tmp_path)
    assert s["ok"] is True
    assert s["totals"] == {"games": 3, "playcount": 8, "playtime_s": 3600, "systems": 2}
    assert s["has_playtime"] is True
    assert s["top_games"][0]["name"] == "Game A"
    assert {"date": "2026-10-10", "count": 1} in s["activity"]


def test_collect_play_stats_without_playtime(appmod, tmp_path):
    _write_gamelist(tmp_path / "nes", [("gameC.zip", "Game C", 1, "20261001T090000", 0)])
    s = appmod.collect_play_stats(tmp_path)
    assert s["has_playtime"] is False
    assert s["totals"]["playtime_s"] == 0
    assert s["top_games"][0]["playcount"] == 1


def test_collect_play_stats_missing_dir_is_safe(appmod, tmp_path):
    s = appmod.collect_play_stats(tmp_path / "nope")
    assert s["ok"] is True
    assert s["totals"]["games"] == 0


# ─── A3: pick_random_game ──────────────────────────────────────────────

def test_pick_random_game_returns_game_with_art(appmod, tmp_path, monkeypatch):
    sys_dir = tmp_path / "snes"
    (sys_dir / "images").mkdir(parents=True)
    (sys_dir / "gameA.zip").write_bytes(b"x")
    (sys_dir / "gameB.zip").write_bytes(b"x")
    (sys_dir / "images" / "gameA-image.png").write_bytes(b"x")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    game = appmod.pick_random_game(tmp_path)
    assert game is not None
    assert game["system"] == "snes"
    assert game["filename"] == "gameA.zip"
    assert game["has_art"] is True


def test_pick_random_game_none_without_art(appmod, tmp_path):
    sys_dir = tmp_path / "snes"
    sys_dir.mkdir()
    (sys_dir / "gameA.zip").write_bytes(b"x")
    assert appmod.pick_random_game(tmp_path) is None
