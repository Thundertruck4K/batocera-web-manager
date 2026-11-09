# -*- coding: utf-8 -*-
"""Tests del primer arranque: la comprobacion de BIOS.

La comprobacion de las BIOS **no** se hace al instalar: se hace al abrir el
manager por primera vez. El instalador solo arma el mecanismo (borra el
marcador) y avisa; el manager escanea la consola, baja de la fuente lo que
falte e informa de lo que encontro y de lo que no.

Estos tests fijan ese reparto de papeles:

- el instalador **arma** la comprobacion y no escanea nada;
- el backend avisa si queda por hacer y donde se guarda el marcador;
- la interfaz tiene el boton de escanear, el modal del primer arranque y las
  tarjetas de BIOS mas pequenas.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"
INSTALL = ROOT / "install.sh"
PAGINA = ROOT / "frontend" / "src" / "pages" / "Bios.tsx"
MODAL = ROOT / "frontend" / "src" / "components" / "bios" / "PrimerArranqueBios.tsx"
ARRASTRABLE = ROOT / "frontend" / "src" / "App.tsx"
TARJETA = ROOT / "frontend" / "src" / "components" / "bios" / "BiosSystemCard.tsx"
HOOK = ROOT / "frontend" / "src" / "hooks" / "useTrabajoBios.ts"


# ── El instalador solo arma la comprobacion ───────────────────────────

def test_el_instalador_arma_la_comprobacion():
    """El instalador borra el marcador: eso es lo que hace que el manager
    compruebe las BIOS en el primer arranque."""
    txt = INSTALL.read_text(encoding="utf-8")
    assert "batocera_manager_bios_first.json" in txt
    assert 'rm -f "$BIOS_FIRST"' in txt


def test_el_instalador_no_escanea_las_bios():
    """El escaneo NO se hace en la instalacion: solo se avisa de que pasara.

    Si el instalador bajara las BIOS, la instalacion tardaria minutos y el
    usuario veria una consola en silencio.
    """
    txt = INSTALL.read_text(encoding="utf-8")
    assert "seedhost" not in txt, "el instalador no descarga BIOS"
    # El paso de BIOS solo avisa: no hay ninguna descarga en ese trozo.
    paso = txt.split("8 · BIOS")[-1]
    assert "curl" not in paso and "wget" not in paso
    assert "se comprobarán al abrir el manager" in txt or "se comprobarán al abrir el manager" in txt


def test_el_instalador_avisa_de_lo_que_pasa():
    txt = INSTALL.read_text(encoding="utf-8")
    assert "BIOS" in txt
    assert "comprobarán" in txt or "comprobación" in txt


def test_el_marcador_se_borra_de_verdad(tmp_path):
    """Se prueba el instalador de verdad (con bash, sobre una carpeta temporal)."""
    try:
        from test_install_sh import _run
    except Exception:                                   # pragma: no cover
        pytest.skip("no hay un bash utilizable")
    base = tmp_path / "base"
    base.mkdir()
    marcador = base / "batocera_manager_bios_first.json"
    marcador.write_text(json.dumps({"fecha": 1, "resumen": {}}), encoding="utf-8")
    assert marcador.exists()

    r = _run(base, answer="n")

    assert r.returncode == 0, r.stdout + r.stderr
    assert not marcador.exists(), "el marcador debe quedar borrado"
    assert "BIOS" in r.stdout


# ── El marcador y la comprobacion ──────────────────────────────────────

def test_sin_marcador_queda_por_comprobar(appmod):
    estado = appmod.bios_firstcheck({})
    assert estado["ok"] is True
    assert estado["pendiente"] is True
    assert estado["fecha"] is None


def test_con_marcador_ya_no_queda_por_comprobar(appmod):
    appmod._bios_first_write({"esperadas": 12, "faltantes": 3})
    estado = appmod.bios_firstcheck({})
    assert estado["pendiente"] is False
    assert estado["fecha"]
    assert estado["resumen"]["esperadas"] == 12


def test_un_marcador_roto_no_tumba(appmod):
    """Un fichero a medias no puede dejar la aplicacion sin responder."""
    ruta = appmod._bios_first_file()
    ruta.write_text("{esto no es json", encoding="utf-8")
    estado = appmod.bios_firstcheck({})
    assert estado["ok"] is True
    assert estado["pendiente"] is True


def test_el_marcador_vive_al_lado_de_los_ajustes(appmod):
    """El marcador va en la carpeta de sistema, no en la de las BIOS."""
    ruta = appmod._bios_first_file()
    assert ruta.name == "batocera_manager_bios_first.json"
    assert ruta.parent == Path(appmod.SETTINGS_FILE).parent


def test_los_endpoints_nuevos_estan():
    txt = APP.read_text(encoding="utf-8")
    assert '"/api/bios/firstcheck"' in txt
    assert '"/api/bios/descargar/start"' in txt
    assert '"/api/bios/job"' in txt


def test_el_escaneo_va_en_segundo_plano():
    """Baja ficheros de internet: tiene que ir en un hilo, no en la peticion."""
    txt = APP.read_text(encoding="utf-8")
    bloque = txt.split('"/api/bios/descargar/start"')[1][:600]
    assert "_rt_jobs.JOBS.lanzar" in bloque


def test_la_comprobacion_no_toca_lo_que_ya_esta():
    """Solo se baja lo que falta: nada se sobrescribe."""
    txt = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "No borra ni sobrescribe nada que ya este bien" in txt
    fuente = (ROOT / "romtools" / "biosfuente.py").read_text(encoding="utf-8")
    assert "faltantes" in fuente


# ── La interfaz ─────────────────────────────────────────────────────────

def test_el_boton_de_escanear_se_ve():
    """El boton de reescanear no puede quedar escondido en un icono."""
    h = PAGINA.read_text(encoding="utf-8")
    assert "Escanear el sistema" in h


def test_el_modal_del_primer_arranque_esta_montado():
    """El modal se monta en la aplicacion: sale en cualquier pagina."""
    h = ARRASTRABLE.read_text(encoding="utf-8")
    assert "PrimerArranqueBios" in h
    assert MODAL.exists()


def test_el_modal_enseña_el_progreso_y_avisa():
    """El trabajo es largo: la interfaz tiene que decir que sigue viva."""
    h = MODAL.read_text(encoding="utf-8")
    assert "<Progress" in h
    assert "no hace falta cerrar la ventana" in h


def test_el_modal_informa_de_lo_que_no_se_encuentra():
    """Lo que no esta en la fuente se dice: no se disimula."""
    h = MODAL.read_text(encoding="utf-8")
    assert "no están en la fuente" in h
    assert "Escanear el sistema" in h


def test_la_pagina_muestra_el_progreso_del_escaneo():
    h = PAGINA.read_text(encoding="utf-8")
    assert "<Progress" in h
    assert "no hace falta cerrar la ventana" in h.lower() or \
           "No hace falta cerrar la ventana" in h


def test_las_tarjetas_de_bios_son_mas_pequenas():
    """La seccion de BIOS es una rejilla apretada: muchas columnas."""
    h = PAGINA.read_text(encoding="utf-8")
    assert "xl:grid-cols-4" in h
    assert "2xl:grid-cols-6" in h
    tarjeta = TARJETA.read_text(encoding="utf-8")
    assert "aspect-[16/6]" in tarjeta


def test_el_trabajo_se_pregunta_en_segundo_plano():
    """La consulta del trabajo va con temporizador: no bloquea la pagina."""
    h = HOOK.read_text(encoding="utf-8")
    assert "setTimeout" in h
    assert "biosJob" in h
