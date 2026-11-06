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
SOURCES = SRC / "lib" / "scraperSources.ts"
CARD = SRC / "components" / "scraper" / "ScraperSystemCard.tsx"
SYSTEM_MODAL = SRC / "components" / "scraper" / "ScrapeSystemModal.tsx"
ROM_MODAL = SRC / "components" / "scraper" / "ScrapeRomModal.tsx"
FOLDER = SRC / "components" / "scraper" / "RomFolderView.tsx"
TOPBAR = SRC / "components" / "layout" / "Topbar.tsx"


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
    sources = _read(SOURCES)
    for fuente in ("screenscraper", "thegamesdb", "igdb"):
        assert fuente in sources, f"falta la fuente {fuente}"
    assert "SCRAPER_SOURCES" in _read(SYSTEM_MODAL)
    assert "SCRAPER_SOURCES" in _read(ROM_MODAL)


def test_guardar_valida_las_credenciales_antes_de_cerrar():
    modal = _read(SYSTEM_MODAL)
    assert "sourceReady" in modal
    assert "if (!ready)" in modal
    # La validación ocurre antes de cerrar el modal.
    assert modal.index("if (!ready)") < modal.index("onClose()")


def test_al_guardar_un_juego_la_tabla_se_actualiza():
    """Guardar un juego deja la vista en el sistema, con la tabla al día.

    Antes se volvía a la lista de sistemas y el juego se quedaba en «media
    ausente» hasta que se recargaba a mano.
    """
    page = _read(PAGE)
    rom = re.search(r"const handleRomSaved = \(\) => \{(.*?)\n  \}", page, re.S)
    assert rom, "no se encontró el manejador de guardado de un juego"
    assert "refreshFolder" in rom.group(1), "hay que recargar la tabla de ROMs"
    assert "setSelected(null)" not in rom.group(1), "no debe salir del sistema"

    sistema = re.search(r"const handleSystemSaved = \(\) => \{(.*?)\n  \}", page, re.S)
    assert sistema, "no se encontró el manejador del scrape de sistema"
    assert "setSelected(null)" in sistema.group(1), "el scrape del sistema vuelve a la lista"


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


# ── Vista previa e imagen ─────────────────────────────────────────────

def test_el_modal_muestra_la_imagen_del_juego():
    modal = _read(ROM_MODAL)
    assert "image_url" in modal
    assert "/api/scraper/image" in modal, "la carátula debe servirse por el proxy"
    assert "<img" in modal


def test_el_backend_sirve_la_imagen_por_proxy():
    src = Path(appmod_path()).read_text(encoding="utf-8")
    assert "/api/scraper/image" in src
    assert "def _scraper_image_proxy" in src
    assert "Referer" in src, "ScreenScraper no sirve sus imágenes sin referer"


def appmod_path() -> str:
    """Ruta del backend desde la raíz del repo."""
    return str(ROOT / "app.py")


# ── Prioridad de fuentes ──────────────────────────────────────────────

def test_el_modal_de_rom_deja_elegir_las_fuentes():
    modal = _read(ROM_MODAL)
    assert "toggleSource" in modal
    assert "Fuentes (por orden de prioridad)" in modal
    assert "sources," in modal, "debe enviar la lista de fuentes a probar"


def test_el_orden_de_prioridad_es_screen_scraper_primero():
    sources = _read(SOURCES)
    assert sources.index("screenscraper") < sources.index("thegamesdb")
    assert sources.index("thegamesdb") < sources.index("igdb")


def test_el_modal_avisa_de_las_fuentes_sin_datos():
    modal = _read(ROM_MODAL)
    assert "fallbacks" in modal
    assert "no tenían datos" in modal


def test_el_scrape_de_sistema_ofrece_el_respaldo():
    modal = _read(SYSTEM_MODAL)
    assert "fallback_sources" in modal
    assert "respaldo" in modal.lower()


def test_el_scrape_de_sistema_prioriza_la_fuente_elegida():
    modal = _read(SYSTEM_MODAL)
    assert "source," in modal


# ── Botón de volver siempre visible ───────────────────────────────────

def test_el_boton_de_volver_esta_en_la_barra():
    """El botón de volver tiene que estar siempre en pantalla."""
    topbar = _read(TOPBAR)
    assert "leading" in topbar, "la barra superior debe admitir contenido a la izquierda"

    page = _read(PAGE)
    assert "leading=" in page
    assert "Volver" in page

    # Y ya no debe vivir dentro del contenido con scroll.
    assert (
        "mb-4 inline-flex cursor-pointer items-center gap-1.5 rounded-xl px-2 py-1.5"
        not in page
    ), "el botón de volver ya no debe estar en el contenido con scroll"


# ── La carátula tarda: hay que avisar mientras llega ──────────────────

def test_el_modal_avisa_mientras_carga_la_caratula():
    modal = _read(ROM_MODAL)
    assert "imgState" in modal, "debe seguir el estado de carga de la imagen"
    assert "onLoad" in modal, "hay que detectar cuándo la carátula está lista"
    assert "onError" in modal, "hay que detectar cuándo la carátula falla"
    assert "Cargando carátula" in modal, "debe avisar de que la carátula está llegando"


def test_el_backend_cachea_las_caratulas():
    """La descarga desde ScreenScraper tarda: no debe repetirse en cada apertura."""
    src = Path(appmod_path()).read_text(encoding="utf-8")
    assert "def scraper_proxy_image" in src
    assert "_IMG_PROXY_CACHE" in src, "las imágenes deben guardarse en caché"
    assert "def warm_scraper_image" in src, "la búsqueda debe pedir la imagen en segundo plano"
    assert "scraper_proxy_allowed" in src, "el proxy no debe ser un proxy abierto"


# ── Aviso en modal (éxito automático, error con log) ─────────────────

def test_existe_un_aviso_en_modal():
    hook = SRC / "hooks" / "useNotify.tsx"
    assert hook.exists(), "falta el proveedor de avisos en modal"
    texto = _read(hook)
    assert "NotifyProvider" in texto
    assert "showNotify" in texto
    # El éxito se cierra solo y el error espera a que se confirme.
    assert "autoCloseMs" in texto
    assert "AUTO_CLOSE_MS" in texto
    assert "Cerrar" in texto, "el error necesita un botón de confirmación"


def test_el_modal_de_rom_avisa_del_exito_y_del_error():
    modal = _read(ROM_MODAL)
    assert "useNotify" in modal
    assert "showNotify" in modal
    assert "variant: 'success'" in modal
    assert "variant: 'error'" in modal
    assert "detail:" in modal, "el error debe enseñar el log"


def test_el_scraping_de_sistema_avisa_al_terminar():
    modal = _read(SYSTEM_MODAL)
    assert "useNotify" in modal
    assert "showNotify" in modal
    assert "aggregated" in modal, "el aviso debe resumir el trabajo"


def test_la_tabla_se_actualiza_al_guardar_un_juego():
    """Tras guardar, la vista se queda en el sistema para ver el cambio."""
    page = _read(PAGE)
    assert "handleRomSaved" in page
    assert "handleSystemSaved" in page
    bloque = re.search(r"const handleRomSaved = \(\) => \{(.*?)\n  \}", page, re.S)
    assert bloque, "no se encontró el manejador de guardado"
    assert "refreshFolder" in bloque.group(1), "hay que recargar la tabla"
    assert "setSelected(null)" not in bloque.group(1), "no debe salir del sistema"
