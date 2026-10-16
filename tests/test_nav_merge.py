"""Tests de la reagrupación del nav y de los paneles fusionados.

Reagrupación: 8 items sueltos -> 5 bloques con 6 destinos.
Fusiones: "BIOS Faltante" pasa a ser pestaña dentro de "ROMs & BIOS", y
"Vista Previa XML" deja de ser panel propio para vivir dentro de
"Agregar / Editar".
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def test_biosmissing_is_a_tab_inside_roms_panel():
    h = _html()
    assert 'id="roms-pane-bios"' in h, "la pestaña BIOS Faltante debe vivir dentro de ROMs & BIOS"
    assert 'id="roms-pane-content"' in h, "falta el panel de contenido de ROMs"
    assert "function showRomTab(" in h, "falta el conmutador de pestañas"
    assert 'id="panel-biosmissing"' not in h, "panel-biosmissing ya no debe existir como panel propio"


def test_preview_is_inline_in_add_panel():
    h = _html()
    assert 'id="add-preview-wrap"' in h, "la vista previa debe vivir dentro del panel Agregar/Editar"
    assert 'id="panel-preview"' not in h, "panel-preview ya no debe existir como panel propio"


def test_previewXml_reveals_inline_section():
    m = re.search(r"async function previewXml\(\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta previewXml()"
    body = m.group(1)
    assert "add-preview-wrap" in body, "previewXml debe revelar la sección inline"
    assert "showPanel('preview'" not in body, "previewXml ya no debe saltar a un panel aparte"


def test_showRomTab_toggles_panes():
    m = re.search(r"function showRomTab\(([\s\S]*?)\n\}", _html())
    assert m, "falta showRomTab()"
    body = m.group(1)
    assert "roms-pane-bios" in body and "roms-pane-content" in body


def test_showpanel_has_no_dead_panels():
    m = re.search(r"function showPanel\(name, btn\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta showPanel()"
    body = m.group(1)
    assert "'biosmissing'" not in body, "showPanel ya no debe manejar el panel biosmissing"
    assert "'preview'" not in body, "showPanel ya no debe manejar el panel preview"
