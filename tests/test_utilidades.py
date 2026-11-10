# -*- coding: utf-8 -*-
"""Las utilidades de conversion que instala el ``install.sh``.

Aqui no se descarga nada: la funcion de descarga se sustituye por una que
escribe unos bytes de prueba. Lo que se comprueba es lo que de verdad
importa: que la suma ``sha256`` se verifica antes de instalar, que el
binario acaba con permisos de ejecucion y que lo que no se puede instalar
solo lleva su motivo.
"""

import hashlib
import io
import os
import tarfile
from pathlib import Path

import pytest

from romtools import utilidades


# ── La tabla de utilidades ────────────────────────────────────────────────

def test_las_utilidades_descargables_estan_todas():
    ids = [entrada["id"] for entrada in utilidades.UTILIDADES]
    assert "rom-converto" in ids
    assert "nodtool" in ids
    assert "3dstool" in ids


def test_cada_utilidad_dice_de_que_proyecto_y_release_sale():
    for entrada in utilidades.UTILIDADES:
        assert entrada["proyecto"], entrada["id"]
        assert entrada["version"].startswith("v"), entrada["id"]
        assert entrada["licencia"], entrada["id"]
        assert entrada["binario"], entrada["id"]


def test_las_sumas_son_sha256_de_64_caracteres():
    """Una suma mal escrita haria fallar la instalacion en la consola."""
    for entrada in utilidades.UTILIDADES:
        for arq, (asset, suma) in entrada["assets"].items():
            assert len(suma) == 64, "%s/%s" % (entrada["id"], arq)
            assert all(c in "0123456789abcdef" for c in suma), "%s/%s" % (entrada["id"], arq)
            assert asset, "%s/%s" % (entrada["id"], arq)


def test_el_rom_converto_tiene_binario_para_las_tres_arquitecturas():
    entrada = utilidades.por_id("rom-converto")
    assert set(entrada["assets"]) == {"x86_64", "aarch64", "armv7l"}


def test_el_nodtool_tiene_binario_estatico_para_tres_arquitecturas():
    entrada = utilidades.por_id("nodtool")
    assert set(entrada["assets"]) == {"x86_64", "aarch64", "i686"}


def test_el_3dstool_solo_tiene_binario_para_x86_64():
    """El 3dstool sólo publica build para x86_64: en una ARM no se puede."""
    entrada = utilidades.por_id("3dstool")
    assert set(entrada["assets"]) == {"x86_64"}


def test_la_url_apunta_a_la_release_del_proyecto():
    url = utilidades.url_de(utilidades.por_id("rom-converto"), "rom-converto-cli-linux-x64")
    assert url == ("https://github.com/DevYukine/rom-converto/releases/download/"
                   "v0.24.0/rom-converto-cli-linux-x64")


# ── Las que no se pueden instalar ─────────────────────────────────────────

def test_las_que_no_se_instalan_solo_dicen_el_motivo():
    for entrada in utilidades.no_instalables():
        assert entrada["motivo"].strip(), entrada["id"]
        assert entrada["nombre"], entrada["id"]


def test_ninguna_de_las_no_instalables_se_instala_a_solas():
    instalables = {entrada["id"] for entrada in utilidades.UTILIDADES}
    for entrada in utilidades.no_instalables():
        assert entrada["id"] not in instalables, entrada["id"]


def test_las_no_instalables_cubren_las_herramientas_sin_binario():
    """Las que el manager lista pero no se pueden bajar tienen que estar aqui."""
    ids = {entrada["id"] for entrada in utilidades.no_instalables()}
    for esperado in ("dolphin-tool", "wiitool", "ndstool", "extract-xiso",
                     "maxcso", "xorriso"):
        assert esperado in ids, esperado


# ── La arquitectura ───────────────────────────────────────────────────────

@pytest.mark.parametrize("maquina,esperado", [
    ("x86_64", "x86_64"),
    ("AMD64", "x86_64"),
    ("aarch64", "aarch64"),
    ("arm64", "aarch64"),
    ("armv7l", "armv7l"),
    ("i686", "i686"),
    ("riscv64", ""),
])
def test_la_arquitectura_se_reconoce(monkeypatch, maquina, esperado):
    monkeypatch.setattr(utilidades.platform, "machine", lambda: maquina)
    assert utilidades.arquitectura() == esperado


def test_la_carpeta_de_los_binarios_es_el_bin_del_base():
    assert utilidades.utilidades_dir("/userdata/system") == os.path.join("/userdata/system", "bin")
    assert utilidades.utilidades_dir("") == os.path.join("/userdata/system", "bin")


# ── Instalar ──────────────────────────────────────────────────────────────

def _entrada(contenido: bytes, formato: str = "binario") -> dict:
    """Una utilidad de mentira, con la suma de sus bytes de prueba."""
    suma = hashlib.sha256(contenido).hexdigest()
    entrada = {
        "id": "demo",
        "nombre": "demo",
        "binario": "demo",
        "proyecto": "ejemplo/demo",
        "version": "v1.0.0",
        "licencia": "MIT",
        "para": "para las pruebas",
        "formato": formato,
        "assets": {"x86_64": ("demo-linux-x64", suma)},
    }
    if formato == "tar.gz":
        entrada["miembro"] = "demo"
    return entrada


def _descarga_falsa(contenido: bytes, llamadas: list | None = None):
    """Sustituye a la descarga: escribe bytes en vez de ir a la red."""
    def descarga(url, ruta, timeout=900, progreso=None):
        if llamadas is not None:
            llamadas.append(url)
        with open(ruta, "wb") as fh:
            fh.write(contenido)
        if progreso:
            progreso(len(contenido), len(contenido))
        return len(contenido)
    return descarga


def test_instala_verifica_la_suma_y_deja_el_binario_ejecutable(tmp_path, monkeypatch):
    contenido = b"#!/bin/sh\necho hola\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "instalada", resumen["detalle"]
    destino = tmp_path / "demo"
    assert destino.read_bytes() == contenido
    assert os.access(str(destino), os.X_OK), "tiene que ser ejecutable"


def test_no_instala_un_archivo_cuya_suma_no_cuadra(tmp_path, monkeypatch):
    contenido = b"contenido mauvais"
    entrada = _entrada(contenido)
    # Se cambia la suma esperada: es como si el asset fuese otro.
    entrada["assets"]["x86_64"] = ("demo-linux-x64", "0" * 64)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "error"
    assert "sha256" in resumen["detalle"]
    assert not (tmp_path / "demo").exists(), "no debe quedar un binario sin verificar"
    assert not list(tmp_path.glob(".*descargando*")), "no debe quedar la descarga a medias"


def test_saca_el_binario_de_un_tar_gz(tmp_path, monkeypatch):
    """El 3dstool viene en un tar.gz: hay que sacar el binario de dentro."""
    contenido = b"#!/bin/sh\necho 3dstool\n"
    tarball = tmp_path / "3dstool.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        info = tarfile.TarInfo("3dstool")
        info.size = len(contenido)
        tar.addfile(info, io.BytesIO(contenido))
        extra = tarfile.TarInfo("otro.txt")
        extra.size = 3
        tar.addfile(extra, io.BytesIO(b"abc"))

    entrada = _entrada(tarball.read_bytes(), formato="tar.gz")
    entrada["miembro"] = "3dstool"
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(tarball.read_bytes()))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "instalada", resumen["detalle"]
    assert (tmp_path / "demo").read_bytes() == contenido
    assert not (tmp_path / "otro.txt").exists(), "del tar.gz solo sale el binario"


def test_no_vuelve_a_bajar_lo_que_ya_esta(tmp_path, monkeypatch):
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    llamadas: list = []
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido, llamadas))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    utilidades.instalar(entrada, str(tmp_path))

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "ya-estaba"
    assert len(llamadas) == 1, "no debe volver a descargar lo que ya esta"


def test_con_forzar_vuelve_a_bajarlo(tmp_path, monkeypatch):
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    llamadas: list = []
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido, llamadas))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    utilidades.instalar(entrada, str(tmp_path))

    resumen = utilidades.instalar(entrada, str(tmp_path), forzar=True)

    assert resumen["estado"] == "instalada"
    assert len(llamadas) == 2


def test_avisa_cuando_no_hay_binario_para_la_arquitectura(tmp_path, monkeypatch):
    entrada = _entrada(b"#!/bin/sh\n")
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "aarch64")
    entrada["assets"] = {"x86_64": ("demo-linux-x64", "0" * 64)}

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "sin-binario"
    assert "aarch64" in resumen["detalle"]


def test_el_manifiesto_apunta_que_esta_instalado(tmp_path, monkeypatch):
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))

    utilidades.instalar_varias(str(tmp_path))

    datos = utilidades.manifiesto(str(tmp_path))
    assert "demo" in datos
    assert datos["demo"]["version"] == "v1.0.0"


def test_el_manifiesto_apunta_la_suma_tambien_si_ya_estaba(tmp_path, monkeypatch):
    """Si el binario ya estaba puesto a mano, se apunta su suma igualmente."""
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))
    (tmp_path / "demo").write_bytes(contenido)

    utilidades.instalar_varias(str(tmp_path))

    datos = utilidades.manifiesto(str(tmp_path))
    assert datos["demo"]["sha256"] == hashlib.sha256(contenido).hexdigest()


def test_el_manifiesto_actualiza_la_suma_de_lo_que_ya_estaba(tmp_path, monkeypatch):
    """Un manifiesto viejo, sin suma, se completa en la siguiente pasada."""
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))
    (tmp_path / "demo").write_bytes(contenido)
    # Como queda tras una instalacion anterior, sin la suma.
    utilidades.guardar_manifiesto(str(tmp_path),
                                  {"demo": {"version": "v1.0.0", "sha256": "",
                                            "instalado": "2026-01-01T00:00:00"}})

    utilidades.instalar_varias(str(tmp_path))

    datos = utilidades.manifiesto(str(tmp_path))
    assert datos["demo"]["sha256"] == hashlib.sha256(contenido).hexdigest()
    assert datos["demo"]["instalado"] == "2026-01-01T00:00:00", "no se pierde la fecha"


def test_un_binario_ya_puesto_no_se_toca_aunque_no_haya_asset(tmp_path, monkeypatch):
    """En una arquitectura sin build, un binario puesto a mano se respeta."""
    entrada = _entrada(b"x")
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "aarch64")
    (tmp_path / "demo").write_bytes(b"#!/bin/sh\n")

    resumen = utilidades.instalar(entrada, str(tmp_path))

    assert resumen["estado"] == "ya-estaba"
    assert (tmp_path / "demo").exists()


def test_quitar_borra_el_binario_y_su_apunte(tmp_path, monkeypatch):
    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))
    utilidades.instalar_varias(str(tmp_path))

    borrado = utilidades.quitar(entrada, str(tmp_path))

    assert borrado is True
    assert not (tmp_path / "demo").exists()
    assert "demo" not in utilidades.manifiesto(str(tmp_path))
    assert utilidades.quitar(entrada, str(tmp_path)) is False


def test_un_fallo_no_impide_las_demas_utilidades(tmp_path, monkeypatch):
    """Si una falla, las otras se instalan igual."""
    bueno = b"#!/bin/sh\nbueno\n"

    def descarga(url, ruta, timeout=900, progreso=None):
        if "malo" in url:
            with open(ruta, "wb") as fh:
                fh.write(b"contenido malo")
        else:
            with open(ruta, "wb") as fh:
                fh.write(bueno)
        return 0

    mala = _entrada(b"x")
    mala["id"] = "malo"
    mala["binario"] = "malo"
    mala["assets"]["x86_64"] = ("malo-linux", "0" * 64)
    buena = _entrada(bueno)
    buena["id"] = "bueno"
    buena["binario"] = "bueno"

    monkeypatch.setattr(utilidades, "descarga", descarga)
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (mala, buena))

    resultados = utilidades.instalar_varias(str(tmp_path))

    estados = {r["id"]: r["estado"] for r in resultados}
    assert estados["malo"] == "error"
    assert estados["bueno"] == "instalada"
    assert (tmp_path / "bueno").exists()


# ── La línea de comandos ──────────────────────────────────────────────────

def _args(**extra):
    import argparse
    base = dict(command="utilidades", ids=[], destino="", arq="x86_64",
                timeout=30, forzar=False, remove=False, install=False, list=False,
                root="/userdata/system")
    base.update(extra)
    return argparse.Namespace(**base)


def test_la_linea_de_comandos_lista_lo_que_se_puede_instalar(tmp_path, capsys):
    from romtools import __main__ as cli

    codigo = cli.cmd_utilidades(_args(destino=str(tmp_path)))

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "rom-converto" in salida
    assert "nodtool" in salida
    assert "3dstool" in salida
    assert "wiitool" in salida, "las que no se pueden instalar tambien se listan"


def test_la_linea_de_comandos_instala(tmp_path, monkeypatch, capsys):
    from romtools import __main__ as cli

    contenido = b"#!/bin/sh\n"
    entrada = _entrada(contenido)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(contenido))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))

    codigo = cli.cmd_utilidades(_args(install=True, destino=str(tmp_path)))

    assert codigo == 0
    assert (tmp_path / "demo").exists()
    assert "[OK]" in capsys.readouterr().out


def test_la_linea_de_comandos_avisa_si_falla(tmp_path, monkeypatch, capsys):
    from romtools import __main__ as cli

    entrada = _entrada(b"x")
    entrada["assets"]["x86_64"] = ("demo-linux", "0" * 64)
    monkeypatch.setattr(utilidades, "descarga", _descarga_falsa(b"x"))
    monkeypatch.setattr(utilidades, "arquitectura", lambda: "x86_64")
    monkeypatch.setattr(utilidades, "UTILIDADES", (entrada,))

    codigo = cli.cmd_utilidades(_args(install=True, destino=str(tmp_path)))

    assert codigo == 1
    assert "[X]" in capsys.readouterr().out


def test_borrar_sin_decir_cual_no_hace_nada(tmp_path):
    from romtools import __main__ as cli

    codigo = cli.cmd_utilidades(_args(remove=True, destino=str(tmp_path)))

    assert codigo == 1
