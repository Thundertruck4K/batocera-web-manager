# -*- coding: utf-8 -*-
"""El rom-converto: las conversiones a RVZ y a WBFS.

El rom-converto (DevYukine/rom-converto, MIT) es un binario externo. Aqui no
se llama de verdad: se sustituye por un ``subprocess.run`` falso que anota la
linea de ordenes, que es lo que hay que comprobar (que a cada formato de
origen le toca su familia de comandos: ``dol`` es GameCube y ``rvl`` es Wii).

Los ficheros de prueba son minimos y sinteticos: no hace falta ningun juego
de verdad ni ninguna utilidad en la consola.
"""

import subprocess
import types

import pytest

from romtools import formats


# ── Los ficheros de prueba ──────────────────────────────────────────────

def _iso_gamecube() -> bytes:
    """Una ISO minima con la magia de GameCube y la de ISO 9660."""
    datos = bytearray(0x8100)
    datos[0x1C:0x20] = b"\xc2\x33\x9f\x3d"
    datos[0x8001:0x8006] = b"CD001"
    return bytes(datos)


def _iso_wii() -> bytes:
    """Una ISO minima con la magia de Wii y la de ISO 9660."""
    datos = bytearray(0x8100)
    datos[0x18:0x1C] = b"\x5d\x1c\x9e\xa3"
    datos[0x8001:0x8006] = b"CD001"
    return bytes(datos)


def _iso_plana() -> bytes:
    """Una ISO 9660 que no es de ninguna consola."""
    datos = bytearray(0x8100)
    datos[0x8001:0x8006] = b"CD001"
    return bytes(datos)


def _gcm() -> bytes:
    """El volcado original de GameCube."""
    return b"\x00" * 512


def _gcz() -> bytes:
    """El GCZ: un gzip con cuatro bytes delante."""
    return b"\x01\xc0\x0b\xb1" + b"\x00" * 508


def _wbfs() -> bytes:
    """Un WBFS de Wii."""
    return b"WBFS" + b"\x00" * 508


def _wia() -> bytes:
    """Un WIA de Wii."""
    return b"WIA\x00" + b"\x00" * 508


def _rvz() -> bytes:
    """Un RVZ de verdad: empieza por «RVZ\\x01»."""
    return b"RVZ\x01" + b"\x00" * 508


# ── El falso subproceso ─────────────────────────────────────────────────

class _FalsoRomConverto:
    """Un ``subprocess.run`` falso: anota las llamadas y finge que convierte.

    Sustituye al modulo ``subprocess`` entero dentro de ``formats``, asi que
    el codigo de verdad (la localizacion del binario y la llamada) se ejecuta
    igual.
    """

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, consola="gamecube", returncode=0, stderr=""):
        self.llamadas = []
        self.comandos = []
        self.consola = consola
        self.returncode = returncode
        self.stderr = stderr

    def run(self, args, **kwargs):
        self.llamadas.append((list(args), kwargs))
        # La llamada es: binario, --no-update-check, familia, operacion...
        familia = args[2] if len(args) > 2 else ""
        operacion = ""
        if len(args) > 3 and args[3] in ("compress", "migrate", "decompress"):
            operacion = args[3]
        self.comandos.append((familia, operacion))
        if self.returncode != 0:
            return types.SimpleNamespace(returncode=self.returncode, stdout="",
                                         stderr=self.stderr)
        if familia == "info":
            texto = ("Format: GameCube (RVZ)" if self.consola == "gamecube"
                     else "Format: Wii (RVZ)")
            return types.SimpleNamespace(returncode=0, stdout=texto, stderr="")
        if operacion in ("compress", "migrate", "decompress"):
            salida = args[args.index("-o") + 1]
            with open(salida, "wb") as fh:
                fh.write(b"contenido")
        return types.SimpleNamespace(returncode=0, stdout="hecho", stderr="")


def _con_rom_converto(monkeypatch, consola="gamecube", returncode=0, stderr=""):
    """Deja el motor creyendo que hay un rom-converto y devuelve el falso."""
    monkeypatch.setattr(formats.shutil, "which",
                        lambda binario: "/usr/bin/rom-converto"
                        if binario == "rom-converto" else None)
    falso = _FalsoRomConverto(consola, returncode, stderr)
    monkeypatch.setattr(formats, "subprocess", falso)
    return falso


def _operacion(falso, indice=0):
    """La familia y la operacion de una llamada (``dol compress``…)."""
    return falso.comandos[indice]


# ── La deteccion ────────────────────────────────────────────────────────

def test_un_rvz_de_verdad_se_detecta(tmp_path):
    """Un RVZ de verdad empieza por «RVZ\\x01», no por «RVZ\\x00»."""
    ruta = tmp_path / "juego.rvz"
    ruta.write_bytes(_rvz())
    assert formats.detect_format(str(ruta)).kind == "rvz"


def test_el_rvz_sigue_por_la_marca(tmp_path):
    """Da igual la version: lo que se busca es la marca."""
    ruta = tmp_path / "juego.rvz"
    ruta.write_bytes(b"RVZ\x02" + b"\x00" * 200)
    assert formats.detect_format(str(ruta)).kind == "rvz"


# ── Sin la utilidad ─────────────────────────────────────────────────────

def test_sin_el_rom_converto_no_se_puede_convertir(tmp_path, monkeypatch):
    """Sin la utilidad se explica el problema, no se finge que ha salido."""
    monkeypatch.setattr(formats.shutil, "which", lambda binario: None)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_gamecube())
    with pytest.raises(ValueError) as error:
        formats.convert(str(origen), "rvz", sistema="gamecube")
    assert "rom-converto" in str(error.value)


def test_el_rom_converto_disponible_depende_del_binario(monkeypatch):
    monkeypatch.setattr(formats.shutil, "which", lambda binario: None)
    assert formats.rom_converto_disponible() is False
    monkeypatch.setattr(formats.shutil, "which",
                        lambda binario: "/usr/bin/rom-converto"
                        if binario == "rom-converto" else None)
    assert formats.rom_converto_disponible() is True


# ── A RVZ ────────────────────────────────────────────────────────────────

def test_la_iso_de_gamecube_se_convierte_en_rvz(tmp_path, monkeypatch):
    """GameCube va con la familia ``dol``."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_gamecube())
    salida = tmp_path / "juego.rvz"

    resultado = formats.convert(str(origen), "rvz", str(salida),
                                sistema="gamecube")

    assert resultado["ok"] is True
    assert resultado["out"] == str(salida)
    assert salida.exists()
    assert _operacion(falso) == ("dol", "compress")


def test_el_gcm_se_convierte_en_rvz(tmp_path, monkeypatch):
    """El GCM es el volcado original de GameCube: tambien con ``dol``."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.gcm"
    origen.write_bytes(_gcm())
    salida = tmp_path / "juego.rvz"

    formats.convert(str(origen), "rvz", str(salida), sistema="gamecube")

    assert _operacion(falso) == ("dol", "compress")


def test_el_gcz_se_migra_en_rvz(tmp_path, monkeypatch):
    """El GCZ es un formato viejo: se migra, no se comprime."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.gcz"
    origen.write_bytes(_gcz())
    salida = tmp_path / "juego.rvz"

    formats.convert(str(origen), "rvz", str(salida), sistema="gamecube")

    assert _operacion(falso) == ("dol", "migrate")


def test_la_iso_de_wii_se_convierte_en_rvz(tmp_path, monkeypatch):
    """Wii va con la familia ``rvl``."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_wii())
    salida = tmp_path / "juego.rvz"

    formats.convert(str(origen), "rvz", str(salida), sistema="wii")

    assert _operacion(falso) == ("rvl", "compress")


def test_el_wbfs_se_convierte_en_rvz(tmp_path, monkeypatch):
    """El WBFS de Wii se comprime con ``rvl compress``."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.wbfs"
    origen.write_bytes(_wbfs())
    salida = tmp_path / "juego.rvz"

    formats.convert(str(origen), "rvz", str(salida), sistema="wii")

    assert _operacion(falso) == ("rvl", "compress")


def test_el_wia_se_migra_en_rvz(tmp_path, monkeypatch):
    """El WIA es el formato viejo de Wii: se migra."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.wia"
    origen.write_bytes(_wia())
    salida = tmp_path / "juego.rvz"

    formats.convert(str(origen), "rvz", str(salida), sistema="wii")

    assert _operacion(falso) == ("rvl", "migrate")


def test_la_conversion_no_busca_actualizaciones(tmp_path, monkeypatch):
    """Cada conversion no tiene que irse a la red a preguntar por la version."""
    falso = _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_gamecube())

    formats.convert(str(origen), "rvz", str(tmp_path / "juego.rvz"),
                    sistema="gamecube")

    argumentos, _opciones = falso.llamadas[0]
    assert "--no-update-check" in argumentos


def test_dos_conversiones_no_se_pisan(tmp_path, monkeypatch):
    """Dos conversiones del mismo fichero no se pisan entre si."""
    _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_gamecube())

    primera = formats.convert(str(origen), "rvz", sistema="gamecube")
    segunda = formats.convert(str(origen), "rvz", sistema="gamecube")

    assert primera["out"] != segunda["out"]
    assert origen.exists()


def test_una_iso_sin_consola_no_se_convierte(tmp_path, monkeypatch):
    """Sin saber de que consola es, no se puede decidir: se dice."""
    _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_plana())

    with pytest.raises(ValueError) as error:
        formats.convert(str(origen), "rvz")

    assert "GameCube" in str(error.value)


def test_un_error_del_rom_converto_se_cuenta(tmp_path, monkeypatch):
    """Si lautility falla, se cuenta lo que dijo y no se finge nada."""
    _con_rom_converto(monkeypatch, returncode=1, stderr="no se puede comprimir")
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_gamecube())

    with pytest.raises(ValueError) as error:
        formats.convert(str(origen), "rvz", str(tmp_path / "juego.rvz"),
                        sistema="gamecube")

    assert "no se puede comprimir" in str(error.value)


# ── A WBFS y a ISO ──────────────────────────────────────────────────────

def test_el_wbfs_sale_de_un_rvz_de_wii(tmp_path, monkeypatch):
    """El WBFS se saca de un RVZ de Wii con ``rvl decompress``."""
    falso = _con_rom_converto(monkeypatch, consola="wii")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())
    salida = tmp_path / "juego.wbfs"

    resultado = formats.convert(str(origen), "wbfs", str(salida), sistema="wii")

    assert resultado["ok"] is True
    assert salida.exists()
    assert _operacion(falso) == ("rvl", "decompress")


def test_un_rvz_de_gamecube_no_se_pasa_a_wbfs(tmp_path, monkeypatch):
    """El WBFS es de Wii: un RVZ de GameCube no se puede convertir en eso."""
    _con_rom_converto(monkeypatch, consola="gamecube")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())

    with pytest.raises(ValueError) as error:
        formats.convert(str(origen), "wbfs", str(tmp_path / "juego.wbfs"))

    assert "Wii" in str(error.value)


def test_el_wbfs_no_se_crea_desde_una_iso(tmp_path, monkeypatch):
    """El rom-converto no crea WBFS desde una ISO: no se ofrece."""
    _con_rom_converto(monkeypatch)
    origen = tmp_path / "juego.iso"
    origen.write_bytes(_iso_wii())

    with pytest.raises(ValueError) as error:
        formats.convert(str(origen), "wbfs", sistema="wii")

    assert "RVZ" in str(error.value)


def test_el_rvz_se_descomprime_en_iso(tmp_path, monkeypatch):
    """Un RVZ de GameCube se descomprime con ``dol decompress``."""
    falso = _con_rom_converto(monkeypatch, consola="gamecube")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())
    salida = tmp_path / "juego.iso"

    resultado = formats.convert(str(origen), "iso", str(salida),
                                sistema="gamecube")

    assert resultado["ok"] is True
    assert salida.exists()
    assert _operacion(falso) == ("dol", "decompress")


def test_el_rvz_de_wii_se_descomprime_con_rvl(tmp_path, monkeypatch):
    """Un RVZ de Wii se descomprime con ``rvl decompress``."""
    falso = _con_rom_converto(monkeypatch, consola="wii")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())

    formats.convert(str(origen), "iso", str(tmp_path / "juego.iso"),
                    sistema="wii")

    assert _operacion(falso) == ("rvl", "decompress")


def test_la_consola_del_rvz_se_sabe_por_el_sistema(tmp_path, monkeypatch):
    """Si el sistema ya dice de que consola es, no hace falta preguntarlo."""
    falso = _con_rom_converto(monkeypatch, consola="wii")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())

    formats.convert(str(origen), "iso", str(tmp_path / "juego.iso"),
                    sistema="gamecube")

    # Solo hay una llamada: la de descomprimir.
    assert len(falso.llamadas) == 1
    assert _operacion(falso) == ("dol", "decompress")


def test_sin_el_sistema_se_pregunta_al_rom_converto(tmp_path, monkeypatch):
    """Si no se sabe de que consola es, lo dice el propio rom-converto."""
    falso = _con_rom_converto(monkeypatch, consola="wii")
    origen = tmp_path / "juego.rvz"
    origen.write_bytes(_rvz())

    formats.convert(str(origen), "iso", str(tmp_path / "juego.iso"))

    assert _operacion(falso, 0) == ("info", "")
    assert _operacion(falso, 1) == ("rvl", "decompress")


# ── El catalogo ──────────────────────────────────────────────────────────

def test_el_catalogo_ofrece_el_rvz_para_gamecube_y_wii():
    assert "rvz" in formats.FORMAT_CATALOGUE["iso-gamecube"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["iso-wii"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["gcm"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["gcz"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["wbfs"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["wia"][1]


def test_el_catalogo_no_ofrece_wbfs_desde_una_iso():
    """El rom-converto no lo crea desde una ISO: no se ofrece."""
    assert "wbfs" not in formats.FORMAT_CATALOGUE["iso-gamecube"][1]
    assert "wbfs" not in formats.FORMAT_CATALOGUE["iso-wii"][1]
    assert "wbfs" in formats.FORMAT_CATALOGUE["rvz"][1]


def test_el_rvz_es_convertible_a_iso():
    assert "rvz" in formats.CONVERTIBLE_TO_ISO
