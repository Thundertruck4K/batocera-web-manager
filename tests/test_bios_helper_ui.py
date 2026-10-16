"""Tests de la UI del asistente de BIOS (enlace GitHub, descarga por URL, aviso legal)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def test_ui_has_github_link_fetch_and_legal_notice():
    h = HTML.read_text(encoding="utf-8")
    assert "function fetchBios(" in h
    assert "function biosGhUrl(" in h
    assert "/api/bios/fetch" in h
    assert "github.com/search" in h
    assert "type=code" in h
    # Aviso legal: la app no aloja ni sugiere fuentes de BIOS
    assert "no incluye" in h or "no aloja" in h
