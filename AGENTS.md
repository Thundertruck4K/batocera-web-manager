# Batocera System Manager Web — Agent Guide

> **Este repo es el proyecto único.** Interfaz React + Tailwind CSS, backend Python puro y la
> interfaz clásica de un solo fichero (`templates/index.html`) como respaldo.

## Entorno de desarrollo local (una instancia)

El proyecto se trabaja en **un solo repositorio**:

| | |
|---|---|
| GitHub | `Thundertruck4K/batocera-web-manager` |
| Local | `D:\PROGRAMACION\PROYECTOS PROPIOS\batocera_web_react` |
| Backend | `:5001` |
| Interfaz | `frontend/` (Vite en `:5173`) |
| Respaldo | `templates/index.html` |

- No hay repo hermano al que propagar el backend: `app.py` es único.
- Herramientas de desarrollo, fuera de los repos, en `D:\UTILS\batocera_web`: `dev.ps1` / `dev.cmd`
  (`dev`, `backend`, `stop`, `status`, `check`) y `check-dev-env.py`, que exige el repo limpio y
  subido, vigila que el bundle y los `.sh` no lleven CRLF y comprueba que el `APP_REPO` del backend
  y la URL de clone del `install.sh` apunten a este mismo repositorio.
- **Nunca `push` directo a `master`**: rama `feature/...` o `fix/...` → PR → merge.
- `frontend/dist/` **se versiona** (el dispositivo no tiene Node): recompila con `npm run build` y
  sube el bundle en el mismo commit que los cambios del frontend.
- Windows: la ExecutionPolicy bloquea los `.ps1` → usa `dev.cmd`. Los `.cmd` necesitan **CRLF** y sin
  acentos. El `bash` de este entorno es **PowerShell 5.1** (sin `&&`, sin `cmd`, `npm` → `npm.cmd`).

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
- **Node.js en el dispositivo (opcional)**: la Batocera de desarrollo tiene Node v26 LTS en
  `/userdata/system/node/current` (enlazado en `/usr/bin/node` y `/usr/bin/npm`). Se instaló desde el
  tarball oficial de nodejs.org porque Batocera es **Buildroot** y no tiene `apt`/`dpkg`: no se puede
  instalar nada por gestor de paquetes. El bloque `# [batocera-node]` de
  `/userdata/system/custom.sh` rehace los enlaces en cada arranque (la partición `/usr` es un overlay
  que se pierde al reiniciar). Con eso se puede recompilar el frontend en la propia consola:
  `cd /userdata/system/batocera_web/frontend && npm ci && npm run build` → el bundle sale con los
  **mismos hashes** que el versionado en el repo. **No hace falta para usar la app**: el despliegue
  normal sigue siendo subir `frontend/dist/` ya compilado.
  - `install.sh` (v1.6) sabe instalarlo solo: descarga el tarball oficial, **verifica el sha256
    contra el `SHASUMS256.txt`**, lo deja en `$BASE_DIR/node/current` y escribe el bloque
    `# [batocera-node]`. Se fuerza con `BM_NODE=install`; `BM_NODE=skip` lo salta; por defecto
    (`auto`) pregunta, y sin terminal interactiva no instala nada.
- **Git en el dispositivo (opcional)**: Batocera es Buildroot y **no trae git**. Se instaló con
  **micromamba** (binario estático) contra el canal `conda-forge`: el entorno queda en
  `/userdata/system/mamba/envs/git` y se enlaza en `/usr/bin/git`. El bloque `# [batocera-git]` de
  `/userdata/system/custom.sh` rehace el enlace en cada arranque (la partición `/usr` es un overlay
  que se pierde al reiniciar). Ojo: el paquete de conda-forge arrastra ~250 MB (Perl, OpenSSL,
  curl…), aunque la caché de paquetes se borra al terminar.
  - `install.sh` (v1.6) lo instala solo si falta: descarga micromamba, **verifica su sha256** contra
    el hash fijado en el script, crea el entorno con `micromamba create` y escribe el bloque
    `# [batocera-git]`. Se fuerza con `BM_GIT=install`; `BM_GIT=skip` lo salta; por defecto
    (`auto`) avisa de que falta y lo instala.
  - El `sha256` de micromamba 2.10.0 está **contrastado con la API de anaconda.org** para
    `linux-64`, `linux-aarch64` y `linux-ppc64le` (no hay build para `armv7l`).

## Architecture

- **Single-file backend**: `app.py` (~5780 lines) — HTTP handler, dashboard, scraper (ScreenScraper.fr, TheGamesDB, IGDB), autostart manager
- **Frontend React**: `frontend/` — React 19 + TypeScript + Vite 6 + Tailwind CSS v4. El backend sirve
  `frontend/dist/` cuando está compilado; si no lo está, cae a la interfaz clásica de un solo fichero
  (`templates/index.html`), que sigue siendo el respaldo. Ver «Frontend» más abajo.
- ROM scan has a 60-second in-memory cache (`_rom_cache`)
- Settings are read from JSON file on every request (no in-memory cache for settings)
- `install.sh` is current (v1.6): installs to `/userdata/system/batocera_web/` (matches the default `app_path`), pure stdlib, no Flask. Supports `BM_BASE_DIR`, `BM_CUSTOM_SH`, `BM_PYTHON`, `BM_PORT` overrides. It validates the port (1-65535), **rewrites** the `# [batocera-manager]` block of `custom.sh` (never duplicates it and never keeps a stale port/path), starts the block with a `pkill` that kills the previous instance, and restarts the manager if it was already running
- **Fase de validación de utilidades** (`install.sh` v1.6): el instalador comprueba **git** y **node** antes de instalar nada. Si están, sigue sin preguntar; si faltan, avisa («no se encontró X en el sistema: es necesario instalarlo para continuar») y los instala. Git se instala con micromamba + `conda-forge` (sha256 fijado en el script, `BM_MICROMAMBA_SHA256` lo puede sobrescribir); Node con el tarball oficial de nodejs.org. `BM_GIT`/`BM_NODE` aceptan `auto`, `install` y `skip`.
- **Contrato del servicio**: `/api/service/status` devuelve `autostart` (`registered`/`installed`,
  `manual_mode`, `cmd`, `block`, `path`) y `process` (`running`, `pids`, `pid`, `port`, `cmd`). El
  frontend React y la interfaz clásica leen **las mismas claves**: si se toca uno, se toca el otro
  (`frontend/src/lib/types.ts` y `app.py` van de la mano).

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
  Variable `BATOCERA_BACKEND` para cambiar el destino del proxy; con `dev.cmd dev` (backend en :5001),
  apúntala a `http://127.0.0.1:5001` para que Vite pegue con el backend local.
- **La interfaz clásica sigue viva**: `templates/index.html` y sus tests (`tests/test_mono_charts.py`,
  `tests/test_ui_theme.py`) no se tocan. `render_index()` no ha cambiado; `render_app()` elige la SPA
  si `frontend/dist/index.html` existe y si no, la clásica.
- **Vista de depuración**: el sidebar tiene una entrada «Depuración» (`/depuracion`) que monta el
  componente `LogStream` de [`overtrue/ui`](https://ui.overtrue.xyz/components/log-stream), instalado
  con el CLI de shadcn en `frontend/src/components/overtrue/log-stream.tsx` (y `frontend/components.json`
  como configuración del registro). El backend mantiene un historial circular de 500 eventos con nivel
  (`log_event()`), lo sirve por `GET /api/logs` y lo empuja en vivo por `GET /api/logs/stream` (SSE).
  El cliente es `frontend/src/hooks/useLogStream.ts` (EventSource, con deduplicación por id).

## Key notes

- **Tests**: 583 con `pytest` en `tests/` (48 ficheros de test; backend stdlib + helpers de UI extraídos por regex). No hay linting ni typechecking
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
- **Source chain**: ScreenScraper is always tried first; if it has no data, TheGamesDB and IGDB are
  the fallback. The chain lives in the backend (`scrape_search_cascade`), so the ROM modal and the
  system scrape share it. `POST /api/scraper/search` takes `sources` (ordered list) and answers with
  `source` (the one that hit) and `tried`; the system batch takes `fallback_sources`.
- **Media URLs must never carry credentials to the browser**: ScreenScraper returns them with
  `devpassword`/`sspassword` embedded. `ss_media_public_url()` strips them and
  `ss_media_signed_url()` puts them back when downloading server-side. The classic UI asks for the
  originals with `raw_media: true` (it shows the image directly and may use unsaved credentials).
- **The preview of a cover goes through the backend** (`GET /api/scraper/image`): ScreenScraper does
  not serve images without its referer. The proxy caches in memory (24 images / 3 MB) and only
  allows the scraping hosts, so it is not an open proxy.
- **TheGamesDB searches by exact title**: it will not find "007: Agent Under Fire" when asked for
  "007 Agent Under Fire", so the search tries name variants and, if needed, drops the platform
  filter. Without that, the fallback chain finds nothing.
- **Saving a game must hit the right `<game>` entry**: the same game can be catalogued in the system
  root and in a subfolder, so `save_gamelist_entry` matches the exact relative path first and only
  falls back to the file name. Matching by name first writes the data into the wrong entry and the
  ROM stays in "sin media" forever. `list_rom_folder` reads the system gamelist when the current
  folder has none (its paths are relative to the system root).
- Credentials read from `batocera.conf` keys: `global.scrapper.user`, `global.scrapper.password`, etc.
- Scraping respects rate limits (`maxthreads` from SS response, minimum 0.5s delay)
- The `--port` CLI flag is the only command-line argument supported

## Workflow

- The `superpowers` plugin is installed at `C:\Users\folk3\.minimax\plugins\superpowers/` — a port of https://github.com/obra/superpowers v7.0.1 (MIT, obra). Its 15 skills appear in the catalog as `superpowers:<name>` (e.g. `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:systematic-debugging`).
- A `SessionStart` hook injects the `using-superpowers` bootstrap plus the MiniMax Code tool mapping (`skills/using-superpowers/references/mcode-tools.md`) at session start. The skill catalog itself is rebuilt on session start, so a freshly installed plugin needs a new session to become loadable.
- Specs and plans live in `docs/superpowers/specs/` and `docs/superpowers/plans/` (`YYYY-MM-DD-<slug>-design.md` and `YYYY-MM-DD-<slug>-plan.md`).
- Tool mapping for this harness: `Read`→`read`, `Write`→`write`, `Edit`→`edit`, `Bash`→`bash`, `Glob`→`glob`, `Grep`→`grep`, `TodoWrite`→`todowrite`, `Task`→`task`, `Skill`→`skill`. The `bash` tool is **PowerShell 5.1 on Windows**, so POSIX shell one-liners must be rewritten.
