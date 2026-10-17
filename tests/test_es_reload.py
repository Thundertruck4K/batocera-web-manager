# -*- coding: utf-8 -*-
"""Tests de la recarga automática de EmulationStation tras scrapear.

Problema real (2026-10-16): el scraping desde la web guardaba los metadatos
correctamente en `roms/<sistema>/gamelist.xml`, pero en la TV se veía solo la
imagen. Causa: EmulationStation lee las gamelists al arrancar y las mantiene en
memoria; la imagen sí aparece porque ES autodetecta la carpeta `images/`, pero
el texto no se relee hasta que ES se reinicia.

Solución: tras un scrapeo que guardó metadatos, recargar ES.
"""
from __future__ import annotations


def test_reload_skips_when_no_meta_saved(appmod, monkeypatch):
    """Sin metadatos guardados no se toca EmulationStation."""
    calls = []
    monkeypatch.setattr(appmod, "restart_emulationstation",
                        lambda: (calls.append(1), (True, {}))[1])

    out = appmod.reload_es_after_scrape(False)

    assert out["reloaded"] is False
    assert calls == [], "no debe reiniciar ES si no se guardó nada"


def test_reload_calls_restart_when_meta_saved(appmod, monkeypatch):
    calls = []
    monkeypatch.setattr(appmod, "restart_emulationstation",
                        lambda: (calls.append(1), (True, {"ok": True}))[1])

    out = appmod.reload_es_after_scrape(True)

    assert calls == [1], "debe reiniciar ES cuando se guardaron metadatos"
    assert out == {"ok": True, "reloaded": True}


def test_reload_reports_error_without_raising(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "restart_emulationstation",
                        lambda: (False, {"error": "swissknife caído"}))

    out = appmod.reload_es_after_scrape(True)

    assert out["ok"] is False
    assert out["reloaded"] is False
    assert "swissknife caído" in out["error"]


def test_reload_never_raises_on_unexpected_exception(appmod, monkeypatch):
    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setattr(appmod, "restart_emulationstation", boom)

    out = appmod.reload_es_after_scrape(True)

    assert out["ok"] is False
    assert out["reloaded"] is False
    assert "kaboom" in out["error"]


def _fake_system(tmp_path):
    (tmp_path / "ps2").mkdir()
    (tmp_path / "ps2" / "juego.iso").write_bytes(b"x")
    return {
        "name": "ps2",
        "roms": [{"name": "juego", "filename": "juego.iso", "ext": ".iso",
                  "is_rom": True, "has_image": False}],
    }


def test_do_scrape_system_counts_saved_meta(appmod, monkeypatch, tmp_path):
    """`do_scrape_system` informa cuántas entradas escribió en la gamelist."""
    settings = {"roms_base": str(tmp_path)}
    monkeypatch.setattr(appmod, "get_rom_systems",
                        lambda s, fast=False: [_fake_system(tmp_path)])
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (
        {"noms": [{"region": "wor", "text": "Juego"}], "medias": []}, None, {}))
    saved = []
    monkeypatch.setattr(appmod, "save_gamelist_entry",
                        lambda base, meta: saved.append(meta))

    res = appmod.do_scrape_system(
        settings, "ps2", "screenscraper",
        {"ss_region": "wor", "ss_lang": "es"}, {"only_missing": True})

    assert res["meta_saved"] == 1
    assert saved and saved[0]["name"] == "Juego"


def test_do_scrape_system_meta_saved_zero_when_nothing_found(appmod, monkeypatch, tmp_path):
    settings = {"roms_base": str(tmp_path)}
    monkeypatch.setattr(appmod, "get_rom_systems",
                        lambda s, fast=False: [_fake_system(tmp_path)])
    monkeypatch.setattr(appmod, "ss_search_game", lambda *a, **k: (None, "sin resultados", {}))
    monkeypatch.setattr(appmod, "save_gamelist_entry", lambda base, meta: None)

    res = appmod.do_scrape_system(
        settings, "ps2", "screenscraper",
        {"ss_region": "wor", "ss_lang": "es"}, {"only_missing": True})

    assert res["meta_saved"] == 0


def _batch_job():
    return {
        "id": "abc123", "systems": ["ps2"], "source": "screenscraper",
        "creds": {}, "options": {}, "settings": {"roms_base": "/tmp/roms"},
        "status": "running", "progress": 0, "current_system": "",
        "current_rom": "", "progress_raw": [0, 0], "partial": {},
        "systems_done": 0, "systems_result": {},
        "aggregated": {"ok": 0, "fail": 0, "skip": 0, "total": 0,
                       "errors": [], "meta_saved": 0},
        "quota": {}, "created_at": 0, "error": None,
    }


def _fake_batch_scrape(meta_saved):
    def _fn(settings, sys_name, source, creds, options, cb=None):
        return {"ok": 1, "fail": 0, "skip": 0, "errors": [], "total": 1,
                "quota": {}, "meta_saved": meta_saved}
    return _fn


def test_batch_reloads_es_after_saving_meta(appmod, monkeypatch):
    calls = []
    lock_free = []

    def fake_reload(flag=True):
        # El lock de jobs no puede estar tomado durante la recarga: bloquearía
        # el sondeo de progreso del front-end (el reinicio puede tardar ~1 min).
        got = appmod._scraper_jobs_lock.acquire(blocking=False)
        lock_free.append(got)
        if got:
            appmod._scraper_jobs_lock.release()
        calls.append(flag)
        return {"ok": True, "reloaded": True}

    monkeypatch.setattr(appmod, "do_scrape_system", _fake_batch_scrape(1))
    monkeypatch.setattr(appmod, "reload_es_after_scrape", fake_reload)
    job = _batch_job()

    appmod._process_batch_job(job)

    assert calls == [True], "debe recargar ES al terminar el lote"
    assert lock_free == [True], "la recarga no debe hacerse con el lock tomado"
    assert job["es_reload"] == {"ok": True, "reloaded": True}
    assert job["aggregated"]["meta_saved"] == 1


def test_batch_skips_es_reload_when_nothing_saved(appmod, monkeypatch):
    calls = []

    def fake_reload(flag=True):
        calls.append(flag)
        return {"ok": True, "reloaded": True}

    monkeypatch.setattr(appmod, "do_scrape_system", _fake_batch_scrape(0))
    monkeypatch.setattr(appmod, "reload_es_after_scrape", fake_reload)
    job = _batch_job()

    appmod._process_batch_job(job)

    assert calls == [], "sin metadatos guardados no se recarga ES"
    assert job.get("es_reload") is None
