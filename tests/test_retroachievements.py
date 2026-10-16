"""Tests de la integración con RetroAchievements (récords personales).

Cubren:
- `_ra_get`: autenticación por query (`z`=usuario, `y`=key, `u`=usuario), sin red
  si faltan credenciales y tolerante a fallos.
- Normalizadores: perfil, logros recientes, progreso y premios.
- `get_retroachievements`: resumen combinado y cacheado.
- Estructura del frontend (Ajustes + Dashboard).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"
APP = ROOT / "app.py"


def _creds(user="tester", key="KEY123"):
    return {"ra_user": user, "ra_api_key": key, "ra_enabled": True}


# ─── Tarea 1: _ra_get + settings ───────────────────────────────────────

def test_default_settings_has_ra_keys(appmod):
    for k in ("ra_user", "ra_api_key", "ra_enabled"):
        assert k in appmod.DEFAULT_SETTINGS, f"falta {k} en DEFAULT_SETTINGS"


def test_ra_get_without_credentials_makes_no_request(appmod, monkeypatch):
    calls = []

    def fake(url, timeout=10):
        calls.append(url)
        return "{}"

    monkeypatch.setattr(appmod, "_ra_urlopen", fake)
    assert appmod._ra_get({"ra_user": "", "ra_api_key": ""}, "API_GetUserProfile.php") is None
    assert appmod._ra_get({}, "API_GetUserProfile.php") is None
    assert calls == [], "no debe llamar a la red sin credenciales"


def test_ra_get_builds_auth_params(appmod, monkeypatch):
    seen = {}

    def fake(url, timeout=10):
        seen["url"] = url
        return '{"User": "tester"}'

    monkeypatch.setattr(appmod, "_ra_urlopen", fake)
    out = appmod._ra_get(_creds(), "API_GetUserProfile.php", {"c": 5})

    assert out == {"User": "tester"}
    url = seen["url"]
    assert url.startswith(appmod.RA_API_BASE + "/API_GetUserProfile.php?")
    assert "z=tester" in url and "y=KEY123" in url and "u=tester" in url and "c=5" in url


def test_ra_get_network_error_returns_none(appmod, monkeypatch):
    def boom(url, timeout=10):
        raise OSError("sin red")

    monkeypatch.setattr(appmod, "_ra_urlopen", boom)
    assert appmod._ra_get(_creds(), "API_GetUserProfile.php") is None


def test_ra_get_bad_json_returns_none(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_urlopen", lambda url, timeout=10: "<html>no json</html>")
    assert appmod._ra_get(_creds(), "API_GetUserProfile.php") is None


# ─── Tarea 2: normalizadores ───────────────────────────────────────────

PROFILE = {
    "User": "tester", "UserPic": "/UserPic/tester.png",
    "MemberSince": "2016-01-02 00:43:04", "RichPresenceMsg": "Playing Super Mario",
    "LastGameID": 19504, "TotalPoints": 399597, "TotalSoftcorePoints": 10,
    "TotalTruePoints": 1599212, "Motto": "hola",
}

RECENT = [
    {"Date": "2023-12-27 16:04:50", "HardcoreMode": 1, "AchievementID": 98012,
     "Title": "Beginner I", "Description": "Clear stages", "BadgeName": "108302",
     "Points": 5, "TrueRatio": 25, "GameTitle": "Pokemon Pinball mini",
     "GameID": 14715, "ConsoleName": "Pokemon Mini", "BadgeURL": "/Badge/108302.png"},
    {"Date": "2023-12-26 10:00:00", "HardcoreMode": 0, "AchievementID": 1,
     "Title": "Otro", "Description": "", "BadgeName": "1", "Points": 3,
     "TrueRatio": 3, "GameTitle": "Otro juego", "GameID": 2,
     "ConsoleName": "NES", "BadgeURL": "/Badge/1.png"},
]

COMPLETION = {"Count": 1, "Total": 2, "Results": [
    {"GameID": 20246, "Title": "Sonic", "ImageIcon": "/Images/074560.png",
     "ConsoleName": "Mega Drive", "MaxPossible": 40, "NumAwarded": 10,
     "NumAwardedHardcore": 8, "HighestAwardKind": "beaten-hardcore",
     "HighestAwardDate": "2023-10-27T02:52:34+00:00"},
]}

AWARDS = {"TotalAwardsCount": 1613, "MasteryAwardsCount": 805,
          "CompletionAwardsCount": 0, "BeatenHardcoreAwardsCount": 807,
          "BeatenSoftcoreAwardsCount": 0, "EventAwardsCount": 2}


def test_ra_profile_normalizes(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: PROFILE)
    p = appmod.ra_profile(_creds())
    assert p["user"] == "tester"
    assert p["points"] == 399597 and p["true_points"] == 1599212
    assert p["avatar"] == "https://retroachievements.org/UserPic/tester.png"
    assert p["member_since"] == "2016-01-02 00:43:04"
    assert p["motto"] == "hola"


def test_ra_profile_none_when_unavailable(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: None)
    assert appmod.ra_profile(_creds()) is None


def test_ra_recent_achievements_normalizes(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: RECENT)
    out = appmod.ra_recent_achievements(_creds())
    assert out[0]["title"] == "Beginner I"
    assert out[0]["game"] == "Pokemon Pinball mini"
    assert out[0]["badge"] == "https://retroachievements.org/Badge/108302.png"
    assert out[0]["hardcore"] is True and out[1]["hardcore"] is False


def test_ra_recent_achievements_caps(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: RECENT * 20)
    assert len(appmod.ra_recent_achievements(_creds())) == 12


def test_ra_recent_achievements_empty_on_error(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: None)
    assert appmod.ra_recent_achievements(_creds()) == []


def test_ra_completion_normalizes(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: COMPLETION)
    out = appmod.ra_completion(_creds())
    assert out[0]["title"] == "Sonic"
    assert out[0]["percent"] == 25.0
    assert out[0]["icon"] == "https://retroachievements.org/Images/074560.png"


def test_ra_completion_handles_zero_max(appmod, monkeypatch):
    data = {"Results": [{"GameID": 1, "Title": "X", "MaxPossible": 0, "NumAwarded": 0}]}
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: data)
    assert appmod.ra_completion(_creds())[0]["percent"] == 0.0


def test_ra_awards_normalizes(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: AWARDS)
    a = appmod.ra_awards(_creds())
    assert a == {"total": 1613, "mastery": 805, "completion": 0,
                 "beaten_hardcore": 807, "beaten_softcore": 0, "events": 2}


def test_ra_awards_none_on_error(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: None)
    assert appmod.ra_awards(_creds()) is None

