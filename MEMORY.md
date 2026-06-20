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
├── app.py                 # ~2800 líneas — servidor HTTP + API REST + scraper + dashboard
├── templates/
│   └── index.html         # ~3120 líneas — SPA con todo el CSS/JS inline (l10n: es)
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

## Issues conocidos

1. **Sin tests/linting/typechecking** — No existe infraestructura de pruebas
2. **`install.sh` desactualizado** — Instala a `/userdata/system/batocera-manager/` pero `app_path` por defecto es `/userdata/system/batocera_web/app.py`
3. **Scraper necesita credenciales** — ScreenScraper.fr requiere user/pass en `batocera.conf`; TheGamesDB/IGDB requieren API key
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
