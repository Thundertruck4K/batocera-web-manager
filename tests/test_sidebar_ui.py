from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

_SIDEBAR_RE = re.compile(r'<aside class="sidebar">([\s\S]*?)</aside>')
_NAV_RE = re.compile(r'<nav class="nav">([\s\S]*?)</nav>')
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF]"
)


def _sidebar() -> str:
    html = HTML.read_text(encoding="utf-8")
    m = _SIDEBAR_RE.search(html)
    assert m, 'no se encontró <aside class="sidebar">'
    return m.group(1)


def _nav() -> str:
    html = HTML.read_text(encoding="utf-8")
    m = _NAV_RE.search(html)
    assert m, 'no se encontró <nav class="nav">'
    return m.group(1)


def test_six_nav_items_with_emoji_icons():
    nav = _nav()
    assert len(re.findall(r'class="nav-item', nav)) == 6
    assert "<svg" not in nav, "los items del sidebar usan emoji, no SVG monocromo"
    assert len(_EMOJI_RE.findall(nav)) >= 6, "cada item debe llevar su emoji de color"


def test_nav_items_keep_showpanel_handlers():
    s = _sidebar()
    for pid in ["dashboard", "roms", "list", "add", "themes", "settings"]:
        assert f"showPanel('{pid}',this)" in s, f"falta handler showPanel('{pid}')"


def test_sidebar_has_five_sections():
    s = _sidebar()
    for label in ["Estado", "Contenido", "Sistemas", "Personalización", "Ajustes"]:
        assert label in s, f"falta la sección {label}"


def test_nav_has_no_svg_icons():
    assert "<svg" not in _nav(), "los items del sidebar no deben usar SVG monocromo"


def test_badges_kept():
    s = _sidebar()
    for bid in ["badge-count", "badge-biosmissing"]:
        assert f'id="{bid}"' in s, f"falta el badge {bid}"


def test_showpanel_still_toggles_single_active():
    js = HTML.read_text(encoding="utf-8")
    m = re.search(r"function showPanel\(name, btn\)\s*\{([\s\S]*?)\n\}", js)
    assert m, "falta showPanel"
    body = m.group(1)
    assert ".nav-item" in body and "remove('active')" in body and "add('active')" in body


def _theme_var(name: str) -> str:
    """Valor de una variable CSS en el bloque :root (tema oscuro)."""
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r":root\s*\{([^}]*)\}", css, re.S)
    assert m, "falta el bloque :root"
    v = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", m.group(1))
    assert v, f"falta la variable {name} en :root"
    return v.group(1).strip()


def test_active_item_is_flat_highlight():
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r"\.nav-item\.active\s*\{([^}]*)\}", css, re.S)
    assert m, "falta la regla .nav-item.active"
    body = m.group(1)
    assert "background" in body and "var(--active-bg)" in body, "el activo es un realce plano y claro"
    assert "gradient" not in body, "Aurora Glass: el activo no lleva degradado"
    assert "box-shadow" not in body, "sin relieve"
    assert "border" not in body, "sin borde"
    # El realce sigue siendo un velo blanco translucido en el tema oscuro.
    assert _theme_var("--active-bg") == "rgba(255,255,255,.085)"


def test_nav_hover_lightens_background():
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r"\.nav-item:hover\s*\{([^}]*)\}", css, re.S)
    assert m, "falta la regla .nav-item:hover"
    assert "background" in m.group(1) and "var(--hover-bg)" in m.group(1), "el hover ilumina el botón"
    assert _theme_var("--hover-bg") == "rgba(255,255,255,.055)"
