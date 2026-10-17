# -*- coding: utf-8 -*-
"""Tests de ss_search_game con sistemas sin mapeo en ScreenScraper.

Causa raíz del fallo en producción: para ROMs grandes (>128 MB, sin CRC),
ScreenScraper exige un `systemeid` válido. Si el sistema no está en
SS_SYSTEMS (valor 0), el scraping fallaba con HTTP 400 por cada ROM.
El fallback por nombre (jeuRecherche.php) sí funciona, pero `ss_search_game`
abortaba en el 400 antes de intentarlo.
"""
from __future__ import annotations


def test_ss_search_game_falls_back_to_name_when_system_unmapped(appmod, monkeypatch):
    """Sistema sin mapeo (sys_id=0): debe intentar búsqueda por nombre."""
    urls = []

    def fake_fetch(url, timeout=20):
        urls.append(url)
        # Primer intento (jeuInfos con systemeid=0) -> 400
        if "jeuInfos.php" in url:
            return None, "HTTP 400: Champ systemeid obligatoire si aucun CRC", {}
        # Segundo intento (jeuRecherche) -> éxito
        return {"header": {"success": "true"}, "response": {"jeu": {"id": "1"}}}, None, {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)

    jeu, err, quota = appmod.ss_search_game(
        "SomeGame.zip", "triforce", "u", "p",
        rom_path=None,  # sin CRC disponible
        devid="d", devpassword="dp",
    )

    assert jeu is not None, err
    assert err is None
    # Debe haber intentado el fallback por nombre
    assert any("jeuRecherche.php" in u for u in urls), urls


def test_ss_search_game_skips_jeuinfos_when_no_crc_and_unmapped(appmod, monkeypatch):
    """Si no hay CRC y el sistema no está mapeado, no debe llamar a jeuInfos
    (petición condenada al 400); debe ir directo al nombre."""
    urls = []

    def fake_fetch(url, timeout=20):
        urls.append(url)
        return {"header": {"success": "true"}, "response": {"jeu": {"id": "1"}}}, None, {}

    monkeypatch.setattr(appmod, "_ss_fetch_json", fake_fetch)

    appmod.ss_search_game(
        "SomeGame.zip", "triforce", "u", "p",
        rom_path=None,
        devid="d", devpassword="dp",
    )

    assert not any("jeuInfos.php" in u for u in urls), urls
    assert any("jeuRecherche.php" in u for u in urls), urls
