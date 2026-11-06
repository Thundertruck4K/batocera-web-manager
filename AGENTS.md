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
- **Los `<select>` nativos no respetan el tema**: pintan su propio fondo (blanco con letras pálidas).
  El componente `Select` de `frontend/src/components/ui/Field.tsx` les quita el aspecto nativo
  (`appearance-none`), les pone el fondo de la app y dibuja la flecha; el `color-scheme` (claro/oscuro
  según `.dark`) y el fondo de `option` están en `index.css` para que la lista desplegada también
  siga la paleta.
- **El interruptor (`Toggle`) va anclado**: la bola lleva `left-0.5` y se mueve con `translate-x-5`
  sobre un carril de 44 px, para que el recorrido sea simétrico (2 px de margen a cada lado). Sin
  `left` el navegador la centraba y al activarse se salía del carril. El color de la bola sale de los
  tokens (`bg-foreground` apagada, `bg-primary-foreground` encendida) para que contraste en los dos
  temas.
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

- **Tests**: 673 con `pytest` en `tests/` (54 ficheros de test; backend stdlib + helpers de UI extraídos por regex). No hay linting ni typechecking
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
- **A game that already has media is not scraped again**: the ROM modal checks `has_image` and, if
  it is set, shows the local `gamelist.xml` data plus the library cover (`/api/rom-image`) without
  hitting any source. Scraping it again is opt-in via the "Escapear" button, and saving in local
  mode only updates the metadata (never re-downloads the image).
- Credentials read from `batocera.conf` keys: `global.scrapper.user`, `global.scrapper.password`, etc.
- Scraping respects rate limits (`maxthreads` from SS response, minimum 0.5s delay)
- **Some games are a folder, not a file**: EmulationStation treats a directory as a game when its name
  carries one of the system's extensions (`Myst.scummvm/`, `Alone in the Dark.pc/`, `kof94.pc/`), and
  the `gamelist.xml` stores that path (`<path>./Myst.scummvm</path>`). `game_folder_extensions()`
  reads the extensions from `es_systems.cfg` (the user's one wins, `.residualvm` joins `.scummvm`),
  `is_game_folder()` detects them (also by the marker file inside, e.g. `Myst.scummvm/myst.scummvm`)
  and `game_folder_search_name()` strips the extension to get the title to search for. Such a game is
  listed as a ROM (`is_game_folder: true`), scraped **by name** (`name_only`, never hashed: a folder
  has no hash) and saved with the folder path in the gamelist.
- **What counts as a game**: `is_game_file(name, exts)` decides it, with `exts` =
  `system_game_extensions()` (the system's own extensions from `es_systems.cfg` plus the global
  `ROM_EXTENSIONS`, minus the extensions that are not games). That is what keeps `_info.txt` (every
  system folder has one describing its formats), `gamelist.xml` and the save states (`*.sav`, `*.srm`,
  `*.dat`, `*.keys`) out of the ROM lists, the scraper and the counters. `list_rom_folder`,
  `get_rom_systems`, `count_rom_systems` and `pick_random_game` all use it.
  - The system's own declaration wins over `NON_GAME_EXTENSIONS`: the `.dat` files of **naomi**,
    atomiswave and systemsp *are* the game, not a save file.
  - `NEVER_GAME_EXTENSIONS` wins over the system: the emulator configs
    (`citron_config.xci_config`, `eden_config.xci_config`) are never a game, even though the
    user's `es_systems_switch.cfg` declares `.xci_config`.
- **The dashboard counts what is on the disk**: `count_disk_games()` walks the first level of every
  system counting game files and game folders (cached 60 s) — the gamelists only know the games that
  were already catalogued. `/api/info` exposes it as `disk_games_count`/`disk_systems_count`, and
  `pick_random_game(settings)` takes the whole settings dict because it needs those extensions.
- **BIOS: the catalogue comes from the console itself** (`app.py`, section "Gestión de BIOS").
  - `get_bios_catalog()` reads `/usr/bin/batocera-systems` (the official Python script, parsed with
    `ast` — never executed) and gets slug, display name, path, md5 and **the member each ZIP must
    contain** (`zippedFile`). `/usr/share/batocera/datainit/bios/readme.txt` is the fallback (no
    slugs, no members: matched by path set against the embedded `BIOS_DB`), and `BIOS_DB` the last
    resort. Cached 1 h; the list changes with the Batocera version, so it must not be frozen.
  - **Verify by content, never by name**: Batocera checks the md5 of what is *inside* each ZIP, not
    the md5 of the ZIP. Comparing the file's own md5 marked 83 healthy BIOS as broken (204 "ok" vs
    the real 287). `_bios_entry_state()` opens the ZIP and checks every required member.
  - States: `ok`, `sin_verificar`, `hash_distinto`, `miembro_falta`, `reparable_zip`,
    `reparable_ruta`, `ausente`, `omitida`, `ilegible`. `build_bios_index()` hashes the disk once
    (5 min cache, files over 64 MiB are skipped: they are not BIOS) with reverse indexes by name
    and by md5 to find what is "somewhere else".
  - `repair_bios()` regroups the required members from other ZIPs of the SD (or moves the file from
    another folder), always verifies the result and quarantines what it replaces in
    `/userdata/bios/.quarantine/`. **It looks for the content before touching the destination**, so
    a failed repair never leaves the system without its BIOS.
  - Endpoints: `GET /api/bios/catalog`, `GET /api/bios/summary`, `POST /api/bios/scan`,
    `POST /api/bios/repair`. The SPA section is `pages/Bios.tsx` (+ `components/bios/`).
- **ScreenScraper's name search needs a platform id, and time**: without `systemeid` (or with `0`)
  the API still answers, but it searches every platform and takes over a minute, so the name search
  uses `SS_SEARCH_TIMEOUT_NAME` (75 s) — with the old 20 s timeout the result was always lost. The
  map lives in `SS_SYSTEMS` (`dos` → 135, "PC Dos"; `scummvm`/`residualvm` → 123). The name search is
  fuzzy and its first result is often a different game ("Doom" → "Hugo III: Jungle of Doom"), so
  `_ss_best_jeu()` picks the candidate whose title matches the searched name.
- **RetroAchievements data is cached on disk**: the summary is stored in
  `/userdata/system/batocera_manager_ra_cache.json` next to the settings, so entering the section
  after a manager restart does not hit the API. `RA_CACHE_TTL` (6 h, configurable with
  `ra_cache_ttl`) is how long the data is served, and `RA_MIN_REFRESH` (60 s) is the minimum gap
  between two downloads even when the user asks for a forced refresh (`?force=1`).
- The `--port` CLI flag is the only command-line argument supported

## Workflow

- The `superpowers` plugin is installed at `C:\Users\folk3\.minimax\plugins\superpowers/` — a port of https://github.com/obra/superpowers v7.0.1 (MIT, obra). Its 15 skills appear in the catalog as `superpowers:<name>` (e.g. `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:systematic-debugging`).
- A `SessionStart` hook injects the `using-superpowers` bootstrap plus the MiniMax Code tool mapping (`skills/using-superpowers/references/mcode-tools.md`) at session start. The skill catalog itself is rebuilt on session start, so a freshly installed plugin needs a new session to become loadable.
- Specs and plans live in `docs/superpowers/specs/` and `docs/superpowers/plans/` (`YYYY-MM-DD-<slug>-design.md` and `YYYY-MM-DD-<slug>-plan.md`).
- Tool mapping for this harness: `Read`→`read`, `Write`→`write`, `Edit`→`edit`, `Bash`→`bash`, `Glob`→`glob`, `Grep`→`grep`, `TodoWrite`→`todowrite`, `Task`→`task`, `Skill`→`skill`. The `bash` tool is **PowerShell 5.1 on Windows**, so POSIX shell one-liners must be rewritten.
