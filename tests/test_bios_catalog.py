"""Tests de la gestión de BIOS: catálogo oficial, estado real y reparación.

La lista de BIOS que exige Batocera no es fija: la consola la trae en
`/usr/bin/batocera-systems` (slug, nombre, ruta, md5 y el miembro exacto que
va DENTRO de cada ZIP) y en `readme.txt`. El campo `zippedFile` es la clave:
un ZIP es correcto si lleva dentro los ficheros que se piden, no si su md5
coincide, porque el md5 del ZIP no es el de lo que contiene.

Y al revés: Batocera tampoco es rígido con el hash de las BIOS. Si el fichero
está en su sitio, el emulador funciona igual. Por eso el estado se decide por
**presencia y estructura**, nunca por el hash.
"""
from __future__ import annotations

import hashlib
import json
import zipfile

import pytest


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _script(catalogo: dict) -> str:
    """Genera un `batocera-systems` falso con el catálogo dado."""
    return "#!/usr/bin/env python\nBIOS_FILES = " + json.dumps(catalogo, indent=2) + "\n"


def _zip(path, members: dict):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)


def _reset(appmod):
    appmod._bios_catalog_cache["ts"] = 0.0
    appmod._bios_catalog_cache["data"] = None
    appmod._bios_index_cache.clear()
    appmod._bios_zip_cache.clear()
    appmod._bios_zipidx_cache.clear()


@pytest.fixture
def entorno(appmod, tmp_path, monkeypatch):
    """Catálogo oficial falso, carpeta de BIOS temporal y ajustes aislados."""
    script = tmp_path / "batocera-systems"
    script.write_text(_script({}), encoding="utf-8")
    monkeypatch.setattr(appmod, "BIOS_CATALOG_SCRIPT", script)
    monkeypatch.setattr(appmod, "BIOS_CATALOG_ALT", tmp_path / "no-hay-alternativa")
    monkeypatch.setattr(appmod, "BIOS_README_FILE", tmp_path / "no-hay-readme.txt")
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    bios = tmp_path / "bios"
    bios.mkdir()
    # El catálogo guardado en disco (respaldo cuando el script no se puede
    # leer) no debe pasar de un test a otro.
    cache = appmod._bios_catalog_disk_file()
    if cache.exists():
        cache.unlink()
    _reset(appmod)
    yield {"bios": bios, "script": script,
           "settings": {"bios_dir": str(bios), "roms_base": str(tmp_path / "roms")}}
    _reset(appmod)


def _catalogo_zip(md5_miembro: str) -> dict:
    """Catálogo de un sistema cuya BIOS es un ZIP con un miembro dentro."""
    return {
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": md5_miembro, "zippedFile": "alf rev 57.u8", "file": "bios/adam.zip"},
        ]},
    }


# ── El catálogo ────────────────────────────────────────────────────────

def test_el_catalogo_oficial_manda(appmod, entorno):
    """El script de la consola es la fuente de verdad."""
    md5 = "01bba3bcd46d8a586dd6ec555accc133"
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    catalog = appmod.get_bios_catalog()
    assert catalog["source"] == str(entorno["script"])
    adam = catalog["systems"]["adam"]
    assert adam["name"] == "Coleco Adam"
    # La ruta pierde el prefijo `bios/` (la carpeta real es /userdata/bios)
    assert "adam.zip" in adam["files"]
    # El miembro del ZIP se guarda con su nombre y su md5
    miembros = adam["files"]["adam.zip"]["members"]
    assert miembros == [{"name": "alf rev 57.u8", "md5": md5}]


def test_respaldo_al_readme(appmod, entorno):
    """Sin el script oficial se usa el readme.txt de la consola."""
    readme = entorno["script"].parent / "readme.txt"
    readme.write_text(
        "Coleco Adam:\n"
        " bios/adam.zip\n"
        "01bba3bcd46d8a586dd6ec555accc133 bios/adam.zip\n"
        " bios/adam_ddp.zip\n"
        " bios/adam_fdc.zip\n"
        " bios/adam_kb.zip\n"
        " bios/adam_prn.zip\n",
        encoding="utf-8")
    appmod.BIOS_README_FILE = readme
    _reset(appmod)
    catalog = appmod.get_bios_catalog()
    assert catalog["source"] == str(readme)
    # El readme no trae slug: se empareja con el catálogo embebido por rutas
    assert "adam" in catalog["systems"]
    assert catalog["systems"]["adam"]["files"]["adam.zip"]["md5s"] == [
        "01bba3bcd46d8a586dd6ec555accc133"]


def test_una_seccion_desconocida_conserva_su_nombre(appmod, entorno):
    """Una sección que no encaja con el catálogo embebido se queda con su nombre."""
    readme = entorno["script"].parent / "readme.txt"
    readme.write_text("Sistema Inventado:\n bios/inventado.bin\n", encoding="utf-8")
    appmod.BIOS_README_FILE = readme
    _reset(appmod)
    catalog = appmod.get_bios_catalog()
    assert "sistema_inventado" in catalog["systems"]
    assert catalog["systems"]["sistema_inventado"]["name"] == "Sistema Inventado"


def test_respaldo_al_catalogo_embebido(appmod, entorno):
    """Sin nada en la consola se usa el BIOS_DB embebido."""
    catalog = appmod.get_bios_catalog()
    assert catalog["source"] == "builtin"
    assert "adam" in catalog["systems"]


def test_el_catalogo_guardado_sirve_de_respaldo(appmod, entorno):
    """Si el script no se puede leer, se usa el último catálogo bueno.

    El embebido es de otra versión y tiene más rutas (376 frente a 362), así
    que usarlo de golpe haría que todos los estados cambiasen sin motivo.
    """
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "01bba3bcd46d8a586dd6ec555accc133", "file": "bios/adam.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    bueno = appmod.get_bios_catalog()
    assert bueno["source"] == str(entorno["script"])

    # Ahora el script deja de poder leerse (la SD falla de vez en cuando).
    entorno["script"].unlink()
    _reset(appmod)
    respaldo = appmod.get_bios_catalog()
    assert respaldo["source"] == str(entorno["script"])
    assert respaldo["systems"] == bueno["systems"]


# ── Los estados ────────────────────────────────────────────────────────

def test_un_zip_correcto_se_measure_por_su_contenido(appmod, entorno):
    """Regresión: el md5 del ZIP no es el de lo que lleva dentro.

    Un ZIP cuyo md5 propio no está en la lista aceptada, pero que contiene el
    fichero que pide el catálogo con su md5, está bien. Antes se marcaba como
    incorrecto.
    """
    contenido = b"ALF ROM"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"alf rev 57.u8": contenido})
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["adam"]["files"][0]
    assert fichero["estado"] == "ok"
    # Y el md5 propio del ZIP no coincide con el esperado
    assert fichero["md5"] != md5


def test_zip_incompleto(appmod, entorno):
    """Al ZIP le falta un miembro: no está bien."""
    entorno["script"].write_text(
        _script(_catalogo_zip("01bba3bcd46d8a586dd6ec555accc133")), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"otro fichero.u8": b"xxx"})
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["adam"]["files"][0]
    assert fichero["estado"] == "miembro_falta"
    assert fichero["faltan"] == ["alf rev 57.u8"]


def test_fichero_plano_ok(appmod, entorno):
    """Un fichero con el md5 esperado está bien."""
    contenido = b"5200 rom"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": md5, "file": "bios/5200.rom"}]}}), encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "5200.rom").write_bytes(contenido)
    data = appmod.scan_bios(entorno["settings"])
    assert data["systems"]["atari5200"]["files"][0]["estado"] == "ok"


def test_el_hash_no_decide_el_estado(appmod, entorno):
    """Un fichero con un md5 que no es el esperado: si está, está bien.

    Batocera no es rígido con el hash de las BIOS (las de triforce o hikaru
    lanzan los juegos con el hash que traía la tarjeta), así que un md5
    distinto no convierte la BIOS en un problema.
    """
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": "281f20ea4320404ec820fb7ec0693b38", "file": "bios/5200.rom"}]}}),
        encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "5200.rom").write_bytes(b"otra cosa")
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["atari5200"]["files"][0]
    assert fichero["estado"] == "ok"
    # El hash se sigue enseñando como dato.
    assert fichero["md5"] == _md5(b"otra cosa")


def test_el_miembro_sirve_por_nombre(appmod, entorno):
    """El ZIP lleva el fichero que pide el catálogo con otro contenido.

    Sin verificación de hash, lo que importa es que el fichero esté dentro con
    el nombre que espera Batocera.
    """
    entorno["script"].write_text(
        _script(_catalogo_zip("01bba3bcd46d8a586dd6ec555accc133")), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"alf rev 57.u8": b"otro contenido"})
    data = appmod.scan_bios(entorno["settings"])
    assert data["systems"]["adam"]["files"][0]["estado"] == "ok"


def test_sin_hash_publicado(appmod, entorno):
    """Batocera no publica md5 para ese fichero: está, pero sin verificar."""
    entorno["script"].write_text(_script({
        "snes": {"name": "Super Nintendo", "biosFiles": [
            {"md5": "", "file": "bios/snes.bin"}]}}), encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "snes.bin").write_bytes(b"lo que sea")
    data = appmod.scan_bios(entorno["settings"])
    assert data["systems"]["snes"]["files"][0]["estado"] == "sin_verificar"


def test_ausente(appmod, entorno):
    """No está en ninguna parte."""
    entorno["script"].write_text(_script({
        "segaai": {"name": "Sega AI", "biosFiles": [
            {"md5": "", "file": "bios/segaai.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    data = appmod.scan_bios(entorno["settings"])
    assert data["systems"]["segaai"]["files"][0]["estado"] == "ausente"


def test_reparable_zip(appmod, entorno):
    """El miembro que falta está dentro de otro ZIP de la consola."""
    contenido = b"ALF ROM"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": contenido})
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["adam"]["files"][0]
    assert fichero["estado"] == "reparable_zip"
    assert fichero["fuente"] == "otro.zip"


def test_reparable_ruta(appmod, entorno):
    """El fichero está en la consola pero en otra carpeta."""
    contenido = b"5200 rom"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": md5, "file": "bios/5200.rom"}]}}), encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "Machines").mkdir()
    (entorno["bios"] / "Machines" / "5200.rom").write_bytes(contenido)
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["atari5200"]["files"][0]
    assert fichero["estado"] == "reparable_ruta"
    assert fichero["fuente"] == "Machines/5200.rom"


def test_omitida(appmod, entorno):
    """El usuario la marcó como no necesaria."""
    entorno["script"].write_text(_script({
        "segaai": {"name": "Sega AI", "biosFiles": [
            {"md5": "", "file": "bios/segaai.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    appmod._missing_bios_skipped.add("segaai/segaai.zip")
    data = appmod.scan_bios(entorno["settings"])
    assert data["systems"]["segaai"]["files"][0]["estado"] == "omitida"
    assert data["summary"]["omitida"] == 1


def test_el_resumen_cuenta_y_los_extras(appmod, entorno):
    """El resumen cuadra y los ficheros de más se cuentan aparte."""
    md5 = _md5(b"datos")
    entorno["script"].write_text(_script({
        "segaai": {"name": "Sega AI", "biosFiles": [
            {"md5": md5, "file": "bios/segaai.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "segaai.zip").write_bytes(b"datos")
    (entorno["bios"] / "readme.txt").write_text("no me pide nadie", encoding="utf-8")
    data = appmod.scan_bios(entorno["settings"])
    assert data["summary"]["ok"] == 1
    assert data["summary"]["ausente"] == 0
    assert data["extras"] == 1
    assert data["scanned"] == 2


# ── La reparación ──────────────────────────────────────────────────────

def test_reparar_reconstruye_el_zip(appmod, entorno):
    """Se reúne el ZIP con los miembros que pide el catálogo."""
    contenido = b"ALF ROM"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": contenido})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is True
    assert resultado["estado"] == "ok"
    destino = entorno["bios"] / "adam.zip"
    with zipfile.ZipFile(destino) as z:
        assert z.namelist() == ["alf rev 57.u8"]
        assert _md5(z.read("alf rev 57.u8")) == md5


def test_reparar_manda_el_original_a_la_cuarentena(appmod, entorno):
    """El ZIP que estaba en su sitio no se pisa: se guarda aparte."""
    contenido = b"ALF ROM"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    viejo = entorno["bios"] / "adam.zip"
    _zip(viejo, {"sin relacion": b"basura"})
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": contenido})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is True
    cuarentena = entorno["bios"] / ".quarantine"
    assert cuarentena.is_dir()
    assert any(p.name.endswith("adam.zip") for p in cuarentena.iterdir())


def test_reparar_no_toca_lo_que_ya_esta_bien(appmod, entorno):
    """Si la BIOS ya cumple el catálogo, no se toca nada."""
    contenido = b"ALF ROM"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script(_catalogo_zip(md5)), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"alf rev 57.u8": contenido})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is True
    assert resultado["motivo"] == "ya estaba en su sitio"
    assert not (entorno["bios"] / ".quarantine").exists()


def test_reparar_un_fichero_plano_lo_mueve(appmod, entorno):
    """Un fichero suelto con el md5 correcto se coloca en su ruta."""
    contenido = b"5200 rom"
    md5 = _md5(contenido)
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": md5, "file": "bios/5200.rom"}]}}), encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "Machines").mkdir()
    (entorno["bios"] / "Machines" / "5200.rom").write_bytes(contenido)
    resultado = appmod.repair_bios(entorno["settings"], "atari5200", "5200.rom")
    assert resultado["ok"] is True
    assert (entorno["bios"] / "5200.rom").read_bytes() == contenido


def test_reparar_sin_contenido_no_inventa(appmod, entorno):
    """Si el contenido no está en la consola, lo dice y no escribe nada."""
    entorno["script"].write_text(_script({
        "segaai": {"name": "Sega AI", "biosFiles": [
            {"md5": "", "file": "bios/segaai.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    resultado = appmod.repair_bios(entorno["settings"], "segaai", "segaai.zip")
    assert resultado["ok"] is False
    assert "no se ha encontrado" in resultado["error"]
    assert not (entorno["bios"] / "segaai.zip").exists()


def test_reparar_sin_contenido_no_toca_el_fichero_que_ya_estaba(appmod, entorno):
    """Si no hay contenido que poner, el fichero que estaba no se mueve.

    La cuarentena sólo se hace cuando ya se sabe que hay algo que escribir:
    si no, el destino se quedaría vacío y la BIOS se perdería de vista.
    """
    entorno["script"].write_text(_script({
        "segaai": {"name": "Sega AI", "biosFiles": [
            {"md5": "281f20ea4320404ec820fb7ec0693b38", "file": "bios/segaai.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    destino = entorno["bios"] / "segaai.zip"
    destino.write_bytes(b"lo que hay ahora")
    resultado = appmod.repair_bios(entorno["settings"], "segaai", "segaai.zip")
    # El fichero está en su sitio: el hash no lo convierte en un problema, así
    # que no se toca nada (y no hay cuarentena).
    assert resultado["ok"] is True
    assert destino.read_bytes() == b"lo que hay ahora"
    assert not (entorno["bios"] / ".quarantine").exists()


def test_reparar_un_zip_incompleto_sin_contenido_no_lo_pisa(appmod, entorno):
    """Un ZIP al que le falta un miembro y no hay nada que poner: no se toca."""
    entorno["script"].write_text(
        _script(_catalogo_zip("01bba3bcd46d8a586dd6ec555accc133")), encoding="utf-8")
    _reset(appmod)
    destino = entorno["bios"] / "adam.zip"
    _zip(destino, {"sin relacion": b"basura"})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is False
    assert "no se ha encontrado" in resultado["error"]
    # El ZIP sigue donde estaba, con su contenido intacto.
    with zipfile.ZipFile(destino) as z:
        assert z.namelist() == ["sin relacion"]
    assert not (entorno["bios"] / ".quarantine").exists()


def test_reparar_un_sistema_desconocido(appmod, entorno):
    """Un sistema que no está en el catálogo se rechaza."""
    resultado = appmod.repair_bios(entorno["settings"], "nada", "x.zip")
    assert resultado["ok"] is False
    assert "no se conoce el sistema" in resultado["error"]


def test_reparar_no_escribe_un_zip_incompleto(appmod, entorno):
    """Si no se puede reunir todo, no se escribe un ZIP a medias."""
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": "01bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 57.u8",
             "file": "bios/adam.zip"},
            {"md5": "02bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 58.u8",
             "file": "bios/adam.zip"},
        ]}}), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": b"ALF ROM"})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is False
    assert resultado["faltan"] == ["alf rev 58.u8"]
    # El destino no se crea: mejor no tener nada que tener un ZIP a medias.
    assert not (entorno["bios"] / "adam.zip").exists()


def test_reparar_reutiliza_lo_que_ya_hay_en_el_destino(appmod, entorno):
    """Lo que el destino ya tiene se cuenta: sólo falta el resto."""
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": "01bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 57.u8",
             "file": "bios/adam.zip"},
            {"md5": "02bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 58.u8",
             "file": "bios/adam.zip"},
        ]}}), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"alf rev 57.u8": b"ALF ROM"})
    _zip(entorno["bios"] / "otro.zip", {"alf rev 58.u8": b"ALF ROM 2"})
    resultado = appmod.repair_bios(entorno["settings"], "adam", "adam.zip")
    assert resultado["ok"] is True
    with zipfile.ZipFile(entorno["bios"] / "adam.zip") as z:
        assert sorted(z.namelist()) == ["alf rev 57.u8", "alf rev 58.u8"]


def test_un_zip_incompleto_no_es_reparable(appmod, entorno):
    """Si ningún otro ZIP tiene lo que falta, el estado es «falta un fichero»."""
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": "01bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 57.u8",
             "file": "bios/adam.zip"},
            {"md5": "02bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 58.u8",
             "file": "bios/adam.zip"},
        ]}}), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "adam.zip", {"alf rev 57.u8": b"ALF ROM"})
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": b"ALF ROM"})
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["adam"]["files"][0]
    assert fichero["estado"] == "miembro_falta"
    assert fichero["faltan"] == ["alf rev 58.u8"]


def test_ausente_si_otro_zip_solo_trae_parte(appmod, entorno):
    """Si ningún ZIP trae todo lo que hace falta, no es reparable."""
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": "01bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 57.u8",
             "file": "bios/adam.zip"},
            {"md5": "02bba3bcd46d8a586dd6ec555accc133", "zippedFile": "alf rev 58.u8",
             "file": "bios/adam.zip"},
        ]}}), encoding="utf-8")
    _reset(appmod)
    _zip(entorno["bios"] / "otro.zip", {"alf rev 57.u8": b"ALF ROM"})
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["adam"]["files"][0]
    assert fichero["estado"] == "ausente"


def test_reparar_no_sale_de_la_carpeta(appmod, entorno):
    """Una ruta con `..` no se puede colar."""
    entorno["script"].write_text(_script(_catalogo_zip("0" * 32)), encoding="utf-8")
    _reset(appmod)
    resultado = appmod.repair_bios(entorno["settings"], "adam", "../fuera.zip")
    assert resultado["ok"] is False


# ── La búsqueda de la BIOS que falta: GitHub y subida manual ──────────

def test_reparable_ruta_por_nombre(appmod, entorno):
    """El mismo nombre de fichero está en otra carpeta: se puede colocar."""
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": "281f20ea4320404ec820fb7ec0693b38", "file": "bios/5200.rom"}]}}),
        encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "Machines").mkdir()
    (entorno["bios"] / "Machines" / "5200.rom").write_bytes(b"otra version")
    data = appmod.scan_bios(entorno["settings"])
    fichero = data["systems"]["atari5200"]["files"][0]
    assert fichero["estado"] == "reparable_ruta"
    assert fichero["fuente"] == "Machines/5200.rom"


def test_reparar_por_nombre(appmod, entorno):
    """Se coloca el fichero de otra carpeta aunque el hash sea distinto."""
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": "281f20ea4320404ec820fb7ec0693b38", "file": "bios/5200.rom"}]}}),
        encoding="utf-8")
    _reset(appmod)
    (entorno["bios"] / "Machines").mkdir()
    (entorno["bios"] / "Machines" / "5200.rom").write_bytes(b"otra version")
    resultado = appmod.repair_bios(entorno["settings"], "atari5200", "5200.rom")
    assert resultado["ok"] is True
    assert (entorno["bios"] / "5200.rom").read_bytes() == b"otra version"


def test_el_catalogo_trae_el_enlace_de_github(appmod, entorno):
    """Cada BIOS y cada sistema llevan su enlace para buscarlos en GitHub."""
    entorno["script"].write_text(_script({
        "atari5200": {"name": "Atari 5200", "biosFiles": [
            {"md5": "", "file": "bios/5200.rom"}]}}), encoding="utf-8")
    _reset(appmod)
    data = appmod.scan_bios(entorno["settings"])
    sistema = data["systems"]["atari5200"]
    assert "github.com" in sistema["github"]
    assert "5200.rom" in sistema["files"][0]["github"]


def test_el_enlace_de_github_busca_el_nombre_exacto(appmod):
    """El enlace busca el nombre del fichero, entrecomillado."""
    url = appmod.github_bios_search_url("neogeo/neo-geo.7z")
    assert url.startswith("https://github.com/search?q=")
    assert "neo-geo.7z" in url
    assert "%22" in url


def test_no_hay_fuentes_de_archive(appmod):
    """Ya no se busca en archive.org: el flujo es GitHub y subida manual."""
    for nombre in ("bios_sources", "search_bios_sources", "install_bios_source",
                   "repair_bios_from_source"):
        assert not hasattr(appmod, nombre), nombre
