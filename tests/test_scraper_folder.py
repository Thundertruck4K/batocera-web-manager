"""Tests del listado de ROMs que usa la sección de Scraper de la SPA.

La pantalla de un sistema reparte sus ROMs en «Media presente» y «Media
ausente». Ese reparto sale del campo `has_image` de `list_rom_folder`, que a
su vez lo lee del `<image>` del gamelist.xml del sistema.
"""
from __future__ import annotations

GAMELIST = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game>
        <path>./Juego con imagen.sfc</path>
        <name>Juego con imagen</name>
        <image>./images/Juego con imagen-image.png</image>
        <genre>Plataformas</genre>
        <publisher>Nintendo</publisher>
        <releasedate>1991T000000</releasedate>
    </game>
</gameList>
"""


def _preparar(appmod, tmp_path):
    """Crea un sistema con dos ROMs (una con imagen y otra sin) y una subcarpeta."""
    base = tmp_path / "roms"
    sistema = base / "snes"
    sistema.mkdir(parents=True)
    (sistema / "Juego con imagen.sfc").write_bytes(b"rom1")
    (sistema / "Juego sin imagen.sfc").write_bytes(b"rom2")
    (sistema / "gamelist.xml").write_text(GAMELIST, encoding="utf-8")
    sub = sistema / "Coleccion"
    sub.mkdir()
    (sub / "Juego de la coleccion.sfc").write_bytes(b"rom3")
    return {"roms_base": str(base)}


def test_el_listado_marca_el_rom_con_imagen(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    folder = appmod.list_rom_folder(settings, "snes")

    assert folder is not None
    por_nombre = {item["filename"]: item for item in folder["items"]}
    assert por_nombre["Juego con imagen.sfc"]["has_image"] is True
    assert por_nombre["Juego sin imagen.sfc"]["has_image"] is False


def test_el_listado_trae_los_metadatos_del_gamelist(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    folder = appmod.list_rom_folder(settings, "snes")

    por_nombre = {item["filename"]: item for item in folder["items"]}
    juego = por_nombre["Juego con imagen.sfc"]
    assert juego["genre"] == "Plataformas"
    assert juego["publisher"] == "Nintendo"
    assert juego["year"] == "1991"


def test_el_listado_informa_del_tamano_y_del_conteo(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    folder = appmod.list_rom_folder(settings, "snes")

    assert folder["system"] == "snes"
    assert folder["subpath"] == ""
    assert folder["breadcrumb"] == ["snes"]
    assert folder["item_count"] == len(folder["items"])
    assert folder["has_gamelist"] is True
    assert folder["is_empty"] is False
    roms = [item for item in folder["items"] if item["is_rom"]]
    assert len(roms) == 2
    assert all(item["size_human"] for item in roms)


def test_el_listado_marca_las_carpetas(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    folder = appmod.list_rom_folder(settings, "snes")

    carpetas = [item for item in folder["items"] if item["is_dir"]]
    assert len(carpetas) == 1
    assert carpetas[0]["filename"] == "Coleccion"


def test_el_listado_acepta_una_subcarpeta(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    folder = appmod.list_rom_folder(settings, "snes", "Coleccion")

    assert folder["subpath"] == "Coleccion"
    assert folder["breadcrumb"] == ["snes", "Coleccion"]
    assert [item["filename"] for item in folder["items"]] == ["Juego de la coleccion.sfc"]


def test_un_sistema_inexistente_no_devuelve_carpeta(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    assert appmod.list_rom_folder(settings, "no-existe") is None


def test_una_subruta_fuera_del_sistema_es_rechazada(appmod, tmp_path):
    settings = _preparar(appmod, tmp_path)

    assert appmod.list_rom_folder(settings, "snes", "../../etc") is None


# ── El guardado tiene que dar con la entrada correcta ────────────────

GAMELIST_DUPLICADO = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game>
        <path>./Juego/Juego.sfc</path>
        <name>Juego (subcarpeta)</name>
    </game>
    <game>
        <path>./Juego.sfc</path>
        <name>Juego (raíz)</name>
    </game>
</gameList>
"""


def test_el_guardado_usa_la_entrada_de_la_ruta_exacta(appmod, tmp_path):
    """El mismo juego puede estar en la raíz y en una subcarpeta.

    Si el guardado se casa con la primera entrada que coincide por nombre, la
    ROM de la raíz se queda sin datos y su imagen no aparece en la tabla.
    """
    base = tmp_path / "roms"
    sistema = base / "snes"
    sistema.mkdir(parents=True)
    (sistema / "gamelist.xml").write_text(GAMELIST_DUPLICADO, encoding="utf-8")

    appmod.save_gamelist_entry(str(base), {
        "system": "snes", "subpath": "", "filename": "Juego.sfc",
        "name": "Juego", "desc": "El de la raíz",
        "image_path": "./images/Juego-image.png",
    })

    gl = (sistema / "gamelist.xml").read_text(encoding="utf-8")
    entrada_raiz = gl[gl.index('<path>./Juego.sfc</path>'):]
    entrada_raiz = entrada_raiz[:entrada_raiz.index("</game>")]
    assert "El de la raíz" in entrada_raiz
    assert "./images/Juego-image.png" in entrada_raiz


def test_el_guardado_conserva_la_entrada_de_la_subcarpeta(appmod, tmp_path):
    base = tmp_path / "roms"
    sistema = base / "snes"
    (sistema / "Coleccion").mkdir(parents=True)
    (sistema / "gamelist.xml").write_text(GAMELIST_DUPLICADO, encoding="utf-8")

    appmod.save_gamelist_entry(str(base), {
        "system": "snes", "subpath": "Coleccion", "filename": "Juego.sfc",
        "name": "Juego", "desc": "El de la subcarpeta",
    })

    gl = (sistema / "gamelist.xml").read_text(encoding="utf-8")
    assert "El de la subcarpeta" in gl
    assert "El de la raíz" not in gl


def test_el_listado_usa_el_gamelist_del_sistema_en_una_subcarpeta(appmod, tmp_path):
    """En una subcarpeta sin gamelist propio se lee el de la raíz del sistema."""
    base = tmp_path / "roms"
    sistema = base / "snes"
    (sistema / "Coleccion").mkdir(parents=True)
    (sistema / "Coleccion" / "Juego de la coleccion.sfc").write_bytes(b"rom")
    (sistema / "gamelist.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game>
        <path>./Coleccion/Juego de la coleccion.sfc</path>
        <name>Juego de la coleccion</name>
        <image>./images/Juego de la coleccion-image.png</image>
    </game>
</gameList>
""", encoding="utf-8")

    folder = appmod.list_rom_folder({"roms_base": str(base)}, "snes", "Coleccion")

    assert folder["items"][0]["has_image"] is True
    assert folder["has_gamelist"] is True
