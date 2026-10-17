# -*- coding: utf-8 -*-
"""Tests de UI: aviso de recarga de EmulationStation tras scrapear.

ES solo relee las gamelists al arrancar, así que tras un scrapeo que guardó
metadatos el manager lo recarga y la UI debe avisarlo. El helper puro
`esReloadNotice(esReload)` construye ese aviso.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _helper_source():
    m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?<script>(.*?)</script>[\s\S]*?<!-- <<< UI-HELPERS",
                  _html(), re.S)
    assert m, "No se encontró bloque UI-HELPERS"
    return m.group(1)


def _run_node_eval(js: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    p = subprocess.run([node, "-e", js], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}\n{p.stdout}"
    return p.stdout.strip()


def _call(es_reload):
    src = _helper_source()
    js = ("const console=global.console;\n" + src + "\n"
          + "console.log(JSON.stringify(esReloadNotice("
          + json.dumps(es_reload) + ")));\n")
    return json.loads(_run_node_eval(js))


def test_helper_exists():
    assert "function esReloadNotice" in _helper_source(), "falta el helper esReloadNotice"


def test_no_notice_without_reload_info():
    assert _call(None) == ""
    assert _call({"ok": True, "reloaded": False}) == ""


def test_success_notice_when_reloaded():
    html = _call({"ok": True, "reloaded": True})
    assert "success-box" in html
    assert "EmulationStation" in html


def test_warn_notice_with_manual_button_on_failure():
    html = _call({"ok": False, "reloaded": False, "error": "swissknife failed"})
    assert "warn-box" in html
    assert "swissknife failed" in html
    assert "restartES()" in html, "el aviso de fallo debe ofrecer recargar a mano"


def test_error_message_is_escaped():
    html = _call({"ok": False, "reloaded": False, "error": "<img src=x onerror=1>"})
    assert "<img src=x" not in html
    assert "&lt;img" in html


def test_single_download_shows_reload_notice():
    m = re.search(r"async function scraperDownload\(\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta scraperDownload()"
    assert "esReloadNotice" in m.group(1), \
        "la descarga individual debe avisar de la recarga de ES"


def test_system_poll_shows_reload_notice():
    m = re.search(r"async function scraperSystemPoll\(\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta scraperSystemPoll()"
    assert "esReloadNotice" in m.group(1), \
        "el scraping por sistema debe avisar de la recarga de ES"


def test_batch_refresh_shows_reload_notice():
    m = re.search(r"async function scraperBatchRefresh\(\)\s*\{([\s\S]*?)\n\}\n", _html())
    assert m, "falta scraperBatchRefresh()"
    assert "esReloadNotice" in m.group(1), \
        "el scraping por lote debe avisar de la recarga de ES"
