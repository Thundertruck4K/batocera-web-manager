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


# ─── Persistencia e inyección en el HTML ────────────────────────────

def test_default_settings_has_ui_theme(appmod):
    assert appmod.DEFAULT_SETTINGS.get("ui_theme") == "dark"


def test_html_tag_declares_theme_attributes():
    css = _css()
    assert 'data-theme="{{ui_theme}}"' in css
    assert 'data-theme-mode="{{ui_theme}}"' in css


def test_render_index_injects_theme(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "load_settings",
        lambda: {**appmod.DEFAULT_SETTINGS, "ui_theme": "light"},
    )
    out = appmod.render_index()
    assert 'data-theme="light"' in out
    assert 'data-theme-mode="light"' in out
    assert "{{ui_theme}}" not in out


def test_render_index_falls_back_to_dark(appmod, monkeypatch):
    monkeypatch.setattr(
        appmod, "load_settings",
        lambda: {**appmod.DEFAULT_SETTINGS, "ui_theme": "no-existe"},
    )
    out = appmod.render_index()
    assert 'data-theme="dark"' in out
    assert 'data-theme-mode="dark"' in out


# ─── Superficies que aún eran de fondo oscuro ───────────────────────

def test_modal_background_is_theme_aware():
    """El modal era translúcido sobre un scrim negro: en claro, texto oscuro
    sobre panel casi negro = ilegible. En claro debe ser opaco."""
    dark = _block(":root")
    light = _block(LIGHT)
    assert "var(--modal-bg)" in _css(), ".modal debe usar var(--modal-bg)"
    assert "--modal-bg" in dark and "--modal-bg" in light
    # En claro el fondo del modal tiene que ser opaco.
    assert "var(--panel)" in _var(light, "modal-bg")


def test_scrim_is_theme_aware():
    dark = _block(":root")
    light = _block(LIGHT)
    assert "var(--scrim)" in _css(), ".modal-overlay debe usar var(--scrim)"
    assert _var(dark, "scrim") != _var(light, "scrim")


def test_code_chip_is_theme_aware():
    dark = _block(":root")
    light = _block(LIGHT)
    assert "var(--code-bg)" in _css()
    assert _var(dark, "code-bg") != _var(light, "code-bg")


def test_gradient_text_is_darkened_in_the_light_theme():
    """Los degradados de texto del dashboard eran pastel: ilegibles en claro."""
    dark = _block(":root")
    light = _block(LIGHT)
    for name in ("hero-grad", "usage-grad"):
        assert f"var(--{name})" in _css()
        assert _var(dark, name) != _var(light, name)


def test_light_gradient_text_is_readable_on_the_light_background():
    def lum(h):
        h = h.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

        def lin(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    def ratio(a, b):
        l1, l2 = lum(a), lum(b)
        hi, lo = max(l1, l2), min(l1, l2)
        return (hi + 0.05) / (lo + 0.05)

    light = _block(LIGHT)
    bg = _var(light, "bg")
    for name in ("hero-grad", "usage-grad"):
        for hexcolor in re.findall(r"#[0-9a-fA-F]{6}", _var(light, name)):
            r = ratio(hexcolor, bg)
            assert r >= 4.5, f"claro: {hexcolor} en --{name} sobre --bg: {r:.2f} < 4.5"


# ─── Conmutador, selector y script inline ───────────────────────────

def test_inline_script_resolves_auto_before_paint():
    css = _css()
    assert "prefers-color-scheme: light" in css
    # El script va en <head>: si no, el tema se aplicaria tarde y parpadearia.
    head = css[css.index("<head>"):css.index("</head>")]
    assert "prefers-color-scheme: light" in head


def test_theme_functions_exist():
    css = _css()
    for fn in ("function toggleTheme(", "function onUiThemeChange(",
               "function saveUiTheme(", "function _applyTheme(",
               "function _resolveAutoTheme(", "function _initTheme("):
        assert fn in css, f"falta {fn}"


def test_sidebar_has_theme_toggle():
    css = _css()
    m = re.search(r'<aside class="sidebar">([\s\S]*?)</aside>', css)
    assert m, "no se encontró el sidebar"
    assert 'id="theme-toggle"' in m.group(1)
    assert "toggleTheme()" in m.group(1)


def test_settings_has_theme_selector():
    css = _css()
    assert 'id="set-ui-theme"' in css
    for value in ("dark", "light", "auto"):
        assert f'<option value="{value}"' in css


def test_theme_selector_is_wired_to_the_change_handler():
    css = _css()
    assert 'onchange="onUiThemeChange(this.value)"' in css


# ─── El modo "auto" no puede pisar un tema explicito ─────────────────

def test_the_auto_theme_listener_can_be_removed():
    """El listener de matchMedia tiene que poder quitarse.

    Con el modo "auto" activo, si el sistema operativo cambia de tema, el
    listener escribe en data-theme. Si el usuario elige despues un tema
    explicito, ese listener seguiria escribiendo encima y el tema volveria
    al del sistema sin avisar.
    """
    css = _css()
    assert "removeEventListener" in css, "falta quitar el listener de matchMedia"
    assert "removeListener" in css, "falta la API antigua de matchMedia"


def test_switching_to_an_explicit_theme_removes_the_auto_listener():
    css = _css()
    m = re.search(r"function\s+_applyTheme\(mode\)\s*\{(.*?)\n\}", css, re.S)
    assert m, "no se encontro _applyTheme"
    assert "_removeAutoThemeListener" in m.group(1), (
        "al elegir un tema explicito hay que quitar el listener de 'auto'")
