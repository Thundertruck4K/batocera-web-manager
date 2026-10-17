# Plan: Restyle «Aurora Glass» del gestor completo

**Fecha:** 2026-10-16 (re-escrito el 2026-10-17 tras perderse el original)
**Especificación:** `docs/superpowers/specs/2026-10-16-aurora-glass-restyle-design.md`
**Fichero objetivo:** `templates/index.html`
**Tests existentes:** `tests/*.py` (231) — **no se modifican**. Deben seguir pasando.
**Commit al terminar cada tarea.**

---

## 1. Contexto y restricciones

- Todo el CSS/markup/JS vive en `templates/index.html`.
- UI-HELPERS: entre `<!-- >>> UI-HELPERS` y `<!-- <<< UI-HELPERS`. **No tocar sus marcadores.**
- `showPanel(name, btn)` debe conservar `.nav-item`, `remove('active')`, `add('active')`; su cuerpo no debe contener `'biosmissing'` ni `'preview'`.
- `.nav-item.active { … }` debe contener `gradient` y `border`.
- `.nav-item.active svg { … }` debe contener `var(--accent)` y `stroke`.
- Sidebar: `<aside class="sidebar">`, `<nav class="nav">`, 6 `.nav-item`, ≥6 `<svg>`, sin emojis en el nav, 5 secciones, badges `badge-count`/`badge-biosmissing`.
- Contraste: `--text2`/`--text3` ≥ 4.5 vs `--bg`/`--panel` (`test_theme_contrast`, 4 tests).
- Sin renombrar tokens `:root`. Los tokens de apoyo del fichero (`--bg4`, `--border2`, `--accent2`, `--green2`, `--red2`, `--orange`, `--purple2`, `--sidebar`, `--transition`) se conservan; se añade `--aurora`.
- No cambiar IDs/clases/estructura/lógica JS. **Sí se ajustan literales de color** (CSS, estilos en línea, cadenas JS).

---

## 2. Estado (2026-10-17)

| Tarea | Estado |
|---|---|
| 1. Tokens + Google Fonts | **hecho** (`e454213` fuentes, `f8086ba` tokens) |
| 2. Capa FX (aurora, grano, partículas) + reduced-motion | **hecho** (`5b039bc`, `bc224eb`, `56427c1`) |
| 3. Superficies (cristal 4 sitios, tarjetas+brillo, info/warn/success) | **hecho** (`f385f6a`, `0849189` completa system-card/fan-card/service-status-box) |
| 4. Materialización (`mat`) + reduced-motion | **hecho** (`c793382`) |
| 5. Unificación de paleta fuera de `:root` | **hecho** (`0849189`, `7138684`) |
| 6. Verificación final | **hecho** (231 verdes, `node --check` OK, 6 paneles + modal + tabla, 0 colores viejos en runtime) |

---

## 3. Tarea 5 — Unificación de paleta (en curso)

Tres frentes, sin tocar estructura/IDs/clases/lógica:

1. **CSS suelto** (bloque `<style>`): sustituir literales por tokens.
2. **Acentos estáticos en estilos en línea** (tarjetas KPI: `style="--card-accent:#f0883e"`): recolorear desde CSS con reglas por `id` y `!important` (ganan al estilo en línea sin editarlo).
3. **Cadenas de color en JS**: `HW_COLORS`/`CARD_PALETTE` (bloque UI-HELPERS), estado de ES (`#238636`/`#da3633`), colores de las gráficas de tacho/red. Editar **solo los literales**.

### Mapa de sustitución

| Literal viejo | Uso | Nuevo |
|---|---|---|
| `#58a6ff`, `#388bfd`, `#1f6feb`, `#6e40c9`, `#0d9488` | azules/acentos | `var(--accent)` |
| `rgba(88,166,255,*)`, `rgba(110,168,254,*)` | azul translúcido | `rgba(124,156,255,*)` |
| `#3fb950`, `#2ea043`, `#238636` | verdes | `var(--green)` / `var(--green2)` |
| `rgba(63,185,80,*)` | verde translúcido | `rgba(63,214,139,*)` |
| `#f85149`, `#da3633` | rojos | `var(--red)` / `var(--red2)` |
| `rgba(248,81,73,*)` | rojo translúcido | `rgba(255,107,107,*)` |
| `#d29922`, `#e3b341` | amarillos | `var(--yellow)` |
| `rgba(210,153,34,*)` | amarillo translúcido | `rgba(242,196,107,*)` |
| `#f0883e`, `#e08b4c`, `#ff6900` | naranjas | `var(--orange)` |
| `rgba(240,136,62,*)` | naranja translúcido | `rgba(255,167,107,*)` |
| `#6b3fa0`, `#bc8cff`, `#b18cf0` | morados | `var(--purple)` / `var(--purple2)` |
| `rgba(188,140,255,*)` | morado translúcido | `rgba(169,139,255,*)` |
| `#76b900` | verde NVIDIA | dejar (marca) o mapear a `var(--green)` |

### Puntos concretos pendientes

- **Badges** (`.badge-*`): fondos translúcidos a los rgba nuevos.
- **Botones**: `.btn-primary:hover` `#388bfd` → hover de `--accent2`; `.btn-success:hover` `#2ea043` → hover de `--green2`; `.btn-danger:hover` `#f85149` → hover de `--red2`.
- **`.log-box`** `color:#3fb950` → `var(--green)`.
- **Superficies que faltan por el tratamiento de cristal/brillo**: `.system-card`, `.fan-card`, `.service-status-box` (mismo `linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.012)), var(--panel)` + `box-shadow`).
- **Acentos KPI inline** vía CSS `!important` por `id` (`#kpi-cpu`, `#kpi-gpu`, `#kpi-ram`, `#kpi-disk`, `#kpi-net`).
- **JS**: `HW_COLORS`, `CARD_PALETTE` (UI-HELPERS), ES (`#238636`/`#da3633`), tacho.

**Criterio de aceptación:** paleta unificada; tests verdes; `grep` final de literales solo con tokens y colores de marca justificados.

**Commit:** `style(unify): unifica paleta fuera de :root (CSS, KPI inline, JS)`

---

## 4. Tarea 6 — Verificación final

1. `python -m pytest` → 231 verdes (canarios: `test_theme_contrast`, `test_sidebar_ui`, `test_landing_dashboard`, `test_nav_merge`, `test_random_game_ui`, `test_scraper_system_ui`, `test_es_reload_ui`).
2. Extraer el bloque JS y comprobar sintaxis (como ya se hacía con `node --check` si hay node).
3. Recorrido visual en el navegador: los 6 paneles, un modal, una tabla; materialización, legibilidad, sin errores en consola.
4. `prefers-reduced-motion`: sin animaciones.
5. Barrido final de literales.

---

## 5. Notas de ejecución

- Un solo fichero. Cambios quirúrgicos. `git add templates/index.html` antes de cada commit.
- **No** editar tests.
- El regex de `.nav-item.active` casa hasta el primer `}` → no anidar llaves en ese cuerpo.
- Ante cualquier edición que no persista: verificar con `git show HEAD:templates/index.html` (el fichero se ha visto revertido por un proceso externo).
