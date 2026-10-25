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
