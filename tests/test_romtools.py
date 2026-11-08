"""Tests del paquete `romtools`: DAT, identificacion, nombres y formatos.

El paquete es puro Python de la biblioteca estandar, asi que se puede probar
sin red y sin consola: los DAT de prueba se escriben a mano y las imagenes
sinteticas se construyen sector a sector.
"""

import json
import os
import struct
import time
import zipfile
from pathlib import Path

import pytest

from romtools import dats, formats, identify, jobs, naming, progress, rename, sets

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


def test_un_indice_viejo_se_rehace_desde_el_dat(tmp_path):
    """Un indice del formato viejo no tiene la lista de juegos: se rehace.

    Los indices instalados antes de que los mapas guardaran la posicion del
    juego llevan el juego entero dentro de cada mapa y en «games» solo el
    numero. Sin la lista de juegos no se puede comparar la biblioteca con el
    DAT, asi que el indice se reconstruye desde el DAT, que sigue ahi.
    """
    _escribir(tmp_path, "prueba.dat", CLRMAMEPRO)
    juegos = dats.parse_dat(str(tmp_path / "prueba.dat"))
    viejo = dats.build_index(juegos)          # los mapas con el juego entero
    meta = {"system": "prueba", "source": "test", "dat": "Prueba",
            "version": "2026.01.01", "games": len(juegos)}
    meta.update(viejo)
    (tmp_path / "prueba.json").write_text(json.dumps(meta), encoding="utf-8")

    cargado = dats.load_index("prueba", str(tmp_path))

    # La lista de juegos esta y es la del DAT, no la reconstruida con los mapas.
    assert [j["name"] for j in cargado["juegos"]] == ["Juego (USA)", "Otro (Europe)"]
    assert cargado["by_hash"]["crc32:ABCD1234"]["name"] == "Juego (USA)"
    assert cargado["by_name"]["juego usa"]["name"] == "Juego (USA)"

    # El indice queda escrito en el formato nuevo, con su fichero de metadatos.
    guardado = json.loads((tmp_path / "prueba.json").read_text(encoding="utf-8"))
    assert isinstance(guardado["juegos"], list)
    assert len(guardado["juegos"]) == 2
    assert guardado["by_name"]["juego usa"] == 0     # una posicion, no el juego
    meta_lado = json.loads((tmp_path / "prueba.meta.json").read_text(encoding="utf-8"))
    assert meta_lado["games"] == 2
    assert meta_lado["dat"] == "Prueba"


def test_un_indice_viejo_sin_dat_no_se_inventa(tmp_path):
    """Si el DAT no esta, el indice viejo no se puede rehacer: no se inventa."""
    juegos = dats.parse_dat(_escribir(tmp_path, "otro.dat", CLRMAMEPRO))
    viejo = dats.build_index(juegos)
    meta = {"system": "prueba", "source": "test", "dat": "Prueba",
            "games": len(juegos)}
    meta.update(viejo)
    (tmp_path / "prueba.json").write_text(json.dumps(meta), encoding="utf-8")

    assert dats.load_index("prueba", str(tmp_path)) is None


def test_la_migracion_no_toca_un_indice_ya_nuevo(tmp_path):
    """Un indice en el formato nuevo se lee tal cual, sin reescribirlo."""
    _escribir(tmp_path, "prueba.dat", CLRMAMEPRO)
    compacto = dats.build_index_compacto(dats.parse_dat(str(tmp_path / "prueba.dat")))
    indice = {"juegos": compacto["juegos"], "by_hash": compacto["by_hash"],
              "by_serial": compacto["by_serial"], "by_name": compacto["by_name"],
              "by_name_size": compacto["by_name_size"],
              "by_title": compacto["by_title"],
              "by_gamecode": compacto.get("by_gamecode", {})}
    (tmp_path / "prueba.json").write_text(json.dumps(indice), encoding="utf-8")
    antes = (tmp_path / "prueba.json").read_text(encoding="utf-8")

    cargado = dats.load_index("prueba", str(tmp_path))

    assert len(cargado["juegos"]) == 2
    assert (tmp_path / "prueba.json").read_text(encoding="utf-8") == antes
    assert not (tmp_path / "prueba.meta.json").exists()


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


def test_la_busqueda_por_titulo_no_usa_las_palabras_de_las_etiquetas(tmp_path):
    """«(USA)» no puede ser la palabra que encuentra el juego.

    En el DAT de PlayStation 2, «(USA)» comparte palabra con un cuarto de los
    titulos (2.260 candidatos de 11.065) y la busqueda se iba a 0,3 s por
    fichero: comparar ps2 entero tardaba 33 s. Las palabras de la busqueda
    salen del titulo **pelado**, sin etiquetas.
    """
    ruta = tmp_path / "Cosa (USA).bin"
    ruta.write_bytes(b"x")
    indice = {"by_hash": {}, "by_serial": {}, "by_name": {},
              "by_title": {"juego usa": [{"name": "Juego (USA).bin",
                                          "description": "Juego (USA)",
                                          "roms": [{"name": "Juego (USA).bin"}]}]}}
    match = identify.identify(str(ruta), indice)
    assert match.candidates == []


def test_el_titulo_pelado_si_encuentra_el_juego(tmp_path):
    """Lo de antes sigue funcionando: el juego se encuentra por el titulo."""
    ruta = tmp_path / "Juego (USA).bin"
    ruta.write_bytes(b"x")
    indice = {"by_hash": {}, "by_serial": {}, "by_name": {},
              "by_title": {"juego usa": [{"name": "Juego (USA).bin",
                                          "description": "Juego (USA)",
                                          "roms": [{"name": "Juego (USA).bin"}]}]}}
    match = identify.identify(str(ruta), indice)
    assert match.method == "titulo"
    assert match.entry["name"] == "Juego (USA).bin"


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
    # Las acciones son identificadores: el frontend los compara, no sus textos.
    ids = [accion["id"] for accion in info.actions]
    assert "pbp" in ids
    assert all(isinstance(accion["id"], str) for accion in info.actions)
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
    """Cada formato del catalogo tiene etiqueta y sus acciones son reales."""
    for kind, (etiqueta, acciones) in formats.FORMAT_CATALOGUE.items():
        assert etiqueta
        # Hay formatos que no se pueden convertir (un RVZ, un WAD): lo que no
        # puede ser es apuntar a una conversion que no existe.
        for accion in acciones:
            assert accion in formats.CAPACIDADES


def test_las_capacidades_tienen_label():
    """Cada capacidad sabe como se llama y que hace."""
    for id_capacidad, cap in formats.CAPACIDADES.items():
        assert cap["label"]
        assert cap["ayuda"]


# ── El motor de conversiones revisado ───────────────────────────────────

def _iso_de_prueba(tmp_path, nombre="juego.iso", sectores=40):
    """Un ISO 9660 minimo, con su descriptor de volumen."""
    iso = tmp_path / nombre
    with open(iso, "wb") as fh:
        for i in range(sectores):
            sector = bytearray(2048)
            if i == 16:
                sector[0] = 1        # descriptor de volumen primario
                sector[1:6] = b"CD001"
                sector[6] = 1
            fh.write(bytes(sector))
    return iso


def test_la_magia_de_nintendo_64_dice_el_byte_order(tmp_path):
    """El byte order se ve en la cabecera, no en el nombre del fichero."""
    cuerpo = bytes(range(256)) * 4
    casos = {
        "juego.n64": (b"\x40\x12\x37\x80", "n64-n64"),
        "juego.z64": (b"\x80\x37\x12\x40", "n64-z64"),
        "juego.v64": (b"\x37\x80\x40\x12", "n64-v64"),
    }
    for nombre, (magia, kind) in casos.items():
        ruta = tmp_path / nombre
        ruta.write_bytes(magia + cuerpo)
        info = formats.detect_format(str(ruta))
        assert info.kind == kind, nombre


def test_un_v64_mal_puesto_se_detecta_por_la_magia(tmp_path):
    """Hay volcados que se llaman .v64 y estan en big endian."""
    ruta = tmp_path / "raro.v64"
    ruta.write_bytes(b"\x40\x12\x37\x80" + bytes(64))
    assert formats.detect_format(str(ruta)).kind == "n64-n64"


def test_las_tres_rom_de_nintendo_64_son_la_misma(tmp_path):
    """De native a little endian y a byte swapped, y de vuelta."""
    cuerpo = bytes(range(256)) * 8
    n64 = tmp_path / "juego.n64"
    n64.write_bytes(b"\x40\x12\x37\x80" + cuerpo)

    z64 = formats.convert(str(n64), "z64")
    datos = open(z64["out"], "rb").read()
    assert datos[:4] == b"\x80\x37\x12\x40"
    assert datos[4:] == formats._swap32(cuerpo)

    v64 = formats.convert(str(n64), "v64")
    datos = open(v64["out"], "rb").read()
    assert datos[:4] == b"\x37\x80\x40\x12"

    vuelta = formats.convert(v64["out"], "z64")
    assert open(vuelta["out"], "rb").read()[:4] == b"\x80\x37\x12\x40"


def test_las_rom_de_super_nintendo_cambian_de_cabecera(tmp_path):
    """SFC, SMC y FIG son la misma ROM con otra cabecera delante."""
    cuerpo = bytes(range(256)) * 8
    smc = tmp_path / "juego.smc"
    cabecera = bytearray(512)
    cabecera[0x08:0x0A] = b"\xaa\xbb"
    smc.write_bytes(bytes(cabecera) + cuerpo)

    sfc = formats.convert(str(smc), "sfc")
    assert open(sfc["out"], "rb").read() == cuerpo

    fig = formats.convert(str(smc), "fig")
    datos = open(fig["out"], "rb").read()
    assert datos[:4] == b"FIG "
    assert datos[1024:] == cuerpo

    vuelta = formats.convert(fig["out"], "sfc")
    assert open(vuelta["out"], "rb").read() == cuerpo


def test_el_cso_va_y_vuelve(tmp_path):
    """Un CSO se comprime y se descomprime sin perder un byte."""
    iso = _iso_de_prueba(tmp_path)
    original = iso.read_bytes()

    cso = formats.convert(str(iso), "cso")
    assert open(cso["out"], "rb").read(4) == b"CSO!"

    vuelta = formats.convert(cso["out"], "iso")
    assert open(vuelta["out"], "rb").read() == original


def test_el_ciso_va_y_vuelve(tmp_path):
    """Un CISO se comprime y se descomprime sin perder un byte."""
    iso = _iso_de_prueba(tmp_path)
    original = iso.read_bytes()

    ciso = formats.convert(str(iso), "ciso")
    assert open(ciso["out"], "rb").read(4) == b"CISO"

    vuelta = formats.convert(ciso["out"], "iso")
    assert open(vuelta["out"], "rb").read() == original


def test_el_gcz_va_y_vuelve(tmp_path):
    """Un GCZ se comprime y se descomprime sin perder un byte."""
    iso = _iso_de_prueba(tmp_path)
    original = iso.read_bytes()

    gcz = formats.convert(str(iso), "gcz")
    assert open(gcz["out"], "rb").read(4) == b"\x01\xc0\x0b\xb1"

    vuelta = formats.convert(gcz["out"], "iso")
    assert open(vuelta["out"], "rb").read() == original


def test_extraer_un_zip(tmp_path):
    """Un ZIP se extrae en una carpeta al lado."""
    origen = tmp_path / "juego.zip"
    with zipfile.ZipFile(origen, "w") as zf:
        zf.writestr("dentro.txt", "hola")
    salida = formats.convert(str(origen), "extraer")
    assert (Path(salida["out"]) / "dentro.txt").read_text() == "hola"


def test_las_conversiones_no_pisan_el_original(tmp_path):
    """Dos conversiones del mismo fichero no se pisan entre si."""
    iso = _iso_de_prueba(tmp_path)
    primera = formats.convert(str(iso), "zip")
    segunda = formats.convert(str(iso), "zip")
    assert primera["out"] != segunda["out"]
    assert iso.exists()


def test_el_iso_de_un_bin_cue_conserva_el_original(tmp_path):
    """Al ir y volver, el ISO vuelve a ser el que era."""
    iso = _iso_de_prueba(tmp_path)
    original = iso.read_bytes()

    bin_cue = formats.convert(str(iso), "bin-cue")
    assert os.path.getsize(bin_cue["out"]) == 40 * 2352

    vuelta = formats.convert(bin_cue["cue"], "iso")
    assert open(vuelta["out"], "rb").read() == original


def test_el_chd_necesita_el_chdman(tmp_path):
    """Sin chdman se explica, no se finge que ha salido bien."""
    if formats.chdman_disponible():
        return
    iso = _iso_de_prueba(tmp_path)
    try:
        formats.convert(str(iso), "chd")
    except ValueError as exc:
        assert "chdman" in str(exc)
    else:
        raise AssertionError("deberia haber fallado sin chdman")


def test_el_chd_distingue_los_dos_tipos_de_sector():
    """Un CHD de ISO y otro de BIN/CUE guardan los sectores distinto.

    El que viene de un BIN/CUE lleva el sector entero (sincronizacion y
    cabecera); el que viene de un ISO guarda los 2.048 bytes de datos sin
    cabecera. Hay que saber cual de los dos es para no leer basura.
    """
    # Modo 2352: cada unidad lleva sus 12 bytes de sincronizacion y los 4
    # de cabecera delante de los datos.
    unidades = b""
    for i in range(20):
        unidad = bytearray(2448)
        if i == 16:
            unidad[16] = 1
            unidad[17:22] = b"CD001"
        unidades += bytes(unidad)
    assert formats._chd_modo(unidades, 2448) == 16

    # Modo 2048: los datos van seguidos, y detras viene el relleno.
    unidades = b""
    for i in range(20):
        unidad = bytearray(2448)
        if i == 16:
            unidad[0] = 1
            unidad[1:6] = b"CD001"
        unidades += bytes(unidad)
    assert formats._chd_modo(unidades, 2448) == 0


def test_el_indice_compacto_se_guarda_y_se_vuelve_a_leer(tmp_path):
    """En disco el indice guarda la posicion del juego; al leerlo, el juego.

    Si guardara el juego entero en cada hash, el indice de un DAT grande
    ocuparia gigabytes: el de Super Nintendo pesa mas de 800 KB y tiene
    miles de juegos.
    """
    juegos = [
        {"name": "Juego (USA)", "description": "Juego (USA)",
         "cloneof": "", "region": "USA", "serial": "SLUS-00001",
         "roms": [{"name": "Juego (USA).bin", "size": 1234, "crc": "ABCDEF12",
                   "md5": "0" * 32, "sha1": "1" * 40, "serial": ""}]},
        {"name": "Otro (Europa)", "description": "Otro (Europa)",
         "cloneof": "", "region": "Europe", "serial": "SLES-00002",
         "roms": [{"name": "Otro (Europa).bin", "size": 4321, "crc": "12345678",
                   "md5": "2" * 32, "sha1": "3" * 40, "serial": ""}]},
    ]
    compacto = dats.build_index_compacto(juegos)
    # En el indice compacto lo que se guarda es la posicion del juego.
    assert compacto["by_hash"]["crc32:ABCDEF12"] == 0
    clave = next(iter(compacto["by_name_size"]))
    assert compacto["by_name_size"][clave] == 1234

    meta = {"system": "prueba", "games": len(juegos),
            "juegos": compacto["juegos"],
            "by_hash": compacto["by_hash"],
            "by_serial": compacto["by_serial"],
            "by_name": compacto["by_name"],
            "by_name_size": compacto["by_name_size"],
            "by_title": compacto["by_title"]}
    (tmp_path / "prueba.json").write_text(json.dumps(meta), encoding="utf-8")

    indice = dats.load_index("prueba", str(tmp_path))

    assert indice["by_hash"]["crc32:ABCDEF12"]["name"] == "Juego (USA)"
    assert indice["by_serial"]["SLES-00002"]["name"] == "Otro (Europa)"
    assert indice["by_name_size"][clave] == 1234
    titulo = next(iter(indice["by_title"]))
    assert indice["by_title"][titulo][0]["name"] == "Juego (USA)"


def test_los_metadatos_del_dat_no_viven_en_el_indice(tmp_path):
    """El estado de los DAT se lee sin cargar el indice.

    El indice puede pesar varios megas (el de un DAT grande tiene la lista
    de juegos); leerlo entero en cada consulta se comería la memoria de la
    consola. Los metadatos van en su propio fichero.
    """
    indice = {"juegos": [{"name": "Juego " * 40} for _ in range(200)],
              "by_hash": {"sha1:" + "a" * 40: 0}}
    (tmp_path / "prueba.json").write_text(json.dumps(indice), encoding="utf-8")
    (tmp_path / "prueba.dat").write_bytes(b"clrmamepro (\n)")
    (tmp_path / "prueba.meta.json").write_text(
        json.dumps({"system": "prueba", "source": "libretro-no-intro",
                    "dat": "Nintendo - Prueba", "games": 200}),
        encoding="utf-8")

    ficheros = dats.dat_files(str(tmp_path))

    assert len(ficheros) == 1
    assert ficheros[0]["system"] == "prueba"
    assert ficheros[0]["games"] == 200
    assert ficheros[0]["dat"] == "Nintendo - Prueba"


def test_un_dat_sin_metadatos_sigue_visto(tmp_path):
    """Un DAT instalado antes de la separacion se lee igual."""
    (tmp_path / "prueba.json").write_text(
        json.dumps({"system": "prueba", "source": "libretro-no-intro",
                    "dat": "Nintendo - Prueba", "games": 7,
                    "by_hash": {}}), encoding="utf-8")
    (tmp_path / "prueba.dat").write_bytes(b"clrmamepro (\n)")

    ficheros = dats.dat_files(str(tmp_path))

    assert ficheros[0]["games"] == 7
    assert ficheros[0]["dat"] == "Nintendo - Prueba"


# ── El gamelist.xml se actualiza al renombrar ───────────────────────────

GAMELIST = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game id="1">
        <path>./Clay Fighter.smd</path>
        <name>Clay Fighter</name>
        <desc>Un parque de atracciones</desc>
        <image>./images/Clay Fighter-image.png</image>
        <marquee>./images/Clay Fighter-marquee.png</marquee>
        <video>./videos/Clay Fighter-video.mp4</video>
        <genre>Lucha</genre>
    </game>
</gameList>
"""


def _sistema_con_media(tmp_path):
    """Una carpeta de sistema con una ROM, su media y su gamelist."""
    (tmp_path / "images").mkdir()
    (tmp_path / "videos").mkdir()
    (tmp_path / "Clay Fighter.smd").write_bytes(b"ROM")
    (tmp_path / "images" / "Clay Fighter-image.png").write_bytes(b"PNG")
    (tmp_path / "images" / "Clay Fighter-marquee.png").write_bytes(b"PNG")
    (tmp_path / "videos" / "Clay Fighter-video.mp4").write_bytes(b"MP4")
    # Una imagen de otro juego que empieza igual: no se debe tocar.
    (tmp_path / "images" / "Clay Fighter 2-image.png").write_bytes(b"PNG")
    (tmp_path / "gamelist.xml").write_text(GAMELIST, encoding="utf-8")
    return tmp_path


def test_el_renombrado_actualiza_el_gamelist_y_la_media(tmp_path):
    """Al renombrar, la ficha y las imagenes siguen al juego.

    Sin esto, EmulationStation se queda con las fichas de los ficheros
    viejos: la imagen aparece pero sin su juego, y el nombre que sale en la
    TV es el anterior.
    """
    carpeta = _sistema_con_media(tmp_path)
    plan = {"items": [{"file": "Clay Fighter.smd",
                       "proposed": "Clay Fighter (Europe).smd",
                       "action": "renombrar", "companions": []}]}

    salida = rename.apply_plan(plan, str(carpeta), root=str(tmp_path / "journal"))

    assert salida["ok"] is True
    assert (carpeta / "Clay Fighter (Europe).smd").exists()
    assert (carpeta / "images" / "Clay Fighter (Europe)-image.png").exists()
    assert (carpeta / "images" / "Clay Fighter (Europe)-marquee.png").exists()
    assert (carpeta / "videos" / "Clay Fighter (Europe)-video.mp4").exists()
    # La imagen de otro juego no se toca.
    assert (carpeta / "images" / "Clay Fighter 2-image.png").exists()

    gamelist = (carpeta / "gamelist.xml").read_text(encoding="utf-8")
    assert "<path>./Clay Fighter (Europe).smd</path>" in gamelist
    assert "<image>./images/Clay Fighter (Europe)-image.png</image>" in gamelist
    assert "<marquee>./images/Clay Fighter (Europe)-marquee.png</marquee>" in gamelist
    assert "<video>./videos/Clay Fighter (Europe)-video.mp4</video>" in gamelist
    # Los metadatos se conservan.
    assert "<desc>Un parque de atracciones</desc>" in gamelist
    assert "<genre>Lucha</genre>" in gamelist
    assert "<name>Clay Fighter</name>" in gamelist


def test_deshacer_el_renombrado_deja_el_gamelist_como_estaba(tmp_path):
    """Deshacer devuelve los nombres, la media y el gamelist."""
    carpeta = _sistema_con_media(tmp_path)
    plan = {"items": [{"file": "Clay Fighter.smd",
                       "proposed": "Clay Fighter (Europe).smd",
                       "action": "renombrar", "companions": []}]}
    rename.apply_plan(plan, str(carpeta), root=str(tmp_path / "journal"))

    salida = rename.undo_last(root=str(tmp_path / "journal"))

    assert salida["ok"] is True
    assert (carpeta / "Clay Fighter.smd").exists()
    assert (carpeta / "images" / "Clay Fighter-image.png").exists()
    assert (carpeta / "gamelist.xml").read_text(encoding="utf-8") == GAMELIST


# ── Los discos de Wii: el codigo de juego cruza con el DAT ────────────────

#: El DAT de Wii de Redump: el codigo de juego va en el serial.
WII_DAT = [
    {"name": "Excite Truck (USA)", "description": "Excite Truck (USA)",
     "serial": "RVL-REXE-USA", "region": "USA",
     "roms": [{"name": "Excite Truck (USA).iso", "size": 4699979776,
               "crc": "762F0503", "md5": "214B54C48427CE47C183E83195DBFCDE",
               "sha1": "43724FDD3F0DBDBF23DCAD2B3036749B53DE173B"}]},
    {"name": "Excite Truck (Europe)", "description": "Excite Truck (Europe)",
     "serial": "RVL-REXP-EUR", "region": "Europe",
     "roms": [{"name": "Excite Truck (Europe).iso", "size": 4699979776,
               "crc": "D9D64AFF", "md5": "844E3F34AFF950F7919259D7FDB2E986",
               "sha1": "D9C2DE6B049BD756FDC553DF0972EF52AE901D0F"}]},
]

#: El MD5 que lleva el propio juego dentro del volcado.
WII_MD5 = "5fd682d8ef74b90f8d538f92a75318a1"


def _wbfs(codigo="REXP01", titulo="Excite Truck"):
    """Un volcado de Wii con la informacion del disco, como la lleva el WBFS."""
    head = bytearray(0x400)
    head[0:4] = b"WBFS"
    head[4:8] = (1212416).to_bytes(4, "big")
    base = 0x200
    head[base:base + 6] = codigo.encode("ascii")
    head[base + 0x1C:base + 0x20] = bytes.fromhex("5d1c9ea3")
    head[base + 0x20:base + 0x20 + len(titulo)] = titulo.encode("ascii")
    head[base + 0xEC:base + 0xF0] = b"MD5#"
    head[base + 0xF0:base + 0x100] = bytes.fromhex(WII_MD5)
    return bytes(head) + b"\x00" * 8192


def test_el_volcado_de_wii_dice_su_codigo_de_juego(tmp_path):
    """Del WBFS se leen el codigo de juego, el MD5 del juego y el titulo."""
    wad = tmp_path / "REXP01.wbfs"
    wad.write_bytes(_wbfs())

    disco = identify.wii_disc_info(str(wad))

    assert disco is not None
    assert disco.game_code == "REXP"
    assert disco.maker_code == "01"
    assert disco.md5 == WII_MD5
    assert disco.title == "Excite Truck"
    # La region va en el ultimo caracter del codigo de juego.
    assert disco.region == "EUROPE"


def test_un_fichero_normal_no_tiene_informacion_de_disco(tmp_path):
    """Lo que no es un disco de Wii no se inventa informacion."""
    rom = tmp_path / "Juego.smd"
    rom.write_bytes(b"ROM")

    assert identify.wii_disc_info(str(rom)) is None


def test_el_indice_del_dat_guarda_el_codigo_de_juego():
    """El codigo de juego es la clave con la que el DAT identifica un disco."""
    indice = dats.build_index(WII_DAT)

    assert "REXP" in indice["by_gamecode"]
    assert indice["by_gamecode"]["REXP"][0]["name"] == "Excite Truck (Europe)"


def test_el_volcado_de_wii_se_identifica_por_el_codigo(tmp_path):
    """El nombre del fichero no dice nada, pero el codigo de dentro si."""
    wad = tmp_path / "REXP01.wbfs"
    wad.write_bytes(_wbfs())
    indice = dats.build_index(WII_DAT)

    match = identify.identify(str(wad), indice, hash_allowed=False)

    assert match.method == "gamecode"
    assert match.entry["name"] == "Excite Truck (Europe)"
    assert match.confidence >= 0.95
    # El cruce enseña los dos lados: el hash del juego y el del DAT.
    assert match.signature["wii"]["game_code"] == "REXP"
    assert match.signature["wii"]["md5"] == WII_MD5


def test_el_plan_de_wii_renombra_la_carpeta_del_juego(tmp_path):
    """En Wii el juego es una carpeta: lo que se renombra es la carpeta."""
    carpeta = tmp_path / "Excite Truck [REXP01]"
    carpeta.mkdir()
    (carpeta / "REXP01.wbfs").write_bytes(_wbfs())
    indice = dats.build_index(WII_DAT)

    plan = rename.plan_rename(
        [{"path": str(carpeta / "REXP01.wbfs"),
          "carpeta": "Excite Truck [REXP01]", "ext": ""}], indice)

    assert len(plan["items"]) == 1
    item = plan["items"][0]
    assert item["action"] == "renombrar"
    assert item["method"] == "gamecode"
    assert item["current"] == "Excite Truck [REXP01]"
    # La carpeta conserva el sufijo con el codigo del disco.
    assert item["proposed"] == "Excite Truck (Europe) [REXP01]"
    # El cruce se enseña con los hashes de los dos lados.
    assert item["hashes"]["archivo"]["game_code"] == "REXP"
    assert item["hashes"]["dat"]["crc"] == "D9D64AFF"


def test_el_indice_guardado_conserva_el_codigo_de_juego(tmp_path):
    """El cruce por codigo sobrevive al viaje del indice por disco."""
    compacto = dats.build_index_compacto(WII_DAT)
    indice = {"juegos": compacto["juegos"], "by_hash": compacto["by_hash"],
              "by_serial": compacto["by_serial"], "by_name": compacto["by_name"],
              "by_name_size": compacto["by_name_size"],
              "by_title": compacto["by_title"],
              "by_gamecode": compacto["by_gamecode"]}
    (tmp_path / "wii.json").write_text(json.dumps(indice), encoding="utf-8")

    cargado = dats.load_index("wii", str(tmp_path))

    assert "REXP" in cargado["by_gamecode"]
    assert cargado["by_gamecode"]["REXP"][0]["name"] == "Excite Truck (Europe)"


def test_al_renombrar_wii_se_actualiza_el_gamelist(tmp_path):
    """La ruta del gamelist lleva la carpeta, asi que tambien se actualiza."""
    base = tmp_path / "wii"
    carpeta = base / "Excite Truck [REXP01]"
    carpeta.mkdir(parents=True)
    (carpeta / "REXP01.wbfs").write_bytes(_wbfs())
    (base / "images").mkdir()
    (base / "images" / "REXP01-image.png").write_bytes(b"PNG")
    (base / "gamelist.xml").write_text(
        '''<?xml version="1.0"?>
<gameList>
    <game id="1">
        <path>./Excite Truck [REXP01]/REXP01.wbfs</path>
        <name>Excite Truck</name>
        <image>./images/REXP01-image.png</image>
        <genre>Conduccion</genre>
    </game>
</gameList>
''', encoding="utf-8")
    indice = dats.build_index(WII_DAT)
    plan = rename.plan_rename(
        [{"path": str(carpeta / "REXP01.wbfs"),
          "carpeta": "Excite Truck [REXP01]", "ext": ""}], indice)

    salida = rename.apply_plan(plan, str(base), root=str(tmp_path / "journal"))

    assert salida["ok"] is True
    # Se renombra la carpeta y el volcado se queda dentro con su nombre.
    assert (base / "Excite Truck (Europe) [REXP01]" / "REXP01.wbfs").exists()
    gamelist = (base / "gamelist.xml").read_text(encoding="utf-8")
    assert "<path>./Excite Truck (Europe) [REXP01]/REXP01.wbfs</path>" in gamelist
    # La media va con el codigo del disco: no se toca.
    assert (base / "images" / "REXP01-image.png").exists()
    assert "<genre>Conduccion</genre>" in gamelist

    deshacer = rename.undo_last(root=str(tmp_path / "journal"))
    assert deshacer["ok"] is True
    assert (base / "Excite Truck [REXP01]" / "REXP01.wbfs").exists()
    assert "<path>./Excite Truck [REXP01]/REXP01.wbfs</path>" in \
        (base / "gamelist.xml").read_text(encoding="utf-8")


def test_sin_gamelist_no_pasa_nada(tmp_path):
    """Un sistema sin gamelist.xml se renombra igual, sin que se queje."""
    (tmp_path / "Juego.smd").write_bytes(b"ROM")
    plan = {"items": [{"file": "Juego.smd", "proposed": "Juego (USA).smd",
                       "action": "renombrar", "companions": []}]}

    salida = rename.apply_plan(plan, str(tmp_path), root=str(tmp_path / "journal"))

    assert salida["ok"] is True
    assert (tmp_path / "Juego (USA).smd").exists()


# ── El progreso del plan de renombrado ────────────────────────────────────

def test_el_progreso_avanza_por_bytes():
    """Dentro de un fichero, la barra se mueve por bytes leidos."""
    prog = progress.Progress(4, "identificando los ficheros")

    prog.empezar("Juego.iso", 100, hechos=0)
    prog.leidos(25)
    assert prog.estado()["porcentaje"] == 6   # la cuarta parte de un fichero

    prog.leidos(75)
    assert prog.estado()["porcentaje"] == 25  # el fichero entero

    prog.completar()
    estado = prog.estado()
    assert estado["porcentaje"] == 100
    assert estado["terminado"] is True


def test_el_plan_avisa_del_progreso(tmp_path):
    """El plan va contando los ficheros que lleva revisados."""
    (tmp_path / "Juego (USA).smd").write_bytes(b"ROM")
    (tmp_path / "Otro (USA).smd").write_bytes(b"ROM")
    indice = {"by_name": {}, "by_hash": {}, "by_serial": {}, "by_title": {}}
    estados = []

    plan = rename.plan_rename([str(tmp_path / "Juego (USA).smd"),
                                str(tmp_path / "Otro (USA).smd")],
                               indice, progreso=estados.append)

    assert len(plan["items"]) == 2
    assert estados, "el plan tiene que avisar del progreso"
    assert estados[0]["total"] == 2, "el total se sabe antes de empezar"
    assert estados[-1]["porcentaje"] == 100
    assert estados[-1]["total"] == 2
    assert estados[-1]["terminado"] is True
    # Se ve que fichero se esta mirando.
    assert any(e["actual"] == "Juego (USA).smd" for e in estados)


def test_el_plan_mueve_la_barra_mientras_hashea(tmp_path):
    """Dentro de un fichero grande hay estados intermedios."""
    rom = tmp_path / "Juego desconocido.iso"
    rom.write_bytes(b"x" * (3 * 1024 * 1024))
    indice = {"by_name": {}, "by_hash": {}, "by_serial": {}, "by_title": {}}
    estados = []

    rename.plan_rename([str(rom)], indice, progreso=estados.append)

    intermedios = [e for e in estados if 0 < e["porcentaje"] < 100]
    assert intermedios, "la barra tiene que moverse mientras se hashea"


def test_el_trabajo_devuelve_el_resultado():
    """Un trabajo en segundo plano acaba con su resultado."""
    registro = jobs.Jobs()

    trabajo = registro.lanzar("plan", lambda job: {"ok": True, "items": []})
    for _ in range(300):
        if trabajo.estado != "trabajando":
            break
        time.sleep(0.01)

    assert trabajo.estado == "listo"
    estado = trabajo.as_dict()
    assert estado["ok"] is True
    assert estado["resultado"]["items"] == []
    assert estado["porcentaje"] == 100


def test_el_trabajo_que_falla_lo_dice():
    """Si el trabajo revienta, se dice por que."""
    registro = jobs.Jobs()

    def revienta(job):
        raise RuntimeError("se ha roto")

    trabajo = registro.lanzar("plan", revienta)
    for _ in range(300):
        if trabajo.estado != "trabajando":
            break
        time.sleep(0.01)

    assert trabajo.estado == "error"
    assert "se ha roto" in trabajo.as_dict()["error"]


def test_el_trabajo_guarda_el_progreso():
    """El trabajo va guardando el progreso que le pasa el calculo."""
    registro = jobs.Jobs()
    vistos = []

    def tarea(job):
        job.progreso({"hechos": 3, "total": 10, "porcentaje": 30,
                      "actual": "Juego.iso", "mensaje": "identificando"})
        vistos.append(job.as_dict())
        return {"ok": True}

    trabajo = registro.lanzar("plan", tarea)
    for _ in range(300):
        if trabajo.estado != "trabajando":
            break
        time.sleep(0.01)

    assert trabajo.estado == "listo"
    assert vistos, "el trabajo tiene que guardar el progreso"
    assert vistos[0]["hechos"] == 3
    assert vistos[0]["total"] == 10
    assert vistos[0]["porcentaje"] == 30
    assert vistos[0]["actual"] == "Juego.iso"
