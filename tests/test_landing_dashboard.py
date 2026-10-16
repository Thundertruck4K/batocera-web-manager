"""Tests de estructura del landing y del dashboard rediseñado.

Comprueban que `templates/index.html` y `app.py` contienen los enganches
esperados (marcado, funciones JS y endpoints). No ejecutan el JS.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"
APP = ROOT / "app.py"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _app() -> str:
    return APP.read_text(encoding="utf-8")


# ─── A4: endpoints ─────────────────────────────────────────────────────

def test_endpoints_declared():
    src = _app()
    assert '"/api/game-stats"' in src
    assert '"/api/random-game"' in src
    assert "collect_play_stats(" in src
    assert "pick_random_game(" in src
