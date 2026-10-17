# -*- coding: utf-8 -*-
"""Tests de la fila del dashboard: «Juego al azar» + «Actividad de juego».

Las dos tarjetas comparten una misma fila de la grilla (dos mitades) en vez de
ocupar cada una una fila entera: a ancho completo se veían demasiado anchas y
desperdiciaban espacio. Dentro de la tarjeta de actividad, sus dos bloques se
apilan para que los nombres de los juegos no salgan cortados a media anchura.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _rule(css: str, selector: str) -> str:
    m = re.search(re.escape(selector) + r"\{([^}]*)\}", css)
    assert m, f"falta la regla {selector}"
    return m.group(1)


def test_dash_double_wraps_both_cards():
    """Las dos tarjetas van dentro del mismo contenedor de fila."""
    h = _html()
    ini = h.index('<div class="dash-double">')
    fin = h.index("<!-- Récords personales")
    seg = h[ini:fin]
    assert 'id="dash-random-game"' in seg, "la tarjeta al azar no está en la fila"
    assert 'id="dash-playstats"' in seg, "la tarjeta de actividad no está en la fila"
    # el contenedor abre y cierra dentro del segmento, envolviendo las dos tarjetas
    assert seg.count("<div") - seg.count("</div>") == 0


def test_dash_double_is_two_columns_and_collapses():
    css = _html()
    rule = _rule(css, ".dash-double")
    assert "grid-template-columns:1fr 1fr" in rule
    assert "gap:14px" in rule
    # en pantallas estrechas se apilan otra vez
    m = re.search(r"@media \(max-width:900px\)\{([^\n]*)\}", css)
    assert m and re.search(r"\.dash-double\{grid-template-columns:1fr\}", m.group(1)), \
        "la fila debe apilarse en pantallas estrechas"


def test_activity_blocks_stack_inside_the_half_card():
    """A media anchura, «Más jugados» y la gráfica van uno debajo del otro."""
    rule = _rule(_html(), ".dash-playstats-grid")
    assert "grid-template-columns:1fr;" in rule, "los bloques deben apilarse"
    assert "1fr 1fr" not in rule, "dos columnas internas cortarían los nombres"
