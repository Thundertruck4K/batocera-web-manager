# -*- coding: utf-8 -*-
"""El mapa de formatos por sistema y las utilidades que hacen falta."""
import types

import pytest

from romtools import formats
from romtools import formatos_sistemas as fs

#: Las extensiones que trae el `es_systems.cfg` de la consola para un sistema.
ES_SISTEMS = {
    "snes": "7z bsx dx2 fig gd3 gd7 sfc smc swc zip",
    "psp": "chd cso iso pbp",
    "gamecube": "ciso dol elf gcm gcz iso json m3u rvz wbfs",
    "psx": "cbn ccd chd cue img iso m3u mdf pbp toc",
}


def _info(kind):
    """Una informacion de formato minima, como la que devuelve el motor."""
    return types.SimpleNamespace(kind=kind, actions=[])


def _exts(sistema):
    """Las extensiones del sistema, como las devuelve el `es_systems.cfg`."""
    return ES_SISTEMS[sistema].split()


# ── Los formatos de cada sistema ───────────────────────────────────────

def test_el_cfg_de_la_consola_manda_sobre_la_tabla():
    formatos = fs.formatos_de_sistema("snes", _exts("snes"))
    assert "sfc" in formatos and "zip" in formatos
    # La extension viene con punto en el cfg: se normaliza.
    assert not any(e.startswith(".") for e in formatos)


def test_sin_cfg_se_usa_la_tabla_de_respaldo():
    formatos = fs.formatos_de_sistema("gamecube")
    assert "rvz" in formatos and "gcz" in formatos
    assert "chd" not in formatos          # el GameCube no admite CHD
    assert "zip" not in formatos          # ni ZIP


def test_un_sistema_desconocido_no_admite_nada():
    assert fs.formatos_de_sistema("no-existe-este") == []
    assert fs.formatos_de_sistema(None) == []


def test_la_nota_del_sistema_explica_el_formato():
    assert "SFC" in fs.nota_de_sistema("snes")
    assert fs.nota_de_sistema("no-existe-este") == ""


def test_el_resumen_trae_los_formatos_y_las_compresiones():
    resumen = fs.resumen_sistema("snes", _exts("snes"))
    assert resumen["sistema"] == "snes"
    assert resumen["preferido"] == "sfc"
    assert "zip" in resumen["compresiones"]
    assert "7z" in resumen["compresiones"]


# ── Las conversiones que se ofrecen ────────────────────────────────────

def test_un_psp_no_ofrece_comprimir_en_zip():
    """El PSP no admite ZIP: ofrecerlo es trabajo que luego no sirve."""
    acciones = fs.acciones_para(_info("iso"), "psp", _exts("psp"))
    ids = [a["id"] for a in acciones]
    assert "zip" not in ids
    assert "7z" not in ids
    assert "chd" in ids            # el CHD si lo admite
    assert "cso" in ids


def test_un_gamecube_no_ofrece_chd_ni_zip():
    acciones = fs.acciones_para(_info("iso-gamecube"), "gamecube",
                                _exts("gamecube"))
    ids = [a["id"] for a in acciones]
    assert "chd" not in ids
    assert "zip" not in ids
    assert "gcz" in ids
    assert "ciso" in ids


def test_snes_ofrece_las_dos_compresiones():
    """La compresion es una propiedad del sistema, no del formato."""
    acciones = fs.acciones_para(_info("snes-smc"), "snes", _exts("snes"))
    ids = [a["id"] for a in acciones]
    assert "zip" in ids
    assert "7z" in ids


def test_lo_que_el_sistema_no_admite_no_se_ofrece():
    """Las acciones que el sistema no admite no salen en la lista."""
    acciones = fs.acciones_para(_info("iso"), "psp", _exts("psp"))
    for accion in acciones:
        assert accion["admite"] is True


def test_sin_datos_del_sistema_no_se_filtra_nada():
    """Si el sistema no se conoce, se ofrece el catalogo de siempre."""
    acciones = fs.acciones_para(_info("iso"), "no-existe-este")
    ids = [a["id"] for a in acciones]
    assert "chd" in ids and "zip" in ids


def test_una_rom_ya_comprimida_no_se_vuelve_a_comprimir():
    acciones = fs.acciones_para(_info("zip"), "snes", _exts("snes"))
    ids = [a["id"] for a in acciones]
    assert "zip" not in ids
    assert "extraer" in ids


def test_cada_accion_dice_si_hay_herramienta():
    acciones = fs.acciones_para(_info("iso-gamecube"), "gamecube",
                                _exts("gamecube"))
    for accion in acciones:
        assert "disponible" in accion
        assert "herramienta" in accion
        if not accion["disponible"]:
            assert accion["falta"]
            assert "falta la utilidad" in accion["motivo"]


def test_si_falta_la_utilidad_la_accion_avisa(monkeypatch):
    """Sin `rom-converto` el RVZ aparece, pero desactivado y con el motivo."""
    monkeypatch.setattr(fs.shutil, "which", lambda binario: None)
    acciones = fs.acciones_para(_info("iso-gamecube"), "gamecube",
                                _exts("gamecube"))
    rvz = [a for a in acciones if a["id"] == "rvz"]
    assert rvz, "el RVZ se ofrece: el GameCube lo admite"
    assert rvz[0]["disponible"] is False
    assert rvz[0]["falta"] == "rom-converto"
    assert "rom-converto" in rvz[0]["motivo"]


def test_la_herramienta_nativa_siempre_esta_disponible(monkeypatch):
    monkeypatch.setattr(fs.shutil, "which", lambda binario: None)
    assert fs.herramienta_disponible("nativo") is True
    assert fs.herramienta_disponible("no-existe") is False


# ── El inventario de utilidades ─────────────────────────────────────────

def test_el_inventario_dice_que_hay_en_la_consola():
    inventario = fs.inventario_herramientas()
    assert inventario
    ids = [item["id"] for item in inventario]
    for clave in ("nativo", "chdman", "7z", "dolphin-tool", "wiitool"):
        assert clave in ids
    for item in inventario:
        assert "nombre" in item
        assert "licencia" in item
        assert "para" in item
        assert "instalar" in item
        assert "disponible" in item


def test_cada_utilidad_dice_de_donde_sale():
    for item in fs.inventario_herramientas():
        if item["id"] == "nativo":
            continue
        assert item["url"], "la utilidad %s necesita su pagina" % item["id"]
        assert item["licencia"]


# ── La extension que produce cada conversion ────────────────────────────

def test_la_extension_de_cada_accion():
    assert fs.extension_de_accion("iso") == "iso"
    assert fs.extension_de_accion("bin-cue") == "cue"
    assert fs.extension_de_accion("extraer") is None
    assert fs.extension_de_accion("7z") == "7z"


def test_la_herramienta_de_cada_accion():
    assert fs.herramienta_de_accion("chd") == "chdman"
    assert fs.herramienta_de_accion("7z") == "7z"
    assert fs.herramienta_de_accion("rvz") == "rom-converto"
    assert fs.herramienta_de_accion("iso") == "nativo"


# ── La integracion en el backend ────────────────────────────────────────

def test_el_backend_filtra_las_acciones_por_sistema(appmod, monkeypatch):
    """Lo que ve el usuario depende del sistema, no solo del formato."""
    monkeypatch.setattr(appmod, "get_system_extensions",
                        lambda system, settings, builtin_path=None:
                        set(_exts("psp")) if system == "psp" else set())
    info = _info("iso")
    ids = [a["id"] for a in appmod.tools_acciones(info, "psp", {})]
    assert "zip" not in ids
    assert "chd" in ids


def test_el_backend_avisa_de_las_utilidades(appmod):
    """El resumen de sistemas trae el catalogo de utilidades."""
    datos = appmod.tools_formatos_sistemas({})
    assert datos["ok"] is True
    assert "herramientas" in datos
    assert any(h["id"] == "chdman" for h in datos["herramientas"])


def test_el_backend_devuelve_los_sistemas_de_la_biblioteca(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "tools_sistemas",
                        lambda settings: [{"name": "snes"}, {"name": "psp"}])
    monkeypatch.setattr(appmod, "get_system_extensions",
                        lambda system, settings, builtin_path=None:
                        set(_exts(system)))
    datos = appmod.tools_formatos_sistemas({})
    sistemas = {s["sistema"]: s for s in datos["sistemas"]}
    assert set(sistemas) == {"snes", "psp"}
    assert "zip" in sistemas["snes"]["compresiones"]
    assert sistemas["psp"]["compresiones"] == []
