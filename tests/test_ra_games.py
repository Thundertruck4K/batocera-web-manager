"""Tests del dashboard de logros (RetroAchievements + biblioteca local).

Cubren:
- `ra_normalize_title`: clave comparable entre el título de RA y el del ROM.
- `build_local_game_index`: índice desde los gamelist.xml y desde los ficheros.
- `match_local_game`: emparejado exacto y preferencia por el que tiene carátula.
- `get_ra_games`: payload del dashboard y la regla de «no tocar la red».
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def _gamelist(sys_dir: Path, games: list[tuple[str, str]]) -> None:
    """Crea un gamelist.xml con (ruta, nombre) y el fichero del ROM."""
    sys_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path, name in games:
        rows.append(f"<game><path>./{path}</path><name>{name}</name></game>")
        rom = sys_dir / path
        rom.parent.mkdir(parents=True, exist_ok=True)
        rom.write_bytes(b"x")
    (sys_dir / "gamelist.xml").write_text(
        "<gameList>" + "".join(rows) + "</gameList>", encoding="utf-8"
    )


def _creds(user="tester", key="KEY123", **extra):
    base = {"ra_user": user, "ra_api_key": key, "ra_enabled": True}
    base.update(extra)
    return base


# ─── A1: normalización de títulos ──────────────────────────────────────

def test_ra_normalize_title_folds_accents_and_regions(appmod):
    assert appmod.ra_normalize_title("Pokémon Red (USA)") == "pokemon red"
    assert appmod.ra_normalize_title("Pokemon Red") == "pokemon red"
    assert appmod.ra_normalize_title("Mega Man 2 (USA, Europe)") == "mega man 2"
    assert appmod.ra_normalize_title("Mega Man 2") == "mega man 2"


def test_ra_normalize_title_strips_tags(appmod):
    assert appmod.ra_normalize_title("Sonic [!]") == "sonic"
    assert appmod.ra_normalize_title("~Hack~ Sonic the Hedgehog 2") == "sonic the hedgehog 2"
    assert appmod.ra_normalize_title("Final Fantasy (Disc 1)") == "final fantasy"


def test_ra_normalize_title_normalizes_punctuation(appmod):
    assert appmod.ra_normalize_title("Super Mario Bros.") == "super mario bros"
    assert appmod.ra_normalize_title("Mario & Luigi") == "mario and luigi"
    assert appmod.ra_normalize_title("Baldur's Gate") == "baldurs gate"


def test_ra_normalize_title_empty_is_safe(appmod):
    assert appmod.ra_normalize_title("") == ""
    assert appmod.ra_normalize_title(None) == ""


# ─── A2: índice de la biblioteca local ─────────────────────────────────

def test_build_local_game_index_uses_gamelist_names(appmod, tmp_path):
    _gamelist(tmp_path / "nes", [("Mega Man 2 (USA).zip", "Mega Man 2")])
    index = appmod.build_local_game_index(tmp_path)
    assert "mega man 2" in index
    assert index["mega man 2"] == [("nes", "Mega Man 2 (USA).zip", "")]


def test_build_local_game_index_keeps_subfolders(appmod, tmp_path):
    _gamelist(tmp_path / "arcade", [("CPS1/1942.zip", "1942")])
    index = appmod.build_local_game_index(tmp_path)
    assert index["1942"] == [("arcade", "1942.zip", "CPS1")]


def test_build_local_game_index_also_indexes_the_filename(appmod, tmp_path):
    """El nombre del fichero también sirve: «1942 (Capcom).zip» casa con «1942»."""
    sys_dir = tmp_path / "fbneo"
    sys_dir.mkdir()
    (sys_dir / "1942 (Capcom).zip").write_bytes(b"x")
    (sys_dir / "gamelist.xml").write_text(
        "<gameList><game><path>./1942 (Capcom).zip</path>"
        "<name>Capcom 1942</name></game></gameList>",
        encoding="utf-8",
    )
    index = appmod.build_local_game_index(tmp_path)
    assert "capcom 1942" in index
    assert "1942" in index


def test_build_local_game_index_skips_missing_roms(appmod, tmp_path):
    sys_dir = tmp_path / "nes"
    sys_dir.mkdir()
    (sys_dir / "gamelist.xml").write_text(
        "<gameList><game><path>./fantasma.zip</path><name>Fantasma</name></game></gameList>",
        encoding="utf-8",
    )
    index = appmod.build_local_game_index(tmp_path)
    assert index == {}, "un ROM que ya no está en disco no debe indexarse"


def test_build_local_game_index_without_gamelist_uses_filenames(appmod, tmp_path):
    sys_dir = tmp_path / "snes"
    sys_dir.mkdir()
    (sys_dir / "Super Metroid (USA).sfc").write_bytes(b"x")
    (sys_dir / "leeme.txt").write_bytes(b"x")
    index = appmod.build_local_game_index(tmp_path)
    # el nombre del fichero se normaliza igual que el de RA: «(USA)» desaparece
    assert "super metroid" in index
    assert not any(k.startswith("leeme") for k in index)


def test_build_local_game_index_missing_base_is_empty(appmod, tmp_path):
    assert appmod.build_local_game_index(tmp_path / "no-existe") == {}


# ─── A3: emparejado con la biblioteca local ────────────────────────────

def test_match_local_game_exact_match(appmod, tmp_path):
    _gamelist(tmp_path / "nes", [("Mega Man 2 (USA).zip", "Mega Man 2")])
    index = appmod.build_local_game_index(tmp_path)
    hit = appmod.match_local_game(index, tmp_path, "Mega Man 2")
    assert hit is not None
    assert hit["system"] == "nes"
    assert hit["filename"] == "Mega Man 2 (USA).zip"
    assert hit["has_art"] is False


def test_match_local_game_prefers_the_one_with_art(appmod, tmp_path):
    sys_dir = tmp_path / "nes"
    _gamelist(sys_dir, [("A.zip", "Mega Man 2"), ("B.zip", "Mega Man 2")])
    (sys_dir / "images").mkdir()
    (sys_dir / "images" / "B-image.png").write_bytes(b"x")
    index = appmod.build_local_game_index(tmp_path)
    hit = appmod.match_local_game(index, tmp_path, "Mega Man 2")
    assert hit["filename"] == "B.zip"
    assert hit["has_art"] is True


def test_match_local_game_no_match_returns_none(appmod, tmp_path):
    _gamelist(tmp_path / "nes", [("Mega Man 2 (USA).zip", "Mega Man 2")])
    index = appmod.build_local_game_index(tmp_path)
    assert appmod.match_local_game(index, tmp_path, "Super Mario World") is None


def test_match_local_game_does_not_match_partial_titles(appmod, tmp_path):
    # «Mega Man» no debe casar con «Mega Man 2»: sería otro juego.
    _gamelist(tmp_path / "nes", [("Mega Man 2 (USA).zip", "Mega Man 2")])
    index = appmod.build_local_game_index(tmp_path)
    assert appmod.match_local_game(index, tmp_path, "Mega Man") is None


# ─── A4: payload del dashboard ─────────────────────────────────────────

PROFILE = {"user": "tester", "avatar": "", "points": 399597, "true_points": 1599212,
           "softcore_points": 10, "member_since": "2016-01-02 00:43:04", "motto": "",
           "rich_presence": "", "last_game_id": 19504}

AWARDS = {"total": 1613, "mastery": 805, "completion": 0,
          "beaten_hardcore": 807, "beaten_softcore": 0, "events": 2}

COMPLETION = [
    {"game_id": 14402, "title": "Mega Man 2", "console": "NES",
     "icon": "https://retroachievements.org/Images/1.png",
     "num_awarded": 12, "num_awarded_hardcore": 3, "max_possible": 20,
     "hardcore": True, "percent": 60.0, "award_kind": "beaten-hardcore",
     "award_date": "2024-01-01T00:00:00+00:00", "recent_date": "2024-01-02T00:00:00+00:00"},
    {"game_id": 999, "title": "Juego Raro", "console": "PC",
     "icon": "https://retroachievements.org/Images/2.png",
     "num_awarded": 1, "num_awarded_hardcore": 0, "max_possible": 30,
     "hardcore": False, "percent": 3.3, "award_kind": "",
     "award_date": "", "recent_date": ""},
]


def _summary():
    return {"ok": True, "configured": True, "enabled": True, "updated": 123.0,
            "profile": PROFILE, "awards": AWARDS, "completion": list(COMPLETION),
            "recent": []}


def test_get_ra_games_without_credentials_makes_no_request(appmod, monkeypatch):
    called = []
    monkeypatch.setattr(appmod, "get_retroachievements",
                        lambda *a, **k: called.append(1))
    out = appmod.get_ra_games({"ra_user": "", "ra_api_key": "", "ra_enabled": True})
    assert out["configured"] is False and out["ok"] is False
    assert out["games"] == [] and out["total"] == 0
    assert called == [], "sin credenciales no se toca la red"


def test_get_ra_games_disabled_makes_no_request(appmod, monkeypatch):
    called = []
    monkeypatch.setattr(appmod, "get_retroachievements",
                        lambda *a, **k: called.append(1))
    out = appmod.get_ra_games(_creds(ra_enabled=False))
    assert out["configured"] is True and out["enabled"] is False
    assert called == [], "desactivado no se toca la red"


def test_get_ra_games_pairs_games_with_local_roms(appmod, monkeypatch, tmp_path):
    sys_dir = tmp_path / "nes"
    _gamelist(sys_dir, [("Mega Man 2 (USA).zip", "Mega Man 2")])
    (sys_dir / "images").mkdir()
    (sys_dir / "images" / "Mega Man 2 (USA)-image.png").write_bytes(b"x")

    monkeypatch.setattr(appmod, "get_retroachievements", lambda *a, **k: _summary())
    appmod._local_index_cache.update({"ts": 0, "data": None, "base": ""})

    out = appmod.get_ra_games(_creds(roms_base=str(tmp_path)))

    assert out["ok"] is True and out["configured"] is True
    assert out["profile"]["user"] == "tester"
    assert out["awards"]["mastery"] == 805
    assert out["total"] == 2 and out["matched"] == 1

    hit = out["games"][0]
    assert hit["local"] is True
    assert hit["system"] == "nes"
    assert hit["filename"] == "Mega Man 2 (USA).zip"
    assert hit["has_art"] is True
    assert hit["system_name"], "el sistema debe traer su nombre legible"

    miss = out["games"][1]
    assert miss["local"] is False
    assert miss["has_art"] is False
    assert miss["filename"] == "" and miss["system"] == ""


def test_get_ra_games_keeps_the_ra_fields(appmod, monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "get_retroachievements", lambda *a, **k: _summary())
    appmod._local_index_cache.update({"ts": 0, "data": None, "base": ""})
    out = appmod.get_ra_games(_creds(roms_base=str(tmp_path)))
    g = out["games"][0]
    assert g["title"] == "Mega Man 2"
    assert g["num_awarded"] == 12 and g["max_possible"] == 20
    assert g["num_awarded_hardcore"] == 3
    assert g["percent"] == 60.0
    assert g["award_kind"] == "beaten-hardcore"
    assert g["icon"].startswith("https://retroachievements.org/")


def test_get_ra_games_api_failure_returns_empty(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "get_retroachievements",
                        lambda *a, **k: {"ok": False, "completion": []})
    out = appmod.get_ra_games(_creds())
    assert out["ok"] is False and out["games"] == []


def test_get_ra_games_uses_the_cached_index(appmod, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(appmod, "get_retroachievements", lambda *a, **k: _summary())
    monkeypatch.setattr(appmod, "build_local_game_index",
                        lambda base: calls.append(base) or {})
    appmod._local_index_cache.update({"ts": 0, "data": None, "base": ""})

    appmod.get_ra_games(_creds(roms_base=str(tmp_path)))
    appmod.get_ra_games(_creds(roms_base=str(tmp_path)))
    assert len(calls) == 1, "la segunda llamada debe reutilizar el índice"


# ─── A5: endpoint ──────────────────────────────────────────────────────

def test_ra_games_endpoint_declared():
    src = APP.read_text(encoding="utf-8")
    assert '"/api/retroachievements/games"' in src
    assert "get_ra_games(" in src
