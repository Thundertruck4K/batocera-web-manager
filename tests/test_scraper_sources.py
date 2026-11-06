"""Tests de la cadena de fuentes del scraper.

ScreenScraper es la prioridad (es la fuente con más información); si no
encuentra el juego se prueban TheGamesDB e IGDB como respaldo.
"""
from __future__ import annotations

import json

CFG = {
    "ss_user": "usuario",
    "ss_password": "clave",
    "ss_devid": "",
    "ss_devpassword": "",
    "tgdb_apikey": "clave-tgdb",
    "igdb_client_id": "cliente",
    "igdb_client_secret": "secreto",
    "ss_region": "wor",
    "ss_lang": "es",
    "ss_image_type": "mixrbv1",
    "scraper_source": "screenscraper",
}


# ── Credenciales ──────────────────────────────────────────────────────

def test_cada_fuente_detecta_sus_credenciales(appmod):
    assert appmod.source_has_creds("screenscraper", CFG) is True
    assert appmod.source_has_creds("thegamesdb", CFG) is True
    assert appmod.source_has_creds("igdb", CFG) is True

    sin_ss = {**CFG, "ss_user": "", "ss_password": ""}
    assert appmod.source_has_creds("screenscraper", sin_ss) is False
    assert appmod.source_has_creds("thegamesdb", sin_ss) is True

    sin_tgdb = {**CFG, "tgdb_apikey": ""}
    assert appmod.source_has_creds("thegamesdb", sin_tgdb) is False

    sin_igdb = {**CFG, "igdb_client_secret": ""}
    assert appmod.source_has_creds("igdb", sin_igdb) is False


# ── Búsqueda en una fuente ───────────────────────────────────────────

def test_la_busqueda_devuelve_la_imagen_de_vista_previa(appmod, monkeypatch):
    juego = {"name": "Juego", "medias": [
        {"type": "mixrbv1", "url": "https://www.screenscraper.fr/caja.png", "format": "PNG"}]}
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (juego, None, {"maxthreads": 1}))
    monkeypatch.setattr(appmod, "ss_build_meta", lambda game, region="wor", lang="es": {"name": "Juego"})
    monkeypatch.setattr(appmod, "ss_media_url",
                        lambda game, itype, region="wor": ("https://img/caja.png", ".png"))

    game, meta, img_types, image_url, err, quota = appmod.scrape_search_one(
        "screenscraper", "Juego.iso", "snes", CFG)

    assert game is not None
    assert image_url == "https://img/caja.png"
    assert "mixrbv1" in img_types
    assert err is None


def test_las_fuentes_sin_credenciales_no_se_consultan(appmod, monkeypatch):
    """TheGamesDB sin API key no debe gastar una petición."""
    llamadas = []

    def fake_tgdb(*args, **kwargs):
        llamadas.append(args)
        return None, "Sin resultados"

    monkeypatch.setattr(appmod, "tgdb_search_game", fake_tgdb)
    cfg = {**CFG, "tgdb_apikey": ""}

    appmod.scrape_search_one("thegamesdb", "Juego.iso", "snes", cfg)

    assert llamadas == []


# ── La cascada ────────────────────────────────────────────────────────

def _monkeypatch_fuentes(appmod, monkeypatch, ss=None, tgdb=None, igdb=None):
    monkeypatch.setattr(appmod, "ss_search_game",
                        lambda *a, **k: (ss, None, {"maxthreads": 1}) if ss else (None, "Sin resultados", {}))
    monkeypatch.setattr(appmod, "ss_build_meta", lambda game, region="wor", lang="es": {"name": "ss"})
    monkeypatch.setattr(appmod, "ss_media_url", lambda game, itype, region="wor": ("https://img/ss.png", ".png"))
    monkeypatch.setattr(appmod, "tgdb_search_game",
                        lambda *a, **k: (tgdb, None) if tgdb else (None, "Sin resultados"))
    monkeypatch.setattr(appmod, "tgdb_build_meta", lambda game, key=None: {"name": "tgdb"})
    monkeypatch.setattr(appmod, "tgdb_get_image", lambda gid, key: ("https://img/tgdb.png", None))
    monkeypatch.setattr(appmod, "igdb_search_game",
                        lambda *a, **k: (igdb, None) if igdb else (None, "Sin resultados"))
    monkeypatch.setattr(appmod, "igdb_build_meta", lambda game: {"name": "igdb"})
    monkeypatch.setattr(appmod, "igdb_get_image_url", lambda game: "https://img/igdb.png")


def test_screen_scraper_tiene_la_prioridad(appmod, monkeypatch):
    _monkeypatch_fuentes(appmod, monkeypatch,
                         ss={"name": "ss"}, tgdb={"id": 1}, igdb={"id": 2})

    game, meta, img_types, image_url, source, tried, err, quota = appmod.scrape_search_cascade(
        "Juego.iso", "snes", CFG, sources=["screenscraper", "thegamesdb", "igdb"])

    assert source == "screenscraper"
    assert game == {"name": "ss"}
    assert tried == ["screenscraper"]
    assert err is None


def test_se_pasa_a_la_siguiente_fuente_si_no_hay_datos(appmod, monkeypatch):
    _monkeypatch_fuentes(appmod, monkeypatch, ss=None, tgdb={"id": 1}, igdb={"id": 2})

    game, meta, img_types, image_url, source, tried, err, quota = appmod.scrape_search_cascade(
        "Juego.iso", "snes", CFG, sources=["screenscraper", "thegamesdb", "igdb"])

    assert source == "thegamesdb"
    assert game == {"id": 1}
    assert tried == ["screenscraper", "thegamesdb"]
    assert image_url == "https://img/tgdb.png"


def test_la_cascada_avisa_si_no_encuentra_nada(appmod, monkeypatch):
    _monkeypatch_fuentes(appmod, monkeypatch)

    game, meta, img_types, image_url, source, tried, err, quota = appmod.scrape_search_cascade(
        "Juego.iso", "snes", CFG, sources=["screenscraper", "thegamesdb", "igdb"])

    assert game is None
    assert source is None
    assert tried == ["screenscraper", "thegamesdb", "igdb"]
    assert err


def test_una_fuente_sin_credenciales_se_salta_en_la_cascada(appmod, monkeypatch):
    _monkeypatch_fuentes(appmod, monkeypatch, ss=None, tgdb={"id": 1}, igdb={"id": 2})
    cfg = {**CFG, "tgdb_apikey": ""}

    game, meta, img_types, image_url, source, tried, err, quota = appmod.scrape_search_cascade(
        "Juego.iso", "snes", cfg, sources=["screenscraper", "thegamesdb", "igdb"])

    # TheGamesDB se salta por falta de credenciales y se pasa a IGDB.
    assert source == "igdb"
    assert "thegamesdb" in tried


def test_el_orden_pedido_se_respeta(appmod, monkeypatch):
    _monkeypatch_fuentes(appmod, monkeypatch, ss={"name": "ss"}, tgdb={"id": 1})

    game, meta, img_types, image_url, source, tried, err, quota = appmod.scrape_search_cascade(
        "Juego.iso", "snes", CFG, sources=["thegamesdb", "screenscraper"])

    assert source == "thegamesdb"


# ── El respaldo en el scrape de sistema ──────────────────────────────

def _preparar_sistema(appmod, monkeypatch, tmp_path):
    roms_base = tmp_path / "roms"
    sistema = roms_base / "snes"
    sistema.mkdir(parents=True)
    (sistema / "Juego.iso").write_bytes(b"rom")

    monkeypatch.setattr(appmod, "get_rom_systems", lambda settings, fast=False: [{
        "name": "snes",
        "roms": [{"filename": "Juego.iso", "name": "Juego", "is_rom": True,
                   "has_image": False, "ext": ".iso"}],
    }])
    monkeypatch.setattr(appmod, "save_gamelist_entry", lambda base, meta: None)
    monkeypatch.setattr(appmod, "download_image_generic",
                        lambda url, dest, referer_for=None: (True, str(dest)))
    _monkeypatch_fuentes(appmod, monkeypatch, tgdb={"id": 1})
    return {"roms_base": str(roms_base)}


def test_el_scrape_de_sistema_usa_el_respaldo(appmod, monkeypatch, tmp_path):
    settings = _preparar_sistema(appmod, monkeypatch, tmp_path)
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (None, "Sin resultados", {}))

    res = appmod.do_scrape_system(settings, "snes", "screenscraper", dict(CFG),
                                  {"fallback_sources": True})

    assert res["meta_saved"] == 1
    assert res["fail"] == 0
    assert res["total"] == 1


def test_sin_respaldo_el_scrape_de_sistema_falla(appmod, monkeypatch, tmp_path):
    settings = _preparar_sistema(appmod, monkeypatch, tmp_path)
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (None, "Sin resultados", {}))

    res = appmod.do_scrape_system(settings, "snes", "screenscraper", dict(CFG), {})

    assert res["meta_saved"] == 0
    assert res["fail"] == 1
    assert res["errors"]


# ── El proxy de carátulas ─────────────────────────────────────────────

class _FakeResp:
    """Respuesta mínima con el contexto que espera el proxy."""

    def __init__(self, data: bytes, ctype: str = "image/png"):
        self.data = data
        self.headers = {"Content-Type": ctype}

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_el_proxy_solo_admite_los_hosts_de_las_fuentes(appmod):
    assert appmod.scraper_proxy_allowed("https://neoclone.screenscraper.fr/jeu/1/mixrbv1.jpg")
    assert appmod.scraper_proxy_allowed("https://cdn.thegamesdb.com/images/original/x.jpg")
    assert appmod.scraper_proxy_allowed("https://cdn.thegamesdb.net/images/original/x.jpg")
    assert appmod.scraper_proxy_allowed("https://images.igdb.com/igdb/image/upload/x.jpg")

    # Ni direcciones internas ni hosts que sólo parecen de una fuente.
    assert not appmod.scraper_proxy_allowed("http://192.168.1.1/admin")
    assert not appmod.scraper_proxy_allowed("http://localhost:5000/api/config")
    assert not appmod.scraper_proxy_allowed("https://evil.com/?u=screenscraper.fr")


def test_el_proxy_guarda_la_imagen_en_cache(appmod, monkeypatch):
    appmod._IMG_PROXY_CACHE.clear()
    peticiones = []

    def fake_urlopen(req, timeout=None):
        peticiones.append(req)
        return _FakeResp(b"PNG-DATA")

    monkeypatch.setattr(appmod._ureq, "urlopen", fake_urlopen)
    url = "https://neoclone.screenscraper.fr/jeu/1/mixrbv1.jpg"

    ctype, data, err = appmod.scraper_proxy_image(url)
    assert err is None
    assert data == b"PNG-DATA"
    assert ctype == "image/png"
    # ScreenScraper sólo entrega sus imágenes si llega el referer.
    assert peticiones[0].get_header("Referer") == "https://www.screenscraper.fr/gameinfos.php"

    # La segunda vez sale de la caché: no se vuelve a descargar.
    ctype2, data2, err2 = appmod.scraper_proxy_image(url)
    assert data2 == b"PNG-DATA"
    assert err2 is None
    assert len(peticiones) == 1
    appmod._IMG_PROXY_CACHE.clear()


def test_el_proxy_no_cachea_las_imagenes_grandes(appmod, monkeypatch):
    appmod._IMG_PROXY_CACHE.clear()
    grande = b"x" * (appmod._IMG_PROXY_MAX_BYTES + 1)
    monkeypatch.setattr(appmod._ureq, "urlopen",
                        lambda req, timeout=None: _FakeResp(grande))

    url = "https://neoclone.screenscraper.fr/jeu/2/mixrbv1.jpg"
    ctype, data, err = appmod.scraper_proxy_image(url)

    assert err is None
    assert len(data) == len(grande)
    assert url not in appmod._IMG_PROXY_CACHE
    appmod._IMG_PROXY_CACHE.clear()


def test_calentar_la_imagen_respeta_la_lista_de_hosts(appmod, monkeypatch):
    import time as _time

    pedidas = []
    monkeypatch.setattr(appmod, "scraper_proxy_image",
                        lambda url, cfg=None: pedidas.append(url) or ("image/png", b"x", None))

    appmod.warm_scraper_image("http://192.168.1.1/admin")
    assert pedidas == []

    appmod.warm_scraper_image("https://neoclone.screenscraper.fr/jeu/1/mixrbv1.jpg")
    for _ in range(60):
        if pedidas:
            break
        _time.sleep(0.05)
    assert pedidas == ["https://neoclone.screenscraper.fr/jeu/1/mixrbv1.jpg"]


# ── Las credenciales no pueden viajar al navegador ─────────────────────

MEDIA_URL = ("https://neoclone.screenscraper.fr/api2/mediaJeu.php"
             "?devid=batoceralinux&devpassword=secreto-dev"
             "&softname=batocera_manager&ssid=usuario&sspassword=clave-usuario"
             "&systemeid=13&jeuid=4880&media=mixrbv1(wor)")


def test_la_url_de_medios_sin_credenciales(appmod):
    publica = appmod.ss_media_public_url(MEDIA_URL)

    assert "secreto-dev" not in publica
    assert "clave-usuario" not in publica
    assert "usuario" not in publica
    assert "systemeid=13" in publica
    assert "media=mixrbv1%28wor%29" in publica, "el tipo de imagen debe conservarse"


def test_la_url_se_vuelve_a_firmar_en_el_servidor(appmod):
    cfg = {**CFG, "ss_devid": "batoceralinux", "ss_devpassword": "secreto-dev"}
    firmada = appmod.ss_media_signed_url(appmod.ss_media_public_url(MEDIA_URL), cfg)

    assert "devpassword=secreto-dev" in firmada
    assert "sspassword=clave" in firmada
    assert "ssid=usuario" in firmada
    assert "systemeid=13" in firmada


def test_el_juego_que_se_manda_no_lleva_credenciales(appmod):
    juego = {"name": "Juego", "medias": [
        {"type": "mixrbv1", "url": MEDIA_URL, "region": "wor"}]}

    publico = appmod.ss_media_public_game(juego)

    assert "secreto-dev" not in json.dumps(publico)
    assert "clave-usuario" not in json.dumps(publico)
    # El tipo y la región se conservan para poder elegir la imagen.
    assert publico["medias"][0]["type"] == "mixrbv1"
    assert publico["medias"][0]["region"] == "wor"
    # El original no se toca (el servidor lo sigue usando para descargar).
    assert "secreto-dev" in juego["medias"][0]["url"]


def test_la_busqueda_no_devuelve_credenciales(appmod, monkeypatch):
    juego = {"name": "Juego", "medias": [{"type": "mixrbv1", "url": MEDIA_URL}]}
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (juego, None, {}))
    monkeypatch.setattr(appmod, "ss_build_meta", lambda game, region="wor", lang="es": {"name": "Juego"})

    game, meta, img_types, image_url, err, quota = appmod.scrape_search_one(
        "screenscraper", "Juego.iso", "snes", CFG)

    assert "secreto-dev" not in json.dumps(game)
    assert "clave-usuario" not in json.dumps(game)
    assert "secreto-dev" not in (image_url or "")
    assert "clave-usuario" not in (image_url or "")


def test_la_interfaz_clasica_puede_pedir_las_urls_originales(appmod, monkeypatch):
    """La interfaz clásica muestra la imagen directamente, sin proxy."""
    juego = {"name": "Juego", "medias": [{"type": "mixrbv1", "url": MEDIA_URL}]}
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (juego, None, {}))
    monkeypatch.setattr(appmod, "ss_build_meta", lambda game, region="wor", lang="es": {"name": "Juego"})

    game, meta, img_types, image_url, err, quota = appmod.scrape_search_one(
        "screenscraper", "Juego.iso", "snes", CFG, public=False)

    assert "secreto-dev" in json.dumps(game)
    assert "secreto-dev" in (image_url or "")


# ── La búsqueda en TheGamesDB tolera el nombre del ROM ────────────────

def test_las_variantes_de_nombre_para_thegamesdb(appmod):
    variantes = appmod._tgdb_name_variants("007 Agent Under Fire")

    assert variantes[0] == "007 Agent Under Fire"
    assert "Agent Under Fire" in variantes
    # Y no se repite ni se vacía
    assert len(variantes) == len(set(variantes))
    assert appmod._tgdb_name_variants("") == []


def test_la_busqueda_en_thegamesdb_prueba_las_variantes(appmod, monkeypatch):
    """Si el nombre tal cual no aparece, se prueba sin el prefijo numérico."""
    llamadas = []

    def fake_query(nombre, api_key, platform_id=None):
        llamadas.append((nombre, platform_id))
        if nombre == "Agent Under Fire":
            return [{"id": 42, "game_title": "007: Agent Under Fire", "platform": 2}], None
        return [], None

    monkeypatch.setattr(appmod, "_tgdb_query", fake_query)

    juego, err = appmod.tgdb_search_game("007 - Agent Under Fire (USA).iso",
                                         "gamecube", "clave-tgdb")

    assert err is None
    assert juego["id"] == 42
    assert ("007 Agent Under Fire", 2) in llamadas
    assert ("Agent Under Fire", 2) in llamadas


def test_la_busqueda_en_thegamesdb_usa_el_filtro_de_plataforma(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_tgdb_query",
                        lambda nombre, api_key, platform_id=None: ([{"id": 1}], None))

    juego, err = appmod.tgdb_search_game("Juego.iso", "gamecube", "clave-tgdb")

    assert err is None
    assert juego["id"] == 1


def test_sin_resultados_avisa_en_thegamesdb(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_tgdb_query",
                        lambda nombre, api_key, platform_id=None: ([], None))

    juego, err = appmod.tgdb_search_game("Juego.iso", "gamecube", "clave-tgdb")

    assert juego is None
    assert err


def test_el_scrape_de_sistema_firma_la_url_para_descargar(appmod, monkeypatch, tmp_path):
    settings = _preparar_sistema(appmod, monkeypatch, tmp_path)
    urls = []

    def fake_download(url, dest, referer_for=None):
        urls.append(url)
        return True, str(dest)

    monkeypatch.setattr(appmod, "download_image_generic", fake_download)
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (
        {"name": "Juego", "medias": [{"type": "mixrbv1", "url": MEDIA_URL, "region": "wor"}]},
        None, {}))
    monkeypatch.setattr(appmod, "ss_media_url",
                        lambda game, itype, region="wor": (MEDIA_URL, ".png"))
    monkeypatch.setattr(appmod, "ss_build_meta", lambda game, region="wor", lang="es": {"name": "Juego"})

    cfg = {**CFG, "ss_devid": "batoceralinux", "ss_devpassword": "secreto-dev"}
    appmod.do_scrape_system(settings, "snes", "screenscraper", cfg, {})

    assert urls, "debería descargarse la imagen"
    assert "devpassword=secreto-dev" in urls[0]
    # Las credenciales de la config mandan sobre las que venían en la URL.
    assert "sspassword=clave" in urls[0]
    assert "sspassword=clave-usuario" not in urls[0]


# ── Buscar con un nombre que no es el del fichero ─────────────────────

def test_la_busqueda_acepta_un_nombre_que_no_es_un_fichero(appmod, monkeypatch):
    """Al editar el nombre, la búsqueda va por nombre aunque no haya fichero."""
    pedidos = []

    def fake_fetch(url, timeout=20):
        pedidos.append(url)
        if "jeuInfos.php" in url:
            # Sin CRC, ScreenScraper no puede validar el juego por fichero.
            return None, "HTTP 400: systemeid invalide", {}
        return {
            "header": {"success": "true"},
            "response": {"jeu": {"nom": "007: Agent Under Fire"}},
        }, None, {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)

    juego, err, quota = appmod.ss_search_game(
        "007: Agent Under Fire", "gamecube", "usuario", "clave",
        rom_path="/no/existe/Juego.iso",
        devid="batoceralinux", devpassword="secreto")

    assert err is None
    assert juego
    assert juego.get("nom") == "007: Agent Under Fire"
    # Se probó primero por fichero y luego por nombre.
    assert any("jeuInfos.php" in u for u in pedidos)
    assert any("jeuRecherche.php" in u for u in pedidos)


def test_la_busqueda_con_nombre_no_pide_hash_si_no_hay_fichero(appmod, monkeypatch):
    pedidos = []

    def fake_fetch(url, timeout=20):
        pedidos.append(url)
        return None, "HTTP 400", {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)

    appmod.ss_search_game("Nombre Editado", "gamecube", "usuario", "clave",
                          rom_path="/no/existe/Juego.iso",
                          devid="batoceralinux", devpassword="secreto")

    infos = [u for u in pedidos if "jeuInfos.php" in u]
    assert infos
    assert "romtaille=0" in infos[0]
    assert "crc=" not in infos[0]
    assert "md5=" not in infos[0]
