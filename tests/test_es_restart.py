"""Tests del reinicio manual de EmulationStation (opt-in) y del flag pendiente."""
from __future__ import annotations


def test_mark_and_status_flag(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_es_restart_pending", False)
    appmod.mark_es_restart_pending()
    assert appmod.get_es_status()["restart_pending"] is True
    appmod.mark_es_restart_pending(False)
    assert appmod.get_es_status()["restart_pending"] is False


def test_restart_runs_swissknife(appmod, monkeypatch):
    calls = {}

    class _P:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        return _P()

    import subprocess as sp
    monkeypatch.setattr(sp, "run", fake_run)
    monkeypatch.setattr(appmod, "_es_restart_pending", True)

    ok, info = appmod.restart_emulationstation()
    assert ok is True, info
    assert calls["cmd"] == ["batocera-es-swissknife", "--restart"]
    assert appmod._es_restart_pending is False, "un reinicio correcto limpia el flag"


def test_restart_missing_binary(appmod, monkeypatch):
    import subprocess as sp

    def fake_run(cmd, **kw):
        raise FileNotFoundError()

    monkeypatch.setattr(sp, "run", fake_run)
    ok, info = appmod.restart_emulationstation()
    assert ok is False
    assert "error" in info


def test_restart_nonzero_exit(appmod, monkeypatch):
    import subprocess as sp

    class _P:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(sp, "run", lambda cmd, **kw: _P())
    ok, info = appmod.restart_emulationstation()
    assert ok is False
    assert "boom" in info["error"]
