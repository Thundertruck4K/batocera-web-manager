"""Tests de las fuentes de BIOS en archive.org.

El emparejamiento con archive.org es siempre POR CONTENIDO: el md5 que exige el
catálogo de Batocera tiene que aparecer en el fichero de la fuente o dentro de
uno de sus ZIP. El nombre sólo sirve para ordenar la búsqueda.

Los tests no tocan la red: se simulan las peticiones a archive.org (metadatos
y rangos HTTP) con monkeypatch.
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import zipfile

import pytest


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _zip_bytes(members: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def _script(catalogo: dict) -> str:
    return "#!/usr/bin/env python\nBIOS_FILES = " + json.dumps(catalogo, indent=2) + "\n"


def _reset(appmod):
    appmod._bios_catalog_cache["ts"] = 0.0
    appmod._bios_catalog_cache["data"] = None
    appmod._bios_index_cache.clear()
    appmod._bios_zip_cache.clear()
    appmod._bios_zipidx_cache.clear()
    appmod._bios_sources_cache["ts"] = 0.0
    appmod._bios_sources_cache["data"] = None
    appmod._bios_container_cache.clear()
    appmod._bios_payload_cache.clear()


@pytest.fixture
def entorno(appmod, tmp_path, monkeypatch):
    """Catálogo falso, carpeta de BIOS temporal y fuentes aisladas."""
    script = tmp_path / "batocera-systems"
    script.write_text(_script({}), encoding="utf-8")
    monkeypatch.setattr(appmod, "BIOS_CATALOG_SCRIPT", script)
    monkeypatch.setattr(appmod, "BIOS_CATALOG_ALT", tmp_path / "no-hay-alternativa")
    monkeypatch.setattr(appmod, "BIOS_README_FILE", tmp_path / "no-hay-readme.txt")
    monkeypatch.setattr(appmod, "_missing_bios_skipped", set())
    # La caché de fuentes va a un fichero propio de cada test: si no, una
    # fuente indexada en un test se colaría en el siguiente.
    monkeypatch.setattr(appmod, "_bios_sources_file",
                        lambda: tmp_path / "fuentes.json")
    monkeypatch.setattr(appmod, "_bios_containers_file",
                        lambda: tmp_path / "contenedores.json")
    bios = tmp_path / "bios"
    bios.mkdir()
    _reset(appmod)
    yield {"bios": bios, "script": script, "tmp": tmp_path, "monkeypatch": monkeypatch,
           "settings": {"bios_dir": str(bios), "roms_base": str(tmp_path / "roms")}}
    _reset(appmod)


class RedFalsa:
    """Simula archive.org: metadatos de items y ficheros con rango."""

    def __init__(self, items: dict):
        # {identificador: {"meta": {...}, "files": {nombre: bytes}}}
        self.items = items
        self.peticiones = []

    # -- utilidades para el monkeypatch -------------------------------
    def _item(self, item_id):
        return self.items.get(item_id) or {}

    def get(self, url, timeout=45, limit=None):
        self.peticiones.append(("GET", url))
        if "/metadata/" in url:
            ident = url.split("/metadata/", 1)[1]
            item = self._item(ident)
            files = [{"name": n, "md5": _md5(d), "size": len(d), "source": "original"}
                     for n, d in (item.get("files") or {}).items()]
            return json.dumps({"metadata": item.get("meta") or {},
                               "files": files}).encode()
        ident, nombre = url.split("/download/", 1)[1].split("/", 1)
        nombre = urllib_unquote(nombre)
        data = (self._item(ident).get("files") or {}).get(nombre)
        if data is None:
            raise FileNotFoundError(url)
        if limit is not None and len(data) > limit:
            raise RuntimeError("el fichero es demasiado grande")
        return data

    def head(self, url, timeout=45):
        self.peticiones.append(("HEAD", url))
        ident, nombre = url.split("/download/", 1)[1].split("/", 1)
        nombre = urllib_unquote(nombre)
        data = (self._item(ident).get("files") or {}).get(nombre)
        if data is None:
            raise FileNotFoundError(url)
        return len(data), "bytes"

    def rango(self, url, start, length, timeout=45):
        self.peticiones.append(("RANGE", url))
        ident, nombre = url.split("/download/", 1)[1].split("/", 1)
        nombre = urllib_unquote(nombre)
        data = (self._item(ident).get("files") or {}).get(nombre)
        if data is None:
            raise FileNotFoundError(url)
        return data[start:start + length]


def urllib_unquote(text: str) -> str:
    from urllib.parse import unquote
    return unquote(text)


def _conectar(appmod, red: RedFalsa):
    """Engancha la red falsa a las funciones de archive.org."""
    appmod._ia_get = lambda url, timeout=45, limit=None: red.get(url, timeout, limit)
    appmod._ia_head = lambda url, timeout=45: red.head(url, timeout)
    appmod._ia_range = lambda url, start, length, timeout=45: red.rango(url, start, length)


# ── El catálogo de fuentes ──────────────────────────────────────────────

def test_las_fuentes_por_defecto_estan_indexadas(appmod, entorno):
    """Cada fuente por defecto aparece con su licencia y su autor."""
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity BIOS Collection", "creator": "Emularity Team",
                 "license": "CC-BY-SA-3.0"},
        "files": {"a5200.zip": b"x"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files", "title": "Emularity"}])
    try:
        data = appmod.bios_sources(force=True)
    finally:
        pass
    assert data["sources"][0]["id"] == "emularity_bios_v1"
    assert data["sources"][0]["license"] == "CC-BY-SA-3.0"
    assert data["sources"][0]["creator"] == "Emularity Team"
    assert data["sources"][0]["files"] == 1


def test_el_indice_se_guarda_en_disco(appmod, entorno):
    """El catálogo de fuentes se cachea 7 días en el fichero de ajustes."""
    red = RedFalsa({"emularity_bios_v1": {"meta": {}, "files": {"a5200.zip": b"x"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        appmod.bios_sources(force=True)
    finally:
        pass
    cache = appmod._bios_sources_file()
    assert cache.exists()
    datos = json.loads(cache.read_text(encoding="utf-8"))
    assert "emularity_bios_v1" in datos["items"]


# ── La búsqueda ─────────────────────────────────────────────────────────

def test_busca_por_md5_publicado(appmod, entorno):
    """Si archive.org publica el md5 del fichero, es un candidato directo."""
    contenido = b"la-bios-que-busca-batocera"
    digest = _md5(contenido)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity"}, "files": {"adam.zip": contenido}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        encontrado = appmod.search_bios_sources(
            entorno["settings"], "adam", "adam.zip")
    finally:
        pass
    assert encontrado["ok"] is True
    directos = [c for c in encontrado["candidates"] if c["match"] == "md5"]
    assert len(directos) == 1
    cand = directos[0]
    assert cand["kind"] == "fichero"
    assert cand["md5"] == digest
    assert cand["match"] == "md5"


def test_busca_dentro_de_un_zip_por_md5(appmod, entorno):
    """Un ZIP sirve si lleva dentro el fichero que pide el catálogo."""
    interior = b"el-rom-de-adam"
    digest = _md5(interior)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": digest, "zippedFile": "alf rev 57.u8", "file": "bios/adam.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    zip_bueno = _zip_bytes({"alf rev 57.u8": interior})
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity"}, "files": {"adam.zip": zip_bueno}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        encontrado = appmod.search_bios_sources(
            entorno["settings"], "adam", "adam.zip")
    finally:
        pass
    assert encontrado["ok"] is True
    assert encontrado["candidates"], "debería encontrar el ZIP con el miembro"
    cand = encontrado["candidates"][0]
    assert cand["kind"] == "miembro"
    assert cand["member"] == "alf rev 57.u8"
    assert cand["md5"] == digest


def test_no_hay_fuente_dice_que_no_la_hay(appmod, entorno):
    """Si no hay ninguna fuente, se dice con claridad (no se falla en silencio)."""
    digest = _md5(b"nadie lo tiene")
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {"meta": {}, "files": {"otro.zip": b"nada"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        encontrado = appmod.search_bios_sources(
            entorno["settings"], "adam", "adam.zip")
    finally:
        pass
    assert encontrado["ok"] is True
    assert encontrado["candidates"] == []
    assert "no hay ninguna fuente" in encontrado["motivo"]


def test_un_zip_con_el_mismo_nombre_pero_distinto_no_sirve(appmod, entorno):
    """El nombre no vale: si el contenido no es el del catálogo, no es candidato."""
    interior = b"otra-cosa-distinta"
    digest = _md5(b"el-rom-de-adam")
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": digest, "zippedFile": "alf rev 57.u8", "file": "bios/adam.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    zip_malo = _zip_bytes({"alf rev 57.u8": interior})
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {}, "files": {"adam.zip": zip_malo}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        encontrado = appmod.search_bios_sources(
            entorno["settings"], "adam", "adam.zip")
    finally:
        pass
    verificados = [c for c in encontrado["candidates"] if c["match"] == "miembro"]
    assert verificados == [], "un ZIP con otro contenido no puede ser candidato"


# ── Los contenedores candidatos ─────────────────────────────────────────

def _miembro(nombre, size=100):
    return {"name": nombre, "size": size, "csize": size, "crc": 0,
            "method": 0, "offset": 0}


def test_un_contenedor_que_no_se_puede_leer_no_se_cachea(appmod, entorno):
    """Si un ZIP falla al abrirse, el vacío no se cachea: envenenaría la caché.

    Un contenedor ilegible significa «no he podido mirarlo», no «no hay nada
    dentro». Si se cacheara el vacío, esa BIOS se quedaría sin fuente para
    siempre.
    """
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {}, "files": {"adam.zip": b"esto no es un zip"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    miembros = appmod._bios_container_members("emularity_bios_v1", "adam.zip")
    assert miembros == {}
    cache = appmod._bios_containers_file()
    if cache.exists():
        assert "emularity_bios_v1|adam.zip" not in cache.read_text(encoding="utf-8")


def test_un_contenedor_leido_se_cachea(appmod, entorno):
    """Un contenedor que sí se abre se cachea (no se vuelve a bajar)."""
    zip_bueno = _zip_bytes({"alf rev 57.u8": b"contenido"})
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {}, "files": {"adam.zip": zip_bueno}}})
    _conectar(appmod, red)
    miembros = appmod._bios_container_members("emularity_bios_v1", "adam.zip")
    assert miembros == {"alf rev 57.u8": _md5(b"contenido")}
    assert "emularity_bios_v1|adam.zip" in \
        appmod._bios_containers_file().read_text(encoding="utf-8")


def test_la_busqueda_no_se_eterniza(appmod, entorno):
    """Si se pasa el plazo, la búsqueda se corta: archive.org puede ir lento."""
    contenido = b"la-bios-que-busca-batocera"
    digest = _md5(contenido)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    zip_bueno = _zip_bytes({"alf rev 57.u8": b"contenido"})
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {}, "files": {"adam.zip": zip_bueno}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    monkey.setattr(appmod, "BIOS_SOURCE_DEADLINE", -1)
    encontrado = appmod.search_bios_sources(
        entorno["settings"], "adam", "adam.zip")
    assert encontrado["ok"] is True
    assert encontrados_por_miembro(encontrado) == []


def encontrados_por_miembro(encontrado):
    """Candidatos verificados contra el md5 del catálogo."""
    return [c for c in encontrado.get("candidates") or []
            if c.get("match") in ("md5", "miembro")]


def test_el_contenedor_se_busca_por_la_carpeta_de_la_ruta(appmod, entorno):
    """`enterprise/ep128emu/roms/exos20.rom` se busca dentro de `ep128.zip`."""
    miembros = [_miembro("MESS ROMs/ep128.zip"), _miembro("MESS ROMs/otro.zip")]
    cands = appmod._bios_container_candidates(
        miembros, "ep128emu/roms/exos20.rom", "enterprise")
    assert [c["name"] for c in cands] == ["MESS ROMs/ep128.zip"]


def test_el_contenedor_se_busca_por_el_sistema(appmod, entorno):
    """El sistema manda: `bbc` busca dentro de `bbc.zip`."""
    miembros = [_miembro("otro.zip"), _miembro("bbc.zip")]
    cands = appmod._bios_container_candidates(
        miembros, "Acorn/basic2.rom", "bbc")
    assert cands[0]["name"] == "bbc.zip"


def test_sin_contenedores_no_hay_nada_que_abrir(appmod, entorno):
    """Un fichero que no parece un ZIP no se propone como contenedor."""
    miembros = [_miembro("basic2.rom"), _miembro("carpeta/")]
    cands = appmod._bios_container_candidates(
        miembros, "Acorn/basic2.rom", "bbc")
    assert cands == []


# ── La instalación ──────────────────────────────────────────────────────

def test_instala_un_fichero_de_una_fuente(appmod, entorno):
    """El fichero se descarga, se verifica por md5 y se coloca en su sitio."""
    contenido = b"la-bios-que-busca-batocera"
    digest = _md5(contenido)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity BIOS Collection", "creator": "Emularity Team"},
        "files": {"adam.zip": contenido}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        resultado = appmod.install_bios_source(
            entorno["settings"], "adam", "adam.zip",
            {"item": "emularity_bios_v1", "name": "adam.zip"})
    finally:
        pass
    assert resultado["ok"] is True
    assert resultado["estado"] == "ok"
    assert (entorno["bios"] / "adam.zip").read_bytes() == contenido
    assert resultado["fuente"] == "Emularity BIOS Collection"


def test_no_instala_un_contenido_que_no_cuadra(appmod, entorno):
    """Si el md5 no es el del catálogo, no se escribe nada."""
    digest = _md5(b"la-bios-que-busca-batocera")
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {}, "files": {"adam.zip": b"contenido-que-no-es"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        resultado = appmod.install_bios_source(
            entorno["settings"], "adam", "adam.zip",
            {"item": "emularity_bios_v1", "name": "adam.zip"})
    finally:
        pass
    assert resultado["ok"] is False
    assert not (entorno["bios"] / "adam.zip").exists()


def test_repara_un_zip_desde_una_fuente(appmod, entorno):
    """Un ZIP de la fuente se rehace con los ficheros que exige el catálogo."""
    interior = b"el-rom-de-adam"
    digest = _md5(interior)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": digest, "zippedFile": "alf rev 57.u8", "file": "bios/adam.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    zip_bueno = _zip_bytes({"alf rev 57.u8": interior})
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity"}, "files": {"adam.zip": zip_bueno}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        resultado = appmod.install_bios_source(
            entorno["settings"], "adam", "adam.zip",
            {"item": "emularity_bios_v1", "name": "adam.zip"})
    finally:
        pass
    assert resultado["ok"] is True
    destino = entorno["bios"] / "adam.zip"
    with zipfile.ZipFile(destino) as z:
        assert z.namelist() == ["alf rev 57.u8"]
        assert z.read("alf rev 57.u8") == interior


def test_una_fuente_que_no_esta_en_el_catalogo_se_rechaza(appmod, entorno):
    """No se acepta ninguna fuente que no esté en el catálogo (ni URLs sueltas)."""
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": _md5(b"x"), "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({})
    _conectar(appmod, red)
    resultado = appmod.install_bios_source(
        entorno["settings"], "adam", "adam.zip",
        {"item": "inventado", "name": "adam.zip"})
    assert resultado["ok"] is False
    assert "catálogo" in resultado["error"]


def test_el_boton_reparar_busca_en_la_consola_primero(appmod, entorno):
    """«Reparar» usa el contenido de la consola antes de bajar nada."""
    digest = _md5(b"la-bios-que-busca-batocera")
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    # El mismo contenido está en otra ruta de la consola.
    (entorno["bios"] / "otro").mkdir()
    (entorno["bios"] / "otro" / "adam.zip").write_bytes(b"la-bios-que-busca-batocera")
    red = RedFalsa({})
    _conectar(appmod, red)
    resultado = appmod.repair_bios_from_source(
        entorno["settings"], "adam", "adam.zip", "archive")
    assert resultado["ok"] is True
    assert (entorno["bios"] / "adam.zip").exists()
    # No ha hecho falta ninguna petición a archive.org
    assert red.peticiones == []


def test_el_boton_reparar_cae_en_archive_org(appmod, entorno):
    """Si en la consola no está, «Reparar» busca en archive.org."""
    contenido = b"la-bios-que-busca-batocera"
    digest = _md5(contenido)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {
        "meta": {"title": "Emularity"}, "files": {"adam.zip": contenido}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        resultado = appmod.repair_bios_from_source(
            entorno["settings"], "adam", "adam.zip", "archive")
    finally:
        pass
    assert resultado["ok"] is True
    assert (entorno["bios"] / "adam.zip").read_bytes() == contenido


def test_el_boton_reparar_explica_cuando_no_hay_fuente(appmod, entorno):
    """Si no hay ninguna fuente, el error lo dice claro."""
    digest = _md5(b"nadie-lo-tiene")
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": digest, "file": "bios/adam.zip"}]}}), encoding="utf-8")
    _reset(appmod)
    red = RedFalsa({"emularity_bios_v1": {"meta": {}, "files": {"otro.zip": b"nada"}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "emularity_bios_v1", "kind": "files"}])
    try:
        resultado = appmod.repair_bios_from_source(
            entorno["settings"], "adam", "adam.zip", "archive")
    finally:
        pass
    assert resultado["ok"] is False
    assert "no hay ninguna fuente" in resultado["error"]
    assert not (entorno["bios"] / "adam.zip").exists()


# ── El ZIP remoto ───────────────────────────────────────────────────────

def test_lee_el_indice_central_de_un_zip_remoto(appmod, entorno):
    """El índice central se lee por rangos, sin bajar el ZIP entero."""
    zip_datos = _zip_bytes({"uno.rom": b"a" * 100, "dos.rom": b"b" * 200})
    red = RedFalsa({"pack": {"meta": {}, "files": {"bios.zip": zip_datos}}})
    _conectar(appmod, red)
    entradas = appmod._remote_zip_index(
        "https://archive.org/download/pack/bios.zip")
    nombres = [e["name"] for e in entradas]
    assert nombres == ["uno.rom", "dos.rom"]
    # Sólo se ha pedido el final del fichero y el directorio central
    for _tipo, url in red.peticiones:
        assert url.endswith("bios.zip")


def test_extrae_un_miembro_de_un_zip_remoto(appmod, entorno):
    """De un ZIP remoto se extrae sólo el miembro pedido."""
    zip_datos = _zip_bytes({"uno.rom": b"contenido-uno", "dos.rom": b"contenido-dos"})
    red = RedFalsa({"pack": {"meta": {}, "files": {"bios.zip": zip_datos}}})
    _conectar(appmod, red)
    entradas = appmod._remote_zip_index(
        "https://archive.org/download/pack/bios.zip")
    url = "https://archive.org/download/pack/bios.zip"
    datos = appmod._remote_zip_member(url, entradas[1])
    assert datos == b"contenido-dos"


def test_el_zip_remoto_aporta_el_miembro_buscado(appmod, entorno):
    """Una BIOS puede estar dentro del ZIP grande de un item."""
    interior = b"el-rom-de-adam"
    digest = _md5(interior)
    entorno["script"].write_text(_script({
        "adam": {"name": "Coleco Adam", "biosFiles": [
            {"md5": "", "file": "bios/adam.zip"},
            {"md5": digest, "zippedFile": "alf rev 57.u8", "file": "bios/adam.zip"}]}}),
        encoding="utf-8")
    _reset(appmod)
    zip_interno = _zip_bytes({"alf rev 57.u8": interior})
    zip_grande = _zip_bytes({"MESS ROMs/adam.zip": zip_interno})
    red = RedFalsa({"pack": {"meta": {"title": "Pack"},
                             "files": {"bios.zip": zip_grande}}})
    _conectar(appmod, red)
    monkey = entorno["monkeypatch"]
    monkey.setattr(appmod, "BIOS_SOURCES_DEFAULT", [
        {"id": "pack", "kind": "zip", "file": "bios.zip"}])
    try:
        encontrado = appmod.search_bios_sources(
            entorno["settings"], "adam", "adam.zip")
        assert encontrado["candidates"], "debería encontrar el ZIP del item"
        cand = encontrado["candidates"][0]
        assert cand["kind"] == "miembro"
        resultado = appmod.install_bios_source(
            entorno["settings"], "adam", "adam.zip", cand)
    finally:
        pass
    assert resultado["ok"] is True
    with zipfile.ZipFile(entorno["bios"] / "adam.zip") as z:
        assert z.read("alf rev 57.u8") == interior


def test_zip_sin_rangos_no_se_puede_leer(appmod, entorno):
    """Si el servidor no admite rangos, se dice y no se rompe nada."""
    class SinRangos(RedFalsa):
        def head(self, url, timeout=45):
            size, _ = super().head(url, timeout)
            return size, "none"

    red = SinRangos({"pack": {"meta": {}, "files": {"bios.zip": b"x" * 100}}})
    _conectar(appmod, red)
    with pytest.raises(Exception):
        appmod._remote_zip_index("https://archive.org/download/pack/bios.zip")
