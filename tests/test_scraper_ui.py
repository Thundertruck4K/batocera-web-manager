"""Tests de la sección de Scraper en la SPA.

Comprueban el código fuente del frontend: que la ruta exista, que la sección
ya no esté marcada como *Pronto* en el menú, que use la API de scraping de
Batocera sin enseñar las credenciales, que las tarjetas lleven icono temático
y número de ROMs, que al abrir un sistema se vea el reparto de media y que los
modales offercan Actualizar / Guardar / Editar.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"

NAV = SRC / "lib" / "nav.ts"
API = SRC / "lib" / "api.ts"
APP = SRC / "App.tsx"
PAGE = SRC / "pages" / "Scraper.tsx"
ICONS = SRC / "lib" / "systemIcons.ts"
CARD = SRC / "components" / "scraper" / "ScraperSystemCard.tsx"
SYSTEM_MODAL = SRC / "components" / "scraper" / "ScrapeSystemModal.tsx"
ROM_MODAL = SRC / "components" / "scraper" / "ScrapeRomModal.tsx"
FOLDER = SRC / "components" / "scraper" / "RomFolderView.tsx"


def _read(path: Path) -> str:
    assert path.exists(), f"falta {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


# ── Ruta y menú ────────────────────────────────────────────────────────

def test_la_seccion_tiene_ruta():
    app = _read(APP)
    assert 'path="/scraper"' in app
    assert "ScraperPage" in app


def test_el_menu_ya_no_marca_scraper_como_pendiente():
    nav = _read(NAV)
    linea = next(l for l in nav.splitlines() if "'/scraper'" in l)
    assert "pending" not in linea, "la sección de scraper ya está implementada"
    assert "Palette" in linea


def test_la_seccion_llama_a_los_endpoints_del_scraper():
    api = _read(API)
    for endpoint in (
        "/api/scraper/config",
        "/api/scraper/search",
        "/api/scraper/download",
        "/api/scraper/batch",
        "/api/scraper/save-config",
        "/api/rom-folder/",
    ):
        assert endpoint in api, f"falta el endpoint {endpoint}"


# ── Filtros ────────────────────────────────────────────────────────────

def test_la_pagina_tiene_filtros():
    page = _read(PAGE)
    assert "query" in page
    assert "typeFilter" in page
    assert "statusFilter" in page
    assert "sort" in page


def test_hay_filtro_por_estado_y_por_tipo():
    page = _read(PAGE)
    assert "STATUS_FILTERS" in page
    assert "Con ROMs" in page and "Sin media" in page and "Vacíos" in page
    assert "typeFilter" in page and "types.map" in page


def test_la_pagina_ordena_los_sistemas():
    page = _read(PAGE)
    assert "Más ROMs" in page
    assert "Menos ROMs" in page
    assert "Cobertura" in page


# ── Tarjetas ───────────────────────────────────────────────────────────

def test_la_tarjeta_muestra_icono_nombre_descripcion_y_roms():
    card = _read(CARD)
    assert "systemIcon" in card
    assert "fullname" in card
    assert "manufacturer" in card
    assert "rom_count" in card


def test_los_iconos_son_tematicos_por_sistema():
    icons = _read(ICONS)
    for icono in ("Joystick", "Gamepad2", "Tablet", "Terminal", "Package"):
        assert icono in icons, f"falta el icono {icono}"


def test_los_iconos_tienen_respaldo_por_tipo():
    icons = _read(ICONS)
    assert "iconByType" in icons
    for tipo in ("Arcade", "Portátiles", "Ordenadores", "Consolas"):
        assert tipo in icons, f"falta el tipo {tipo}"


# ── Pantalla de ROMs ───────────────────────────────────────────────────

def test_la_pagina_muestra_media_presente_y_ausente():
    folder = _read(FOLDER)
    assert "Media presente" in folder
    assert "Media ausente" in folder


def test_el_reparto_se_hace_con_el_campo_has_image():
    folder = _read(FOLDER)
    assert "has_image" in folder
    assert "withMedia" in folder and "withoutMedia" in folder


def test_el_traslado_entre_pantallas_usa_fade():
    page = _read(PAGE)
    assert "AnimatePresence" in page
    assert 'mode="wait"' in page
    assert "opacity" in page


def test_la_tarjeta_abre_el_modal_de_rom():
    page = _read(PAGE)
    assert "ScrapeRomModal" in page
    assert "onOpenRom" in page
    assert "setRomItem" in page


def test_las_caraturas_salen_del_servidor():
    folder = _read(FOLDER)
    assert "/api/rom-image/" in folder
    assert "subpath" in folder


# ── Modales flotantes ──────────────────────────────────────────────────

def test_el_modal_de_sistema_tiene_actualizar_guardar_y_editar():
    modal = _read(SYSTEM_MODAL)
    for boton in ("Actualizar", "Editar", "Guardar"):
        assert boton in modal, f"falta el botón {boton}"


def test_el_modal_de_rom_tiene_actualizar_guardar_y_editar():
    modal = _read(ROM_MODAL)
    for boton in ("Actualizar", "Editar", "Guardar"):
        assert boton in modal, f"falta el botón {boton}"


def test_los_modales_son_flotantes():
    for modal in (_read(SYSTEM_MODAL), _read(ROM_MODAL)):
        assert "<Modal" in modal


def test_el_modal_admite_varias_fuentes_de_scraping():
    icons = _read(ICONS)
    for fuente in ("screenscraper", "thegamesdb", "igdb"):
        assert fuente in icons, f"falta la fuente {fuente}"
    assert "SCRAPER_SOURCES" in _read(SYSTEM_MODAL)


def test_guardar_valida_las_credenciales_antes_de_cerrar():
    modal = _read(SYSTEM_MODAL)
    assert "sourceReady" in modal
    assert "if (!ready)" in modal
    # La validación ocurre antes de cerrar el modal.
    assert modal.index("if (!ready)") < modal.index("onClose()")


def test_al_guardar_se_vuelve_a_la_lista_principal():
    page = _read(PAGE)
    handle = page[page.index("const handleSaved"):]
    assert "setSelected(null)" in handle
    assert "setRomItem(null)" in handle


def test_el_modal_de_rom_guarda_los_metadatos_editados():
    modal = _read(ROM_MODAL)
    assert "api.updateRomMeta" in modal
    assert "api.scraperDownload" in modal


# ── Credenciales ───────────────────────────────────────────────────────

def test_el_frontend_no_muestra_las_credenciales_en_claro():
    modal = _read(SYSTEM_MODAL)
    # Sólo se permite leer el indicador «_set» (si hay credenciales guardadas),
    # nunca el valor de la credencial.
    for credencial in (
        "ss_user",
        "ss_password",
        "ss_devid",
        "ss_devpassword",
        "tgdb_apikey",
        "igdb_client_id",
        "igdb_client_secret",
    ):
        acceso = re.search(rf"config\.{credencial}(?![_A-Za-z0-9])", modal)
        assert acceso is None, f"se está pintando config.{credencial}"
    assert "_set" in modal, "debe usar los indicadores de «configurado»"


def test_el_scraping_no_manda_credenciales_al_servidor():
    modal = _read(SYSTEM_MODAL)
    bloque = re.search(r"api\.scrapeBatch\(\{(.*?)\}\)", modal, re.S)
    assert bloque, "no se encontró la llamada al trabajo por lotes"
    for credencial in ("ss_user", "ss_password", "tgdb_apikey", "igdb_client_id"):
        assert credencial not in bloque.group(1), f"se manda {credencial} al scrape"


def test_la_descarga_de_un_rom_no_manda_credenciales():
    modal = _read(ROM_MODAL)
    bloque = re.search(r"api\.scraperDownload\(\{(.*?)\}\)", modal, re.S)
    assert bloque, "no se encontró la llamada de descarga"
    for credencial in ("ss_user", "ss_password", "tgdb_apikey", "igdb_client_id"):
        assert credencial not in bloque.group(1), f"se manda {credencial} al scrape"
