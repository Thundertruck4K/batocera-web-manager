"""Tests de la UI de reinicio de EmulationStation (botón + aviso de pendiente).

Verifica la estructura del HTML/JS embebido: el aviso global en la barra
superior, el botón y aviso en la tarjeta de ES, y los handlers que consumen
`/api/es/status` (sondeo ligero) y `/api/es/restart` (acción manual).
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def test_topbar_has_global_es_pending_badge():
    assert 'id="es-pending-global"' in _html(), "falta el aviso global de reinicio pendiente"


def test_es_card_has_restart_button_and_pending_notice():
    h = _html()
    assert 'id="kpi-es-pending"' in h, "falta el aviso de pendiente en la tarjeta de ES"
    assert 'onclick="restartES()"' in h, "falta el botón de reinicio de ES"


def test_restartES_confirms_and_posts():
    m = re.search(r"async function restartES\(\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta restartES()"
    body = m.group(1)
    assert "confirm(" in body, "debe pedir confirmación antes de reiniciar"
    assert "/api/es/restart" in body and "POST" in body


def test_pollEsStatus_uses_light_endpoint():
    m = re.search(r"async function pollEsStatus\(\)\s*\{([\s\S]*?)\n\}", _html())
    assert m, "falta pollEsStatus()"
    assert "/api/es/status" in m.group(1)


def test_setEsPending_toggles_both_badges():
    m = re.search(r"function setEsPending\(([\s\S]*?)\n\}", _html())
    assert m, "falta setEsPending()"
    body = m.group(1)
    assert "es-pending-global" in body and "kpi-es-pending" in body
