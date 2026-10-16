"""Tests de persistencia del *skip* de BIOS faltantes.

Antes el set `_missing_bios_skipped` vivía solo en memoria y se perdía al
reiniciar el servidor. Ahora se persiste en un JSON junto a los settings.
"""
from __future__ import annotations


def _use_tmp_settings(appmod, tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "SETTINGS_FILE", tmp_path / "settings.json")
    appmod._missing_bios_skipped.clear()


def test_skip_persists_across_reload(appmod, tmp_path, monkeypatch):
    _use_tmp_settings(appmod, tmp_path, monkeypatch)

    appmod.set_bios_skipped("snes/st0019.bin")
    assert "snes/st0019.bin" in appmod._missing_bios_skipped

    # Simula reinicio: memoria vacía + recarga desde disco.
    appmod._missing_bios_skipped.clear()
    appmod.load_bios_skipped()
    assert "snes/st0019.bin" in appmod._missing_bios_skipped


def test_unskip_persists(appmod, tmp_path, monkeypatch):
    _use_tmp_settings(appmod, tmp_path, monkeypatch)

    appmod.set_bios_skipped("psx/scph1001.bin")
    appmod.unset_bios_skipped("psx/scph1001.bin")

    appmod._missing_bios_skipped.clear()
    appmod.load_bios_skipped()
    assert "psx/scph1001.bin" not in appmod._missing_bios_skipped


def test_load_tolerates_missing_file(appmod, tmp_path, monkeypatch):
    _use_tmp_settings(appmod, tmp_path, monkeypatch)
    # No existe el fichero: no debe lanzar.
    appmod.load_bios_skipped()
    assert appmod._missing_bios_skipped == set()


def test_load_tolerates_corrupt_file(appmod, tmp_path, monkeypatch):
    _use_tmp_settings(appmod, tmp_path, monkeypatch)
    (tmp_path / "batocera_manager_bios_skipped.json").write_text("{no-json", encoding="utf-8")
    appmod.load_bios_skipped()
    assert appmod._missing_bios_skipped == set()


def test_set_empty_key_is_noop(appmod, tmp_path, monkeypatch):
    _use_tmp_settings(appmod, tmp_path, monkeypatch)
    appmod.set_bios_skipped("")
    assert appmod._missing_bios_skipped == set()
