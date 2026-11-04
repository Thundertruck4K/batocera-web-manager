"""Tests del sistema de verificación de actualizaciones mayores del manager.

Cubre:
- `parse_version`: extraer (mayor, menor) de una etiqueta de release.
- `_fetch_app_update`: elegir la release más reciente del feed Atom y marcar
  si es una versión MAYOR que la instalada.
- `get_app_update`: caché de 1 h y tolerancia a fallos de red.
- Endpoint `/api/app-update`.
- Frontend: banner, funciones JS y llamada al arranque.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"
APP = ROOT / "app.py"

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>tag:github.com,2008:Repository/1/v2.0</id>
    <updated>2026-11-01T10:00:00Z</updated>
    <link rel="alternate" type="text/html" href="https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v2.0"/>
    <title>v2.0 — Gran rewrite</title>
  </entry>
  <entry>
    <id>tag:github.com,2008:Repository/1/v1.4</id>
    <updated>2026-10-18T03:23:05Z</updated>
    <link rel="alternate" type="text/html" href="https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.4"/>
    <title>v1.4 — lo anterior</title>
  </entry>
</feed>
"""

ATOM_OLDER = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>tag:github.com,2008:Repository/1/v1.4</id>
    <updated>2026-10-18T03:23:05Z</updated>
    <link rel="alternate" type="text/html" href="https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.4"/>
    <title>v1.4 — lo anterior</title>
  </entry>
</feed>
"""


# ─── parse_version ────────────────────────────────────────────────────────

def test_parse_version_basica(appmod):
    assert appmod.parse_version("1.4") == (1, 4)
    assert appmod.parse_version("v2.0") == (2, 0)
    assert appmod.parse_version(" 3.12 ") == (3, 12)


def test_parse_version_rechaza_basura(appmod):
    for malo in ("", None, "abc", "v", "1", "latest", "1.x"):
        assert appmod.parse_version(malo) is None


# ─── _fetch_app_update ────────────────────────────────────────────────────

def test_fetch_app_update_detecta_version_mayor(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_fetch_feed", lambda url, timeout=8: ATOM)
    out = appmod._fetch_app_update()
    assert out is not None
    assert out["version"] == "2.0"
    assert out["tag"] == "v2.0"
    assert out["major"] is True
    assert out["newer"] is True
    assert out["current"] == appmod.APP_VERSION
    assert out["url"].endswith("/v2.0")


def test_fetch_app_update_ignora_menor(appmod, monkeypatch):
    """Una 1.4 publicada no es una actualización mayor."""
    monkeypatch.setattr(appmod, "_fetch_feed", lambda url, timeout=8: ATOM_OLDER)
    out = appmod._fetch_app_update()
    assert out is not None
    assert out["version"] == "1.4"
    assert out["major"] is False
    assert out["newer"] is False


def test_fetch_app_update_sin_red_devuelve_none(appmod, monkeypatch):
    def boom(url, timeout=8):
        raise OSError("sin red")
    monkeypatch.setattr(appmod, "_fetch_feed", boom)
    assert appmod._fetch_app_update() is None


def test_fetch_app_update_con_xml_invalido(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_fetch_feed", lambda url, timeout=8: "<no es xml")
    assert appmod._fetch_app_update() is None


def test_fetch_app_update_ignora_entradas_sin_version(appmod, monkeypatch):
    feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><id>tag:github.com,2008:Repository/1/nightly</id><title>nightly</title></entry>
    </feed>"""
    monkeypatch.setattr(appmod, "_fetch_feed", lambda url, timeout=8: feed)
    assert appmod._fetch_app_update() is None


# ─── get_app_update (caché) ───────────────────────────────────────────────

def test_get_app_update_cachea_una_hora(appmod, monkeypatch):
    llamadas = []

    def fake(url, timeout=8):
        llamadas.append(url)
        return ATOM

    monkeypatch.setattr(appmod, "_fetch_feed", fake)
    monkeypatch.setattr(appmod, "_app_update_cache", {"ts": 0, "data": None})

    a = appmod.get_app_update()
    b = appmod.get_app_update()
    assert a["version"] == "2.0"
    assert b["version"] == "2.0"
    assert len(llamadas) == 1, "no debe repetir la descarga mientras la caché es válida"


def test_get_app_update_tolera_fallo_de_red(appmod, monkeypatch):
    def boom(url, timeout=8):
        raise OSError("sin red")

    monkeypatch.setattr(appmod, "_fetch_feed", boom)
    monkeypatch.setattr(appmod, "_app_update_cache", {"ts": 0, "data": None})
    assert appmod.get_app_update() is None


# ─── Endpoint ─────────────────────────────────────────────────────────────

def test_endpoint_app_update_declarado():
    src = APP.read_text(encoding="utf-8")
    assert '"/api/app-update"' in src
    assert "get_app_update()" in src


# ─── Frontend ─────────────────────────────────────────────────────────────

def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def test_banner_de_actualizacion_en_el_dashboard():
    h = _html()
    assert 'id="dash-update-banner"' in h
    assert 'id="dash-update-title"' in h
    assert 'id="dash-update-sub"' in h
    assert 'id="dash-update-link"' in h
    assert 'id="dash-update-dismiss"' in h
    assert "update-banner.show{display:flex}" in h


def test_js_del_aviso_de_actualizacion():
    h = _html()
    assert "function renderAppUpdate(" in h
    assert "function loadAppUpdate(" in h
    assert "function initAppUpdate(" in h
    assert "function dismissAppUpdate(" in h
    assert "/api/app-update" in h


def test_el_aviso_se_inicia_al_arrancar():
    h = _html()
    assert "initAppUpdate();" in h


def test_el_aviso_solo_muestra_versiones_mayores():
    """Una minor (1.5) no debe disparar el aviso de 'versión mayor'."""
    h = _html()
    cuerpo = h.split("function renderAppUpdate(", 1)[1].split("\n}", 1)[0]
    assert "if (!u || !u.major)" in cuerpo
    assert "u.major" in cuerpo


def test_el_aviso_se_oculta_si_no_hay_datos():
    """Sin respuesta del servidor el banner debe ocultarse, no quedarse pegado."""
    h = _html()
    cuerpo = h.split("function renderAppUpdate(", 1)[1].split("\n}", 1)[0]
    assert "!u || !u.major" in cuerpo
    assert cuerpo.count("banner.classList.remove('show')") >= 2


def test_el_descartado_recuerda_la_version():
    """Descartar la 2.0 no debe callar el aviso de la 3.0."""
    h = _html()
    assert "bcm_update_dismissed" in h
    cuerpo = h.split("function dismissAppUpdate(", 1)[1].split("\n}", 1)[0]
    assert "localStorage.setItem(UPDATE_KEY, _updateVersion)" in cuerpo
    render = h.split("function renderAppUpdate(", 1)[1].split("\n}", 1)[0]
    assert "dismissed === u.version" in render
