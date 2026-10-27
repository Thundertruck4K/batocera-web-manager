"""Tests del enmascarado de la Web API Key de RetroAchievements.

La Web API Key se guarda en los ajustes del manager, pero el servidor no tiene
autenticación: `/api/settings` es legible desde la LAN. Estos tests fijan que la
credencial nunca sale en claro por la API.
"""
from __future__ import annotations


def test_mask_empty_key_returns_empty(appmod):
    assert appmod.mask_ra_api_key("") == ""
    assert appmod.mask_ra_api_key(None) == ""


def test_mask_short_key_is_fully_hidden(appmod):
    out = appmod.mask_ra_api_key("abc")
    assert "abc" not in out
    assert out == "•" * 8


def test_mask_long_key_keeps_first_and_last_four(appmod):
    out = appmod.mask_ra_api_key("abcd1234efgh5678")
    assert out.startswith("abcd")
    assert out.endswith("5678")
    assert "1234efgh" not in out


def test_public_settings_masks_key_and_adds_flag(appmod):
    pub = appmod.public_settings({"ra_user": "tester", "ra_api_key": "abcd1234efgh5678"})
    assert pub["ra_user"] == "tester"
    assert pub["ra_api_key_set"] is True
    assert "abcd1234efgh5678" not in pub["ra_api_key"]


def test_public_settings_reports_missing_key(appmod):
    pub = appmod.public_settings({"ra_api_key": ""})
    assert pub["ra_api_key_set"] is False
    assert pub["ra_api_key"] == ""


def test_public_settings_does_not_mutate_input(appmod):
    src = {"ra_api_key": "abcd1234efgh5678"}
    appmod.public_settings(src)
    assert src["ra_api_key"] == "abcd1234efgh5678"


def test_public_settings_hides_every_secret(appmod):
    pub = appmod.public_settings({
        "ra_api_key": "abcd1234efgh5678",
        "tgdb_apikey": "TGDB-SECRET-KEY",
    })
    flat = repr(pub)
    assert "abcd1234efgh5678" not in flat
    assert "TGDB-SECRET-KEY" not in flat


# ─── Semántica write-only de la key ─────────────────────────────────

def test_post_keeps_stored_key_when_mask_is_submitted(appmod):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    payload = {"ra_api_key": appmod.mask_ra_api_key(stored["ra_api_key"])}
    out = appmod.apply_settings_update(payload, dict(stored))
    assert out["ra_api_key"] == "abcd1234efgh5678"


def test_post_keeps_stored_key_when_key_absent(appmod):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_user": "otro"}, dict(stored))
    assert out["ra_api_key"] == "abcd1234efgh5678"


def test_post_replaces_key_with_new_value(appmod):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_api_key": "nueva1234clave5678"}, dict(stored))
    assert out["ra_api_key"] == "nueva1234clave5678"


def test_post_empty_key_clears_stored_key(appmod):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_api_key": ""}, dict(stored))
    assert out["ra_api_key"] == ""


def test_post_ignores_unknown_keys(appmod):
    out = appmod.apply_settings_update({"no_existe": "x"}, {"ra_api_key": "abcd1234efgh5678"})
    assert "no_existe" not in out


def test_post_normalises_ui_theme(appmod):
    assert appmod.apply_settings_update({"ui_theme": "light"}, {})["ui_theme"] == "light"
    assert appmod.apply_settings_update({"ui_theme": "auto"}, {})["ui_theme"] == "auto"
    assert appmod.apply_settings_update({"ui_theme": "futurol"}, {})["ui_theme"] == "dark"
    assert appmod.apply_settings_update({"ui_theme": ""}, {})["ui_theme"] == "dark"


def test_post_does_not_mutate_current(appmod):
    current = {"ra_api_key": "abcd1234efgh5678"}
    appmod.apply_settings_update({"ra_api_key": "nueva1234clave5678"}, current)
    assert current["ra_api_key"] == "abcd1234efgh5678"


# ─── Umbral y forma de la máscara ───────────────────────────────────

def test_mask_hides_short_keys_entirely(appmod):
    """Una key de 9 caracteres no puede quedar visible en 8 de sus 9 posiciones."""
    for key in ("abc", "abcdefgh", "abcdefghi", "abcdefghij"):
        out = appmod.mask_ra_api_key(key)
        assert out == "•" * 8, f"key de {len(key)} caracteres: {out}"


def test_mask_shows_extremes_for_long_keys(appmod):
    out = appmod.mask_ra_api_key("abcd1234efgh5678")
    assert out.startswith("abcd")
    assert out.endswith("5678")


def test_stale_mask_from_another_device_does_not_corrupt_the_key(appmod):
    """Una mascara que no es la de la key actual no puede pisar la key real.

    Es el caso multi-dispositivo: el movil tiene una mascara vieja, la key se
    rota en el PC y al guardar desde el movil se mandaba la mascara como si
    fuera la key nueva.
    """
    stored = {"ra_api_key": "ZZZZ3333CCCC4444"}
    stale_mask = appmod.mask_ra_api_key("AAAA1111BBBB2222")
    out = appmod.apply_settings_update({"ra_api_key": stale_mask}, dict(stored))
    assert out["ra_api_key"] == "ZZZZ3333CCCC4444", "la key real se ha corrompido"


def test_looks_like_ra_mask(appmod):
    assert appmod.looks_like_ra_mask(appmod.mask_ra_api_key("abcd1234efgh5678"))
    assert not appmod.looks_like_ra_mask("abcd1234efgh5678")
    assert not appmod.looks_like_ra_mask("")


def test_public_settings_normalises_ui_theme(appmod):
    assert appmod.public_settings({"ui_theme": "futurol"})["ui_theme"] == "dark"
    assert appmod.public_settings({"ui_theme": "light"})["ui_theme"] == "light"
    assert appmod.public_settings({"ui_theme": "auto"})["ui_theme"] == "auto"
    assert appmod.public_settings({})["ui_theme"] == "dark"


def test_post_whitespace_only_clears_the_key(appmod):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_api_key": "   "}, dict(stored))
    assert out["ra_api_key"] == ""


def test_post_keeps_a_key_that_already_has_spaces(appmod):
    stored = {"ra_api_key": "  abcd1234efgh5678  "}
    out = appmod.apply_settings_update({"ra_user": "otro"}, dict(stored))
    assert out["ra_api_key"] == "  abcd1234efgh5678  "


# ─── Frontend: la key se muestra enmascarada ────────────────────────

def _html() -> str:
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    return (root / "templates" / "index.html").read_text(encoding="utf-8")


def test_ra_field_has_hint_element():
    assert 'id="ra-key-hint"' in _html()


def test_load_ra_settings_reports_configured_state():
    html = _html()
    assert "ra_api_key_set" in html, "el hint debe indicar si hay key configurada"


def test_load_ra_settings_never_fills_the_real_key():
    """El frontend no debe asignar la key cruda al campo."""
    import re
    html = _html()
    m = re.search(r"async function loadRASettings\(\)\s*\{(.*?)\n\}", html, re.S)
    assert m, "no se encontró loadRASettings()"
    body = m.group(1)
    assert "data.ra_api_key" in body
    assert "data.ra_api_key ||" in body
    assert "ra_api_key_set" in body
