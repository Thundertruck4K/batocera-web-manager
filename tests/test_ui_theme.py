"""Tests del tema claro/oscuro de la interfaz del manager.

El CSS declara la paleta oscura en `:root` y la clara en
`:root[data-theme="light"]`. Las superficies "glass" (paneles translucidos,
hover, spinner, rejilla) usaban `rgba(255,255,255,…)` asumiendo fondo oscuro:
en el tema claro quedarian invisibles, asi que deben pasar por variables.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

# Superficies translucidas: su valor depende del tema.
GLASS_VARS = [
    "glass", "glass2", "glass-soft", "glass2-soft", "hover-bg", "active-bg",
    "active-fg", "chip-hover-bg", "chip-hover-fg", "badge-bg", "badge-fg",
    "spinner-track", "spinner-top", "grid-line", "fx-dot",
]

# Texto sobre fondos saturados: blanco en oscuro y en claro (verificado).
TEXT_VARS = ["on-accent", "on-photo"]

LIGHT = ':root[data-theme="light"]'


def _css() -> str:
    return HTML.read_text(encoding="utf-8")


def _style() -> str:
    css = _css()
    return css[css.index("<style>"):css.index("</style>")]


def _block(selector: str) -> str:
    css = _css()
    m = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css)
    assert m, f"no se encontró el bloque {selector}"
    return m.group(1)


def _var(block: str, name: str) -> str:
    m = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", block)
    assert m, f"variable --{name} no encontrada en el bloque"
    return m.group(1).strip()


def _outside_theme_blocks() -> str:
    """El CSS con los bloques de tema eliminados."""
    rest = re.sub(rf'{re.escape(LIGHT)}\s*\{{[^}}]*\}}', "", _style())
    return re.sub(r':root\s*\{[^}]*\}', "", rest)


def test_light_block_exists():
    _block(LIGHT)


def test_dark_block_still_exists():
    _block(":root")


def test_glass_vars_defined_in_both_themes():
    dark = _block(":root")
    light = _block(LIGHT)
    for name in GLASS_VARS:
        _var(dark, name)
        _var(light, name)


def test_on_accent_var_defined_in_both_themes():
    for name in TEXT_VARS:
        _var(_block(":root"), name)
        _var(_block(LIGHT), name)


def test_no_raw_white_overlays_outside_theme_blocks():
    """Fuera de los bloques de tema, nada debe usar rgba(255,255,255,…) crudo."""
    offenders = [
        line.strip() for line in _outside_theme_blocks().split("\n")
        if "rgba(255,255,255" in line
    ]
    assert not offenders, (
        "usa variables de tema en vez de rgba(255,255,255,…):\n" + "\n".join(offenders)
    )


def test_no_raw_white_text_outside_theme_blocks():
    """El texto blanco pasa por --on-accent / --on-photo."""
    offenders = [
        line.strip() for line in _outside_theme_blocks().split("\n")
        if "#fff" in line.lower()
    ]
    assert not offenders, (
        "usa var(--on-accent) o var(--on-photo) en vez de #fff:\n" + "\n".join(offenders)
    )
