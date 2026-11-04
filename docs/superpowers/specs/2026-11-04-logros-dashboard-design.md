# Diseño: dashboard de logros (RetroAchievements) en la SPA

**Fecha:** 2026-11-04
**Estado:** aprobado (diseño delegado por el usuario)

## Objetivo

Una sección **Logros** en la SPA con un dashboard de los juegos en los que el
usuario tiene más logros en [RetroAchievements](https://retroachievements.org),
usando **la carátula que dejó el scraper** en la biblioteca local (no el icono
de RA). Cada juego va en su propia tarjeta, con iconos estilizados y el set de
colores del proyecto. Si no hay cuenta configurada, la sección lo avisa y
ofrece configurarla.

Continúa el diseño de `2026-10-16-retroachievements-design.md`, que dejó
explícitamente fuera de alcance «matchear tus ROMs con sets de RA». Eso es
justo lo que hace esta tanda.

## Decisiones

1. **Emparejado por título normalizado**, no por hash. RA publica hashes MD5
   del ROM *descifrado* (`API_GetGameList.php?h=1`), no del fichero comprimido
   de la SD: hashear la biblioteca en una Batocera sería lento y no encajaría.
   Se normaliza el título (regiones, «[!]», «~Hack~», acentos, signos) y se
   busca una coincidencia exacta en la biblioteca local.
2. **Sin coincidencia no se inventa nada**: la tarjeta cae al icono de RA y
   la API informa de cuántos juegos han sido emparejados (`matched`/`total`).
3. **Una sola llamada a la red.** El dashboard reutiliza la caché de
   `get_retroachievements()` (10 min): el rango de juegos sube de 20 a 100 y la
   interfaz clásica sigue mostrando los 5 primeros (corta en el JS).
4. **El índice de la biblioteca se cachea 5 min** y se construye sólo cuando
   hace falta (no al arrancar).
5. **Orden en el cliente.** La API devuelve los juegos; la página los ordena
   por logros obtenidos, por porcentaje o por logros totales, con una barra de
   píldoras.
6. **Sin dependencias nuevas** y **sin tocar `templates/index.html`**.

## Contrato de la API (revisado en api-docs.retroachievements.org)

`API_GetUserCompletionProgress.php` (`u`, `o`, `c`; `c` por defecto 100, máx. 500)
devuelve `{Count, Total, Results[]}` con, por juego: `GameID`, `Title`,
`ImageIcon`, `ConsoleID`, `ConsoleName`, `MaxPossible`, `NumAwarded`,
`NumAwardedHardcore`, `MostRecentAwardedDate`, `HighestAwardKind`
(`mastered` | `completed` | `beaten-hardcore` | `beaten-softcore` | null) y
`HighestAwardDate`.

De ahí salen los datos útiles de cada tarjeta: cuántos logros tienes, cuántos
había, qué porcentaje, en qué modo (softcore/hardcore) y cuándo fue el
último. `API_GetUserProfile.php` aporta los puntos y la fecha de alta;
`API_GetUserAwards.php`, los premios (dominados, completados, batidos).

### Endpoint nuevo

`GET /api/retroachievements/games` →

```json
{
  "ok": true, "configured": true, "enabled": true, "updated": 1762300000.0,
  "profile": { "user": "...", "points": 0, "true_points": 0, "...": "" },
  "awards": { "total": 0, "mastery": 0, "completion": 0, "...": 0 },
  "games": [{
    "game_id": 14402, "title": "Mega Man 2", "console": "NES",
    "icon": "https://retroachievements.org/Images/074560.png",
    "num_awarded": 12, "num_awarded_hardcore": 3, "max_possible": 20,
    "percent": 60.0, "hardcore": true,
    "award_kind": "beaten-hardcore", "award_date": "...", "recent_date": "...",
    "system": "nes", "system_name": "Nintendo Entertainment System",
    "filename": "Mega Man 2 (USA).zip", "subpath": "", "has_art": true,
    "local": true
  }],
  "matched": 8, "total": 12
}
```

`configured=false` si faltan usuario o Web API Key; `enabled=false` si el
interruptor está apagado. En ambos casos **no se toca la red**.

## Backend (`app.py`)

- `ra_normalize_title(text)` → clave comparable (minúsculas, acentos plegados,
  sin etiquetas de región, sin «[!]» ni «~Hack~», «&» → «and»).
- `build_local_game_index(roms_base)` → `{clave: [(system, filename, subpath)]}`
  a partir de los `gamelist.xml` (o de los ficheros sueltos si no hay
  gamelist). Se ignoran las entradas cuyo ROM ya no existe.
- `match_local_game(index, roms_base, title)` → el ROM local, prefiriendo el
  que tiene carátula.
- `get_ra_games(settings)` → el payload de arriba.

## Frontend (`frontend/src`)

- `pages/Achievements.tsx`: la sección. Cabecera con el perfil (usuario,
  puntos, puntos true, miembro desde), cuatro tarjetas de resumen (puntos,
  juegos con progreso, logros obtenidos, dominados) y la rejilla de tarjetas.
  Sin cuenta configurada: aviso con botón a *Configuración*. Desactivado: lo
  mismo, diciendo que está apagado.
- `components/achievements/AchievementCard.tsx`: la tarjeta. Carátula local
  (`/api/rom-image/<sistema>/<fichero>`) o icono de RA como respaldo; píldora
  con la consola; anillo de progreso con el icono del estado; barra de
  progreso; pie con los logros en hardcore y la fecha del último.
- Iconos por estado: `Trophy` (dominado), `Crown` (100 %), `Medal`
  (completado), `Award` (batido), `Sparkles` (en progreso), `Lock` (sin
  logros).
- `lib/nav.ts`: la sección deja de estar marcada como *Pronto*.

## Tests

- `tests/test_ra_games.py`: normalización de títulos, índice local, emparejado
  (con y sin carátula), payload del endpoint y la regla de «no tocar la red
  sin credenciales».
- `tests/test_ra_ui.py`: la sección existe en la SPA (ruta, menú sin *Pronto*,
  aviso de cuenta sin configurar, iconos de estado).

## Fuera de alcance

- Emparejar por hash de RA (imposible con ROMs comprimidos).
- Logros detallados de cada juego (haría falta una llamada por juego).
- Leaderboards, puntuaciones o escritura en RA (sólo lectura).
