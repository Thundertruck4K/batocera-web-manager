"""Tests del scraper de ScreenScraper: URL de la API y credenciales.

Bug de producción (2026-10-16): el scraping fallaba al 100%.
Causas raíz detectadas sobre el Batocera real:

1. `SS_API` apuntaba a `.../apiv2` -> HTTP 404 "File not found."
   (el endpoint correcto es `.../api2/jeuInfos.php`).
2. Las credenciales de desarrollador (`devid`/`devpassword`) nunca se
   rellenaban: `batocera.conf` no tiene esas claves y Batocera las incrusta
   en el binario de EmulationStation -> HTTP 403 "Vérifier vos identifiants
   développeur !".
3. `_scraper_save_config` sólo aceptaba claves `ss_*`, pero el front-end envía
   `global.scrapper.*` -> no se guardaba nada.
"""

import pytest


# ─── 1. URL base de la API ──────────────────────────────────────────

def test_ss_api_base_is_api2(appmod):
    """El host de ScreenScraper expone `api2`, no `apiv2` (404)."""
    assert appmod.SS_API == "https://api.screenscraper.fr/api2"


def test_ss_search_game_builds_urls_on_api2(appmod, monkeypatch):
    """`ss_search_game` debe pegar a /api2/..., nunca a /apiv2/..."""
    urls = []

    def fake_fetch(url, timeout=20):
        urls.append(url)
        return None, "sin red", {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)

    appmod.ss_search_game("Sonic (USA).zip", "genesis", "usuario", "clave",
                          devid="devid_x", devpassword="devpass_x")

    assert urls, "ss_search_game debe intentar al menos una petición"
    assert urls[0].startswith("https://api.screenscraper.fr/api2/jeuInfos.php")
    for u in urls:
        assert "apiv2" not in u


# ─── 2. Detección de credenciales de desarrollador ──────────────────

def test_detect_ss_dev_credentials_reads_es_binary(appmod, tmp_path):
    """Extrae devid/devpassword incrustados en el binario de EmulationStation."""
    binary = tmp_path / "emulationstation"
    binary.write_bytes(
        b"\x7fELF basura binaria \x00\x01"
        b"devid=testdevid123 devpassword=testdevpass456"
        b" mas basura \x00\xff"
    )

    devid, devpassword = appmod.detect_ss_dev_credentials(paths=[binary])

    assert devid == "testdevid123"
    assert devpassword == "testdevpass456"


def test_detect_ss_dev_credentials_without_markers(appmod, tmp_path):
    """Sin marcadores devuelve vacío (no inventa credenciales)."""
    binary = tmp_path / "emulationstation"
    binary.write_bytes(b"\x7fELF sin nada util")

    assert appmod.detect_ss_dev_credentials(paths=[binary]) == ("", "")


def test_detect_ss_dev_credentials_missing_file(appmod, tmp_path):
    """Un binario inexistente no debe lanzar excepción."""
    missing = tmp_path / "no-existe"

    assert appmod.detect_ss_dev_credentials(paths=[missing]) == ("", "")


# ─── 3. get_scraper_config rellena las credenciales ─────────────────

def test_get_scraper_config_fills_dev_creds_from_es_binary(appmod, tmp_path, monkeypatch):
    """Si batocera.conf no trae devid, se toma del binario de ES."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=pepe\n", encoding="utf-8")
    binary = tmp_path / "emulationstation"
    binary.write_bytes(b"devid=binid789 devpassword=binpass789")
    monkeypatch.setattr(appmod, "ES_BINARY_CANDIDATES", (str(binary),))

    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})

    assert cfg["ss_devid"] == "binid789"
    assert cfg["ss_devpassword"] == "binpass789"


def test_get_scraper_config_prefers_conf_dev_creds(appmod, tmp_path, monkeypatch):
    """Lo configurado a mano en batocera.conf gana al binario."""
    conf = tmp_path / "batocera.conf"
    conf.write_text(
        "global.scrapper.devid=confid\n"
        "global.scrapper.devpassword=confpass\n",
        encoding="utf-8",
    )
    binary = tmp_path / "emulationstation"
    binary.write_bytes(b"devid=binid789 devpassword=binpass789")
    monkeypatch.setattr(appmod, "ES_BINARY_CANDIDATES", (str(binary),))

    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})

    assert cfg["ss_devid"] == "confid"
    assert cfg["ss_devpassword"] == "confpass"


def test_get_scraper_config_reads_existing_user_creds(appmod, tmp_path):
    """Las credenciales de usuario de batocera.conf se leen intactas."""
    conf = tmp_path / "batocera.conf"
    conf.write_text(
        "global.scrapper.user=miusuario\n"
        "global.scrapper.password=miclave\n",
        encoding="utf-8",
    )

    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})

    assert cfg["ss_user"] == "miusuario"
    assert cfg["ss_password"] == "miclave"


def test_get_scraper_config_falls_back_to_official_dev_creds(appmod, tmp_path, monkeypatch):
    """Si no hay binario legible se usan las credenciales oficiales de Batocera."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    monkeypatch.setattr(appmod, "ES_BINARY_CANDIDATES", (str(tmp_path / "no-existe"),))

    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})

    assert cfg["ss_devid"] == appmod.SS_DEV_FALLBACK[0]
    assert cfg["ss_devpassword"] == appmod.SS_DEV_FALLBACK[1]


# ─── 4. Credenciales efectivas (servidor + cliente) ─────────────────

def test_resolve_scraper_creds_merges_client_over_server(appmod, tmp_path):
    """El cliente manda usuario/clave; el servidor aporta el devid detectado."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    binary = tmp_path / "emulationstation"
    binary.write_bytes(b"devid=serverid devpassword=serverpass")
    settings = {"batocera_conf": str(conf), "es_binary": str(binary)}

    creds = appmod.resolve_scraper_creds(settings, {
        "ss_user": "cliente", "ss_password": "clave",
    })

    assert creds["ss_user"] == "cliente"
    assert creds["ss_password"] == "clave"
    assert creds["ss_devid"] == "serverid"
    assert creds["ss_devpassword"] == "serverpass"


def test_resolve_scraper_creds_client_devid_wins(appmod, tmp_path):
    """Si el cliente envía su propio devid, tiene prioridad."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    binary = tmp_path / "emulationstation"
    binary.write_bytes(b"devid=serverid devpassword=serverpass")
    settings = {"batocera_conf": str(conf), "es_binary": str(binary)}

    creds = appmod.resolve_scraper_creds(settings, {"ss_devid": "mio"})

    assert creds["ss_devid"] == "mio"
    assert creds["ss_devpassword"] == "serverpass"


# ─── 5. Guardado de configuración en batocera.conf ──────────────────

def test_save_scraper_config_writes_global_scrapper_keys(appmod, tmp_path):
    """Las claves que envía el front-end (`global.scrapper.*`) deben guardarse."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=viejo\n", encoding="utf-8")

    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.user", "val": "nuevo"},
        {"key": "global.scrapper.devid", "val": "midevid"},
    ])

    assert ok, err
    text = conf.read_text(encoding="utf-8")
    assert "global.scrapper.user=nuevo" in text
    assert "global.scrapper.devid=midevid" in text
    assert "viejo" not in text
    assert text.count("global.scrapper.user=") == 1


def test_save_scraper_config_appends_missing_keys(appmod, tmp_path):
    """Una clave nueva se añade sin duplicar las existentes."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.lang=es\n", encoding="utf-8")

    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.region", "val": "eu"},
    ])

    assert ok
    text = conf.read_text(encoding="utf-8")
    assert "global.scrapper.lang=es" in text
    assert "global.scrapper.region=eu" in text


def test_save_scraper_config_ignores_unknown_keys(appmod, tmp_path):
    """Claves fuera de la lista blanca no se escriben."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")

    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.peligroso.clave", "val": "x"},
    ])

    assert ok
    assert "peligroso" not in conf.read_text(encoding="utf-8")


def test_save_scraper_config_rejects_conf_without_newline(appmod, tmp_path):
    """Un conf sin salto final no debe pegar la clave nueva a la última línea."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.lang=es", encoding="utf-8")

    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.region", "val": "eu"},
    ])

    assert ok
    lines = conf.read_text(encoding="utf-8").splitlines()
    assert "global.scrapper.region=eu" in lines


# ─── 6. Parseo de respuestas JSON de ScreenScraper ──────────────────

def test_ss_parse_json_valid_payload(appmod):
    """El parseador normal debe pasar JSON válido sin tocarlo."""
    payload = '{"response":{"jeu":{"romnom":"Sonic.zip","medias":[]}}}'

    data = appmod.ss_parse_json(payload)

    assert data["response"]["jeu"]["romnom"] == "Sonic.zip"


def test_ss_parse_json_tolerates_invalid_backslash_escape(appmod):
    """ScreenScraper devuelve `batocera\\_manager` en sus URLs: no es JSON válido.

    (Evidencia: payload real de 68.217 bytes, fallo `Invalid \\escape` en
    /api2/jeuInfos.php con softname=batocera_manager)."""
    payload = (
        '{"response":{"medias":[{"type":"mixrbv1",'
        '"url":"https://x/api2/mediaJeu.php?softname=batocera\\_manager&media=a"}]}}'
    )

    data = appmod.ss_parse_json(payload)

    assert data["response"]["medias"][0]["url"].endswith("batocera_manager&media=a")


def test_ss_parse_json_keeps_valid_escapes(appmod):
    """Los escapes legítimos no deben re-escaparse (\\n sigue siendo salto de línea)."""
    payload = '{"desc":"primera\\nsegunda","tab":"x\\ty"}'

    data = appmod.ss_parse_json(payload)

    assert data["desc"] == "primera\nsegunda"
    assert data["tab"] == "x\ty"


def test_ss_parse_json_invalid_escape_inside_nested_list(appmod):
    """El saneado aplica a todo el documento, también dentro de listas anidadas."""
    payload = (
        '{"jeux":[{"noms":[{"text":"Juego"}],'
        '"url":"https://x/?softname=batocera\\_manager"},{"romnom":"z"}]}'
    )

    data = appmod.ss_parse_json(payload)

    assert data["jeux"][1]["romnom"] == "z"
    assert data["jeux"][0]["url"].endswith("batocera_manager")

