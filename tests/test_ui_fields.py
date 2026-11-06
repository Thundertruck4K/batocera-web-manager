"""Tests de los controles de formulario de la SPA.

Dos cosas se-arreglaron:

- Las listas desplegables (`<select>`) nativas pintan su propio fondo (blanco
  con letras pálidas) e ignoran el `bg-transparent` del tema. Se les quita el
  aspecto nativo, se les da el fondo de la app y se les dibuja la flecha; la
  lista de opciones se paints con el `color-scheme` declarado en el CSS.
- Los interruptores no eran simétricos: la bola no tenía `left`, asi que el
  navegador la colocaba centrada y al activarse se salia del carril.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
FIELD = SRC / "components" / "ui" / "Field.tsx"
CSS = SRC / "index.css"


def _read(path: Path) -> str:
    assert path.exists(), f"falta {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _bloque(src: str, inicio: str) -> str:
    """Trozo de código desde `inicio` hasta la siguiente exportación."""
    i = src.index(inicio)
    resto = src[i:]
    m = re.search(r"\nexport ", resto[len(inicio):])
    if m:
        return resto[: len(inicio) + m.start()]
    return resto


# ── Lista desplegable ──────────────────────────────────────────────────

def test_la_lista_desplegable_quita_el_aspecto_nativo():
    """Sin `appearance-none` el navegador pinta su fondo (blanco) y sus letras."""
    src = _read(FIELD)
    select = _bloque(src, "export const Select")
    assert "appearance-none" in select, \
        "el <select> debe usar appearance-none para no pintar su propio fondo"
    assert "pr-9" in select, "hay que dejar sitio a la flecha"


def test_la_lista_desplegable_dibuja_su_propia_flecha():
    src = _read(FIELD)
    select = _bloque(src, "export const Select")
    assert "ChevronDown" in select
    assert "pointer-events-none" in select, "la flecha no debe steals el clic"


def test_el_css_declara_el_color_scheme_de_las_listas():
    """La lista de opciones la pinta el navegador: necesita el color-scheme."""
    css = _read(CSS)
    assert re.search(r"select\s*\{[^}]*color-scheme:\s*light", css), \
        "las listas deben declarar color-scheme"
    assert re.search(r"\.dark select\s*\{[^}]*color-scheme:\s*dark", css), \
        "en tema oscuro la lista debe ir en oscuro"
    assert re.search(r"select option\s*\{[^}]*background-color", css), \
        "las opciones deben llevar el fondo del tema"


# ── Interruptor ────────────────────────────────────────────────────────

def test_el_interruptor_ancla_la_bola_para_que_no_se_salga():
    """Sin `left` el navegador centra la bola y al activarse se sale del carril."""
    src = _read(FIELD)
    toggle = _bloque(src, "export function Toggle")
    assert "left-0.5" in toggle, "la bola debe ir anclada a la izquierda"
    assert "translate-x-5" in toggle, "el recorrido debe ser de 20 px (2 px de margen)"
    assert "translate-x-[1.375rem]" not in toggle, \
        "el desplazamiento anterior sacaba la bola del carril"
    assert "translate-x-0.5" not in toggle, \
        "el desplazamiento anterior partia de una posicion no anclada"


def test_el_interruptor_usa_los_colores_del_tema():
    """La bola blanca se perdia en el tema claro (carril negro)."""
    src = _read(FIELD)
    toggle = _bloque(src, "export function Toggle")
    assert "bg-primary-foreground" in toggle, "encendido: bola del color del texto principal"
    assert "bg-foreground" in toggle, "apagado: bola del color del texto"
    assert "bg-white" not in toggle, "la bola blanca no contrasta en tema claro"


# ── Donde se usan ──────────────────────────────────────────────────────

def test_los_desplegables_de_aniadir_sistema_usan_el_componente():
    """«ROMs y extensiones» (Tema) e «Identidad del sistema» (Tipo de equipo)."""
    src = _read(SRC / "pages" / "SystemForm.tsx")
    assert src.count("<Select") == 2, "deben ser los dos desplegables de la pagina"
    assert 'id="hardware"' in src
    assert 'id="theme"' in src
