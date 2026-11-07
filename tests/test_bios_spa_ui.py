"""Tests de la UI de la SPA de BIOS (la sección React de *ROMs y BIOS*).

Se mira el código fuente de los componentes, igual que los tests de la
interfaz clásica miran `templates/index.html`: lo que se comprueba es que no
vuelvan a aparecer las cosas que estropearon el flujo.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODAL = ROOT / "frontend" / "src" / "components" / "bios" / "BiosSystemModal.tsx"
PAGINA = ROOT / "frontend" / "src" / "pages" / "Bios.tsx"


def test_el_modal_toma_los_datos_del_catalogo_de_ahora_mismo():
    """El modal guarda el slug, no una copia.

    Con una copia, al subir una BIOS el modal seguía enseñando el estado
    anterior y había que cerrarlo y abrirlo de nuevo.
    """
    h = PAGINA.read_text(encoding="utf-8")
    assert "selectedSlug" in h
    assert "useState<BiosSystemView | null>" not in h
    assert "systems.find((system) => system.slug === selectedSlug)" in h


def test_el_boton_de_reparar_solo_si_hay_algo_que_reparar():
    """Si no hay BIOS reparables, el botón no se muestra (era inerte)."""
    h = MODAL.read_text(encoding="utf-8")
    assert "reparables.length > 0" in h


def test_al_subir_se_refresca_el_catalogo():
    """Tras subir, el modal se refresca: `onRepaired` vuelve a pedir el catálogo.

    Sin esto, el modal seguía enseñando el estado anterior y había que
    cerrarlo y abrirlo de nuevo.
    """
    h = MODAL.read_text(encoding="utf-8")
    assert "await api.biosUpload(" in h
    assert "onRepaired()" in h


def test_el_input_de_ficheros_no_esta_oculto():
    """Con `display: none` el input no lo alcanza ni el teclado."""
    h = MODAL.read_text(encoding="utf-8")
    assert 'className="hidden"' not in h
    assert "h-px w-px" in h or "sr-only" in h
