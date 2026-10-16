"""Tests de `_detect_configgen_path` de app.py.

Regresión: la ruta de configgen estaba hardcodeada a `/usr/lib/python3.12/...`,
lo que rompía el lanzamiento en Batoceras con otra versión de Python.
"""
from __future__ import annotations


def test_detect_configgen_path_picks_existing(appmod, tmp_path):
    target = tmp_path / "python3.14" / "site-packages" / "configgen" / "emulatorlauncher.py"
    target.parent.mkdir(parents=True)
    target.write_text("# launch\n", encoding="utf-8")

    pat = str(tmp_path / "python3*" / "site-packages" / "configgen" / "emulatorlauncher.py")
    assert appmod._detect_configgen_path([pat]) == str(target)


def test_detect_configgen_path_fallback(appmod, tmp_path):
    pat = str(tmp_path / "python3*" / "site-packages" / "configgen" / "emulatorlauncher.py")
    got = appmod._detect_configgen_path([pat])
    assert got.endswith("emulatorlauncher.py")


def test_default_settings_python_path_is_string(appmod):
    assert isinstance(appmod.DEFAULT_SETTINGS["python_path"], str)
    assert appmod.DEFAULT_SETTINGS["python_path"].endswith("emulatorlauncher.py")
