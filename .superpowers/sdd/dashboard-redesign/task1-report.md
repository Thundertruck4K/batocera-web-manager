# Task 1 — Report: Layout base (sidebar fijo + CSS vars tema oscuro)

- **Status:** DONE
- **Working directory:** `C:\Users\folk3\Downloads\batocera_web`
- **Commit:** `dcba4aa18647a5d171c77bfd8868e90c35bafb5b`
  - Mensaje: `feat(ui): layout base con sidebar fijo y variables CSS del tema oscuro`
  - Ficheros: `templates/index.html` (1 file changed, 53 insertions(+), 32 deletions(-))
- **Resumen de tests:** `python _jscheck.py` → 1 bloque / 127967 chars; `node --check _extracted.js` → sin salida (OK); `python -m pytest` → **32 passed**; `python -m py_compile app.py` → sin salida.

---

## 1. Objetivo y alcance

Reestructurar `templates/index.html` para que tenga un layout con **sidebar fijo** y un
**tema oscuro elegante** basado en variables CSS, **preservando toda la lógica JS existente**.

Estado previo (`HEAD` = `a4d2bf0`): el fichero ya tenía una sidebar, pero:
- usaba `.layout{display:flex;height:100vh;overflow:hidden}` (no `.app` con grid);
- la paleta era GitHub-dark (`--bg:#0d1117`, `--accent:#58a6ff`…), no la del spec;
- no existía la variable `--panel` ni el contenedor `.app` que consumen las tareas 2–7.

Solo se modificó `templates/index.html`. **No se tocó `app.py`** ni ningún endpoint.

---

## 2. Cambios realizados

### 2.1 Variables CSS (`:root`) — Produce del brief

Se fijan **exactamente** los valores pedidos:

| Variable | Valor |
|---|---|
| `--bg` | `#0f1116` |
| `--bg2` | `#161923` |
| `--bg3` | `#20263a` |
| `--panel` | `#1d2133` (nueva) |
| `--text` | `#e6e9ef` |
| `--text2` | `#9aa0c0` |
| `--text3` | `#6b7394` |
| `--accent` | `#6ea8fe` |
| `--border` | `#2b314d` |
| `--green` | `#3fb950` |
| `--yellow` | `#d29922` |
| `--red` | `#f85149` |
| `--purple` | `#6b3fa0` |
| `--mono` | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` |

Se conservan (y se armonizan con la nueva paleta) las variables de apoyo que ya usaba el
CSS existente y que **no** estaban en el spec, para no romper nada: `--bg4`, `--border2`,
`--accent2`, `--green2`, `--red2`, `--orange`, `--radius`, `--radius2`, `--shadow`,
`--font`, `--sidebar`, `--transition`. Se añade `--purple2` (ver §4.1).

### 2.2 Layout `.app` (grid de 260px + 1fr)

```css
.app{
  display:grid;
  grid-template-columns:260px 1fr;
  min-height:100vh;
}
```

- Se renombra el contenedor `<div class="layout">` → `<div class="app">`.
- `.sidebar` pasa a **sticky/fijo**: `position:sticky;top:0;height:100vh;overflow-y:auto`,
  con gradiente sutil `linear-gradient(180deg,var(--bg2),var(--bg))`.
- El contenido se envuelve en `<main class="main">` (antes `<div class="main">`), y
  `</div><!-- /layout -->` → `</div><!-- /app -->`, `</div><!-- /main -->` → `</main>`.
- `.main{display:flex;flex-direction:column;min-width:0}` y `.content{flex:1;padding:26px 28px 40px}`.
- `.topbar` pasa a `position:sticky;top:0;z-index:60` (+ `backdrop-filter:blur(8px)`), de modo
  que la cabecera queda visible al hacer scroll con la nueva página-scroll.
- Responsive: en `@media(max-width:700px)` se añade `.app{grid-template-columns:1fr}`
  para que, al ocultarse la sidebar, el `main` ocupe todo el ancho.

### 2.3 Jerarquía visual

- Superficies de tarjeta/panel: cada regla específica usa `background:var(--panel)`
  — `.card`, `.system-card`, `.modal`, `.dash-card`, `.fan-card` y `.service-status-box`
  (ver §6: en la primera entrega esto se hizo con una regla agrupada que quedaba muerta).
- Los terminales (`.log-box`, `.xml-box`, `.custom-sh-preview`) dejan de usar el `#0d1117`
  hardcodeado y usan `var(--bg)`.
- La marca de la sidebar pasa a `🕹️ Batocera Manager` (según el brief).

### 2.4 Navegación reutilizada

Se conserva la función **existente** `showPanel(name, btn)` y todos los botones
`.nav-item` con `onclick="showPanel('…',this)"`. No se creó ninguna función de navegación nueva.

---

## 3. Verificación (obligatoria)

```
PS C:\Users\folk3\Downloads\batocera_web> python _jscheck.py
bloques <script>: 1 | caracteres: 127967

PS C:\Users\folk3\Downloads\batocera_web> node --check _extracted.js
(sin salida)

PS C:\Users\folk3\Downloads\batocera_web> python -m pytest
................................                                         [100%]
32 passed in 0.15s

PS C:\Users\folk3\Downloads\batocera_web> python -m py_compile app.py
(sin salida)
```

**Extra (no requerido):**
- Conteo de caracteres del JS extraído = **127967**, idéntico al baseline medido **antes** de
  mis cambios → el bloque `<script>` no se tocó.
- Balance de `<style>`: 274/274 y 3/3 llaves. Balance de etiquetas: `<div>` 496/496,
  `<main>` 1/1, `<aside>` 1/1.
- `app.render_index()` renderiza el HTML sin placeholders sin resolver
  (`unresolved placeholders: []`) y contiene `class="app"`, `grid-template-columns:260px 1fr`,
  `--panel:#1d2133` y `<main class="main">`.

---

## 4. Decisiones de diseño y notas

### 4.1 `--purple` oscuro vs. legibilidad (único ajuste fuera del listado literal)

El spec fija `--purple:#6b3fa0`. Ese tono, usado como **color de texto** sobre `--panel`
(`#1d2133`), da un contraste ≈ 2.2:1 (ilegible). En el código, `--purple` **solo** se usa
como color de texto (`.badge-purple`, y el nombre de carpeta en la tabla de ROMs).

Solución **sin tocar JS**:
- se mantiene `--purple:#6b3fa0` (valor del spec, intacto);
- se añade la variable de apoyo `--purple2:#b18cf0` (púrpura claro legible);
- `.badge-purple` usa `var(--purple2)`;
- se añade `#roms-tbody{--purple:var(--purple2)}` para que el `var(--purple)` inline que
  emite el JS de la tabla de ROMs resuelva a un tono claro dentro de ese subárbol
  (override de custom property por scope, patrón CSS estándar).

### 4.2 Scroll de página vs. scroll interno

El layout anterior usaba scroll interno (`.layout{height:100vh;overflow:hidden}` +
`.content{overflow-y:auto}`). Con el `.app` en grid y sidebar sticky se optó por
**scroll de página** (patrón habitual para sidebar fijo), con la `.topbar` también sticky.
No afecta a la lógica JS.

### 4.3 Breakpoint responsive

Se mantiene el ocultado de la sidebar en `≤700px` (comportamiento previo) y se añade el
colapso de columnas del grid ahí mismo. No se subió a 900px para no cambiar la UX en tablets.

---

## 5. Dudas / puntos abiertos

1. **`--purple` del spec**: ¿el autor pretende `#6b3fa0` como *fondo/acento* (y el texto en un
   tono claro) o como color de texto? Se implementó lo primero conservando el valor del spec.
2. **Reporte no commiteado**: el brief indica commitear solo `templates/index.html`
   (`git add templates/index.html && git commit …`). Este reporte se ha escrito pero **no**
   se ha añadido al commit (`.superpowers/` sigue untracked). Indicar si debe versionarse.
3. **Verificación visual**: el navegador del harness no está conectado en esta sesión
   (`browser.disconnected`), por lo que no se pudo adjuntar captura. La comprobación se hizo
   por estructura/`render_index()`; recomendable una revisión visual en la Task 8.
4. **`.layout` eliminado**: se renombró a `.app` (el brief pide `.app`). No había ninguna
   referencia a `.layout`, `.main` ni `.content` en el JS, así que el cambio es seguro.

---

## 6. Fix post-revisión — Finding UI1 (Important)

**Finding:** la regla agrupada

```css
.card,.system-card,.dash-card,.fan-card,.modal,.service-status-box{ background:var(--panel); }
```

era **muerta**: estaba colocada antes de las 6 reglas específicas, y cada una de ellas
redeclaraba `background:var(--bg2)` con la misma especificidad (0,1,0) → ganaba la última,
por lo que `var(--panel)` no se aplicaba nunca (era además su único uso en el CSS).

**Corrección aplicada** (opción 1 del reviewer): se **elimina** la regla agrupada y se pone
`background:var(--panel)` **dentro de cada regla específica**:

| Selector | Antes | Ahora |
|---|---|---|
| `.card` | `background:var(--bg2)` | `background:var(--panel)` |
| `.system-card` | `background:var(--bg2)` | `background:var(--panel)` |
| `.modal` | `background:var(--bg2)` | `background:var(--panel)` |
| `.dash-card` | `background:var(--bg2)` | `background:var(--panel)` |
| `.fan-card` | `background:var(--bg2)` | `background:var(--panel)` |
| `.service-status-box` | `background:var(--bg2)` | `background:var(--panel)` |

En su lugar se deja un comentario-guía (sin declaración) para mantener el hilo documental.
Con esto `--panel` (`#1d2133`) se aplica **realmente**, distinguiendo las tarjetas del
fondo `--bg` (`#0f1116`), que era la intención del rediseño.

**Verificación de que ya no hay regla muerta** (script `_bg_check.py`, temporal): para cada
uno de los 6 selectores la única declaración `background` es `var(--panel)`; no existe
ninguna otra regla posterior (ni en media queries) que la sobreescriba. Los únicos otros
`background` son los `::before` (barras de acento), no relacionados.

**Commit del fix:** `373d231e95af5034de8a62daecffd70d4c9020dc`
— `fix(ui): aplicar var(--panel) dentro de cada regla de tarjeta/panel (regla agrupada muerta)`
— `templates/index.html` (1 file changed, 8 insertions(+), 10 deletions(-)).

**Cobertura re-ejecutada tras el fix:**

```
PS C:\Users\folk3\Downloads\batocera_web> python _jscheck.py
bloques <script>: 1 | caracteres: 127967

PS C:\Users\folk3\Downloads\batocera_web> node --check _extracted.js
(sin salida)

PS C:\Users\folk3\Downloads\batocera_web> python -m pytest
................................                                         [100%]
32 passed in 0.15s

PS C:\Users\folk3\Downloads\batocera_web> python -m py_compile app.py
(sin salida)
```

Extra: JS extraído **127967 chars** (idéntico → JS intacto); balance de `<style>` 273/273 y
3/3; `render_index()` sin placeholders sin resolver y con `--panel:#1d2133` presente.

