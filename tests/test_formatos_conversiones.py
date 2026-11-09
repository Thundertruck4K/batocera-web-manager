# -*- coding: utf-8 -*-
"""Las conversiones nuevas del motor de formatos: 7Z, GDI, MDS, CCD y NRG.

Todo se prueba con ficheros sinteticos minimos, hechos aqui mismo: no hace
falta ningun juego de verdad ni ninguna utilidad de la consola (el 7Z se
simula con un ``subprocess.run`` falso).
"""
import struct
import subprocess
import types

import pytest

from romtools import formats


# ── Ayudas para montar los ficheros de prueba ───────────────────────────

def _sector_modo1(datos):
    """Un sector CD de 2352 bytes (MODE1) con sus datos de usuario."""
    sector = bytearray(2352)
    sector[15] = 0x01
    sector[16:16 + len(datos)] = datos
    return bytes(sector)


class _FalsoSubprocess:
    """Un ``subprocess.run`` falso: anota las llamadas y finge que comprime.

    Sustituye al modulo ``subprocess`` entero dentro de ``formats``, asi que
    el codigo de verdad (la localizacion del 7z y la llamada) se ejecuta igual.
    """

    TimeoutExpired = subprocess.TimeoutExpired

    def __init__(self, listado=""):
        self.llamadas = []
        self.listado = listado

    def run(self, args, **kwargs):
        self.llamadas.append((list(args), kwargs))
        comando = args[1] if len(args) > 1 else ""
        if comando == "a":
            # El 7z crea el fichero comprimido.
            with open(args[4], "wb") as fh:
                fh.write(b"7z\x31\x41\x26\x00")
        elif comando == "x":
            carpeta = args[3][2:]          # el "-o" va pegado a la carpeta
            with open(carpeta + "/dentro.txt", "w", encoding="utf-8") as fh:
                fh.write("hola")
        elif comando == "l":
            return types.SimpleNamespace(returncode=0, stdout=self.listado,
                                         stderr="")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")


def _con_7z(monkeypatch, listado=""):
    """Deja el motor creyendo que hay un 7z y devuelve el falso subproceso."""
    monkeypatch.setattr(formats.shutil, "which",
                        lambda binario: "/usr/bin/7z" if binario == "7z" else None)
    falso = _FalsoSubprocess(listado)
    monkeypatch.setattr(formats, "subprocess", falso)
    return falso


# ── La compresion en 7Z ──────────────────────────────────────────────────

def test_la_capacidad_de_7z_esta_anotada():
    """El 7Z tiene que estar en las capacidades o no se puede ofrecer."""
    assert formats.CAPACIDADES["7z"] == {
        "label": "7Z",
        "ayuda": "comprimido en 7Z (squeeza mas que el ZIP)",
    }


def test_el_7z_se_comprime_con_el_7z_de_la_consola(tmp_path, monkeypatch):
    """La llamada es la de manual: 7z a -t7z -mx=5 salida fichero."""
    falso = _con_7z(monkeypatch)
    origen = tmp_path / "juego.bin"
    origen.write_bytes(b"datos" * 100)
    salida = tmp_path / "juego.7z"

    resultado = formats.compress_7z(str(origen), str(salida))

    assert resultado["ok"] is True
    assert resultado["out"] == str(salida)
    assert resultado["size"] == salida.stat().st_size
    assert resultado["nota"]
    argumentos, opciones = falso.llamadas[0]
    assert argumentos[0] == "/usr/bin/7z"
    assert argumentos[1:] == ["a", "-t7z", "-mx=5", str(salida), "juego.bin"]
    assert opciones["cwd"] == str(tmp_path)


def test_sin_el_7z_no_se_puede_comprimir(tmp_path, monkeypatch):
    """Sin la utilidad se explica el problema, no se finge que ha salido."""
    monkeypatch.setattr(formats.shutil, "which", lambda binario: None)
    origen = tmp_path / "juego.bin"
    origen.write_bytes(b"datos")

    with pytest.raises(ValueError) as error:
        formats.compress_7z(str(origen), str(tmp_path / "juego.7z"))

    assert "7z" in str(error.value)
    assert "falta" in str(error.value)


def test_el_7z_se_descomprime(tmp_path, monkeypatch):
    """La extraccion es un 7z x en la carpeta de al lado."""
    falso = _con_7z(monkeypatch)
    origen = tmp_path / "juego.7z"
    origen.write_bytes(b"7z")

    resultado = formats.extract_7z(str(origen))

    assert resultado["ok"] is True
    assert resultado["out"].endswith("juego")
    argumentos, _opciones = falso.llamadas[-1]
    assert argumentos[1] == "x"
    assert argumentos[-1] == str(origen)


def test_convertir_a_7z_despacha_al_7z(tmp_path, monkeypatch):
    """``convert`` con destino 7Z crea el fichero comprimido."""
    falso = _con_7z(monkeypatch)
    origen = tmp_path / "juego.bin"
    origen.write_bytes(b"datos" * 100)

    resultado = formats.convert(str(origen), "7z")

    assert resultado["ok"] is True
    assert resultado["out"].endswith(".7z")
    argumentos, _opciones = falso.llamadas[0]
    assert argumentos[1] == "a"


def test_convertir_a_7z_no_pisa_el_7z_que_ya_hay(tmp_path, monkeypatch):
    """Dos compresiones del mismo fichero no se pisan entre si."""
    _con_7z(monkeypatch)
    origen = tmp_path / "juego.bin"
    origen.write_bytes(b"datos" * 100)

    primera = formats.convert(str(origen), "7z")
    segunda = formats.convert(str(origen), "7z")

    assert primera["out"] != segunda["out"]
    assert origen.exists()


def test_el_7z_no_puede_escribir_fuera_de_la_carpeta(tmp_path, monkeypatch):
    """Un 7Z con rutas tramposas no se descomprime."""
    _con_7z(monkeypatch, listado="Path = ../fuera.txt\n")
    origen = tmp_path / "juego.7z"
    origen.write_bytes(b"7z")

    with pytest.raises(ValueError) as error:
        formats.extract_7z(str(origen))

    assert "fuera" in str(error.value)


def test_extraer_un_7z(tmp_path, monkeypatch):
    """``extraer`` tambien sabe desempaquetar un 7Z."""
    _con_7z(monkeypatch)
    origen = tmp_path / "juego.7z"
    origen.write_bytes(b"7z")

    resultado = formats.convert(str(origen), "extraer")

    assert resultado["ok"] is True
    assert (resultado["out"] + "/dentro.txt")


def test_el_7z_se_detecta_como_7z(tmp_path):
    """Un .7z es un 7Z, y lo que se puede hacer con el es sacarlo."""
    ruta = tmp_path / "juego.7z"
    ruta.write_bytes(b"7z\x31\x41\x26\x00")
    info = formats.detect_format(str(ruta))
    assert info.kind == "7z"
    assert [accion["id"] for accion in info.actions] == ["extraer"]


# ── El GDI de Dreamcast ──────────────────────────────────────────────────

def test_el_gdi_se_convierte_en_iso(tmp_path):
    """Del GDI sale un ISO con su descriptor de volumen."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.bin", "wb") as fh:
        fh.write(_sector_modo1(datos))
    gdi = tmp_path / "juego.gdi"
    gdi.write_text('TRACK 01 AUDIO\nINDEX 01 00:00:00\nTRACK 02 DATA\n'
                   'INDEX 01 00:00:00\nFILE "juego.bin" 0 00\n',
                   encoding="latin-1")

    salida = formats.gdi_to_iso(str(gdi), str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    contenido = (tmp_path / "salida.iso").read_bytes()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido
    # El audio no cabe en un ISO de Dreamcast: se dice que se queda aparte.
    assert "audio" in salida["nota"]


def test_el_gdi_empieza_por_donde_dice_el_index(tmp_path):
    """Si la pista de datos no empieza en el sector 0, se respeta."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.bin", "wb") as fh:
        for i in range(11):
            fh.write(_sector_modo1(bytes([i]) + datos[1:]))
    gdi = tmp_path / "juego.gdi"
    gdi.write_text('TRACK 01 DATA\nINDEX 01 00:00:10\n'
                   'FILE "juego.bin" 0 00\n', encoding="latin-1")

    formats.gdi_to_iso(str(gdi), str(tmp_path / "salida.iso"))

    contenido = (tmp_path / "salida.iso").read_bytes()
    # Solo entra el sector 10 (el ultimo), no los diez anteriores.
    assert contenido.count(bytes([10]) + datos[1:]) == 1
    assert len(contenido) == (21 + 1) * 2048


def test_el_gdi_con_cada_pista_en_su_fichero(tmp_path):
    """Si cada pista esta en su fichero, el INDEX dice la posicion en el disco."""
    datos = bytes(range(256)) * 8
    (tmp_path / "juego.bin").write_bytes(formats.build_iso([datos]))
    (tmp_path / "audio.bin").write_bytes(b"\x00" * 2352)
    gdi = tmp_path / "juego.gdi"
    gdi.write_text('TRACK 01 AUDIO\nINDEX 01 00:00:00\nFILE "audio.bin" 0 00\n'
                   'TRACK 02 DATA\nINDEX 01 00:02:00\nFILE "juego.bin" 0 00\n',
                   encoding="latin-1")

    formats.gdi_to_iso(str(gdi), str(tmp_path / "salida.iso"))

    contenido = (tmp_path / "salida.iso").read_bytes()
    # Los datos empiezan en el sector 0 de su fichero, no en el 150.
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


def test_el_gdi_sin_fichero_de_datos_explica_el_problema(tmp_path):
    """Si el BIN no esta, se dice cual falta."""
    gdi = tmp_path / "juego.gdi"
    gdi.write_text('TRACK 01 DATA\nINDEX 01 00:00:00\n'
                   'FILE "juego.bin" 0 00\n', encoding="latin-1")

    with pytest.raises(ValueError) as error:
        formats.gdi_to_iso(str(gdi), str(tmp_path / "salida.iso"))

    assert "BIN" in str(error.value)


def test_el_gdi_se_ofrece_como_iso():
    """Un GDI ofrece ISO: antes no ofrecia nada."""
    assert formats.FORMAT_CATALOGUE["gdi"][1] == ["iso"]
    assert formats.FORMAT_CATALOGUE["mdf"][1] == ["iso"]


def test_el_cdi_no_ofrece_una_conversion_que_falla():
    """El CDI es un contenedor binario del que no se sabe leer la sesion.

    Se podria ofrecer la conversion y que fallara al pulsarla, pero es mejor
    que no aparezca: el botonitis lo hace el usuario.
    """
    assert formats.FORMAT_CATALOGUE["cdi"][1] == []
    with pytest.raises(ValueError) as error:
        formats.cdi_to_iso("cualquier.cdi", "salida.iso")
    assert "CDI" in str(error.value)


# ── El GDI de verdad (el de Sega, que no es un CUE) ──────────────────────

def _iso_de_prueba(num_sectores=17):
    """Un ISO 9660 minimo: el descriptor de volumen esta en el sector 16."""
    datos = bytearray()
    for indice in range(num_sectores):
        sector = bytearray(2048)
        if indice == 16:
            sector[1:6] = b"CD001"
            sector[6] = 1
        datos += bytes(sector)
    return bytes(datos)


def _pista_modo1(datos):
    """Los datos de usuario convertidos en sectores de 2352 bytes."""
    salida = bytearray()
    for offset in range(0, len(datos), 2048):
        salida += _sector_modo1(datos[offset:offset + 2048])
    return bytes(salida)


def test_el_gdi_de_sega_se_convierte_en_iso(tmp_path):
    """El GDI de Dreamcast es una linea por pista: numero, LBA, tipo, sector.

    Este es el formato que usa el GDEMU y el que traen los discos de verdad.
    """
    with open(tmp_path / "track03.bin", "wb") as fh:
        fh.write(_pista_modo1(_iso_de_prueba()))
    # La pista 1 es la zona de baja densidad (el menu de la consola): no va
    # en el ISO del juego.
    with open(tmp_path / "track01.bin", "wb") as fh:
        fh.write(_pista_modo1(b"\x00" * 2048))
    (tmp_path / "juego.gdi").write_text(
        "3\n"
        "1 0 4 2352 track01.bin 0\n"
        "2 600 0 2352 track02.raw 0\n"
        "3 45000 4 2352 track03.bin 0\n",
        encoding="latin-1")

    salida = formats.gdi_to_iso(str(tmp_path / "juego.gdi"),
                                str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    with open(tmp_path / "salida.iso", "rb") as fh:
        fh.seek(16 * 2048)
        descriptor = fh.read(6)
    assert descriptor[1:6] == b"CD001"


def test_el_gdi_une_las_pistas_de_la_zona_de_alta_densidad(tmp_path):
    """Si el juego esta repartido en varias pistas, van todas seguidas."""
    with open(tmp_path / "track03.bin", "wb") as fh:
        fh.write(_pista_modo1(_iso_de_prueba()))
    with open(tmp_path / "track20.bin", "wb") as fh:
        fh.write(_pista_modo1(b"\x11" * 2048))
    (tmp_path / "juego.gdi").write_text(
        "3\n"
        "1 0 4 2352 track01.bin 0\n"
        "3 45000 4 2352 track03.bin 0\n"
        "20 45100 4 2352 track20.bin 0\n",
        encoding="latin-1")

    salida = formats.gdi_to_iso(str(tmp_path / "juego.gdi"),
                                str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    assert "pistas de datos unidas" in salida["nota"]
    # La pista 3 (17 sectores) y luego la 20 (un sector).
    assert salida["size"] >= 18 * 2048


def test_el_gdi_sin_fichero_de_datos_lo_explica(tmp_path):
    """Si el BIN no esta, se dice cual falta."""
    (tmp_path / "juego.gdi").write_text(
        "3\n1 0 4 2352 track01.bin 0\n3 45000 4 2352 track03.bin 0\n",
        encoding="latin-1")

    with pytest.raises(ValueError) as error:
        formats.gdi_to_iso(str(tmp_path / "juego.gdi"),
                           str(tmp_path / "salida.iso"))

    assert "track03.bin" in str(error.value)


# ── El MDS de Alcohol 120% y el CCD de CloneCD ──────────────────────────

def test_el_mds_se_convierte_en_iso(tmp_path):
    """El MDS dice que fichero tiene el disco: el ISO sale de ahi."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.img", "wb") as fh:
        fh.write(_sector_modo1(datos))
    mds = tmp_path / "juego.mds"
    mds.write_text('<?xml version="1.0" encoding="utf-8"?>\n'
                   "<METADATA><![CDATA[notas]]></METADATA>\n"
                   "<CONTENT><EXTENSION>.bin</EXTENSION>"
                   '<IMAGE FNAME="juego.img" FORMAT="2352" SIZE="2352" />'
                   "<SECTORFORMAT>2352</SECTORFORMAT></CONTENT>\n",
                   encoding="utf-8")

    salida = formats.mds_to_iso(str(mds), str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    contenido = (tmp_path / "salida.iso").read_bytes()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


def test_el_mds_sin_imagen_explica_el_problema(tmp_path):
    """Un descriptor sin fichero de imagen no se puede convertir."""
    mds = tmp_path / "juego.mds"
    mds.write_text("<CONTENT></CONTENT>", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        formats.mds_to_iso(str(mds), str(tmp_path / "salida.iso"))

    assert "MDS" in str(error.value)


def test_el_ccd_se_convierte_en_iso(tmp_path):
    """El CCD de CloneCD funciona igual que el MDS."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.img", "wb") as fh:
        fh.write(_sector_modo1(datos))
    ccd = tmp_path / "juego.ccd"
    ccd.write_text('<?xml version="1.0"?>\n<CDREC><DISCID>1234</DISCID>'
                   '<IMAGE FNAME="juego.img" FORMAT="2352" />'
                   '<TRACK MODE="MODE1/2352" /></CDREC>\n', encoding="utf-8")

    salida = formats.ccd_to_iso(str(ccd), str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    contenido = (tmp_path / "salida.iso").read_bytes()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


def test_el_img_en_crudo_se_convierte_en_iso(tmp_path):
    """Una imagen suelta (sin descriptor) tambien se puede pasar a ISO."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.img", "wb") as fh:
        fh.write(_sector_modo1(datos))

    salida = formats.img_to_iso(str(tmp_path / "juego.img"),
                                str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    contenido = (tmp_path / "salida.iso").read_bytes()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


# ── El NRG de Nero ───────────────────────────────────────────────────────

def _nrg_de_prueba(ruta, sectores):
    """Un NRG de Nero minimo: los datos al principio y los chunks al final.

    Se monta con la estructura que documenta Nero: el pie dice donde empieza
    la cadena de chunks (identificador, tamano y cuerpo) y el chunk DAOI
    dice donde esta cada pista.
    """
    datos = b"".join(sector for sector in sectores)
    with open(ruta, "wb") as fh:
        fh.write(datos)

    # Cue sheet: la pista 1 es de datos y empieza en el sector 0.
    cue = b""
    cue += bytes([0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    cue += bytes([0x40, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
    cue += bytes([0x40, 0xAA, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])

    # DAOI: una pista de 2048 bytes por sector.
    entrada = b"\x00" * 12                       # ISRC
    entrada += struct.pack(">H", 2048)           # tamano de sector
    entrada += struct.pack(">H", 0)              # modo
    entrada += struct.pack(">H", 0)              # desconocido
    entrada += struct.pack(">I", 0)              # indice 0
    entrada += struct.pack(">I", 0)              # indice 1
    entrada += struct.pack(">I", len(datos))     # fin de la pista
    cuerpo = struct.pack(">I", 22 + len(entrada)) + b"\x00" * 14
    cuerpo += struct.pack(">H", 0) + bytes([1, 1]) + entrada

    chunks = b""
    chunks += b"CUES" + struct.pack(">I", len(cue)) + cue
    chunks += b"DAOI" + struct.pack(">I", len(cuerpo)) + cuerpo
    chunks += b"END!" + struct.pack(">I", 0)

    with open(ruta, "ab") as fh:
        fh.write(chunks)
        fh.write(b"NERO" + struct.pack(">I", len(datos)))
    return datos


def test_el_nrg_se_convierte_en_iso(tmp_path):
    """Del NRG sale el ISO con la pista de datos."""
    datos = _nrg_de_prueba(tmp_path / "juego.nrg",
                            [bytes(2048), bytes(range(256)) * 8])

    salida = formats.nrg_to_iso(str(tmp_path / "juego.nrg"),
                                str(tmp_path / "salida.iso"))

    assert salida["ok"] is True
    contenido = (tmp_path / "salida.iso").read_bytes()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert bytes(range(256)) * 8 in contenido
    assert datos[:2048] in contenido


def test_el_nrg_se_detecta(tmp_path):
    """El NRG se reconoce por su pie, no por la extension."""
    _nrg_de_prueba(tmp_path / "juego.nrg", [bytes(2048)])
    info = formats.detect_format(str(tmp_path / "juego.nrg"))
    assert info.kind == "nrg"
    assert "iso" in [accion["id"] for accion in info.actions]


def test_un_fichero_que_no_es_nrg_explica_el_problema(tmp_path):
    """Sin el pie de Nero no hay NRG que leer."""
    ruta = tmp_path / "juego.nrg"
    ruta.write_bytes(b"esto no es un nrg" * 10)

    with pytest.raises(ValueError) as error:
        formats.nrg_to_iso(str(ruta), str(tmp_path / "salida.iso"))

    assert "NRG" in str(error.value)


# ── El catalogo ──────────────────────────────────────────────────────────

def test_el_catalogo_tiene_las_conversiones_nuevas():
    """Lo que se ofrece sale del catalogo: si no esta, no sale."""
    assert "cso" in formats.FORMAT_CATALOGUE["iso"][1]
    assert "gcz" in formats.FORMAT_CATALOGUE["iso"][1]
    assert "ciso" in formats.FORMAT_CATALOGUE["iso"][1]
    assert "pbp" in formats.FORMAT_CATALOGUE["iso"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["iso-gamecube"][1]
    assert "rvz" in formats.FORMAT_CATALOGUE["iso-wii"][1]
    assert "cso" in formats.FORMAT_CATALOGUE["iso-ps2"][1]
    assert "7z" in formats.FORMAT_CATALOGUE["bin-cue"][1]
    assert "7z" in formats.FORMAT_CATALOGUE["iso"][1]


def test_todas_las_acciones_del_catalogo_existen():
    """Una accion sin capacidad no se ofrece: se pierde en silencio."""
    for kind, (_etiqueta, acciones) in formats.FORMAT_CATALOGUE.items():
        for accion in acciones:
            assert accion in formats.CAPACIDADES, f"{kind} -> {accion}"


def test_los_formatos_nuevos_son_convertibles_a_iso():
    """Los formatos que se pueden pasar a ISO estan en la lista."""
    for kind in ("gdi", "mdf", "cdi", "nrg"):
        assert kind in formats.CONVERTIBLE_TO_ISO
