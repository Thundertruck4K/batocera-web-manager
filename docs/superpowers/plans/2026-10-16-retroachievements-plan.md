# Plan: RetroAchievements — récords personales

**Diseño:** `docs/superpowers/specs/2026-10-16-retroachievements-design.md`
**Reglas:** stdlib, TDD, commits atómicos, `python -m pytest -q`, `python _jscheck.py`.

---

### Tarea 1 — Settings + cliente HTTP + caché

**Archivos:** `app.py`, `tests/test_retroachievements.py` (nuevo).
- `DEFAULT_SETTINGS` += `ra_user`, `ra_api_key`, `ra_enabled`.
- `RA_API_BASE`, `RA_CACHE_TTL = 600`, `_ra_cache = {"ts": 0, "data": None}`.
- `_ra_get(settings, endpoint, params=None, timeout=10)`.

**Tests:** `_ra_get` sin credenciales → `None` (y no llama a la red);
con credenciales construye `?z=<user>&y=<key>&u=<user>` y devuelve el JSON;
error de red → `None`. Se monkeypatchea `app._ra_urlopen` (helper inyectable).
`DEFAULT_SETTINGS` contiene las 3 claves.

**Commit:** `feat(ra): settings de RetroAchievements y cliente HTTP con cache`

---

### Tarea 2 — Normalizadores

**Archivo:** `app.py`; **Tests** en `tests/test_retroachievements.py`.
- `ra_profile(settings)` → `{user, avatar, points, true_points, softcore_points,
  member_since, motto, rich_presence, last_game_id}`.
- `ra_recent_achievements(settings, minutes=10080)` → máx 12, badge absoluto.
- `ra_completion(settings, count=20)` → `percent = num_awarded/max_possible*100`.
- `ra_awards(settings)` → `{total, mastery, completion, beaten_hardcore,
  beaten_softcore, events}`.
- Entradas `None`/vacías → lista/dict vacío, nunca lanzan.

**Commit:** `feat(ra): normalizadores de perfil, logros, progreso y premios`

---

### Tarea 3 — Resumen cacheado + endpoints

**Archivo:** `app.py`.
- `get_retroachievements(settings, force=False)` → `{ok, configured, updated,
  profile, recent, completion, awards}`; `configured=False` sin credenciales;
  caché de 10 min.
- `GET /api/retroachievements` y `GET /api/retroachievements/test`.

**Tests:** cache hit (segunda llamada no toca la red, vía contador en el monkeypatch);
`configured=False` sin credenciales; `/test` presente en `app.py`.

**Commit:** `feat(api): endpoints retroachievements y resumen cacheado`

---

### Tarea 4 — Tarjeta de Ajustes

**Archivo:** `templates/index.html`; **Tests** en `tests/test_retroachievements.py`.
- Tarjeta "RetroAchievements" en `#panel-settings` con `#set-ra-user`,
  `#set-ra-api-key`, `#set-ra-enabled`, botones Guardar/Probar y enlace de ayuda.
- JS: `loadRASettings()`, `saveRASettings()`, `testRA()`; llamada a `loadRASettings()`
  desde `loadSettings()`.

**Tests:** existen los ids; el JS contiene las 3 funciones y `/api/retroachievements/test`.

**Commit:** `feat(ui): configuracion de RetroAchievements en Ajustes`

---

### Tarea 5 — Tarjeta del Dashboard

**Archivo:** `templates/index.html`.
- `#dash-retro` con cuerpo `#dash-retro-body`; estado "sin configurar" con
  botón a Ajustes.
- JS: `loadRetro()` / `renderRetro(r)`; `loadRetro()` desde `initDashboard()`.

**Tests:** existe `#dash-retro`; el JS contiene `function loadRetro(`,
`function renderRetro(` y `/api/retroachievements`.

**Commit:** `feat(ui): tarjeta de records personales en el dashboard`

---

### Tarea 6 — Verificación y docs

- `python -m pytest -q`, `python _jscheck.py`, `node --check _extracted.js`,
  `python -m py_compile app.py`.
- Verificación en vivo (sin credenciales → estado "sin configurar", sin errores).
- `MEMORY.md`: changelog + issue de seguridad de la key; `AGENTS.md`: conteo de tests.

**Commit:** `chore: verifica RetroAchievements y actualiza docs`
