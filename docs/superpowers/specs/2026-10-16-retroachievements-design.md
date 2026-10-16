# Diseño: RetroAchievements — récords personales

**Fecha:** 2026-10-16
**Proyecto:** 4 de 6
**Estado:** aprobado (diseño delegado por el usuario)

## Objetivo

Mostrar, dentro del dashboard, los **récords personales** del usuario en
[RetroAchievements](https://retroachievements.org): puntos, logros recientes,
juegos dominados/completados y progreso. Las credenciales se configuran a mano en
**Ajustes** y la integración es **opcional**.

## Decisiones

1. **Credenciales = usuario + Web API Key.** Nunca la contraseña. La Web API Key
   se saca de `https://retroachievements.org/settings`.
2. **Opcional y a prueba de fallos.** Sin credenciales: no se llama a la red, no
   se muestran errores; el dashboard invita a configurarlo.
3. **Solo stdlib** (`urllib.request`) y **caché con TTL** (10 min), siguiendo el
   patrón de `get_news()` (`{"ts": ..., "data": ...}`).
4. **Ubicación:** credenciales en *Ajustes*; los récords en una tarjeta del
   *Dashboard*. No se añaden ítems al sidebar (quedó con 5 bloques / 6 destinos).
5. **Sin dependencias nuevas.**
6. **Datos honestos.** Si un campo no viene, se omite; no se inventan cifras.

## Contrato de la API (confirmado en api-docs.retroachievements.org)

- **Base:** `https://retroachievements.org/API`
- **Autenticación (query):** `z=<usuario>`, `y=<web api key>`, `u=<usuario>`.

| Endpoint | Query extra | Respuesta (normalizada) |
|---|---|---|
| `API_GetUserProfile.php` | — | `{user, avatar, points, true_points, softcore_points, member_since, motto, rich_presence, last_game_id}` |
| `API_GetUserRecentAchievements.php` | `m=<minutos>` | `[{title, desc, points, true_ratio, hardcore, game, game_id, date, badge}]` |
| `API_GetUserCompletionProgress.php` | `c=`, `o=` | `[{game_id, title, console, icon, num_awarded, max_possible, hardcore, percent, beaten_date, mastery_date}]` |
| `API_GetUserAwards.php` | — | `{total, mastery, completion, beaten_hardcore, beaten_softcore, events}` |

`avatar`, `badge`, `icon` se devuelven como URL absoluta
(`https://retroachievements.org` + el path relativo que entrega la API).

## Backend (`app.py`)

- `DEFAULT_SETTINGS` += `"ra_user": ""`, `"ra_api_key": ""`, `"ra_enabled": False`.
  (Necesario: `POST /api/settings` solo persiste claves presentes en `DEFAULT_SETTINGS`.)
- Constantes: `RA_API_BASE`, `RA_CACHE_TTL = 600`, `_ra_cache = {"ts": 0, "data": None}`.
- `_ra_get(settings, endpoint, params=None, timeout=10)` → `dict|list|None`.
  Construye `{z, y, u, **params}`; `None` si faltan credenciales o si falla (nunca lanza).
- `ra_profile(settings)`, `ra_recent_achievements(settings, minutes=10080)`,
  `ra_completion(settings, count=20)`, `ra_awards(settings)` → normalizados.
- `get_retroachievements(settings, force=False)` → combinado y cacheado:
  `{ok, configured, updated, profile, recent, completion, awards}`.
  `configured=False` si no hay usuario/key; `ok=False` si la API falla.
- Endpoints:
  - `GET /api/retroachievements` → `get_retroachievements(s)`
  - `GET /api/retroachievements/test` → `{"ok", "configured", "user"}` (prueba de conexión)

## Frontend (`templates/index.html`)

### Ajustes
Tarjeta propia "RetroAchievements" (no vía `settingsMeta`):
- `#set-ra-user`, `#set-ra-api-key` (type=password + botón mostrar), `#set-ra-enabled`.
- Botones "Guardar" (`saveRASettings()`) y "Probar conexión" (`testRA()`).
- Nota con enlace a `https://retroachievements.org/settings` explicando de dónde sale la key.
- JS: `loadRASettings()` (rellena desde `/api/settings`), `saveRASettings()`, `testRA()`.

### Dashboard
Tarjeta "🏆 Récords personales (RetroAchievements)"  `#dash-retro`:
- Sin configurar → mensaje + botón que lleva a Ajustes (`showPanel('settings', …)`).
- Configurado → avatar, usuario, **puntos** y **puntos true**, miembro desde, motto;
  **últimos logros** (badge + título + juego); **awards** (dominados/completados).
- JS: `loadRetro()` / `renderRetro(r)`; se llama desde `initDashboard()`.

## Seguridad

- Se guarda la **Web API Key**, no la contraseña.
- `GET /api/settings` ya devuelve todos los ajustes y la app no tiene auth (issue
  conocido del proyecto). Riesgo equivalente al de `batocera.conf`; aceptado para
  un servicio en LAN. Se documenta en `MEMORY.md`.
- No se envía la key al frontend salvo en `/api/settings` (uso local).

## Tests (`tests/test_retroachievements.py`)

Con `monkeypatch` sobre `app.urllib.request.urlopen` (o un helper inyectable):
1. `_ra_get` construye la URL con `z`/`y`/`u` y devuelve `None` sin credenciales.
2. `ra_profile` normaliza (incluye avatar absoluto).
3. `ra_recent_achievements` normaliza (tope de items, badge absoluto).
4. `ra_completion` normaliza y calcula `percent`.
5. `ra_awards` normaliza el resumen.
6. `get_retroachievements` cachea (segunda llamada sin red) y marca `configured=False`.
7. `DEFAULT_SETTINGS` contiene las claves `ra_*`.
8. Estructura HTML: tarjeta de Ajustes, tarjeta del Dashboard, funciones JS y endpoints.

## Fuera de alcance

- Scraping de ROMs vs. RA (matchear tus ROMs con sets de RA). Se puede añadir después.
- Leaderboards / high scores por juego.
- Escritura en RA (solo lectura).
