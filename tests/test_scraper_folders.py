"""Tests de los juegos que en Batocera son una carpeta.

EmulationStation (y por tanto Batocera) trata una carpeta como un juego
cuando su nombre lleva una extension del sistema: en ScummVM el juego es
`Myst.scummvm/`, en DOSBox `Alone in the Dark.pc/`. El gamelist.xml guarda
la ruta de esa carpeta (`<path>./Myst.scummvm</path>`), asi que el scraper
tiene que buscar por el nombre de la carpeta y no puede hashear nada.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

ES_SYSTEMS = """<?xml version="1.0" encoding="UTF-8"?>
<systemList>
    <system>
        <name>scummvm</name>
        <extension>.scummvm .squashfs</extension>
    </system>
    <system>
        <name>dos</name>
        <extension>.pc .dos .zip .dosz</extension>
    </system>
    <system>
        <name>snes</name>
        <extension>.sfc .smc</extension>
    </system>
</systemList>
"""

GAMELIST = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game>
        <path>./Myst.scummvm</path>
        <name>Grim Fandango</name>
        <desc>Juego de la carpeta</desc>
        <image>./media/images/Myst.png</image>
        <genre>Aventura</genre>
    </game>
</gameList>
"""


def _cfg(tmp_path):
    """Escribe un es_systems.cfg de prueba y devuelve su ruta."""
    p = tmp_path / "es_systems.cfg"
    p.write_text(ES_SYSTEMS, encoding="utf-8")
    return p


def _preparar(appmod, tmp_path, monkeypatch):
    """Sistema scummvm con un juego en carpeta y otro en un fichero."""
    base = tmp_path / "roms"
    sistema = base / "scummvm"
    sistema.mkdir(parents=True)
    # Juego en carpeta: la carpeta lleva la extension del sistema.
    juego = sistema / "Myst.scummvm"
    juego.mkdir()
    (juego / "myst.scummvm").write_text("scummvm \n", encoding="utf-8")
    (juego / "myst.dat").write_bytes(b"datos")
    # Carpeta que NO es un juego: se puede entrar dentro.
    varios = sistema / "Juegos varios"
    varios.mkdir()
    (varios / "otro.scummvm").write_text("x", encoding="utf-8")
    # Juego normal en fichero.
    (sistema / "Alone in the Dark.scummvm").write_text("x", encoding="utf-8")
    (sistema / "gamelist.xml").write_text(GAMELIST, encoding="utf-8")

    monkeypatch.setattr(appmod, "ES_SYSTEMS_CFG", _cfg(tmp_path))
    return {"roms_base": str(base)}


# ── Detección ──────────────────────────────────────────────────────────

def test_la_extension_del_sistema_se_saca_del_es_systems_cfg(appmod, tmp_path):
    cfg = _cfg(tmp_path)
    exts = appmod._es_systems_extensions(cfg)
    assert exts["scummvm"] == [".scummvm", ".squashfs"]
    assert exts["dos"] == [".pc", ".dos", ".zip", ".dosz"]


def test_residualvm_cuenta_como_extension_de_scummvm(appmod, tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(appmod, "ES_SYSTEMS_CFG", cfg)
    exts = appmod.game_folder_extensions("scummvm", {"es_cfg_dir": str(tmp_path / "no")})
    assert ".scummvm" in exts
    assert ".residualvm" in exts, "ResidualVM es la misma familia que ScummVM"


def test_una_carpeta_con_la_extension_del_sistema_es_un_juego(appmod, tmp_path):
    exts = {".scummvm"}
    juego = tmp_path / "Myst.scummvm"
    juego.mkdir()
    assert appmod.is_game_folder(juego, exts) is True


def test_una_carpeta_sin_extension_es_una_carpeta(appmod, tmp_path):
    exts = {".scummvm"}
    carpeta = tmp_path / "Juegos varios"
    carpeta.mkdir()
    (carpeta / "otro.scummvm").write_text("x", encoding="utf-8")
    assert appmod.is_game_folder(carpeta, exts) is False


def test_scummvm_se_reconoce_por_el_fichero_marcador(appmod, tmp_path):
    """La carpeta `grim.residualvm` lleva dentro su fichero `grim.residualvm`."""
    exts = {".scummvm", ".residualvm"}
    juego = tmp_path / "grim.residualvm"
    juego.mkdir()
    (juego / "grim.residualvm").write_text("x", encoding="utf-8")
    assert appmod.is_game_folder(juego, exts) is True


def test_el_nombre_de_busqueda_quita_la_extension(appmod):
    assert appmod.game_folder_search_name("Myst.scummvm", {".scummvm"}) == "Myst"
    assert appmod.game_folder_search_name("Alone in the Dark.pc", {".pc"}) == "Alone in the Dark"
    assert appmod.game_folder_search_name("Juego varios", {".scummvm"}) == "Juego varios"


# ── Listado ────────────────────────────────────────────────────────────

def test_el_listado_marca_la_carpeta_como_juego(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)

    folder = appmod.list_rom_folder(settings, "scummvm")

    assert folder is not None
    items = {item["filename"]: item for item in folder["items"]}
    juego = items["Myst.scummvm"]
    assert juego["is_game_folder"] is True
    assert juego["is_rom"] is True, "un juego en carpeta se escrapea como un ROM"
    assert juego["name"] == "Myst", "se muestra el nombre de la carpeta sin extension"
    assert items["Juegos varios"]["is_game_folder"] is False
    assert items["Juegos varios"]["is_rom"] is False


def test_la_carpeta_juego_toma_la_ficha_del_gamelist(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)

    folder = appmod.list_rom_folder(settings, "scummvm")

    items = {item["filename"]: item for item in folder["items"]}
    juego = items["Myst.scummvm"]
    assert juego["has_image"] is True
    assert juego["desc"] == "Juego de la carpeta"
    assert juego["genre"] == "Aventura"


# ── Búsqueda ───────────────────────────────────────────────────────────

def test_la_busqueda_de_una_carpeta_usa_el_nombre_de_la_carpeta(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)

    busqueda, rom_path, solo_nombre = appmod.scraper_search_target(
        settings, "scummvm", "", "Myst.scummvm")

    assert busqueda == "Myst", "se busca por el nombre de la carpeta"
    assert rom_path is None, "una carpeta no se puede hashear"
    assert solo_nombre is True


def test_un_rom_normal_se_sigue_hasheando(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)

    busqueda, rom_path, solo_nombre = appmod.scraper_search_target(
        settings, "scummvm", "", "Alone in the Dark.scummvm")

    assert busqueda == "Alone in the Dark.scummvm"
    assert rom_path and rom_path.endswith("Alone in the Dark.scummvm")
    assert solo_nombre is False


def test_un_nombre_editado_a_mano_se_busca_solo_por_nombre(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)

    busqueda, rom_path, solo_nombre = appmod.scraper_search_target(
        settings, "scummvm", "", "Grim Fandango")

    assert rom_path is None
    assert solo_nombre is True


def test_con_name_only_no_se_pide_el_juego_por_hash(appmod, monkeypatch):
    """Sin hash no se puede usar jeuInfos.php: se busca sólo por nombre."""
    urls = []

    def fake_fetch(url, timeout=20):
        urls.append(url)
        return None, "sin red", {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)
    appmod.ss_search_game("Myst", "scummvm", "usuario", "clave",
                          devid="devid_x", devpassword="devpass_x",
                          name_only=True)

    assert urls, "debe intentar al menos una petición"
    assert all("jeuInfos.php" not in u for u in urls), \
        "con name_only no se busca por hash"
    assert any("jeuRecherche.php" in u for u in urls), "se busca por nombre"


def test_la_cascada_propaga_el_modo_solo_nombre(appmod, monkeypatch):
    vistos = {}

    def fake_ss(*a, **k):
        vistos["name_only"] = k.get("name_only")
        vistos["rom_path"] = k.get("rom_path")
        return None, "Sin resultados", {}

    monkeypatch.setattr(appmod, "ss_search_game", fake_ss)
    monkeypatch.setattr(appmod, "source_has_creds", lambda *a, **k: True)
    appmod.scrape_search_cascade("Myst", "scummvm", {}, sources=["screenscraper"],
                                 rom_path=None, name_only=True)

    assert vistos["name_only"] is True
    assert vistos["rom_path"] is None


# ── Mapeo de plataformas ───────────────────────────────────────────────

def test_el_sistema_dos_esta_mapeado_en_screenscraper(appmod):
    """En ScreenScraper los juegos de DOS estan en la plataforma 135 ("PC Dos")."""
    assert appmod.SS_SYSTEMS["dos"] == 135
    assert appmod.SS_SYSTEMS["scummvm"] == 123


def test_sin_plataforma_la_busqueda_por_nombre_tarda_mas(appmod, monkeypatch):
    """Sin `systemeid` la consulta de ScreenScraper tarda mas de un minuto.

    Con 20 s de timeout se quedaba cortada y se perdia el resultado, asi que
    la busqueda por nombre necesita un margen mayor.
    """
    timeouts = {}

    def fake_fetch(url, timeout=20):
        timeouts["url"] = url
        timeouts["timeout"] = timeout
        return {"header": {"success": "true"},
                "response": {"jeux": [{"id": "1", "noms": [{"text": "Mugen"}]}]}}, None, {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)
    juego, err, _ = appmod.ss_search_game("Mugen", "mugen", "usuario", "clave",
                                          devid="devid_x", devpassword="devpass_x",
                                          name_only=True)

    assert juego is not None, err
    assert "jeuRecherche.php" in timeouts["url"], "sin hash solo se puede buscar por nombre"
    assert timeouts["timeout"] >= 60, \
        "la consulta sin platform id tarda mas de un minuto: 20 s noaban"
    assert appmod.SS_SEARCH_TIMEOUT_NAME >= 60


# ── Elección del juego correcto ────────────────────────────────────────

def _jeu_ss(nombre, sid):
    return {"id": sid, "noms": [{"region": "wor", "text": nombre}]}


def test_de_los_candidatos_se_elige_el_que_casa_con_el_nombre(appmod):
    """La busqueda de ScreenScraper es difusa: el primero no siempre es el bueno."""
    juegos = [_jeu_ss("Hugo III: Jungle of Doom", 1),
              _jeu_ss("Doom", 2),
              _jeu_ss("Doom II", 3)]
    elegido = appmod._ss_best_jeu(juegos, "Doom")
    assert elegido["id"] == 2, "debe ganar el juego que se llama igual"


def test_si_no_hay_coincidencia_exacta_se_queda_el_primero(appmod):
    juegos = [_jeu_ss("Hugo III: Jungle of Doom", 1), _jeu_ss("Doom II", 3)]
    elegido = appmod._ss_best_jeu(juegos, "Doom")
    assert elegido["id"] == 1, "sin coincidencia exacta manda el primero"


def test_la_comparacion_ignora_acentos_y_signos(appmod):
    juegos = [_jeu_ss("Pokemon: Red", 1), _jeu_ss("Pokémon", 2)]
    elegido = appmod._ss_best_jeu(juegos, "Pokemon")
    assert elegido["id"] == 2


# ── Scrape del sistema ─────────────────────────────────────────────────

def test_el_scrape_de_sistema_incluye_las_carpetas_juego(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)
    carpeta = tmp_path / "roms" / "scummvm" / "Myst.scummvm"

    monkeypatch.setattr(appmod, "get_rom_systems", lambda settings, fast=False: [{
        "name": "scummvm",
        "roms": [
            {"filename": "Myst.scummvm", "name": "Myst", "is_rom": True,
             "has_image": False, "ext": ".scummvm", "is_game_folder": True},
            {"filename": "Juegos varios", "name": "Juegos varios", "is_rom": True,
             "has_image": False, "ext": "dir"},
        ],
    }])
    monkeypatch.setattr(appmod, "save_gamelist_entry", lambda base, meta: None)
    monkeypatch.setattr(appmod, "ss_search_game",
                        lambda *a, **k: (None, "Sin resultados", {}))
    monkeypatch.setattr(appmod, "source_has_creds", lambda *a, **k: True)

    res = appmod.do_scrape_system(settings, "scummvm", "screenscraper",
                                  {"ss_user": "u", "ss_password": "p"}, {})

    assert res["total"] == 1, "solo se escrapea la carpeta que es un juego"


def test_el_scrape_de_sistema_busca_por_el_nombre_de_la_carpeta(appmod, tmp_path, monkeypatch):
    settings = _preparar(appmod, tmp_path, monkeypatch)
    vistos = {}

    def fake_ss(nombre, system, *a, **k):
        vistos["nombre"] = nombre
        vistos["name_only"] = k.get("name_only")
        vistos["rom_path"] = k.get("rom_path")
        return None, "Sin resultados", {}

    monkeypatch.setattr(appmod, "get_rom_systems", lambda settings, fast=False: [{
        "name": "scummvm",
        "roms": [{"filename": "Myst.scummvm", "name": "Myst", "is_rom": True,
                  "has_image": False, "ext": ".scummvm", "is_game_folder": True}],
    }])
    monkeypatch.setattr(appmod, "save_gamelist_entry", lambda base, meta: None)
    monkeypatch.setattr(appmod, "ss_search_game", fake_ss)
    monkeypatch.setattr(appmod, "source_has_creds", lambda *a, **k: True)

    appmod.do_scrape_system(settings, "scummvm", "screenscraper",
                            {"ss_user": "u", "ss_password": "p"}, {})

    assert vistos["nombre"] == "Myst", "se busca por el nombre de la carpeta"
    assert vistos["name_only"] is True
    assert vistos["rom_path"] is None


# ── Guardado en el gamelist ────────────────────────────────────────────

def test_la_carpeta_juego_se_guarda_con_la_ruta_de_la_carpeta(appmod, tmp_path):
    """El gamelist guarda la ruta de la carpeta, como hace Batocera."""
    base = tmp_path / "roms"
    sistema = base / "scummvm"
    sistema.mkdir(parents=True)
    (sistema / "Myst.scummvm").mkdir()

    appmod.save_gamelist_entry(str(base), {
        "system": "scummvm", "filename": "Myst.scummvm",
        "name": "Myst", "desc": "Aventura", "image_path": "media/images/Myst.png",
    })

    tree = ET.parse(sistema / "gamelist.xml")
    juego = tree.find(".//game")
    assert juego.findtext("path") == "./Myst.scummvm"
    assert juego.findtext("name") == "Myst"
    assert juego.findtext("image") == "media/images/Myst.png"
