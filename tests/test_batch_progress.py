"""Progreso del lote de scraping (batch).

Bug reportado: la barra se quedaba en 0% durante todo el scrape de un sistema
y saltaba a 100% de golpe al terminar, aunque el job sí estaba trabajando
(el ROM actual iba cambiando). Causa: `job["progress"]` solo se recalculaba
al completar un sistema entero (`_sys_done / total_systems`).
"""
from __future__ import annotations


def _make_job(systems):
    return {
        "id": "t", "systems": systems, "source": "screenscraper",
        "creds": {}, "options": {}, "settings": {},
        "status": "running", "progress": 0,
        "current_system": "", "current_rom": "",
        "systems_done": 0, "systems_result": {},
        "aggregated": {"ok": 0, "fail": 0, "skip": 0, "total": 0, "errors": []},
        "quota": {}, "created_at": 0, "error": None,
        "progress_raw": [0, 0], "partial": {},
    }


def test_batch_progress_advances_within_a_system(appmod):
    """Con un solo sistema, el % debe subir con cada ROM (no quedarse en 0)."""
    p = appmod._batch_progress
    assert p(0, 1, 0, 7) == 0          # aún sin empezar
    assert p(0, 1, 3, 7) == 42         # 3 de 7 ROMs
    assert p(0, 1, 7, 7) <= 99         # nunca 100 hasta completar del todo


def test_batch_progress_combines_systems_and_current_rom(appmod):
    """El % global combina sistemas terminados + fracción del sistema en curso."""
    p = appmod._batch_progress
    assert p(1, 4, 5, 10) == 37        # 1/4 sistemas + mitad del actual
    assert p(2, 4, 0, 10) == 50        # 2/4 sistemas


def test_batch_progress_empty_job_is_zero(appmod):
    assert appmod._batch_progress(0, 0, 0, 0) == 0


def test_process_batch_job_exposes_live_rom_progress(appmod, monkeypatch):
    """Durante el sistema en curso el job debe exponer el ROM actual y un
    progreso intermedio (>0 y <100), no solo aciertos al final."""
    snapshots: list = []
    job = _make_job(["ps2"])

    def fake_scrape(settings, system, source, creds, options, progress_cb=None):
        for i in range(4):
            progress_cb(system, f"rom{i}", i + 1, 4, {"ok": i, "fail": 0, "skip": 0})
            snapshots.append(dict(job))
        return {"ok": 4, "fail": 0, "skip": 0, "errors": [], "total": 4, "quota": {}}

    monkeypatch.setattr(appmod, "do_scrape_system", fake_scrape)
    appmod._process_batch_job(job)

    mid = [s for s in snapshots if 0 < s["progress"] < 100]
    assert mid, "el progreso debe avanzar DENTRO del sistema, no solo al terminar"
    assert any(s["progress_raw"] == [2, 4] for s in snapshots)
    assert any(s["current_rom"] == "rom1" for s in snapshots)
    assert job["progress"] == 100
    assert job["status"] == "completed"
