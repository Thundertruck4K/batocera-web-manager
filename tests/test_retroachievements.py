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


# ─── Tarea 3: resumen cacheado + endpoints ─────────────────────────────

def _fake_ra_get(calls):
    def fake(settings, endpoint, params=None, timeout=10):
        calls.append(endpoint)
        return {
            "API_GetUserProfile.php": PROFILE,
            "API_GetUserRecentAchievements.php": RECENT,
            "API_GetUserCompletionProgress.php": COMPLETION,
            "API_GetUserAwards.php": AWARDS,
        }.get(endpoint)
    return fake


def test_get_retroachievements_ok_and_cached(appmod, monkeypatch):
    appmod._ra_cache["data"] = None
    calls = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(calls))

    r1 = appmod.get_retroachievements(_creds())
    n1 = len(calls)
    r2 = appmod.get_retroachievements(_creds())

    assert r1["ok"] is True and r1["configured"] is True
    assert r1["profile"]["user"] == "tester"
    assert r1["recent"] and r1["completion"] and r1["awards"]
    assert r1 == r2, "la segunda llamada debe devolver el mismo objeto cacheado"
    assert len(calls) == n1, "la segunda llamada no debe tocar la red"
    appmod._ra_cache["data"] = None


def test_get_retroachievements_unconfigured_makes_no_request(appmod, monkeypatch):
    appmod._ra_cache["data"] = None
    called = []
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: called.append(1))

    r = appmod.get_retroachievements({"ra_user": "", "ra_api_key": "", "ra_enabled": True})
    assert r["configured"] is False and r["ok"] is False and r["enabled"] is False
    assert called == [], "no debe llamar a la red"


def test_default_settings_ra_enabled_is_true(appmod):
    # Configurar credenciales implica querer ver los récords: el interruptor
    # debe nacer activo (el default apagado fue la causa del bug reportado).
    assert appmod.DEFAULT_SETTINGS["ra_enabled"] is True


def test_get_retroachievements_configured_but_disabled_makes_no_request(appmod, monkeypatch):
    appmod._ra_cache["data"] = None
    called = []
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: called.append(1))

    r = appmod.get_retroachievements({"ra_user": "u", "ra_api_key": "k", "ra_enabled": False})

    assert r["configured"] is True, "las credenciales están puestas"
    assert r["enabled"] is False
    assert r["ok"] is False and r["profile"] is None
    assert called == [], "desactivado no debe tocar la red"


def test_get_retroachievements_reports_enabled(appmod, monkeypatch):
    appmod._ra_cache["data"] = None
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get([]))
    r = appmod.get_retroachievements(_creds())
    assert r["configured"] is True and r["enabled"] is True and r["ok"] is True
    appmod._ra_cache["data"] = None


def test_ra_test_reports_state(appmod, monkeypatch):
    # La prueba de conexión debe informar también si el interruptor está apagado.
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: PROFILE)
    t = appmod.ra_test({"ra_user": "u", "ra_api_key": "k", "ra_enabled": False})
    assert t == {"ok": True, "configured": True, "enabled": False, "user": "tester"}

    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: None)
    t2 = appmod.ra_test({"ra_user": "", "ra_api_key": ""})
    assert t2["configured"] is False and t2["ok"] is False and t2["enabled"] is False


def test_get_retroachievements_ok_false_on_api_failure(appmod, monkeypatch):
    appmod._ra_cache["data"] = None
    monkeypatch.setattr(appmod, "_ra_get", lambda *a, **k: None)
    r = appmod.get_retroachievements(_creds())
    assert r["configured"] is True and r["ok"] is False


def test_ra_endpoints_declared():
    src = APP.read_text(encoding="utf-8")
    assert '"/api/retroachievements"' in src
    assert '"/api/retroachievements/test"' in src
    assert "get_retroachievements(" in src


# ─── Tarea 4: tarjeta de Ajustes ───────────────────────────────────────

def _html():
    return HTML.read_text(encoding="utf-8")


def test_settings_card_markup():
    h = _html()
    for anchor in ('id="set-ra-user"', 'id="set-ra-api-key"', 'id="set-ra-enabled"',
                   'id="ra-test-result"', 'onclick="saveRASettings()"',
                   'onclick="testRA()"', "RetroAchievements",
                   "retroachievements.org/settings"):
        assert anchor in h, f"falta {anchor}"


def test_settings_js_functions():
    h = _html()
    for fn in ("function loadRASettings(", "function saveRASettings(", "function testRA("):
        assert fn in h, f"falta {fn}"
    assert "/api/retroachievements/test" in h
    assert "loadRASettings();" in h, "loadSettings debe llamar a loadRASettings"


# ─── Tarea 5: tarjeta del Dashboard ────────────────────────────────────

def test_dashboard_retro_card_markup():
    h = _html()
    assert 'id="dash-retro"' in h
    assert 'id="dash-retro-body"' in h
    assert "function loadRetro(" in h
    assert "function renderRetro(" in h
    assert "/api/retroachievements" in h
    assert "loadRetro();" in h, "initDashboard debe llamar a loadRetro"


def test_dashboard_retro_disabled_state_has_activate():
    # Si hay credenciales pero el interruptor está apagado, el dashboard debe
    # ofrecer activarlo (no quedarse mudo) y la prueba de conexión debe avisarlo.
    h = _html()
    assert "function enableRetro(" in h
    assert "enableRetro()" in h, "el estado desactivado debe ofrecer Activar"
    assert "res.enabled" in h, "testRA debe reflejar el interruptor"


def test_dashboard_renders_completion_and_softcore():
    # Una cuenta con progreso pero sin logros recientes debe mostrar algo útil:
    # los juegos en progreso y los puntos softcore.
    h = _html()
    assert "r.completion" in h
    assert "Juegos en progreso" in h
    assert "softcore_points" in h
    assert "num_awarded" in h and "max_possible" in h



