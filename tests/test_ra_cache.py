"""Tests de la cache de los datos de RetroAchievements.

La API de RetroAchievements no publica una cuota numérica, pero su
documentacion pide ser razonable con las peticiones y cachear los datos. Por
eso el resumen:

- se cachea en memoria y **en disco** (asi sobrevive a un reinicio del
  manager, que es cuando mas veces se repetia la llamada),
- se refresca como mucho una vez cada `RA_CACHE_TTL` segundos (6 h por
  defecto, configurable con `ra_cache_ttl`),
- respeta un intervalo minimo entre dos descargas a la red (`RA_MIN_REFRESH`),
  aunque se pida un refresco forzado.
"""
from __future__ import annotations

from pathlib import Path

PROFILE = {"User": "tester", "TotalPoints": 100, "TotalTruePoints": 50,
           "MemberSince": "2020-01-01", "UserPic": "/UserPic/tester.png"}
RECENT = {"UserRecentAchievements": []}
COMPLETION = {"Count": 1, "Total": 1, "Results": [
    {"GameID": 1, "Title": "Myst", "ConsoleID": 123, "ConsoleName": "PC",
     "MaxPossible": 12, "NumAwarded": 3, "NumAwardedHardcore": 1,
     "MostRecentAwardedDate": "2024-01-01", "HighestAwardKind": "mastered",
     "HighestAwardDate": "2024-01-01"}]}
AWARDS = {"MasteryCount": 1, "CompletionCount": 2, "BeatenHardcoreCount": 3,
          "BeatenSoftcoreCount": 4, "AwardedCount": 10, "TotalAwards": 20}


def _creds(user="tester", key="KEY123"):
    return {"ra_user": user, "ra_api_key": key, "ra_enabled": True}


def _fake_ra_get(calls):
    def fake(settings, endpoint, params=None, timeout=10):
        calls.append(endpoint)
        return {
            "API_GetUserProfile.php": PROFILE,
            "API_GetUserRecentAchievements.php": RECENT,
            "API_GetUserCompletionProgress.php": COMPLETION,
            "API_GetUserAwards.php": AWARDS,
        }.get(endpoint)
    return fake


def _limpiar(appmod):
    appmod._ra_cache.update({"ts": 0, "data": None, "user": ""})
    appmod._ra_last_req["ts"] = 0
    try:
        appmod._ra_cache_file().unlink(missing_ok=True)
    except Exception:
        pass


# ── Cache en disco ─────────────────────────────────────────────────────

def test_los_datos_se_guardan_en_disco(appmod, tmp_path, monkeypatch):
    """La cache sobrevive a un reinicio del manager."""
    _limpiar(appmod)
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get([]))

    appmod.get_retroachievements(_creds())

    fichero = appmod._ra_cache_file()
    assert fichero.exists(), "el resumen debe guardarse en disco"
    import json
    raw = json.loads(fichero.read_text(encoding="utf-8"))
    assert raw["user"] == "tester"
    assert raw["data"]["profile"]["user"] == "tester"


def test_al_reiniciar_el_manager_no_se_vuelve_a_llamar_a_la_api(appmod, monkeypatch):
    """Con la cache en disco, entrar en la seccion no llama a la API."""
    _limpiar(appmod)
    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))

    appmod.get_retroachievements(_creds())
    n1 = len(llamadas)

    # Se simula un reinicio: se vacia la memoria, el disco se queda.
    appmod._ra_cache.update({"ts": 0, "data": None, "user": ""})
    r = appmod.get_retroachievements(_creds())

    assert len(llamadas) == n1, "no debe volver a pedir los datos a la API"
    assert r["cached"] is True
    assert r["profile"]["user"] == "tester"


def test_la_cache_de_disco_no_se_usa_para_otro_usuario(appmod, monkeypatch):
    _limpiar(appmod)
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get([]))
    appmod.get_retroachievements(_creds("otro"))
    appmod._ra_cache.update({"ts": 0, "data": None, "user": ""})

    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))
    appmod.get_retroachievements(_creds("distinto"))

    assert llamadas, "los datos de otro usuario no valen"


# ── Tiempo de vida ─────────────────────────────────────────────────────

def test_el_tiempo_de_vida_de_la_cache_es_configurable(appmod):
    assert appmod.DEFAULT_SETTINGS["ra_cache_ttl"] == 21600
    assert appmod._ra_ttl({}) == 21600
    assert appmod._ra_ttl({"ra_cache_ttl": 3600}) == 3600
    # valores absurdos se acotan
    assert appmod._ra_ttl({"ra_cache_ttl": 1}) == 300
    assert appmod._ra_ttl({"ra_cache_ttl": 999999}) == 86400
    assert appmod._ra_ttl({"ra_cache_ttl": "no es un numero"}) == 21600


def test_cuando_la_cache_caduca_se_vuelve_a_pedir(appmod, monkeypatch):
    _limpiar(appmod)
    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))

    appmod.get_retroachievements(_creds())
    n1 = len(llamadas)

    # Se simula que la cache es vieja: se caduca.
    appmod._ra_cache["ts"] -= appmod.RA_CACHE_TTL + 10
    appmod._ra_last_req["ts"] = 0
    appmod.get_retroachievements(_creds())

    assert len(llamadas) > n1, "pasada la cache hay que volver a la API"


# ── Intervalo mínimo entre peticiones ──────────────────────────────────

def test_no_se_hacen_dos_descargas_seguidas(appmod, monkeypatch):
    """Aunque se pida un refresco, no se llama a la API dos veces seguidas."""
    _limpiar(appmod)
    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))

    appmod.get_retroachievements(_creds())
    n1 = len(llamadas)

    r = appmod.get_retroachievements(_creds(), force=True)

    assert len(llamadas) == n1, "no debe tocar la red otra vez"
    assert r["throttled"] is True, "se avisa de que se ha respetado el intervalo"
    assert r["cached"] is True


def test_pasado_el_intervalo_minimo_si_se_refresca(appmod, monkeypatch):
    _limpiar(appmod)
    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))

    appmod.get_retroachievements(_creds())
    n1 = len(llamadas)

    appmod._ra_last_req["ts"] = 0     # como si hubiera pasado el intervalo
    r = appmod.get_retroachievements(_creds(), force=True)

    assert len(llamadas) > n1, "el refresco forzado si descarga datos"
    assert r["cached"] is False
    assert r["throttled"] is False


# ── Lo que ve la interfaz ──────────────────────────────────────────────

def test_el_dashboard_dice_de_donde_salen_los_datos(appmod, monkeypatch):
    _limpiar(appmod)
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get([]))
    monkeypatch.setattr(appmod, "local_game_index", lambda base: {})

    r1 = appmod.get_ra_games(_creds())
    assert r1["cached"] is False
    assert r1["throttled"] is False
    assert r1["updated"]

    r2 = appmod.get_ra_games(_creds())
    assert r2["cached"] is True
    assert r2["age"] is not None and r2["age"] >= 0
    assert r2["total"] == 1
    assert r2["games"][0]["title"] == "Myst"


def test_el_dashboard_no_toca_la_red_sin_credenciales(appmod, monkeypatch):
    llamadas = []
    monkeypatch.setattr(appmod, "_ra_get", _fake_ra_get(llamadas))

    r = appmod.get_ra_games({"ra_user": "", "ra_api_key": "", "ra_enabled": True})

    assert r["configured"] is False
    assert llamadas == []


def test_el_endpoint_acepte_el_parametro_force(appmod):
    src = Path(appmod.__file__).read_text(encoding="utf-8")
    assert "get_ra_games(s, force=force)" in src
    assert "force=1" in src or "force" in src
