"""Tests de `delete_custom_system` (borrado quirúrgico de sistemas)."""
from __future__ import annotations

from pathlib import Path

_MULTI = """<?xml version="1.0" encoding="UTF-8"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/userdata/roms/nes</path>
        <extension>.nes</extension>
    </system>
    <system>
        <name>snes</name>
        <fullname>Super Nintendo</fullname>
        <path>/userdata/roms/snes</path>
        <extension>.sfc</extension>
    </system>
</systemList>
"""

_SINGLE = """<?xml version="1.0" encoding="UTF-8"?>
<systemList>
    <system>
        <name>gameboy</name>
        <fullname>Game Boy</fullname>
        <path>/userdata/roms/gb</path>
        <extension>.gb</extension>
    </system>
</systemList>
"""


def _cfg_dir(tmp_path: Path, content: str) -> Path:
    d = tmp_path / "es_cfg"
    d.mkdir()
    (d / "es_systems_extra.cfg").write_text(content, encoding="utf-8")
    return d


def test_delete_keeps_other_systems_in_same_file(appmod, tmp_path):
    d = _cfg_dir(tmp_path, _MULTI)

    ok, info = appmod.delete_custom_system("nes", {"es_cfg_dir": str(d)})
    assert ok, info
    assert info["file_deleted"] is False
    assert info["removed_systems"] == 1

    remaining = [x["name"] for x in appmod.list_custom_systems({"es_cfg_dir": str(d)})]
    assert remaining == ["snes"], "snes debe sobrevivir al borrado de nes"
    assert (d / "es_systems_extra.cfg").exists(), "el .cfg compartido NO se borra"


def test_delete_last_system_removes_file(appmod, tmp_path):
    d = _cfg_dir(tmp_path, _SINGLE)

    ok, info = appmod.delete_custom_system("gameboy", {"es_cfg_dir": str(d)})
    assert ok, info
    assert info["file_deleted"] is True
    assert not (d / "es_systems_extra.cfg").exists()


def test_delete_unknown_system_is_safe(appmod, tmp_path):
    d = _cfg_dir(tmp_path, _MULTI)

    ok, info = appmod.delete_custom_system("psx", {"es_cfg_dir": str(d)})
    assert ok is False
    assert "error" in info
    # El fichero no debe tocarse.
    assert (d / "es_systems_extra.cfg").exists()
    assert len(appmod.list_custom_systems({"es_cfg_dir": str(d)})) == 2


def test_delete_is_idempotent(appmod, tmp_path):
    d = _cfg_dir(tmp_path, _SINGLE)
    appmod.delete_custom_system("gameboy", {"es_cfg_dir": str(d)})
    ok, _info = appmod.delete_custom_system("gameboy", {"es_cfg_dir": str(d)})
    assert ok is False
