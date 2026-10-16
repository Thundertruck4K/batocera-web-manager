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
