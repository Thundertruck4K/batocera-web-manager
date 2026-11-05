"""Tests del conteo de juegos con imagen por sistema.

La tarjeta del scraper dice cuántos juegos tienen ya su imagen. Ese número
sale del `<image>` del gamelist.xml y sólo cuenta los ROMs que siguen en la
carpeta: el gamelist puede traer entradas de ROMs ya borrados.
"""
from __future__ import annotations

from pathlib import Path

GAMELIST = """<?xml version="1.0" encoding="UTF-8"?>
<gameList>
    <game><path>./Juego con imagen.sfc</path><image>./images/j1.png</image></game>
    <game><path>./Juego sin imagen.sfc</path></game>
    <game><path>./Juego borrado.sfc</path><image>./images/j2.png</image></game>
    <game><path>./Carpeta/Juego en subcarpeta.sfc</path><image>./images/j3.png</image></game>
    <game><path>./notas.txt</path><image>./images/j4.png</image></game>
</gameList>
"""


def _preparar(tmp_path):
    """Crea una biblioteca con un sistema y devuelve (settings, sistemas)."""
    base = tmp_path / "roms"
    sistema = base / "snes"
    sistema.mkdir(parents=True)
    (sistema / "Juego con imagen.sfc").write_bytes(b"rom1")
    (sistema / "Juego sin imagen.sfc").write_bytes(b"rom2")
    (sistema / "notas.txt").write_text("notas", encoding="utf-8")
    (sistema / "gamelist.xml").write_text(GAMELIST, encoding="utf-8")

    systems = [
        {
            "name": "snes",
            "roms": [
                {"filename": "Juego con imagen.sfc", "name": "Juego con imagen",
                 "ext": ".sfc", "is_rom": True},
                {"filename": "Juego sin imagen.sfc", "name": "Juego sin imagen",
                 "ext": ".sfc", "is_rom": True},
                {"filename": "notas.txt", "name": "notas", "ext": ".txt", "is_rom": False},
                {"filename": "Carpeta", "name": "Carpeta", "ext": "dir", "is_rom": True},
            ],
        }
    ]
    return {"roms_base": str(base)}, systems


def test_cuenta_solo_los_roms_que_siguen_en_la_carpeta(appmod, tmp_path):
    settings, systems = _preparar(tmp_path)

    counts = appmod.count_systems_with_images(settings, systems)

    # «Juego con imagen» sí; «Juego sin imagen» no; «Juego borrado» tampoco
    # (ya no está en la carpeta); «notas.txt» no es un ROM.
    assert counts["snes"] == 1


def test_un_sistema_sin_gamelist_no_tiene_imagenes(appmod, tmp_path):
    base = tmp_path / "roms"
    (base / "vacio").mkdir(parents=True)
    settings = {"roms_base": str(base)}
    systems = [{"name": "vacio", "roms": []}]

    counts = appmod.count_systems_with_images(settings, systems)

    assert counts["vacio"] == 0


def test_el_conteo_se_cachea_entre_llamadas(appmod, tmp_path):
    settings, systems = _preparar(tmp_path)

    first = appmod.count_systems_with_images(settings, systems)
    second = appmod.count_systems_with_images(settings, systems)

    assert first == second
    assert appmod._image_count_cache


def test_el_resumen_expone_el_conteo_de_imagenes(appmod, tmp_path):
    settings, systems = _preparar(tmp_path)
    counts = appmod.count_systems_with_images(settings, systems)
    system = {
        "name": "snes",
        "rom_count": 2,
        "media_count": 0,
        "size_human": "1 KB",
        "is_empty": False,
        "has_gamelist": True,
        "has_bios": False,
        "bios_count": 0,
        "image_count": counts["snes"],
    }

    summary = appmod.rom_system_summary(system)

    assert summary["image_count"] == 1


def test_el_resumen_sin_conteo_devuelve_cero(appmod):
    summary = appmod.rom_system_summary({
        "name": "zzz", "rom_count": 0, "media_count": 0, "size_human": "0 B",
        "is_empty": True, "has_gamelist": False, "has_bios": False, "bios_count": 0,
    })

    assert summary["image_count"] == 0


def test_el_endpoint_rellena_el_conteo_de_imagenes(appmod):
    """El listado de sistemas tiene que mandar el conteo de media."""
    src = Path(appmod.__file__).read_text(encoding="utf-8")
    assert "count_systems_with_images(s, systems)" in src
    assert 'x["image_count"] = images.get(x["name"], 0)' in src
