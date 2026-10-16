# Plan de implementación: Landing animado + Rediseño del dashboard

**Fecha:** 2026-10-16
**Diseño:** `docs/superpowers/specs/2026-10-16-landing-dashboard-design.md`
**Reglas del repo:** Python 3.11+ stdlib (sin dependencias), UI en `templates/index.html`
(HTML/CSS/JS embebido), tests en `tests/`, TDD, commits atómicos, `python _jscheck.py`
para validar el JS embebido.

Cada tarea: archivos exactos, firma exacta, test exacto, comportamiento esperado y commit.
Ejecuta siempre: `python -m pytest -q` y, si se toca JS, `python _jscheck.py`.

Convenciones de tests existentes:
- `tests/conftest.py` expone el fixture `appmod` (el módulo `app` cargado sin servidor).
- Los tests de UI leen `templates/index.html` con `re`/texto y afirman estructura.
- Los tests de backend usan `tmp_path` y pasan rutas por parámetro (nada de rutas fijas).

---

## Etapa A — Backend: analítica de juego

### Tarea A1 — `find_user_art()` (arte de usuario primero)

**Archivo:** `app.py` (junto a `_serve_rom_image`, sobre el bloque de ROMs).
**Test:** `tests/test_game_stats.py::test_find_user_art_prefers_user_media`.

Firma:

```python
IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]

# Preferencia de mayor a menor (arte de usuario primero). Cada par es
# (carpeta, sufijo). Con sufijo "" busca "<stem>.<ext>"; si no, "<stem><sufijo>.<ext>".
USER_ART_PREFERENCE = [
    ("media/images", ""),
    ("images",       "-image"),
    ("mixrbv2",      "-mixrbv2"),
    ("mixrbv1",      "-mixrbv1"),
    ("fanart",       "-fanart"),
    ("screenshots",  "-titleshot"),
    ("named_boxarts","-box"),
    ("boxart",       "-box"),
    ("images",       "-box"),
    ("wheels",       "-wheel"),
    ("images",       "-wheel"),
    ("marquees",     "-marquee"),
    ("images",       "-marquee"),
]

def find_user_art(roms_base, system, rom_relpath):
    """Lista de imágenes candidatas para un ROM, arte de usuario primero.

    `roms_base` puede ser str o Path. `system` es el slug. `rom_relpath` es el
    path relativo del ROM dentro del sistema (admite subcarpeta "CPS1/foo.zip").
    Devuelve list[Path] de archivos existentes, sin duplicados, ordenada por
    USER_ART_PREFERENCE (subcarpeta antes que raíz). El `<image>` del
    `gamelist.xml` se agrega al final (o al principio solo si es lo único).
    """
```

Comportamiento:
1. `sys_dir = Path(roms_base) / system`; `stem = Path(rom_relpath).stem`.
2. Bases de búsqueda: `[sys_dir / subdir]` si hay subcarpeta y luego `[sys_dir]`.
3. Para cada base y cada par `(carpeta, sufijo)` en orden, para cada extensión,
   añade la ruta si existe. Sin duplicados.
4. Si la lista queda vacía, lee `sys_dir/"gamelist.xml"`, busca el `<game>` cuyo
   `path` (sin `./`) coincida con `rom_relpath` o cuyo `stem` coincida, y añade su
   `<image>` (resuelto relativo a `sys_dir`) si existe.
5. Nunca lanza: cualquier error → devuelve lo acumulado.

Test (tmp_path): crear `roms_base/snes/media/images/game.png`,
`roms_base/snes/mixrbv2/game-mixrbv2.png`, `roms_base/snes/images/game-image.png`
y un `gamelist.xml` con `<image>./images/game-image.png</image>`.
Afirmar:
```
art = appmod.find_user_art(tmp_path, "snes", "game.zip")
assert art[0].name == "game.png"            # media/images gana
assert art[1].name == "game-image.png"      # images gana a mixrbv2
assert art[2].name == "game-mixrbv2.png"
```
Y otro test: sin arte de usuario pero con `<image>` en gamelist → devuelve esa imagen.

**Commit:** `feat(backend): find_user_art prioriza el arte de usuario`

---

### Tarea A2 — `collect_play_stats()`

**Archivo:** `app.py`.
**Test:** `tests/test_game_stats.py::test_collect_play_stats_aggregates`.

Firma:

```python
def collect_play_stats(roms_base, systems=None):
    """Agrega estadísticas de juego desde los gamelist.xml de `roms_base`.

    `systems`: lista de slugs a incluir; None = todos los subdirectorios.
    Devuelve:
      {
        "ok": True,
        "updated": <epoch float>,
        "has_playtime": bool,          # True si algún juego traía <playtime>
        "totals": {"games": int, "playcount": int, "playtime_s": int, "systems": int},
        "top_games": [ {"system","name","path","playcount","lastplayed",
                        "playtime_s","image"} ],   # ordenado por playcount desc, máx 10
        "by_system": [ {"system","playcount","playtime_s","games"} ],  # playcount desc
        "activity":  [ {"date":"YYYY-MM-DD","count":int} ],  # desde <lastplayed>, últimos 30 días
      }
    """
```

Reglas:
- Recorre `roms_base/<sys>/gamelist.xml` (solo sistemas indicados). Si no existe o falla,
  se salta sin romper.
- Por `<game>`: `playcount=int(<playcount> or 0)`, `lastplayed=<lastplayed>` (formato ES
  `YYYYMMDDTHHMMSS`, puede faltar), `playtime_s=int(<playtime> or 0)`, `name=<name>` o stem.
- Solo cuenta juegos con `playcount>0` **o** `playtime_s>0` para `top_games`.
- `totals.games` = juegos con actividad; `totals.playcount` = suma; `totals.playtime_s` = suma.
- `has_playtime` = `totals.playtime_s > 0`.
- `activity`: parsea `lastplayed` (fallback: ignora si no parsea) y cuenta por día.
- Ordenar `top_games` por `playcount` desc (y `playtime_s` desc como desempate), máx 10.
- `image`: usar `find_user_art(...)` y quedarse con `str(art[0])` si hay, si no `""`.

Test (tmp_path): dos sistemas `snes` y `nes` con gamelists:
- snes: `gameA` playcount=5 playtime=3600 lastplayed=20261010T120000; `gameB` playcount=2.
- nes: `gameC` playcount=1 lastplayed=20261001T090000.
Afirmar `totals == {"games":3,"playcount":8,"playtime_s":3600,"systems":2}`,
`has_playtime is True`, `top_games[0]["name"] == "gameA"`, y que `activity` incluye
`{"date":"2026-10-10","count":1}`.

**Commit:** `feat(backend): collect_play_stats lee playcount/lastplayed/playtime`

---

### Tarea A3 — `pick_random_game()`

**Archivo:** `app.py`.
**Test:** `tests/test_game_stats.py::test_pick_random_game_returns_game_with_art`.

Firma:

```python
def pick_random_game(roms_base, systems=None):
    """Elige un juego al azar entre los que tienen arte disponible.

    Devuelve {"system","name","filename","subpath","has_art":True} o None si no
    hay ningún juego con arte. Usa `random.choice` (testeable monkeypatcheando
    `app.random`).
    """
```

Reglas:
- Reúne candidatos recorriendo `roms_base/<sys>/` (archivos de ROM, sin
  `FILTER_FILES`/`FILTER_DIRS`/ocultos/`gamelist.xml`), y para cada uno comprueba
  `find_user_art(...)`; conserva solo los que tienen arte.
- Test usa `monkeypatch.setattr(appmod.random, "choice", lambda seq: seq[0])` para
  hacerlo determinista.

Test (tmp_path): `snes/gameA.zip` con `snes/images/gameA-image.png` y `snes/gameB.zip`
sin arte. Con `choice` forzado, `pick_random_game` devuelve un dict con
`system=="snes"`, `filename=="gameA.zip"`, `has_art is True`. Y sin ningún arte → `None`.

**Commit:** `feat(backend): pick_random_game elige un juego con arte`

---

### Tarea A4 — Endpoints `GET /api/game-stats` y `GET /api/random-game`

**Archivo:** `app.py` (`do_GET`, junto a `/api/dashboard`).
**Test:** `tests/test_landing_dashboard.py::test_endpoints_declared`.

Añadir:
```python
elif path == "/api/game-stats":
    s = load_settings()
    self.send_json(collect_play_stats(s["roms_base"]))
elif path == "/api/random-game":
    s = load_settings()
    self.send_json({"ok": True, "game": pick_random_game(s["roms_base"])})
```

Test de estructura (lee `app.py`): contiene `"/api/game-stats"` y `"/api/random-game"`,
y llama a `collect_play_stats(` y `pick_random_game(`.

**Commit:** `feat(api): endpoints game-stats y random-game`

---

## Etapa B — Frontend: landing animado

### Tarea B1 — Overlay `#landing` (HTML + CSS + animación)

**Archivo:** `templates/index.html`.
**Test:** `tests/test_landing_dashboard.py::test_landing_overlay_markup`.

Insertar **inmediatamente después de `<body>`** (antes de `<div class="app">`):

```html
<div class="landing" id="landing">
  <div class="landing-inner">
    <div class="landing-logo">
      <svg viewBox="0 0 120 120" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle class="landing-ring" cx="60" cy="60" r="46"/>
        <circle class="landing-ring landing-ring2" cx="60" cy="60" r="34"/>
        <path class="landing-glyph" d="M40 74 L40 50 a8 8 0 0 1 16 0 v24 M64 74 L64 50 M64 62 h16 M80 50 v24"/>
      </svg>
      <div class="landing-pulse"></div>
    </div>
    <h1>Batocera Manager</h1>
    <p class="landing-tagline">Tu centro de mando para EmulationStation</p>
    <div class="landing-facts" id="landing-facts">
      <span class="landing-fact skeleton-pill"></span>
      <span class="landing-fact skeleton-pill"></span>
      <span class="landing-fact skeleton-pill"></span>
    </div>
    <button class="btn btn-primary btn-lg landing-enter" id="landing-enter" onclick="dismissLanding()">Entrar ▸</button>
    <label class="landing-skip"><input type="checkbox" id="landing-never"> No volver a mostrar</label>
  </div>
</div>
```

CSS (junto a los tokens/overlay): `.landing{position:fixed;inset:0;z-index:1200;display:flex;
align-items:center;justify-content:center;background:radial-gradient(1200px 600px at 50% -10%,
rgba(110,168,254,.18),transparent),var(--bg)}`. Añadir animaciones con `@keyframes`
(dibujo del aro con `stroke-dashoffset`, pulso `landing-pulse`, `prefers-reduced-motion`
desactiva animaciones). Añadir `.landing.hidden{opacity:0;pointer-events:none;transition:opacity .35s}`.

Test: el HTML contiene `id="landing"`, `class="landing-ring"`, `onclick="dismissLanding()"`,
`id="landing-never"`; el CSS contiene `@keyframes` y `.landing.hidden`.

**Commit:** `feat(ui): overlay de landing con loader animado`

---

### Tarea B2 — JS del landing (`initLanding` / `dismissLanding`)

**Archivo:** `templates/index.html` (sección JS, antes de la sección de arranque).
**Test:** `tests/test_landing_dashboard.py::test_landing_js_wiring`.

```javascript
const LANDING_KEY = 'bcm_landing_skip';

function initLanding() {
  const el = document.getElementById('landing');
  if (!el) return;
  if (localStorage.getItem(LANDING_KEY) === '1') { el.classList.add('hidden'); return; }
  loadLandingFacts();
  setTimeout(() => { if (!el.classList.contains('hidden')) dismissLanding(); }, 2200);
}

function dismissLanding() {
  const el = document.getElementById('landing');
  if (!el) return;
  const never = document.getElementById('landing-never');
  if (never && never.checked) localStorage.setItem(LANDING_KEY, '1');
  el.classList.add('hidden');
}

async function loadLandingFacts() {
  const box = document.getElementById('landing-facts');
  if (!box) return;
  const [info, dash, bios] = await Promise.all([
    fetchJson('/api/info'), fetchJson('/api/dashboard'), fetchJson('/api/bios/missing'),
  ]);
  const facts = [];
  if (dash && dash.batocera_version) facts.push(`Batocera ${dash.batocera_version}`);
  if (info && typeof info.systems_count === 'number') facts.push(`${info.systems_count} sistemas`);
  if (dash && dash.es && dash.es.running) facts.push('ES en marcha');
  if (bios && typeof bios.total_missing === 'number')
    facts.push(bios.total_missing > 0 ? `${bios.total_missing} BIOS por subsanar` : 'BIOS al día');
  box.innerHTML = facts.map(f => `<span class="landing-fact">${escHtml(f)}</span>`).join('') ||
                  '<span class="landing-fact">Bienvenido</span>';
}
```

- `Esc` cierra el landing: en el listener `DOMContentLoaded` añadir
  `if (e.key === 'Escape') dismissLanding();` **solo si** `#landing` no está oculto
  (no interferir con modales → comprobar `getElementById('landing')?.classList.contains('hidden')`).

Test: el JS contiene `function initLanding(`, `function dismissLanding(`,
`function loadLandingFacts(`, `bcm_landing_skip` y `/api/bios/missing`.

**Commit:** `feat(ui): logica del landing (hechos reales, saltable, recordable)`

---

### Tarea B3 — Enganchar el landing al arranque

**Archivo:** `templates/index.html` (sección `// ─── Boot ───`).
**Test:** `tests/test_landing_dashboard.py::test_boot_calls_init_landing_without_blocking`.

Cambiar:
```javascript
init();
pollEsStatus();
setInterval(pollEsStatus, 15000);
```
por:
```javascript
initLanding();   // overlay opcional; NO bloquea la app
init();
pollEsStatus();
setInterval(pollEsStatus, 15000);
```
Comportamiento: `init()` (y todos los sondeos) corren igual; el landing es una capa
encima. Test: `initLanding();` aparece antes de `init();` y `init();` sigue presente.

**Commit:** `feat(ui): muestra el landing al arrancar sin bloquear la app`

---

## Etapa C — Frontend: dashboard rediseñado

### Tarea C1 — Hero del dashboard

**Archivo:** `templates/index.html` (`#panel-dashboard`, tras la cabecera actual).
**Test:** `tests/test_landing_dashboard.py::test_dashboard_hero_markup`.

Insertar antes de `#dash-kpis`:
```html
<div class="dash-hero" id="dash-hero">
  <div class="dash-hero-main">
    <div class="dash-hero-hello" id="dash-hero-hello">Hola 👋</div>
    <div class="dash-hero-sub" id="dash-hero-sub">Cargando estado…</div>
  </div>
  <div class="dash-hero-stats" id="dash-hero-stats"></div>
</div>
```
JS: `renderHero(d)` llamado desde `renderDashboard(d)`. Saludo por hora
(`<6`=Buenas noches, `<12`=Buenos días, `<20`=Buenas tardes, si no Buenas noches),
sub = `Batocera <v> · uptime <uptime>`, y 4 cifras en `#dash-hero-stats`:
sistemas (de `/api/info`, cacheado en `_heroInfo`), ES (encendido/apagado), y
"Jugados"/"Horas" que se rellenan en C3 (placeholders `--`).
CSS `.dash-hero{...}` con degradado y blur, coherente con `.dash-card`.

Test: existe `id="dash-hero"`, `id="dash-hero-stats"`, y el JS contiene `function renderHero(`.

**Commit:** `feat(ui): hero del dashboard`

---

### Tarea C2 — Card de juego al azar

**Archivo:** `templates/index.html`.
**Test:** `tests/test_landing_dashboard.py::test_random_game_card_markup`.

Insertar (dentro del panel, antes de `#dash-kpis` o tras el hero):
```html
<div class="dash-card dash-random" id="dash-random-game" style="--card-accent:var(--accent)">
  <h3><span class="icon">🎲</span>Juego al azar
    <button class="btn btn-ghost btn-sm" style="margin-left:auto" onclick="loadRandomGame()">↻ Otro</button>
  </h3>
  <div class="dash-random-body" id="dash-random-body">
    <div class="dash-random-img" id="dash-random-img"></div>
    <div class="dash-random-info">
      <div class="dash-random-name" id="dash-random-name">Buscando…</div>
      <div class="dash-random-sys" id="dash-random-sys"></div>
    </div>
  </div>
</div>
```
JS:
```javascript
async function loadRandomGame() {
  const res = await fetchJson('/api/random-game');
  renderRandomGame(res && res.game);
}
function renderRandomGame(g) {
  const img = document.getElementById('dash-random-img');
  const name = document.getElementById('dash-random-name');
  const sys = document.getElementById('dash-random-sys');
  if (!g) { name.textContent = 'Sin juegos con arte todavía'; sys.textContent = ''; img.style.backgroundImage=''; return; }
  const q = g.subpath ? `?subpath=${encodeURIComponent(g.subpath)}` : '';
  img.style.backgroundImage = `url('/api/rom-image/${encodeURIComponent(g.system)}/${encodeURIComponent(g.filename)}${q}')`;
  name.textContent = g.name || g.filename;
  sys.textContent = g.system;
}
```
Llamar `loadRandomGame()` desde `initDashboard()` (una vez; no en el auto-refresh de 5 s).
CSS `.dash-random-img{background-size:cover;background-position:center;aspect-ratio:16/9;border-radius:10px}`
y `.dash-random-body{display:grid;grid-template-columns:minmax(160px,240px) 1fr;gap:16px}`.

Test: existe `id="dash-random-game"`, el JS contiene `function loadRandomGame(`,
`function renderRandomGame(` y `/api/random-game`.

**Commit:** `feat(ui): card de juego al azar con arte de usuario`

---

### Tarea C3 — Analítica de uso (más usados + gráfica fluida)

**Archivo:** `templates/index.html`.
**Test:** `tests/test_landing_dashboard.py::test_playstats_markup` y
`tests/test_landing_dashboard.py::test_activity_svg_path`.

HTML (tras la card del juego al azar):
```html
<div class="dash-card" id="dash-playstats" style="--card-accent:var(--purple2)">
  <h3><span class="icon">📈</span>Actividad de juego
    <span style="font-size:11px;color:var(--text3);font-weight:400" id="dash-playstats-note"></span>
  </h3>
  <div class="dash-playstats-grid">
    <div>
      <div class="ps-sub">Más jugados</div>
      <div id="dash-top-games"></div>
    </div>
    <div>
      <div class="ps-sub" id="dash-activity-label">Últimos 30 días</div>
      <svg class="ps-spark" id="dash-activity" viewBox="0 0 300 80" preserveAspectRatio="none"></svg>
    </div>
  </div>
</div>
```
JS:
```javascript
async function loadPlayStats() {
  const s = await fetchJson('/api/game-stats');
  renderPlayStats(s);
}
function renderPlayStats(s) {
  const note = document.getElementById('dash-playstats-note');
  const top = document.getElementById('dash-top-games');
  const spark = document.getElementById('dash-activity');
  if (!s || !s.ok) { if (note) note.textContent = ''; return; }
  if (note) note.textContent = s.has_playtime
    ? `· ${(s.totals.playtime_s/3600).toFixed(1)} h registradas`
    : '· tiempo no registrado (solo partidas)';
  const max = Math.max(1, ...s.top_games.map(g => g.playcount));
  top.innerHTML = (s.top_games || []).slice(0,5).map(g => `
    <div class="ps-row">
      <span class="ps-name" title="${escHtml(g.name)}">${escHtml(g.name)}</span>
      <span class="ps-bar"><i style="width:${Math.round(g.playcount/max*100)}%"></i></span>
      <span class="ps-val">${g.playcount}</span>
    </div>`).join('') || '<div class="ps-empty">Sin partidas registradas</div>';
  const counts = (s.activity || []).map(a => a.count);
  const maxc = Math.max(1, ...counts);
  const step = counts.length > 1 ? 300/(counts.length-1) : 0;
  const pts = counts.map((c,i) => `${(i*step).toFixed(1)},${(78 - (c/maxc)*70).toFixed(1)}`).join(' ');
  spark.innerHTML = counts.length
    ? `<polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="2"/>`
    : '';
}
```
Llamar `loadPlayStats()` desde `initDashboard()` (una vez), y rellenar en el hero la
cifra "Jugados"/"Horas" si `renderPlayStats` recibe datos (guardar `_heroStats` y
`renderHero` los pinta).
CSS: `.ps-row{display:grid;grid-template-columns:1fr 90px 28px;gap:8px;align-items:center;font-size:12px}`,
`.ps-bar{background:var(--bg3);border-radius:4px;height:8px;overflow:hidden}`,
`.ps-bar i{display:block;height:100%;background:var(--accent)}`, `.ps-spark{width:100%;height:80px}`.

Tests: existe `id="dash-playstats"`, `id="dash-activity"`; el JS contiene
`function renderPlayStats(` y genera `polyline` (buscar `polyline points=`).

**Commit:** `feat(ui): analitica de juego en el dashboard`

---

### Tarea C4 — Orden final y conservación del monitoreo

**Archivo:** `templates/index.html`.
**Test:** `tests/test_landing_dashboard.py::test_tecnico_conservado`.

Verificar (test de estructura) que siguen presentes: `id="dash-kpis"`, `id="dash-row1"`,
`id="dash-row2"`, `id="dash-row-fans"`, `id="dash-storage"`, `id="dash-news"`,
`id="dash-row3"`. Orden nuevo: hero → juego al azar → actividad → KPIs → filas
técnicas → ventiladores → almacenamiento → noticias → red/procesos. Sin cambios de
IDs (no romper `renderDashboard`).

**Commit:** `refactor(ui): ordena el dashboard con el tecnico conservado`

---

## Etapa D — Verificación y cierre

### Tarea D1 — Verificación integral
- `python -m pytest -q` → todo verde (112 actuales + nuevos).
- `python _jscheck.py` + `node --check _extracted.js`.
- `python -m py_compile app.py`.
- En vivo (`browser.evaluate` contra `http://127.0.0.1:5000/`):
  landing visible al abrir, "Entrar" lo cierra, `localStorage` recuerda;
  card de juego al azar con `background-image` no vacío;
  `#dash-activity` con `polyline` si hay actividad;
  sin errores en consola.
- Actualizar `MEMORY.md`/`AGENTS.md` con el conteo real de tests y el changelog.

**Commit:** `chore: verifica landing + dashboard y actualiza docs`

---

## Notas de ejecución

- Un commit por tarea; nunca agrupar.
- Si un test exige cambiar el contrato del harness de tests (p. ej. contar `.nav-item`),
  **no**: el sidebar ya quedó en 6 y este plan no lo toca.
- `escHtml`, `fetchJson`, `toast`, `showPanel` ya existen: reutilizar.
- No añadir dependencias. Todo SVG/CSS.
- Terminado el plan, avisar para pasar al proyecto 4 (RetroAchievements).
