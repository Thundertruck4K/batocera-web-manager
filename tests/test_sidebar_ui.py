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


def test_six_nav_items_with_svg_icons():
    s = _sidebar()
    assert len(re.findall(r'class="nav-item', s)) == 6
    assert len(re.findall(r"<svg", s)) >= 6, "cada item debe tener un icono SVG"
    assert '<span class="icon">' not in s, "no deben quedar iconos emoji"


def test_nav_items_keep_showpanel_handlers():
    s = _sidebar()
    for pid in ["dashboard", "roms", "list", "add", "themes", "settings"]:
        assert f"showPanel('{pid}',this)" in s, f"falta handler showPanel('{pid}')"


def test_sidebar_has_five_sections():
    s = _sidebar()
    for label in ["Estado", "Contenido", "Sistemas", "Personalización", "Ajustes"]:
        assert label in s, f"falta la sección {label}"


def test_nav_has_no_emoji():
    assert not _EMOJI_RE.search(_nav()), "los items del sidebar no deben contener emojis"


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


def test_active_item_uses_accent_gradient_and_border():
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r"\.nav-item\.active\s*\{([^}]*)\}", css, re.S)
    assert m, "falta la regla .nav-item.active"
    body = m.group(1)
    assert "gradient" in body and "border" in body, "Variante C: gradiente + borde acento"


def test_active_item_icon_takes_accent():
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r"\.nav-item\.active\s+svg\s*\{([^}]*)\}", css, re.S)
    assert m, "falta la regla .nav-item.active svg (Variante C: icono en acento)"
    body = m.group(1)
    assert "var(--accent)" in body and "stroke" in body, "el icono activo debe tomar el acento"
