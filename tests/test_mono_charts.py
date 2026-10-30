"""Tests del design system 'mono' (adaptación de amicro.dev/mono-charts).

Las tarjetas del manager adoptan la estructura de mono-charts:
contenedor de 24px, "stage" interior de 14px, píldora de etiqueta y pie
monoespaciado. Los gráficos (velocímetro de 240°, barras redondeadas, donut y
área monótona) se implementan en JS puro: el proyecto no usa framework ni
paso de build, así que no puede usar React ni Recharts.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

DARK = ":root"
LIGHT = ':root[data-theme="light"]'

# Tokens que dependen del tema (el valor cambia entre oscuro y claro).
THEME_TOKENS = [
    "mono-stage", "mono-stage-line", "mono-track",
    "mono-pill-bg", "mono-pill-fg", "mono-pill-line",
    "mono-grid", "mono-inner-hi",
]

# Tokens independientes del tema: se declaran una vez en :root y los hereda
# el tema claro por cascada.
GEOMETRY_TOKENS = ["mono-radius", "mono-stage-radius"]


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _blocks(selector: str) -> list[str]:
    return re.findall(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", _html())


def _vars(selector: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for block in _blocks(selector):
        for m in re.finditer(r"--(mono-[a-z0-9-]+)\s*:\s*([^;]+);", block):
            out[m.group(1)] = m.group(2).strip()
    return out


# ─── Tokens y geometría ──────────────────────────────────────────────────

def test_mono_tokens_defined_in_both_themes():
    dark = _vars(DARK)
    light = _vars(LIGHT)
    for name in THEME_TOKENS:
        assert name in dark, f"--{name} falta en el tema oscuro"
        assert name in light, f"--{name} falta en el tema claro"
    for name in GEOMETRY_TOKENS:
        assert name in dark, f"--{name} falta en :root"


def test_mono_container_geometry_matches_the_reference():
    dark = _vars(DARK)
    assert dark["mono-radius"] == "24px"
    assert dark["mono-stage-radius"] == "14px"


def test_mono_palette_has_six_colors_in_both_themes():
    for name, block in (("oscuro", _vars(DARK)), ("claro", _vars(LIGHT))):
        for i in range(1, 7):
            value = block.get(f"mono-p{i}", "")
            assert re.fullmatch(r"#[0-9a-fA-F]{6}", value), \
                f"--mono-p{i} del tema {name}: {value!r}"


def test_mono_palette_differs_between_themes():
    """La paleta del claro usa tonos mas oscuros para mantener el contraste."""
    dark = _vars(DARK)
    light = _vars(LIGHT)
    assert dark["mono-p1"] != light["mono-p1"]


# ─── Componentes JS ──────────────────────────────────────────────────────

def test_monocharts_object_is_defined():
    h = _html()
    assert "const MonoCharts" in h
    for fn in ("function gauge(", "function rows(", "function donut(",
               "function area(", "function areaMarkup(", "function monotone("):
        assert fn in h, f"falta {fn}"


def test_gauge_is_a_240_degree_arc():
    """El velocimetro barre 240 grados (de las 7 a las 5 en punto), como en mono-charts."""
    h = _html()
    body = h[h.index("function gauge(host, opts)"):]
    body = body[:body.index("function rows(host, opts)")]
    # de las 7 en punto (150 grados) a las 5 en punto (30 grados), pasando por arriba
    assert "150 * Math.PI / 180" in body
    assert "30 * Math.PI / 180" in body
    # el arco se mide en porcentajes del trazo (pathLength=100)
    assert "pathLength: '100'" in body
    assert "stroke-dasharray" in body
    # arco mayor (flag 1) para que el barrido pase por arriba
    assert "A ${r} ${r} 0 1 1" in body
    assert "viewBox: '0 0 160 84'" in body
    # los angulos declarados deben sumar un barrido de 240 grados
    a0 = int(re.search(r"a0 = (\d+) \* Math\.PI", body).group(1))
    a1 = int(re.search(r"a1 = (\d+) \* Math\.PI", body).group(1))
    assert (a1 + 360) - a0 == 240


def test_donut_supports_a_colored_palette():
    h = _html()
    assert "function paletteOf(host, n)" in h
    assert "opts.palette ? paletteOf(host, data.length) : null" in h


def test_area_chart_uses_a_monotone_curve_with_gradient():
    h = _html()
    assert "function monotone(pts)" in h
    assert "linearGradient" in h
    assert "stroke-linecap=\"round\"" in h


# ─── Integración en el dashboard ─────────────────────────────────────────

def test_kpi_cards_use_a_mono_stage_with_sparkline():
    h = _html()
    for key in ("cpu", "gpu", "ram", "disk"):
        assert f'id="kpi-{key}-spark"' in h, key
        assert f'id="kpi-{key}-pill"' in h, key


def test_dashboard_charts_are_wired():
    h = _html()
    assert "MonoCharts.gauge(document.getElementById('gauge-cpu')" in h
    assert "MonoCharts.donut(document.getElementById('dash-storage-donut')" in h
    assert "MonoCharts.rows(document.getElementById('dash-storage-rows')" in h
    assert "MonoCharts.areaMarkup(counts" in h


def test_card_headers_and_bodies_use_the_mono_pieces():
    css = _html()
    for selector in (".mono-pill-accent", ".card-title .icon", ".mono-stage",
                     ".mono-foot", ".mono-value", ".mono-row", ".mono-spark"):
        assert selector in css, f"falta {selector}"


def test_legacy_charts_were_replaced():
    """El tacho con aguja y el tanque de liquido los sustituyen los componentes mono."""
    h = _html()
    assert "tachoInit(" not in h
    assert "tankGauge(" not in h
    assert "tachoArcPath(" not in h


def test_no_raw_white_overlays_outside_theme_blocks():
    """El brillo interior del stage debe pasar por --mono-inner-hi."""
    css = _html()
    style = css[css.index("<style>"):css.index("</style>")]
    rest = re.sub(rf'{re.escape(LIGHT)}\s*\{{[^}}]*\}}', "", style)
    rest = re.sub(r":root\s*\{[^}]*\}", "", rest)
    offenders = [ln.strip() for ln in rest.split("\n") if "rgba(255,255,255" in ln]
    assert not offenders, "usa variables de tema:\n" + "\n".join(offenders)
