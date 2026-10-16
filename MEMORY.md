# MEMORY — Batocera System Manager Web

Proyecto: `batocera_web` v1.2  
Repositorio: `C:\Users\folk3\Downloads\batocera_web`  
Plataforma destino: **Batocera v43+** (Linux, Python 3.12 stdlib)

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | `http.server.BaseHTTPRequestHandler` (stdlib puro, sin Flask) |
| Frontend | SPA con HTML/CSS/JS inline en `templates/index.html` |
| Scraping | ScreenScraper.fr, TheGamesDB, IGDB (Twitch) |
| Dependencias | **Cero** — solo stdlib. Pillow opcional para placeholders de logos |
| CLI | `--port N` (único flag) |

---

## Estructura

```
batocera_web/
├── app.py                 # ~4250 líneas — servidor HTTP + API REST + scraper + dashboard
├── templates/
│   └── index.html         # ~4440 líneas — SPA con todo el CSS/JS inline (l10n: es)
├── batocera_systems.json  # 220 sistemas oficiales con emuladores y cores
├── AGENTS.md              # Guía operativa para asistentes de IA
├── install.sh             # Script de instalación (heredado de v1.0)
├── LICENSE                # MIT
├── MEMORY.md              # Este archivo
└── README.md              # Documentación de usuario
```

---

## Línea de tiempo de cambios

### `44effde` — Estado inicial (v1.2 original)
App funcional con ~1700 líneas de backend, ~2870 de frontend. Instalación por copia manual.

---

### `589bfc7` — docs: add LICENSE, update README to v1.2, expand .gitignore
**Archivos:** `LICENSE` (nuevo), `README.md` (reescrito), `.gitignore` (expandido)

- Licencia MIT agregada
- README actualizado a v1.2: sin Flask, Python 3.12, API reference completa
- `.gitignore` con patrones Python + IDE

---

### `d7b9bff` — fix: path traversal, update install.sh, harden security and UI
**Archivos:** `app.py`, `install.sh`, `templates/index.html`

**Seguridad:**
- Path traversal validado en `DELETE /api/rom/` y `_serve_rom_image`
- `Connection: close` en todas las respuestas JSON

**Scraper:**
- DevID por defecto cambiado de `recalbx` a `batocera_manager`

**Frontend:**
- `uploadBios()` corregido (llamaba `openBiosPanel()` dos veces)
- Selección de nav-item cambiada a `querySelector` (índice frágil)
- `human_size()` con `abs()` para floats negativos

**Instalación:**
- `install.sh` actualizado a v1.2: sin Flask ni Pillow como obligatorios, rutas corregidas

---

### `952fccb` — feat: detect all GPUs (iGPU + dGPU), add nvidia-smi support
**Archivos:** `app.py`, `templates/index.html`

**Backend (`get_gpu_info()` reescrita):**
- Antes: solo detectaba la primera GPU via DRM (`/sys/class/drm/`)
- Ahora: escanea TODAS las tarjetas DRM + ejecuta `nvidia-smi` para GPUs NVIDIA
- `_gpu_from_drm()`: extrae vendor, temp, frecuencia de sysfs por tarjeta
- `_gpu_from_nvidia_smi()`: parsea JSON de `nvidia-smi --query-gpu=... --format=csv,noheader,nounits` para temperatura, uso, VRAM, potencia
- Retorna `gpus[]` con todas las GPUs detectadas + campos `first`/`count` para compatibilidad

**Frontend:**
- Renderiza una dash-card por GPU
- Color del borde por vendor: NVIDIA `#76b900` (verde), AMD `#ff6900` (naranja), otros `#bc8cff` (púrpura)

---

### `d0237c7` — feat: comprehensive BIOS_DB from official batocera-systems source
**Archivos:** `app.py`, `templates/index.html`

**BIOS_DB:**
- Antes: ~30 sistemas hardcodeados con entradas incompletas y algunos MD5 incorrectos
- Ahora: **108 sistemas**, **376 entradas de BIOS** con MD5 extraídos del script oficial `batocera-systems` de Batocera (GitHub upstream)
- Incluye sistemas faltantes: `hikaru`, `naomi2`, `chihiro`, `triforce`, `gamecube`, `psvita`, `segaai`, etc.
- Script generador propio: `generate_bios_db.py` (eliminado post-commit)

**check_bios():**
- Antes: retornaba lista plana → frontend no distinguía "no encontrado" de "sin BIOS"
- Ahora: retorna `{"known": bool, "files": [...]}`
- `known: false` → sistema no está en la base de datos
- `known: true` + `files: []` → sistema conocido sin BIOS requeridas
- `known: true` + `files: [...]` → lista detallada con estado MD5

**Frontend (`renderBios()`):**
- Tres estados diferenciados: "sistema no encontrado", "no requiere BIOS", tabla de verificación
- Adaptado al nuevo formato `data.bios.files`

---

### `feat(HEAD)` — scraping batch, BIOS_DB regenerator, tests, MEMORY update

**Archivos nuevos:** `generate_bios_db.py`, `tests/bios_validator.py`

**Scraping batch programable:**
- Sistema de jobs en background (thread daemon) con cola FIFO
- Endpoints REST: creación, listado, detalle, cancelación
- `do_scrape_system()` extraída como función standalone reusable
- `save_gamelist_entry()` extraída para eliminar dependencia del handler
- UI: tab "Lote múltiple" en modal de scraping, checkboxes por sistema,
  barra de progreso, listado de jobs activos/completados, polling cada 2s
- Backward compatible: endpoint original `/api/scraper/scrape-system` sin cambios

**Script generador BIOS_DB (`generate_bios_db.py`):**
- Descarga `batocera-systems` desde GitHub upstream
- Parsea con `ast` (no regex) para robustez
- Genera `BIOS_DB` y `NOBIOS_PLATFORMS` como código Python ready-to-replace

**BIOS_DB actualizado:**
- De 376 entradas a **705 entradas upstream** (108 sistemas)
- Se regeneró ejecutando `generate_bios_db.py` y reemplazando en `app.py`
- Muchos sistemas ahora tienen MD5s específicos en vez de `None`

**Tests (`tests/bios_validator.py`):**
- `bios_validator.py` compara BIOS_DB local contra upstream
- Reporta sistemas faltantes, entradas extra, diferencias de MD5
- Útil para detectar cuándo regenerar BIOS_DB

---

### `e0f34e2` — fix: case-insensitive BIOS lookup + acknowledge 35 no-BIOS platforms
**Archivos:** `app.py`

**Slug matching:**
- `_bios_key()` normaliza cualquier slug a minúscula + trim antes de buscar
- `_BIOS_LOOKUP`: diccionario combinado `BIOS_DB` + `NOBIOS_PLATFORMS` con claves normalizadas
- `_get_bios_entries()`: helper único para todas las búsquedas
- Previene falsos negativos por mayúsculas/minúsculas o espacios

**NOBIOS_PLATFORMS:**
- 35 plataformas comunes de Batocera que **no requieren BIOS**:
  `3ds`, `amiga`, `amstradcpc`, `arcade`, `atari2600`, `atari7800`, `c64`,
  `famicom`, `fba`, `gamegear`, `gb`, `gbc`, `gc`, `genesis`, `jaguar`,
  `mame`, `mastersystem`, `megacd`, `megadrive`, `n64`, `nes`, `ngp`,
  `pc`, `pce`, `psp`, `sega32x`, `sg1000`, `snes`, `tg16`, `virtualboy`,
  `wii`, `wiiu`, `wonderswan`, `wonderswancolor`, `zxspectrum`
- Ahora muestran "✔ no requiere BIOS" en vez de "sistema no encontrado"

---

## Hardware de desarrollo

| Componente | Modelo |
|-----------|--------|
| Laptop | ASUS TUF Gaming A15 FA506NF |
| CPU | AMD Ryzen 5 7535HS (6C/12T) + Radeon 660M iGPU |
| GPU | NVIDIA GeForce RTX 2050 (4 GB) |
| SO | Batocera 43acu.1 |
| IP | 192.168.1.88 |

---

### `5cf5842` — feat: group duplicate BIOS entries, accordion on BIOS Faltantes, MD5 validation on upload
**Archivos:** `app.py`, `templates/index.html`

**Backend (`_check_bios_grouped()` nueva):**
- Agrupa entradas BIOS por filename: un archivo con 8 MD5s → 1 fila en vez de 8
- `check_bios()`: soporta compatibilidad hacia atrás (elimina `valid_md5s` interno de la respuesta)
- `/api/bios/all`: endpoint completo (para uso futuro)
- `_upload_bios()`: acepta `system` + `file`, calcula MD5 del subido, lo compara contra BIOS_DB, retorna `md5_valid` + `valid_md5s`

**Frontend — ROM & BIOS (sin cambios visuales):**
- `openBiosPanel()` y `renderBios()` mantienen comportamiento original: verifican solo el sistema actual, tabla plana sin acordeón
- Botón "⬆ Subir BIOS" genérico restaurado debajo de la tabla

**Frontend — BIOS Faltantes (acordeón):**
- `renderMissingBios()` ahora renderiza acordeón colapsable por sistema (▶/▼)
- Misma estructura de acordeón que el resto: header clickeable, body expandible
- `uploadSingleBios()` envía `system` + `file` para validación MD5
- Toast indica si MD5 es correcto (✔), incorrecto (⚠) o sin referencia
- Barra de progreso se pinta amarilla si MD5 falla

---

### `current` — edit custom systems, dynamic emulator/core selector, batocera_systems.json, scraper paths fixed
**Archivos:** `app.py`, `templates/index.html`, `batocera_systems.json` (nuevo)

**Edición de sistemas personalizados:**
- `POST /api/update` → `_update_system()`: renombra `.cfg` si cambia el slug (mueve el archivo)
- `GET /api/system/<name>/detail` → `get_custom_system_detail()`: retorna datos + emuladores disponibles
- Botón "✏ Editar" en cada tarjeta de sistema, formulario reutilizado con toggle crear/editar
- Variable global `_editingSystem` trackea el slug original para `old_name` en update

**Base de datos oficial de Batocera:**
- `batocera_systems.json`: 220 sistemas con emuladores y cores, extraído de `table_cache.json` (sitio de compatibilidad oficial de Batocera)
- `GET /api/batocera-systems` sirve el JSON al frontend
- `load_batocera_systems()` carga al inicio, estructura: `{slug: {name, emulators: [{name, libretro, cores, extras}]}}`

**Selector dinámico de emulador/core:**
- Dropdown de sistema referencia (220 opciones) auto-completa nombre, slug, ruta ROM, theme
- Emulador se filtra por sistema seleccionado
- Si el emulador es `libretro`: muestra selects de core y cores adicionales (multi-select tag)
- Si es standalone (dolphin, pcsx2, model2, etc.): campos core/extra se ocultan automáticamente
- `onEmulatorChange()`, `populateCores()`, `applyRefSystem()` en frontend

**Scraper — imágenes en carpeta plana del sistema:**
- `_scraper_download()`: todos los sources (SS, TGDB, IGDB) guardan en `roms_base/<rom_stem>.png` (sin subcarpeta `media/`)
- `meta["image_path"]` = `"./<rom_stem>.png"` en los tres sources

**`save_gamelist_entry()` con `ET.indent()`:**
- Reemplazado `minidom.parseString().toprettyxml()` por `ET.indent()` (Python 3.9+)
- Evita caracteres escapados incorrectamente y pérdida de datos por round-trip frágil
- Soporta campos `year` → `releasedate`, omite valores `None`

**Frontend — refresh ROM tras scrape:**
- `scraperDownload()` actualiza `currentRoms[].has_image` en memoria
- Si el modal ROM está abierto, re-ejecuta `showRomDetail(romIdx)` para reflejar cambios inmediatamente

---

### `95243de` — feat: fan monitor in dashboard (hwmon RPM + animated SVG + failure alerts)

**Archivos:** `app.py`, `templates/index.html`, `README.md`

**Backend:**
- `get_fans()`: escanea `/sys/class/hwmon/hwmon*/fan*_input`, extrae RPM, label, min, flags fault/alarm
  y deriva estado: `ok` / `stopped` (RPM=0 o RPM < min) / `fault` (flag fan*_fault=1)
- Endpoint nuevo `GET /api/fans`
- `get_dashboard()` incluye `fans` en el payload

**Frontend:**
- Fila "Ventiladores" en el dashboard con tarjetas por ventilador
- SVG animado (3 aspas) cuya velocidad de giro escala con las RPM; se pausa si está parado/falla
- RPM en vivo, badge de estado OK/FALLO/DETENIDO con color (verde/rojo/amarillo)
- Banner de alerta superior si hay fallo o ventilador detenido
- Toast de notificación al transicionar ok → fault/stopped (una sola vez por fan)
- Polling independiente cada 1s (`_fanTimer`) mientras el panel dashboard está activo;
  se limpia al cambiar de panel

---

### `95243de` — feat: braille graphs (btop style) in dashboard, dashboard as default panel

**Archivos:** `templates/index.html` (dashboard Fila 3 reescrita)

**Gráficos braille (estilo btop):**
- `brailleGraph(values, height)`: dibuja línea de valores sobre grid braille Unicode
  (U+2800..U+28FF), conectando puntos, 2 muestras por carácter
- `collectHist()`: acumula historial en el frontend — disco (`pct` por mount, 40 muestras),
  red (delta de `rx_raw`/`tx_raw` → bytes/s, 40 muestras), procesos (CPU% por pid, 30 muestras)

**Almacenamiento:** barra sólida reemplazada por línea braille del historial de uso,
color verde/amarillo/rojo según pct

**Red:** texto de totales reemplazado por tasa viva (`fmtRate`) + 2 gráficos braille dinámicos
(↓ verde, ↑ accent) por interfaz

**Procesos:** sparkline braille de CPU% por proceso con color por nivel (rojo>50 / amarillo>20)

**Efectos:** `.braille` con `text-shadow: currentColor` (glow) y `@keyframes brailleGlow`
(pulso de brillo en cada actualización)

**Dashboard como panel inicial:**
- `panel-dashboard` y nav "Dashboard" ahora tienen `active` (antes `panel-add`)
- `init()` llama a `initDashboard()` al arrancar (carga datos + timer de ventiladores)
- Topbar por defecto: "📊 Dashboard / Estado del sistema en tiempo real — Batocera"
- GPU: solo tarjeta NVIDIA, deduplicada por vendor (descarta duplicados DRM y AMD)

---

### `95243de` — Roms & BIOS overhaul: rutas Batocera, devid opcional, validación de subidas

**Archivos:** `app.py`, `templates/index.html`, `README.md`

**Scraper ScreenScraper (replicando Batocera exacto):**
- `SS_API` → `https://api.screenscraper.fr/apiv2` (antes `www.screenscraper.fr/api2`)
- `SS_SYSTEMS` reemplazado por mapa completo de `screenscraper_platformid_map` (c64=66, lynx=28, sg1000=109, snes=4…)
- `ss_search_game()` reescrita: `jeuInfos.php` con `md5`/`crc`/`romtaille`/`systemeid`/`romtype=rom` (hash solo si archivo ≤128 MB), fallback `jeuRecherche.php` por nombre limpio
- Exige `devid`/`devpassword` reales (con cuenta normal SS responde 403); mensaje amigable si faltan
- `get_scraper_config()`: lee `global.scrapper.devid`/`devpassword`, normaliza región (`world`→`wor`)

**Imágenes estilo Batocera (`getSaveAsPath` de batocera-emulationstation):**
- `SS_MEDIA_LAYOUT`: mapea tipo→(carpeta,sufijo) — `mixrbv1/ss/box-2D→images/-image`, `box-3D→-box`, `box-2D-back→-boxback`, `wheel→-wheel`, `marquee→-marquee`, `fanart→-fanart`, `video→videos/-video`, `manual→manuals/-manual`
- `batocera_media_path()`: devuelve `(dest, "./images/<stem>-<sufijo>.<ext>")`
- `ss_media_url()`: preferencia de región (region→wor→us→eu→jp), extensión real del medio
- `do_scrape_system()` y `_scraper_download()` guardan cada tipo en su ruta/sufijo sin sobreescribirse
- `download_image_generic()` con cabecera `Referer` para medios de ScreenScraper
- `save_gamelist_entry()`: soporta `subpath` (ROMs en subcarpetas → `./sub/file.ext`)
- `_serve_rom_image` + `/api/rom-image-info`: fallbacks a sufijos Batocera (`-image`, `-thumb`, `-box`…) en `images/`

**Subidas seguras:**
- `get_system_extensions()`: lee extensiones por sistema de `/usr/share/emulationstation/es_systems.cfg` + `es_systems_*.cfg` custom
- `_upload_rom()`: rechaza extensiones no permitidas (lista en la respuesta)
- `_upload_bios()`: respeta subcarpetas de `file` (`neocd/neocd_f.rom`) + guard de path traversal

**Frontend:**
- Campos `devid`/`devpassword` opcionales en Config y tabs single/system/batch del scraper
- `batchRenderSystems()`: nombre con `min-width:0` + conteo de ROMs por sistema
- Helpers backend nuevos: `crc32_file()`, `_ss_fetch_json()`, `_ss_quota()`, `_ss_parse_jeu()`

**Verificado en máquina (192.168.1.91):** SS sin devid→error amigable, IGDB funciona end-to-end (imagen en `images/Aladdin (Spain)-image.jpg` + gamelist correcto), rechazo de `.txt` para snes, subida BIOS a `neocd/` y guard traversal OK.

---

### `c64b7c2..ae45171` — 7 arreglos de fondo (TDD, 42 → 76 tests)

Cada tarea es un commit atómico con su test; la historia completa se verificó
commit a commit en un worktree temporal (todos GREEN).

| # | Arreglo | Commit |
|---|---------|--------|
| 1 | Reinicio **manual** de ES: `POST /api/es/restart` + flag `restart_pending` en `get_es_status()`; se marca al crear/editar/borrar sistemas | `c64b7c2` |
| 2 | Skip de BIOS persistido en `batocera_manager_bios_skipped.json` (antes solo en memoria); nuevos endpoints `unskip` y `skipped` | `f1b11b6` |
| 3 | `_detect_configgen_path()`: `python_path` se detecta por glob (`python3*`) en vez de hardcodear `/usr/lib/python3.12/...` | `f8b1aea` |
| 4 | `get_system_extensions()`: una definición de usuario **reemplaza** a la integrada (no se unen) — semántica de EmulationStation | `7a919e1` |
| 5 | `delete_custom_system()`: `DELETE /api/system/<name>` borra solo ese `<system>`; el `.cfg` se elimina solo si queda vacío | `a131c3a` |
| 6 | `_scraper_start_lock`: comprobación + arranque atómicos en `_start_batch_worker` (dos peticiones podían crear dos workers) | `dd2fd26` |
| 7 | `tests/bios_validator.py`: `_norm_md5()` admite `md5` como lista (upstream) y `sorted()` tolera `None` | `ae45171` |

Notas:
- `restart_emulationstation()` usa `batocera-es-swissknife --restart` y **nunca se
  invoca solo**: interrumpe la UI en pantalla, solo va vía endpoint/botón.
- Tests nuevos: `test_es_restart`, `test_bios_skip`, `test_configgen`,
  `test_extensions`, `test_system_delete`, `test_batch_worker`,
  `test_bios_validator`.

---

## Issues conocidos

1. **Infraestructura de pruebas** — 76 tests (`pytest`, `tests/`) sin linting ni typechecking
2. **`install.sh` desactualizado** — Instala a `/userdata/system/batocera-manager/` pero `app_path` por defecto es `/userdata/system/batocera_web/app.py`
3. **ScreenScraper sin devid** — SS exige `devid`/`devpassword` de desarrollador (la cuenta normal da 403). El gestor los acepta opcionales; sin ellos usar TGDB/IGDB
4. **Cache de ROMs en memoria** — `_rom_cache` con TTL de 60s, no persiste entre reinicios del servidor
5. **Settings sin cache** — Se lee el JSON en cada request
6. **Sin autenticación** — El servidor expone toda la API sin protección
7. **Sin HTTPS** — Tráfico en texto plano
8. **BIOS_DB no incluye todos los sistemas MAME** — Los BIOS de arcade/MAME están dentro de los ROMs ZIPs, no se verifican separadamente

---

## Cómo contribuir / Próximos pasos

Ver `README.md` → Roadmap y `AGENTS.md` → guía operativa.

Áreas prioritarias:
- Autenticación básica opcional
- Scraping batch programable
- Tests (al menos validación de BIOS_DB contra upstream)
- Script de actualización de BIOS_DB (re-ejecutar generador contra `batocera-systems`)
