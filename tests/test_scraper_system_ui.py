# -*- coding: utf-8 -*-
"""Tests de UI JS: progreso real en la pestaña "Por sistema" del scraper.

La pestaña "Por sistema" ahora crea un job del lote con un único sistema y
sondea `/api/scraper/batch/<id>` para mostrar progreso ROM a ROM. El helper
puro `scraperJobView(job)` debe devolver el estado listo para pintar.
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


def _helper_source():
    html = HTML.read_text(encoding="utf-8")
    m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?<script>(.*?)</script>[\s\S]*?<!-- <<< UI-HELPERS", html, re.S)
    assert m, "No se encontró bloque UI-HELPERS"
    return m.group(1)


def _run_node_eval(js: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    p = subprocess.run([node, "-e", js], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}\n{p.stdout}"
    return p.stdout.strip()


def test_scraper_job_view_exists_in_ui_helpers():
    src = _helper_source()
    assert "function scraperJobView" in src, "falta el helper scraperJobView"


def test_scraper_job_view_active_job():
    src = _helper_source()
    job = {
        "status": "running", "progress": 42, "current_system": "ps2",
        "current_rom": "foo.iso", "progress_raw": [3, 7],
        "partial": {"ok": 2, "fail": 1, "skip": 0},
        "systems_done": 0, "systems": ["ps2"],
        "aggregated": {"ok": 0, "fail": 0, "skip": 0, "total": 0, "errors": []},
    }
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const job = " + json.dumps(job) + ";\n"
        + "console.log(JSON.stringify(scraperJobView(job)));\n"
    )
    out = json.loads(_run_node_eval(js))
    assert out["active"] is True
    assert out["pct"] == 42
    assert out["label"].startswith("Scrapeando")
    assert "foo.iso" in out["label"]
    assert out["stats"].count("3") >= 1 or "3/7" in out["stats"]


def test_scraper_job_view_completed_job():
    src = _helper_source()
    job = {
        "status": "completed", "progress": 100, "current_system": "ps2",
        "current_rom": "", "progress_raw": [0, 0],
        "partial": {},
        "systems_done": 1, "systems": ["ps2"],
        "aggregated": {"ok": 5, "fail": 1, "skip": 0, "total": 6, "errors": ["e1"]},
    }
    js = (
        "const console=global.console;\n"
        + src
        + "\n"
        + "const job = " + json.dumps(job) + ";\n"
        + "console.log(JSON.stringify(scraperJobView(job)));\n"
    )
    out = json.loads(_run_node_eval(js))
    assert out["active"] is False
    assert out["pct"] == 100
    assert "Completado" in out["label"] or "completado" in out["label"].lower()
    assert out["stats"].count("5") >= 1
