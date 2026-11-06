"""Tests del filtrado de ficheros que no son juegos.

En cada carpeta de ROMs de Batocera conviven los juegos con ficheros que no
lo son: el `_info.txt` que documenta los formatos del sistema, el
`gamelist.xml`, los guardados de estado (`Lagoon (Europe).srm`) y los ficheros
de datos de los emuladores (`azumanga.dat`). Esos no se pueden escrapear y no
deben salir en la lista de ROMs.

El criterio es el de EmulationStation: un fichero es un juego si su extension
es una de las del sistema (`es_systems.cfg`), mas la lista global de
extensiones de ROM para no perder los juegos con una extension que el
catalogo no liste.
"""
from __future__ import annotations

ES_SYSTEMS = """<?xml version="1.0" encoding="UTF-8"?>
<systemList>
    <system>
        <name>snes</name>
        <extension>.sfc .smc .zip</extension>
    </system>
    <system>
        <name>steam</name>
        <extension>.steam .sh</extension>
    </system>
    <system>
        <name>scummvm</name>
        <extension>.scummvm .squashfs</extension>
    </system>
    <system>
        <name>naomi</name>
        <extension>.lst .bin .dat .zip .7z</extension>
    </system>
    <system>
        <name>switch</name>
        <extension>.xci .nsp .xci_config</extension>
    </system>
</systemList>
"""


def _cfg(tmp_path):
    p = tmp_path / "es_systems.cfg"
    p.write_text(ES_SYSTEMS, encoding="utf-8")
    return p


def _settings(appmod, tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "ES_SYSTEMS_CFG", _cfg(tmp_path))
    return {"roms_base": str(tmp_path / "roms"),
            "es_cfg_dir": str(tmp_path / "no-existe")}


def _contar(appmod, settings):
    """Cuenta los juegos del disco con la caché limpia (es global)."""
    appmod._disk_games_cache.update({"ts": 0, "data": {"games": 0, "systems": 0}})
    return appmod.count_disk_games(settings)


# ── El criterio ────────────────────────────────────────────────────────

def test_el_info_txt_no_es_un_juego(appmod, tmp_path, monkeypatch):
    exts = appmod.system_game_extensions("snes", _settings(appmod, tmp_path, monkeypatch))
    assert appmod.is_game_file("_info.txt", exts) is False
    assert appmod.is_game_file("gamelist.xml", exts) is False


def test_los_guardados_de_estado_no_son_juegos(appmod, tmp_path, monkeypatch):
    exts = appmod.system_game_extensions("snes", _settings(appmod, tmp_path, monkeypatch))
    for nombre in ("Lagoon (Europe).srm", "Lagoon (Europe).sav",
                   "Lagoon (Europe).state", "azumanga.dat", "autosave.autosave"):
        assert appmod.is_game_file(nombre, exts) is False, nombre


def test_un_rom_si_es_un_juego(appmod, tmp_path, monkeypatch):
    exts = appmod.system_game_extensions("snes", _settings(appmod, tmp_path, monkeypatch))
    assert appmod.is_game_file("Super Mario World.sfc", exts) is True
    assert appmod.is_game_file("Super Mario World.zip", exts) is True


def test_las_extensiones_del_sistema_entran_en_el_criterio(appmod, tmp_path, monkeypatch):
    """Un juego de Steam es un `.steam` o un `.sh`: lo dice su es_systems.cfg."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    exts = appmod.system_game_extensions("steam", settings)
    assert appmod.is_game_file("Half-Life 2.steam", exts) is True
    assert appmod.is_game_file("Steam_Big_Picture.sh", exts) is True
    assert appmod.is_game_file("Steam_Big_Picture.sh.keys", exts) is False


def test_el_dat_de_naomi_es_el_juego(appmod, tmp_path, monkeypatch):
    """En naomi, atomiswave o systemsp el `.dat` es el juego, no un guardado."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    exts = appmod.system_game_extensions("naomi", settings)
    assert appmod.is_game_file("Marvel vs Capcom 2.dat", exts) is True


def test_el_dat_de_snes_no_es_un_juego(appmod, tmp_path, monkeypatch):
    """El mismo `.dat` en un sistema que no lo declara es un fichero de datos."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    exts = appmod.system_game_extensions("snes", settings)
    assert appmod.is_game_file("azumanga.dat", exts) is False


def test_el_xci_config_nunca_es_un_juego(appmod, tmp_path, monkeypatch):
    """Los `*_config.xci_config` son la configuracion del emulador."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    exts = appmod.system_game_extensions("switch", settings)
    assert appmod.is_game_file("citron_config.xci_config", exts) is False
    assert appmod.is_game_file("eden_config.xci_config", exts) is False
    assert appmod.is_game_file("Mario Kart.xci", exts) is True


# ── El listado de una carpeta ──────────────────────────────────────────

def test_la_lista_de_roms_no_muestra_los_ficheros_que_no_son_juegos(appmod, tmp_path, monkeypatch):
    settings = _settings(appmod, tmp_path, monkeypatch)
    sistema = tmp_path / "roms" / "snes"
    sistema.mkdir(parents=True)
    (sistema / "Super Mario World.sfc").write_bytes(b"x")
    (sistema / "_info.txt").write_text("x", encoding="utf-8")
    (sistema / "gamelist.xml").write_text("<gameList/>", encoding="utf-8")
    (sistema / "Lagoon (Europe).srm").write_bytes(b"x")
    (sistema / "media").mkdir()

    folder = appmod.list_rom_folder(settings, "snes")

    nombres = [i["filename"] for i in folder["items"]]
    assert nombres == ["Super Mario World.sfc"], nombres


def test_el_conteo_por_sistema_solo_cuenta_juegos(appmod, tmp_path, monkeypatch):
    settings = _settings(appmod, tmp_path, monkeypatch)
    sistema = tmp_path / "roms" / "snes"
    sistema.mkdir(parents=True)
    (sistema / "Super Mario World.sfc").write_bytes(b"x")
    (sistema / "Lagoon (Europe).srm").write_bytes(b"x")
    (sistema / "_info.txt").write_text("x", encoding="utf-8")

    sistemas = appmod.get_rom_systems(settings)
    snes = [s for s in sistemas if s["name"] == "snes"][0]

    assert snes["rom_count"] == 1, "el guardado de estado no es un juego"


def test_count_rom_systems_ignora_los_ficheros_que_no_son_juegos(appmod, tmp_path, monkeypatch):
    settings = _settings(appmod, tmp_path, monkeypatch)
    sistema = tmp_path / "roms" / "snes"
    sistema.mkdir(parents=True)
    (sistema / "_info.txt").write_text("x", encoding="utf-8")
    (sistema / "Lagoon (Europe).srm").write_bytes(b"x")

    assert appmod.count_rom_systems(settings) == 0


# ── El recuento real del disco ─────────────────────────────────────────

def test_count_disk_games_cuenta_los_juegos_de_verdad(appmod, tmp_path, monkeypatch):
    """El total del panel es el nº de juegos del disco, no el del gamelist."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    base = tmp_path / "roms"
    snes = base / "snes"
    snes.mkdir(parents=True)
    (snes / "a.sfc").write_bytes(b"x")
    (snes / "b.sfc").write_bytes(b"x")
    (snes / "c.srm").write_bytes(b"x")
    (snes / "_info.txt").write_text("x", encoding="utf-8")
    # Un sistema con un juego en carpeta (ScummVM) cuenta como un juego.
    scummvm = base / "scummvm"
    scummvm.mkdir(parents=True)
    (scummvm / "Myst.scummvm").mkdir()

    datos = _contar(appmod, settings)

    assert datos["games"] == 3, "dos ROMs de SNES y un juego en carpeta"
    assert datos["systems"] == 2


def test_count_disk_games_cuenta_las_carpetas_de_juegos(appmod, tmp_path, monkeypatch):
    """Los ports guardan el juego en una subcarpeta: cuenta como una entrada."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    ports = tmp_path / "roms" / "ports"
    ports.mkdir(parents=True)
    (ports / "iortcw").mkdir()
    (ports / "iortcw" / "main").mkdir()

    datos = _contar(appmod, settings)

    assert datos["games"] == 1
    assert datos["systems"] == 1


# ── El juego al azar ───────────────────────────────────────────────────

def test_el_juego_al_azar_puede_ser_una_carpeta(appmod, tmp_path, monkeypatch):
    """En ScummVM el juego es una carpeta: también puede salir en la tarjeta."""
    settings = _settings(appmod, tmp_path, monkeypatch)
    scummvm = tmp_path / "roms" / "scummvm"
    scummvm.mkdir(parents=True)
    (scummvm / "Myst.scummvm").mkdir()
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    juego = appmod.pick_random_game(settings)

    assert juego is not None
    assert juego["system"] == "scummvm"
    assert juego["filename"] == "Myst.scummvm"
    assert juego["name"] == "Myst"


def test_el_juego_al_azar_ignora_los_ficheros_que_no_son_juegos(appmod, tmp_path, monkeypatch):
    settings = _settings(appmod, tmp_path, monkeypatch)
    snes = tmp_path / "roms" / "snes"
    snes.mkdir(parents=True)
    (snes / "Lagoon (Europe).srm").write_bytes(b"x")
    (snes / "_info.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])

    assert appmod.pick_random_game(settings) is None
