"""Tests del paquete `romtools`: DAT, identificacion, nombres y formatos.

El paquete es puro Python de la biblioteca estandar, asi que se puede probar
sin red y sin consola: los DAT de prueba se escriben a mano y las imagenes
sinteticas se construyen sector a sector.
"""

import struct
import zipfile

import pytest

from romtools import dats, formats, identify, naming, rename, sets

# ── DAT de prueba ───────────────────────────────────────────────────────

CLRMAMEPRO = """clrmamepro (
\tname "Prueba"
\tdescription "Prueba"
\tversion "2026.01.01"
)

game (
\tname "Juego (USA)"
\tregion "USA"
\tserial "SLUS-00001"
\trom ( name "Juego (USA).bin" size 1234 crc ABCD1234 md5 0123456789ABCDEF0123456789ABCDEF sha1 0123456789ABCDEF0123456789ABCDEF01234567 serial "SLUS-00001" )
)
game (
\tname "Otro (Europe)"
\tregion "Europe"
\trom ( name "Otro (Europe).bin" size 99 crc 0011AA22 md5 AABBCCDDEEFF00112233445566778899 sha1 BBCCDDEEFF00112233445566778899AABBCCDDEEFF001122 )
)
"""

LOGIQX = """<?xml version="1.0"?>
<datafile>
 <header><name>Prueba</name><description>Prueba</description></header>
 <game name="Juego (Europa)" description="Juego (Europa)" cloneof="Juego (USA)">
  <rom name="Juego (Europa).bin" size="99" crc="0011AA22" md5="AABBCCDDEEFF00112233445566778899" sha1="BBCCDDEEFF00112233445566778899AABBCCDDEEFF001122"/>
 </game>
</datafile>
"""


def _escribir(tmp_path, nombre, texto):
    ruta = tmp_path / nombre
    ruta.write_text(texto, encoding="utf-8")
    return str(ruta)


# ── DAT ─────────────────────────────────────────────────────────────────

def test_el_dat_clrmamepro_se_lee(tmp_path):
    """El formato de libretro (clrmamepro) no es XML y tiene su lector."""
    ruta = _escribir(tmp_path, "prueba.dat", CLRMAMEPRO)
    juegos = dats.parse_dat(ruta)
    assert len(juegos) == 2
    primero = juegos[0]
    assert primero["name"] == "Juego (USA)"
    assert primero["serial"] == "SLUS-00001"
    assert primero["region"] == "USA"
    rom = primero["roms"][0]
    assert rom["name"] == "Juego (USA).bin"
    assert rom["size"] == 1234
    assert rom["crc"] == "ABCD1234"
    assert rom["md5"] == "0123456789abcdef0123456789abcdef"
    assert rom["sha1"].startswith("0123456789abcdef")


def test_el_dat_logiqx_se_lee(tmp_path):
    """El formato de Redump (Logiqx) es XML y se lee con ElementTree."""
    ruta = _escribir(tmp_path, "logiqx.dat", LOGIQX)
    juegos = dats.parse_dat(ruta)
    assert len(juegos) == 1
    assert juegos[0]["cloneof"] == "Juego (USA)"
    assert juegos[0]["roms"][0]["crc"] == "0011AA22"


def test_el_indice_busca_por_hash_y_por_nombre(tmp_path):
    """Con el indice se localiza la ROM por hash, por nombre y por titulo."""
    ruta = _escribir(tmp_path, "prueba.dat", CLRMAMEPRO)
    indice = dats.build_index(dats.parse_dat(ruta))
    assert indice["by_hash"]["crc32:ABCD1234"]["name"] == "Juego (USA)"
    assert indice["by_hash"]["md5:0123456789abcdef0123456789abcdef"]["name"] == "Juego (USA)"
    assert indice["by_name"]["juego usa"]["name"] == "Juego (USA)"
    assert indice["by_serial"]["SLUS-00001"]["name"] == "Juego (USA)"
    assert "juego usa" in indice["by_title"]


def test_el_indice_se_guarda_y_se_cree(tmp_path):
    """El indice queda en disco y se vuelve a leer sin el DAT."""
    ruta = _escribir(tmp_path, "prueba.dat", CLRMAMEPRO)
    juegos = dats.parse_dat(ruta)
    indice = dats.build_index(juegos)
    meta = {"system": "prueba", "source": "test", "dat": "Prueba", "games": len(juegos),
            "by_hash": indice["by_hash"], "by_serial": indice["by_serial"],
            "by_name": indice["by_name"], "by_title": indice["by_title"]}
    import json
    (tmp_path / "prueba.json").write_text(json.dumps(meta), encoding="utf-8")
    cargado = dats.load_index("prueba", str(tmp_path))
    assert cargado["games"] == 2
    assert "crc32:ABCD1234" in cargado["by_hash"]


def test_cada_sistema_de_batocera_tiene_su_dat():
    """El mapa de sistemas tiene los nombres de DAT que se usan de verdad."""
    assert dats.SYSTEM_DAT["ps2"] == ("libretro-redump", "Sony - PlayStation 2")
    assert dats.SYSTEM_DAT["snes"] == ("libretro-no-intro",
                                       "Nintendo - Super Nintendo Entertainment System")
    for sistema, (fuente, nombre) in dats.SYSTEM_DAT.items():
        assert fuente in dats.SOURCES
        assert nombre


# ── Identificacion ──────────────────────────────────────────────────────

def _iso_playstation(tmp_path):
    """Una ISO con la firma de PS2 en la ventana del descriptor."""
    datos = bytearray(0x9000)
    datos[0x8000:0x8006] = b"\x01CD001"
    datos[0x8014:0x8014 + 11] = b"PLAYSTATION"
    ruta = tmp_path / "ps2.iso"
    ruta.write_bytes(bytes(datos))
    return str(ruta)


def test_la_plataforma_se_leye_de_la_cabecera(tmp_path):
    """Cada consola tiene su magia en su sitio."""
    assert identify.detect_platform(_iso_playstation(tmp_path)) == "ps2"

    wii = bytearray(0x40)
    wii[0:6] = b"RSBE01"
    wii[0x18:0x1C] = struct.pack(">I", 0x5D1C9EA3)
    ruta = tmp_path / "wii.iso"
    ruta.write_bytes(bytes(wii))
    assert identify.detect_platform(str(ruta)) == "wii"

    gc = bytearray(0x40)
    gc[0:6] = b"GALE01"
    gc[0x1C:0x20] = struct.pack(">I", 0xC2339F3D)
    ruta = tmp_path / "gc.iso"
    ruta.write_bytes(bytes(gc))
    assert identify.detect_platform(str(ruta)) == "gc"

    xbox = bytearray(0x40)
    xbox[0x14:0x14 + 20] = b"MICROSOFT*XBOX*MEDIA"
    ruta = tmp_path / "xbox.bin"
    ruta.write_bytes(bytes(xbox))
    assert identify.detect_platform(str(ruta)) == "xbox"

    saturn = bytearray(0x40)
    saturn[0x10:0x10 + 15] = b"SEGA SEGASATURN"
    ruta = tmp_path / "saturn.bin"
    ruta.write_bytes(bytes(saturn))
    assert identify.detect_platform(str(ruta)) == "saturn"


def test_el_serial_se_saca_de_la_imagen(tmp_path):
    """En una ISO de PS2 el serial esta en el identificador del volumen."""
    datos = bytearray(0x9000)
    datos[0x8000:0x8006] = b"\x01CD001"
    datos[0x8028:0x8028 + 11] = b"SLUS_204.60"
    ruta = tmp_path / "juego.iso"
    ruta.write_bytes(bytes(datos))
    firma = identify.disc_signature(str(ruta))
    assert firma.serial == "SLUS_204.60"
    assert firma.volume_id == "SLUS_204.60"


def test_los_titulos_se_comparan():
    """Dos escrituras del mismo titulo se parecen; otros no."""
    assert identify.title_similarity("Sonic the Hedgehog", "Sonic The Hedgehog") > 0.9
    assert identify.title_similarity("Sonic the Hedgehog", "Mario Kart") < 0.4
    assert identify.normalize_title("Pokémon Azul ¡Edición!") == "pokemon azul edicion"


def test_la_rom_se_identifica_por_hash(tmp_path):
    """Con el hash el resultado es seguro."""
    import hashlib
    ruta = tmp_path / "juego.bin"
    ruta.write_bytes(b"contenido de prueba")
    crc = f"{__import__('zlib').crc32(b'contenido de prueba') & 0xFFFFFFFF:08X}"
    indice = {"by_hash": {f"crc32:{crc}": {"name": "Juego (USA)",
                                           "description": "Juego (USA)"}},
              "by_serial": {}, "by_name": {}, "by_title": {}}
    match = identify.identify(str(ruta), indice)
    assert match.method == "hash"
    assert match.confidence == 1.0
    assert match.entry["name"] == "Juego (USA)"


def test_la_rom_se_identifica_por_nombre(tmp_path):
    """Sin hash, el nombre identico al del DAT es una senal fuerte."""
    ruta = tmp_path / "Juego (USA).bin"
    ruta.write_bytes(b"x")
    indice = {"by_hash": {}, "by_serial": {},
              "by_name": {"juego usa": {"name": "Juego (USA).bin",
                                       "description": "Juego (USA)"}},
              "by_title": {}}
    match = identify.identify(str(ruta), indice)
    assert match.method == "nombre"
    assert match.confidence >= 0.8


# ── Nombres ─────────────────────────────────────────────────────────────

def test_el_nombre_del_dat_se_descompone():
    parsed = naming.parse_dat_name("Ridge Racer (USA) (Track 1) [SLUS-00237]")
    assert parsed.title == "Ridge Racer"
    assert parsed.tags == ["USA", "Track 1"]
    assert parsed.serial == "SLUS-00237"
    assert parsed.disc_tags == ["Track 1"]
    assert parsed.region_tags == ["USA"]


def test_la_marca_de_volcado_malo_es_la_b():
    """En la convencion GoodTools, ``!`` es volcado verificado y ``[b]`` el malo."""
    malo = naming.parse_dat_name("Juego (USA) [b].a26")
    bueno = naming.parse_dat_name("Juego (USA) [!].a26")
    assert malo.bad is True and malo.good is False
    assert bueno.good is True and bueno.bad is False
    assert "[b]" in malo.marks


def test_el_nombre_destino_es_el_del_dat():
    """El destino es el nombre del DAT, no uno inventado."""
    entrada = {"name": "Juego (USA) [SLUS-00001]",
               "description": "Juego (USA)",
               "roms": [{"name": "Juego (USA) [SLUS-00001].bin"}]}
    assert naming.rom_target_name(entrada, "cualquier.bin") == "Juego (USA) [SLUS-00001].bin"
    assert naming.target_name(entrada, ".bin").startswith("Juego (USA)")


def test_el_nombre_sin_dat_se_ordena():
    """Sin DAT, el nombre del fichero se recompone con la misma gramática."""
    destino = naming.fallback_name("juego [slus-00001] (usa).bin")
    assert destino == "juego (usa) [slus-00001].bin"


# ── Variantes ───────────────────────────────────────────────────────────

def test_la_puntuacion_elige_la_mejor_variante():
    """Una demo pierde contra la version final de la misma region."""
    final = {"name": "Juego (USA)", "description": "Juego (USA)"}
    demo = {"name": "Juego (USA) (Beta 2)", "description": "Juego (USA) (Beta 2)"}
    europea = {"name": "Juego (Europe)", "description": "Juego (Europe)"}
    elegida, score = sets.pick_best([demo, final, europea])
    assert elegida["name"] == "Juego (USA)"
    assert sets.score_entry(demo).total < sets.score_entry(final).total
    assert sets.score_entry(europea).total < sets.score_entry(final).total
    assert any("preliminar" in r for r in sets.score_entry(demo).reasons)


def test_las_marcas_cambian_la_puntuacion():
    malo = sets.score_entry({"name": "Juego (USA) [b]", "description": "x"})
    bueno = sets.score_entry({"name": "Juego (USA) [!]", "description": "x"})
    assert bueno.total > malo.total


def test_el_numero_de_disco_se_saca_del_nombre():
    assert sets.disc_number("Juego (Disc 2)") == 2
    assert sets.disc_number("Juego (USA)") is None
    assert sets.clean_title("Juego (USA) (Disc 1)") == "Juego (Disc 1)"


# ── Variantes: el mismo juego, no el mismo subtitulo ────────────────────

def _candidato(nombre, score, descripcion=None):
    """Un candidato tal y como los devuelve ``identify.match_by_title``."""
    return {"entry": {"name": nombre, "description": descripcion or nombre},
            "score": score}


def test_la_identidad_de_un_juego_ignora_la_region():
    """El titulo y el disco identifican un juego; la region, no."""
    assert sets.game_key("Juego - La Version (World) (En,Ja)") == \
        sets.game_key("Juego - La Version (USA)")
    assert sets.game_key("Juego - La Version (Japan) (Disc A)") != \
        sets.game_key("Juego - La Version (Japan) (Disc B)")
    assert sets.disc_tag("Juego (Disc A)") == "disc a"
    assert sets.disc_tag("Juego (USA)") is None


def test_la_variante_se_elige_dentro_del_mismo_juego():
    """Dos juegos distintos que comparten subtitulo no se confunden.

    Es el caso de «The Director's Cut»: hay varios juegos con ese subtitulo y
    el que tiene mejor region no puede llevarse el renombrado del otro.
    """
    ballz = _candidato("Ballz - The Director's Cut (World) (En,Ja)", 1.0)
    diner = _candidato("D's Diner - The Director's Cut (Japan) (Disc A)", 0.57)
    elegida, score, grupo = sets.pick_best_variant([diner, ballz])
    assert elegida["name"] == "Ballz - The Director's Cut (World) (En,Ja)"
    assert len(grupo) == 1


def test_entre_variantes_del_mismo_juego_manda_la_region():
    """Entre el mismo juego en varias regiones gana la que se prefiera."""
    mundial = _candidato("Juego - La Version (World) (En,Ja)", 1.0)
    us = _candidato("Juego - La Version (USA)", 1.0)
    elegida, score, grupo = sets.pick_best_variant([mundial, us])
    assert elegida["name"] == "Juego - La Version (USA)"
    assert len(grupo) == 2


def test_el_disco_del_fichero_manda():
    """Con varios discos del mismo juego se elige el del fichero."""
    disc_a = _candidato("Juego - La Version (Japan) (Disc A)", 1.0)
    disc_b = _candidato("Juego - La Version (Japan) (Disc B)", 1.0)
    elegida, score, grupo = sets.pick_best_variant(
        [disc_a, disc_b], source="Juego - La Version (Japan) (Disc B).bin")
    assert elegida["name"] == "Juego - La Version (Japan) (Disc B)"


def test_el_plan_no_renombra_a_otro_juego(tmp_path):
    """El caso real de 3DO, de punta a punta."""
    dat = """clrmamepro (
\tname "Prueba"
\tdescription "Prueba"
)

game (
\tname "Ballz - The Director's Cut (World) (En,Ja)"
\trom ( name "Ballz - The Director's Cut (World) (En,Ja).bin" size 10 crc 1111222233334444 md5 11112222333344441111222233334444 sha1 1111222233334444111122223333444411112222333344441111222233334444 )
)
game (
\tname "D's Diner - The Director's Cut (Japan) (Disc A)"
\trom ( name "D's Diner - The Director's Cut (Japan) (Disc A).bin" size 10 crc 5555666677778888 md5 55556666777788885555666677778888 sha1 5555666677778888555566667777888855556666777788885555666677778888 )
)
"""
    ruta = _escribir(tmp_path, "directors.dat", dat)
    indice = dats.build_index(dats.parse_dat(ruta))

    rom = tmp_path / "Ballz - The Director's Cut (1995) (Panasonic) (US) [!].iso"
    rom.write_bytes(b"datos")

    plan = rename.plan_rename([str(rom)], indice)
    propuesta = plan["items"][0]["proposed"]
    assert propuesta.startswith("Ballz - The Director's Cut")
    assert "Diner" not in propuesta
    assert rom.exists()


# ── Plan de renombrado ──────────────────────────────────────────────────

def test_el_plan_propone_el_nombre_del_dat(tmp_path):
    """El plan no toca el disco: solo dice que haria."""
    rom = tmp_path / "juego.bin"
    rom.write_bytes(b"datos")
    indice = {"by_hash": {}, "by_serial": {}, "by_name": {},
              "by_title": {"juego": [{"name": "Juego (USA).bin",
                                      "description": "juego",
                                      "roms": [{"name": "Juego (USA).bin"}]}]}}
    plan = rename.plan_rename([str(rom)], indice)
    assert plan["stats"]["renombrar"] == 1
    assert plan["items"][0]["proposed"] == "Juego (USA).bin"
    assert rom.exists()
    assert rom.name == "juego.bin"


def test_renombrar_y_deshacer(tmp_path):
    """Al aplicar se renombran la ROM y su CUE, y se puede volver atras."""
    rom = tmp_path / "juego.bin"
    rom.write_bytes(b"datos")
    cue = tmp_path / "juego.cue"
    cue.write_text('FILE "juego.bin" BINARY\n', encoding="latin-1")
    indice = {"by_hash": {}, "by_serial": {}, "by_name": {},
              "by_title": {"juego": [{"name": "Juego (USA).bin",
                                      "description": "juego",
                                      "roms": [{"name": "Juego (USA).bin"}]}]}}
    plan = rename.plan_rename([str(rom)], indice)
    salida = rename.apply_plan(plan, str(tmp_path), root=str(tmp_path))
    assert salida["ok"] is True
    assert (tmp_path / "Juego (USA).bin").exists()
    assert (tmp_path / "Juego (USA).cue").exists()
    assert not rom.exists()

    vuelta = rename.undo_last(str(tmp_path))
    assert vuelta["ok"] is True
    assert rom.exists()
    assert cue.exists()


def test_no_se_renombra_nada_fuera_de_la_carpeta(tmp_path):
    """El plan se aplica solo dentro de la carpeta del sistema."""
    fuera = tmp_path.parent / "fuera.bin"
    fuera.write_bytes(b"x")
    try:
        plan = {"items": [{"file": "../fuera.bin", "proposed": "otro.bin",
                           "action": "renombrar", "companions": []}]}
        salida = rename.apply_plan(plan, str(tmp_path), root=str(tmp_path))
        assert salida["ok"] is False
        assert salida["errores"]
        assert not (tmp_path.parent / "otro.bin").exists()
    finally:
        if fuera.exists():
            fuera.unlink()


# ── CLI ─────────────────────────────────────────────────────────────────

def test_el_cli_acepta_el_grupo_dats(tmp_path, capsys):
    """El instalador llama a `romtools dats --install`: tiene que funcionar."""
    from romtools import __main__ as cli

    assert cli.main(["--root", str(tmp_path), "dats", "--list"]) == 0
    salida = capsys.readouterr().out
    assert "3do" in salida

    # La forma corta sigue viva.
    assert cli.main(["--root", str(tmp_path), "list"]) == 0
    assert "3do" in capsys.readouterr().out


def test_el_cli_avisa_de_un_sistema_sin_dat(tmp_path, capsys):
    """Un sistema que no existe se avisa, pero no se cae."""
    from romtools import __main__ as cli

    assert cli.main(["--root", str(tmp_path), "dats", "--install",
                     "no-existe"]) == 1
    assert "no tiene DAT configurado" in capsys.readouterr().out


# ── Formatos ────────────────────────────────────────────────────────────

def _sector_modo1(datos):
    """Un sector CD de 2352 bytes con los datos de usuario dados."""
    sector = bytearray(2352)
    sector[0:12] = b"\x00" * 12
    sector[12] = 0x01
    sector[15] = 0x01
    sector[16:16 + len(datos)] = datos
    return bytes(sector)


def test_el_formato_se_detecta(tmp_path):
    pbp = tmp_path / "juego.pbp"
    pbp.write_bytes(b"PBP\x01" + struct.pack(">5I", 0, 0, 0, 0, 0) + b"\x00" * 100)
    assert formats.detect_format(str(pbp)).kind == "pbp"

    chd = tmp_path / "juego.chd"
    chd.write_bytes(b"MComprHD" + struct.pack(">III", 5, 0, 1) + b"\x00" * 100)
    assert formats.detect_format(str(chd)).kind == "chd"

    wbfs = tmp_path / "juego.wbfs"
    wbfs.write_bytes(b"WBFS" + b"\x00" * 200)
    assert formats.detect_format(str(wbfs)).kind == "wbfs"


def test_bin_cue_a_iso_y_vuelta(tmp_path):
    """La conversion de ida y vuelta deja el ISO con su volumen."""
    datos = bytes(range(256)) * 8
    bin_path = tmp_path / "juego.bin"
    with open(bin_path, "wb") as fh:
        fh.write(_sector_modo1(datos))
    cue = tmp_path / "juego.cue"
    cue.write_text('FILE "juego.bin" BINARY\n  TRACK 01 MODE1/2352\n'
                   '    INDEX 01 00:00:00\n', encoding="latin-1")

    iso = str(tmp_path / "juego.iso")
    salida = formats.bin_cue_to_iso(str(cue), iso)
    assert salida["ok"] is True
    with open(iso, "rb") as fh:
        contenido = fh.read()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido

    de_vuelta = formats.iso_to_bin_cue(iso)
    assert de_vuelta["ok"] is True
    with open(de_vuelta["bin"], "rb") as fh:
        bruto = fh.read()
    assert len(bruto) % 2352 == 0
    assert datos in bruto
    with open(de_vuelta["cue"], encoding="latin-1") as fh:
        assert "TRACK 01 MODE1/2352" in fh.read()


def test_el_cue_de_la_vuelta_va_al_lado_del_bin(tmp_path):
    """Al pedir la vuelta con nombre, el CUE se llama como el BIN."""
    iso = tmp_path / "juego.iso"
    iso.write_bytes(formats.build_iso([bytes(2048)] * 2, volume_id="JUEGO"))
    formats.convert(str(iso), "bin-cue", str(tmp_path / "vuelta"))
    assert (tmp_path / "vuelta.bin").exists()
    assert (tmp_path / "vuelta.cue").exists()
    assert not (tmp_path / "juego.cue").exists()


def test_un_bin_con_cue_se_detecta_como_set(tmp_path):
    """Un .bin con CUE al lado es un BIN+CUE, no un BIN suelto."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.bin", "wb") as fh:
        fh.write(_sector_modo1(datos))
    (tmp_path / "juego.cue").write_text(
        'FILE "juego.bin" BINARY\n  TRACK 01 MODE1/2352\n'
        '    INDEX 01 00:00:00\n', encoding="latin-1")

    info = formats.detect_format(str(tmp_path / "juego.bin"))
    assert info.kind == "bin-cue"
    assert info.label == "BIN + CUE"
    assert "convertir a PBP" in info.actions
    assert info.details["cue"] == "juego.cue"


def test_el_bin_se_convierte_a_iso_pidiendo_el_bin(tmp_path):
    """Al pedir la conversion del .bin se encuentra su CUE hermano."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.bin", "wb") as fh:
        fh.write(_sector_modo1(datos))
    (tmp_path / "juego.cue").write_text(
        'FILE "juego.bin" BINARY\n  TRACK 01 MODE1/2352\n'
        '    INDEX 01 00:00:00\n', encoding="latin-1")

    iso = str(tmp_path / "salida.iso")
    salida = formats.convert(str(tmp_path / "juego.bin"), "iso", iso)
    assert salida["ok"] is True
    with open(iso, "rb") as fh:
        contenido = fh.read()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


def test_el_bin_suelto_se_convierte_a_iso(tmp_path):
    """Un BIN sin CUE tambien se convierte: el modo va en cada sector."""
    datos = bytes(range(256)) * 8
    with open(tmp_path / "juego.bin", "wb") as fh:
        fh.write(_sector_modo1(datos))

    iso = str(tmp_path / "salida.iso")
    salida = formats.convert(str(tmp_path / "juego.bin"), "iso", iso)
    assert salida["ok"] is True
    with open(iso, "rb") as fh:
        contenido = fh.read()
    assert contenido[0x8001:0x8006] == b"CD001"
    assert datos in contenido


def test_el_cue_se_lee(tmp_path):
    """Del CUE se sacan las pistas y el BIN que describe."""
    cue = tmp_path / "juego.cue"
    cue.write_text('FILE "juego.bin" BINARY\n  TRACK 01 MODE1/2352\n'
                   '    INDEX 01 00:00:00\n', encoding="latin-1")
    pistas = formats.parse_cue(str(cue))
    assert len(pistas) == 1
    assert pistas[0]["file"] == "juego.bin"
    assert pistas[0]["tracks"][0]["mode"] == "MODE1/2352"
    assert pistas[0]["tracks"][0]["index"][0]["sector"] == 0


def test_el_parche_ips_se_aplica_y_se_deshace(tmp_path):
    """El parche escribe los bytes y se puede volver al original."""
    rom = tmp_path / "juego.bin"
    rom.write_bytes(bytes(range(16)))
    ips = tmp_path / "juego.ips"
    # Cabecera PATCH + escritura en el offset 4 de 2 bytes + fin.
    ips.write_bytes(b"PATCH" + bytes([0, 0, 4]) + bytes([0, 2]) + b"\xAA\xBB" + b"EOF")

    salida = formats.apply_ips(str(rom), str(ips))
    assert salida["ok"] is True
    assert rom.read_bytes()[4:6] == b"\xAA\xBB"
    assert (tmp_path / "juego.bin.bak").exists()

    formats.revert_ips(str(rom))
    assert rom.read_bytes() == bytes(range(16))


def test_comprimir_y_descomprimir(tmp_path):
    """El ZIP se crea y se vuelve a extraer."""
    origen = tmp_path / "juego.bin"
    origen.write_bytes(b"datos" * 100)
    salida = formats.compress_zip(str(origen))
    assert salida["ok"] is True
    with zipfile.ZipFile(salida["out"]) as zf:
        assert zf.namelist() == ["juego.bin"]


def test_el_catalogo_de_formatos_es_coherente():
    """Cada formato del catalogo tiene etiqueta y acciones."""
    for kind, (etiqueta, acciones) in formats.FORMAT_CATALOGUE.items():
        assert etiqueta
        assert acciones
