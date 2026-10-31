"""Tests del enmascarado de las credenciales del scraper.

Las credenciales del scraper viven en batocera.conf y las lee get_scraper_config()
para hablar con ScreenScraper / TheGamesDB / IGDB. Lo que no debe pasar es que
salgan en claro por la API.
"""
from __future__ import annotations


def test_public_scraper_config_masks_every_credential(appmod):
    cfg = {
        "ss_user": "mi_usuario", "ss_password": "mi_password",
        "ss_devid": "mid", "ss_devpassword": "midevpass",
        "tgdb_apikey": "TGDBKEY", "igdb_client_id": "igdbid",
        "igdb_client_secret": "igdbsecret",
        "ss_region": "wor", "ss_lang": "es",
    }
    pub = appmod.public_scraper_config(cfg)
    flat = repr(pub)
    for secret in ("mi_usuario", "mi_password", "mid", "midevpass",
                   "TGDBKEY", "igdbid", "igdbsecret"):
        assert secret not in flat, f"se filtra {secret}"


def test_public_scraper_config_keeps_non_secret_fields(appmod):
    pub = appmod.public_scraper_config({"ss_region": "eu", "ss_lang": "es",
                                        "ss_image_type": "mixrbv2"})
    assert pub["ss_region"] == "eu"
    assert pub["ss_lang"] == "es"
    assert pub["ss_image_type"] == "mixrbv2"


def test_public_scraper_config_reports_configured_state(appmod):
    pub = appmod.public_scraper_config({"ss_password": "algo", "tgdb_apikey": ""})
    assert pub["ss_password_set"] is True
    assert pub["tgdb_apikey_set"] is False


def test_public_scraper_config_does_not_mutate_input(appmod):
    src = {"ss_password": "secreto"}
    appmod.public_scraper_config(src)
    assert src["ss_password"] == "secreto"


def test_mask_secret_value_hides_short_values_entirely(appmod):
    assert appmod.mask_secret_value("abc") == "•" * 8
    assert appmod.mask_secret_value("") == ""


def test_mask_secret_value_keeps_extremes_of_long_values(appmod):
    out = appmod.mask_secret_value("abcd1234efgh5678")
    assert out.startswith("abcd")
    assert out.endswith("5678")


def test_ra_mask_still_works_through_the_generic_helper(appmod):
    assert (appmod.mask_ra_api_key("abcd1234efgh5678")
            == appmod.mask_secret_value("abcd1234efgh5678"))


# ─── La máscara del cliente no puede pisar la credencial real ───────

def test_resolve_ignores_a_mask_sent_by_the_client(appmod, tmp_path):
    """La mascara del navegador no puede ganar al servidor.

    Si ganara, la mascara acabaria enviada a la API de ScreenScraper.
    """
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=real_user\n"
                    "global.scrapper.password=real_password\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    mask = appmod.mask_secret_value("real_password")
    creds = appmod.resolve_scraper_creds(settings, {
        "ss_user": mask, "ss_password": mask,
    })
    assert creds["ss_user"] == "real_user"
    assert creds["ss_password"] == "real_password"


def test_resolve_still_uses_a_real_value_sent_by_the_client(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=real_user\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    creds = appmod.resolve_scraper_creds(settings, {"ss_user": "otro_usuario"})
    assert creds["ss_user"] == "otro_usuario"


# ─── Guardado write-only ────────────────────────────────────────────

def test_save_keeps_the_stored_credential_when_a_mask_arrives(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n", encoding="utf-8")
    mask = appmod.mask_secret_value("real_password")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": mask},
    ])
    assert ok, err
    assert "global.scrapper.password=real_password" in conf.read_text(encoding="utf-8")


def test_save_writes_a_new_credential(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=old\n", encoding="utf-8")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": "nueva_password"},
    ])
    assert ok, err
    assert "global.scrapper.password=nueva_password" in conf.read_text(encoding="utf-8")


def test_save_empty_without_clear_does_not_touch_the_credential(appmod, tmp_path):
    """Un cliente que no manda `clear` no puede borrar credenciales por error."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": ""},
    ])
    assert ok
    assert "global.scrapper.password=real_password" in conf.read_text(encoding="utf-8")


def test_save_with_clear_erases_only_that_credential(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n"
                    "global.tgdb.apikey=TGDBKEY\n", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": "", "clear": True},
    ])
    assert ok
    text = conf.read_text(encoding="utf-8")
    assert "global.scrapper.password=" in text
    assert "real_password" not in text
    assert "global.tgdb.apikey=TGDBKEY" in text


def test_save_still_writes_non_secret_fields(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.region", "val": "eu"},
    ])
    assert ok
    assert "global.scrapper.region=eu" in conf.read_text(encoding="utf-8")


# ─── Los endpoints no filtran ───────────────────────────────────────

def test_scraper_config_endpoint_does_not_leak_credentials(appmod, tmp_path):
    import json
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=mi_usuario\n"
                    "global.scrapper.password=mi_password\n"
                    "global.tgdb.apikey=TGDBKEY\n"
                    "global.igdb.clientsecret=igdbsecret\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    body = json.dumps(appmod.public_scraper_config(
        appmod.get_scraper_config(settings)))
    assert "mi_usuario" not in body
    assert "mi_password" not in body
    assert "TGDBKEY" not in body
    assert "igdbsecret" not in body


def test_get_scraper_config_still_returns_the_real_values(appmod, tmp_path):
    """La lectura interna sigue dando las credenciales reales: se usan para
    hablar con ScreenScraper."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=mi_password\n", encoding="utf-8")
    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})
    assert cfg["ss_password"] == "mi_password"


def test_handlers_use_the_public_config(appmod):
    from pathlib import Path
    src = (Path(appmod.__file__).parent / "app.py").read_text(encoding="utf-8")
    assert "public_scraper_config(get_scraper_config(s))" in src
    assert '"cfg":public_scraper_config(cfg)' in src
    assert 'self.send_json(get_scraper_config(s))' not in src


# ─── Frontend ───────────────────────────────────────────────────────

def _html(appmod):
    from pathlib import Path
    return (Path(appmod.__file__).parent / "templates" / "index.html").read_text(
        encoding="utf-8")


def test_frontend_reports_configured_credentials(appmod):
    html = _html(appmod)
    assert "_set" in html, "el hint debe indicar que credenciales hay configuradas"
    assert "Configurada" in html


def test_frontend_sends_explicit_clear_flag(appmod):
    html = _html(appmod)
    assert "clear" in html, "el guardado debe marcar explicitamente el borrado"
    assert "_scraperCfg" in html, "el guardado necesita saber si habia credencial"


def test_frontend_never_writes_the_raw_credential_to_the_form(appmod):
    """Los campos se rellenan con lo que llega de la API, ya enmascarado."""
    html = _html(appmod)
    assert "value=\"${escHtml(cfg[f.key]||'')}\"" in html
    assert "sc-pass',          cfg.ss_password||''" in html

# ─── Un valor no puede inyectar directivas en batocera.conf ──────────

def test_save_rejects_a_value_with_a_newline(appmod, tmp_path):
    """Un salto de linea inyectaria una clave nueva en batocera.conf.

    batocera.conf se escribe linea a linea, asi que un "\n" en la credencial
    crea una directiva espuria (p. ej. global.es.foo=bar) y el servidor la
    escribe con permisos de root.
    """
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password",
         "val": "mypass\nglobal.es.foo=bar"},
    ])
    assert not ok, "un valor con salto de linea deberia rechazarse"
    assert "global.es.foo" not in conf.read_text(encoding="utf-8")


def test_save_rejects_a_value_with_a_carriage_return(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password",
         "val": "mypass\rglobal.es.foo=bar"},
    ])
    assert not ok
    assert "global.es.foo" not in conf.read_text(encoding="utf-8")


def test_save_still_accepts_a_password_with_spaces(appmod, tmp_path):
    """Una contrasena puede llevar espacios: solo se rechazan los saltos."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": "mi clave con espacios"},
    ])
    assert ok, err
    text = conf.read_text(encoding="utf-8")
    assert "global.scrapper.password=mi clave con espacios" in text


# ─── La config publica solo expone campos conocidos ──────────────────

def test_public_scraper_config_only_exposes_known_fields(appmod):
    """Lista blanca: un campo nuevo no puede colarse en la respuesta.

    Mismo criterio que public_settings(): si manana se anade un campo
    sensible a get_scraper_config(), no debe servirse en claro por
    Pioneer.
    """
    pub = appmod.public_scraper_config({
        "ss_password": "secreto", "ss_region": "eu",
        "campo_desconocido": "no_debe_salir",
    })
    assert "campo_desconocido" not in pub
    assert "no_debe_salir" not in repr(pub)

def test_the_config_tab_of_the_scraper_modal_also_loads_the_credentials():
    """La pestaña "Configuración" del modal contiene el formulario de credenciales.

    Antes solo se cargaba al abrir el modal por otras pestañas, asi que entrar
    directamente en ella dejaba el formulario vacio.
    """
    import re
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(
        encoding="utf-8")
    m = re.search(r"function\s+scraperTab\(tab\)\s*\{(.*?)\n\}", html, re.S)
    assert m, "no se encontro scraperTab"
    cond = re.search(r"if\s*\(([^)]*)\)\s*\{[^}]*loadScraperConfig", m.group(1))
    assert cond, "scraperTab debe cargar la configuracion de credenciales"
    assert "'config'" in cond.group(1), (
        "la pestaña 'config' tambien debe cargar la configuracion de credenciales")
