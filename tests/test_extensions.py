"""Tests de `get_system_extensions` de app.py (extensiones custom vs integradas)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def _cfg(path: Path, system: str, extensions: str) -> Path:
    root = ET.Element("systemList")
    s = ET.SubElement(root, "system")
    ET.SubElement(s, "name").text = system
    ET.SubElement(s, "extension").text = extensions
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8")
    return path


def test_custom_cfg_replaces_builtin(appmod, tmp_path):
    builtin = _cfg(tmp_path / "builtin.cfg", "nes", ".nes .zip")
    cfg_dir = tmp_path / "cfg"
    _cfg(cfg_dir / "es_systems_custom.cfg", "nes", ".unf")

    got = appmod.get_system_extensions("nes", {"es_cfg_dir": str(cfg_dir)},
                                       builtin_path=str(builtin))
    assert got == {".unf"}, "la definición de usuario debe REEMPLAZAR a la integrada"


def test_builtin_used_when_custom_absent(appmod, tmp_path):
    builtin = _cfg(tmp_path / "builtin.cfg", "nes", ".nes .ZIP")
    cfg_dir = tmp_path / "empty_cfg"
    cfg_dir.mkdir()

    got = appmod.get_system_extensions("nes", {"es_cfg_dir": str(cfg_dir)},
                                       builtin_path=str(builtin))
    assert got == {".nes", ".zip"}, "se usan las integradas y en minúsculas"


def test_builtin_used_when_custom_does_not_define_system(appmod, tmp_path):
    builtin = _cfg(tmp_path / "builtin.cfg", "nes", ".nes")
    cfg_dir = tmp_path / "cfg"
    _cfg(cfg_dir / "es_systems_custom.cfg", "psx", ".bin")

    got = appmod.get_system_extensions("nes", {"es_cfg_dir": str(cfg_dir)},
                                       builtin_path=str(builtin))
    assert got == {".nes"}


def test_missing_everything_returns_empty(appmod, tmp_path):
    got = appmod.get_system_extensions("nes", {"es_cfg_dir": str(tmp_path / "nope")},
                                       builtin_path=str(tmp_path / "nope.cfg"))
    assert got == set()
