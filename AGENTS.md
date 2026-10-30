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

- **Single-file backend**: `app.py` (~5780 lines) — HTTP handler, dashboard, scraper (ScreenScraper.fr, TheGamesDB, IGDB), autostart manager
- **Frontend React**: `frontend/` — React 19 + TypeScript + Vite 6 + Tailwind CSS v4. El backend sirve
  `frontend/dist/` cuando está compilado; si no lo está, cae a la interfaz clásica de un solo fichero
  (`templates/index.html`), que sigue siendo el respaldo. Ver «Frontend» más abajo.
- ROM scan has a 60-second in-memory cache (`_rom_cache`)
- Settings are read from JSON file on every request (no in-memory cache for settings)
- `install.sh` is current (v1.4): installs to `/userdata/system/batocera_web/` (matches the default `app_path`), pure stdlib, no Flask. Supports `BM_BASE_DIR`, `BM_CUSTOM_SH`, `BM_PYTHON`, `BM_PORT` overrides

## Frontend (React + Tailwind)

- `frontend/` es un proyecto Vite independiente: `npm install` y `npm run build` (salida en
  `frontend/dist/`, que **sí se versiona** porque el dispositivo no tiene Node).
- **Tokens del design system**: `frontend/src/index.css` — tema oscuro `#121212` / claro `#f8f9fa`,
  tarjeta `#161616` / blanco, escenario `#0d0d0d`, escala monocroma para gráficos (`--chart-1..4`).
  Se alternan con la clase `.dark` en `<html>`. Curva de movimiento única
  `cubic-bezier(0.16, 1, 0.3, 1)`, duraciones < 300 ms.
- **La API no cambia**: el frontend consume los mismos endpoints `/api/*` que la interfaz clásica.
  `frontend/src/lib/api.ts` es el cliente tipado; `frontend/src/lib/normalize.ts` rellena los campos
  que faltan cuando el backend las deja vacíos (fuera de Linux no hay `/proc` ni `/sys`) para que la
  interfaz degrade en lugar de romperse con una pantalla en blanco.
- En desarrollo: `npm run dev` (Vite en :5173) hace de proxy de `/api` hacia el backend en :5000.
  Variable `BATOCERA_BACKEND` para cambiar el destino del proxy.
- **La interfaz clásica sigue viva**: `templates/index.html` y sus tests (`tests/test_mono_charts.py`,
  `tests/test_ui_theme.py`) no se tocan. `render_index()` no ha cambiado; `render_app()` elige la SPA
  si `frontend/dist/index.html` existe y si no, la clásica.

## Key notes

- **Tests**: 438 con `pytest` en `tests/` (41 ficheros de test; backend stdlib + helpers de UI extraídos por regex). No hay linting ni typechecking
- UI is in Spanish (HTML `lang="es"`), variable names mix English and Spanish
- **Design system "mono"**: dos capas conviven.
  - *Clásica* (`templates/index.html`): tokens `--mono-*` y piezas (`.mono-stage`, `.mono-pill`,
    `.mono-foot`, `.mono-row`) en el `<style>` inline. Los gráficos los dibuja el objeto `MonoCharts`
    (gauge de 240°, barras, donut, área monótona) en JS puro.
  - *React* (`frontend/src/index.css`): los mismos tokens traducidos a variables CSS de Tailwind v4
    (`--color-card`, `--color-stage`, `--color-chart-1..4`…) y componentes en `frontend/src/components/`.
    Los gráficos usan **Recharts** (`animationDuration={280}`, el límite del design system).
  - Al tocar un token, tócalo en las dos capas para que no se desincronicen.
- Scraper sources: ScreenScraper.fr (default, needs SS user/pass), TheGamesDB (needs API key), IGDB (needs Twitch Client ID + Secret)
- Credentials read from `batocera.conf` keys: `global.scrapper.user`, `global.scrapper.password`, etc.
- Scraping respects rate limits (`maxthreads` from SS response, minimum 0.5s delay)
- The `--port` CLI flag is the only command-line argument supported

## Workflow

- The `superpowers` plugin is installed at `C:\Users\folk3\.minimax\plugins\superpowers/` — a port of https://github.com/obra/superpowers v7.0.1 (MIT, obra). Its 15 skills appear in the catalog as `superpowers:<name>` (e.g. `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:systematic-debugging`).
- A `SessionStart` hook injects the `using-superpowers` bootstrap plus the MiniMax Code tool mapping (`skills/using-superpowers/references/mcode-tools.md`) at session start. The skill catalog itself is rebuilt on session start, so a freshly installed plugin needs a new session to become loadable.
- Specs and plans live in `docs/superpowers/specs/` and `docs/superpowers/plans/` (`YYYY-MM-DD-<slug>-design.md` and `YYYY-MM-DD-<slug>-plan.md`).
- Tool mapping for this harness: `Read`→`read`, `Write`→`write`, `Edit`→`edit`, `Bash`→`bash`, `Glob`→`glob`, `Grep`→`grep`, `TodoWrite`→`todowrite`, `Task`→`task`, `Skill`→`skill`. The `bash` tool is **PowerShell 5.1 on Windows**, so POSIX shell one-liners must be rewritten.
