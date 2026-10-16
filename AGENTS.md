# Batocera System Manager Web — Agent Guide

## Run

- Start server: `python3 app.py` (default port 5000, listens on `0.0.0.0`)
- Custom port: `python3 app.py --port 5001`
- No dependencies required — pure Python stdlib HTTP server (`http.server.BaseHTTPRequestHandler`)
- PIL/Pillow is optional (placeholder logo generation; install with `python3 -m pip install pillow --break-system-packages`)

## Platform

- Linux-only, runs on **Batocera v43+**. Reads `/proc/stat`, `/proc/cpuinfo`, `/sys/class/thermal`, etc.
- All paths are under `/userdata/` (persistent storage). Defaults:
  - System CFGs: `/userdata/system/configs/emulationstation/es_systems_<slug>.cfg`
  - Settings: `/userdata/system/batocera_manager_settings.json`
  - ROMs: `/userdata/roms/<system>/`
  - Themes: `/userdata/themes/<theme>/<slug>/art/logo.png`
  - Autostart: `/userdata/system/custom.sh` (marker `# [batocera-manager]` / `# [/batocera-manager]`)
  - `python_path` default: detectado por glob (`/usr/lib/python3*/site-packages/configgen/emulatorlauncher.py`); fallback `python3.12`
- After creating a system CFG, restart ES: `batocera-es-swissknife --restart` (también `POST /api/es/restart`; `get_es_status()` expone `restart_pending`)

## Architecture

- **Single-file backend**: `app.py` (~4250 lines) — HTTP handler, dashboard, scraper (ScreenScraper.fr, TheGamesDB, IGDB), autostart manager
- **Single-file frontend**: `templates/index.html` (~4420 lines) — all CSS/JS inline, server-side rendered via `{{variable}}` string replacement
- ROM scan has a 60-second in-memory cache (`_rom_cache`)
- Settings are read from JSON file on every request (no in-memory cache for settings)
- `install.sh` is outdated: references Flask but app v1.2 uses pure stdlib; also installs to `/userdata/system/batocera-manager/` but app defaults `app_path` to `/userdata/system/batocera_web/app.py`

## Key notes

- **Tests**: 106 con `pytest` en `tests/` (backend stdlib + helpers de UI extraídos por regex). No hay linting ni typechecking
- UI is in Spanish (HTML `lang="es"`), variable names mix English and Spanish
- Scraper sources: ScreenScraper.fr (default, needs SS user/pass), TheGamesDB (needs API key), IGDB (needs Twitch Client ID + Secret)
- Credentials read from `batocera.conf` keys: `global.scrapper.user`, `global.scrapper.password`, etc.
- Scraping respects rate limits (`maxthreads` from SS response, minimum 0.5s delay)
- The `--port` CLI flag is the only command-line argument supported
