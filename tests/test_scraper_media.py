"""Tests de selección de medios y metadatos de ScreenScraper.

Cubren el bug crítico de `ss_media_url` (TypeError por usar SS_MEDIA_LAYOUT
como mapa de tipos) y la preferencia de región en los nombres.
"""


def _game_with(medias):
    return {"medias": medias}


def test_ss_media_url_exact_type_returns_url(appmod):
    game = _game_with([
        {"type": "box-2D", "region": "us", "url": "http://x/box.png", "format": "png"},
        {"type": "mixrbv1", "region": "wor", "url": "http://x/mix.png", "format": "png"},
    ])

    url, ext = appmod.ss_media_url(game, "mixrbv1", "wor")

    assert url == "http://x/mix.png"
    assert ext == ".png"


def test_ss_media_url_prefers_requested_region(appmod):
    game = _game_with([
        {"type": "wheel", "region": "us", "url": "http://x/us.png", "format": "png"},
        {"type": "wheel", "region": "jp", "url": "http://x/jp.png", "format": "png"},
    ])

    url, _ext = appmod.ss_media_url(game, "wheel", "jp")

    assert url == "http://x/jp.png"


def test_ss_media_url_unknown_type_returns_none(appmod):
    game = _game_with([
        {"type": "box-2D", "region": "wor", "url": "http://x/box.png", "format": "png"},
    ])

    url, ext = appmod.ss_media_url(game, "tipo-inexistente", "wor")

    assert url is None
    assert ext is None


def test_ss_media_url_no_medias_returns_none(appmod):
    url, ext = appmod.ss_media_url({"medias": []}, "box-2D", "wor")

    assert url is None
    assert ext is None


def test_ss_build_meta_uses_region_key_for_names(appmod):
    """`jeu.noms` va indexado por `region`, no por `langue`."""
    game = {
        "noms": [
            {"region": "us", "text": "Sonic the Hedgehog (USA)"},
            {"region": "wor", "text": "Sonic the Hedgehog"},
        ],
        "romnom": "Sonic.zip",
    }

    meta = appmod.ss_build_meta(game, region="wor", lang="es")

    assert meta["name"] == "Sonic the Hedgehog"


def test_ss_build_meta_uses_langue_key_for_synopsis(appmod):
    """`jeu.synopsis` va indexado por `langue`."""
    game = {
        "noms": [{"region": "wor", "text": "Juego"}],
        "synopsis": [
            {"langue": "en", "text": "English text"},
            {"langue": "es", "text": "Texto en español"},
        ],
    }

    meta = appmod.ss_build_meta(game, region="wor", lang="es")

    assert meta["desc"] == "Texto en español"


def test_is_gamelist_image_type_marks_primary_art(appmod):
    """Solo los tipos que producen `-image` deben alimentar `<image>`."""
    assert appmod.is_gamelist_image_type("box-2D") is True
    assert appmod.is_gamelist_image_type("mixrbv1") is True
    assert appmod.is_gamelist_image_type("ss") is True
    assert appmod.is_gamelist_image_type("wheel") is False
    assert appmod.is_gamelist_image_type("fanart") is False
    assert appmod.is_gamelist_image_type("video") is False
