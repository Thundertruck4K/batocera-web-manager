# -*- coding: utf-8 -*-
"""Tests del bloque «Instrucciones de uso» del panel Configuración.

Las instrucciones son lo primero que lee quien instala el manager, así que
tienen que reflejar el flujo real de instalación (clonar de GitHub por SSH y
lanzar install.sh) y no mandar a nadie a instalar dependencias que Batocera ya
trae. El paso de arranque automático vive en su propia tarjeta (con botón), así
que no se repite aquí.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _card_block(h: str, marker: str) -> str:
    """Devuelve el <div class="card"> completo que contiene `marker`."""
    i = h.index(marker)
    start = h.rindex('<div class="card">', 0, i)
    depth, pos = 0, start
    while True:
        m = re.compile(r"<div\b|</div>").search(h, pos)
        assert m, "bloque sin cerrar"
        depth += 1 if m.group(0).startswith("<div") else -1
        pos = m.end()
        if depth == 0:
            return h[start:pos]


def _instr() -> str:
    return _card_block(_html(), "Instrucciones de uso")


def test_instructions_use_the_github_clone_flow():
    blk = _instr()
    assert "ssh root@batocera" in blk
    assert "git clone https://github.com/Thundertruck4K/batocera-web-manager.git" in blk
    assert "bash install.sh" in blk
    assert "cd /userdata/system/batocera_web" in blk


def test_instructions_do_not_ask_for_dependencies():
    """Batocera ya trae Python 3: instalar dependencias es un error de novato."""
    blk = _instr()
    assert "pip install" not in blk
    assert "flask" not in blk.lower()
    assert "No hace falta instalar dependencias" in blk


def test_instructions_reach_the_manager_by_network_name():
    blk = _instr()
    assert "http://BATOCERA:5000" in blk
    assert "IP-de-Batocera" not in blk, "el comodín de red sustituye a la IP"


def test_instructions_do_not_duplicate_the_autostart_card():
    """El arranque automático ya tiene su tarjeta con botón."""
    blk = _instr()
    assert "custom.sh" not in blk
    assert "Instalar autostart" not in blk
