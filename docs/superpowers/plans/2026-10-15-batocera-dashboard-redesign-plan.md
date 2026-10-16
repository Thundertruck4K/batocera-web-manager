# Batocera Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Rediseñar el dashboard de Batocera (templates/index.html + app.py) para que sea más atractivo, informativo y ágil, con sidebar fijo, KPIs de hardware y gestión de sistemas fluida.

**Architecture:** SPA en un único `templates/index.html` servido por `app.py` (stdlib `http.server`). El rediseño se hace por secciones sin romper las rutas `/api/*` existentes: primero layout/CSS, luego KPIs, luego sistemas/ROMs, luego scraper/BIOS/servicios, y al final rendimiento.

**Tech Stack:** Python 3.11+ stdlib (`http.server`), HTML/CSS/JS vanilla (sin dependencias), pytest para tests.

**Spec:** docs/superpowers/specs/2026-10-15-batocera-dashboard-redesign-design.md

## Global Constraints

- Solo stdlib de Python; nada de dependencias externas nuevas.
- No romper rutas `/api/*` existentes ni el contrato JSON actual.
- Todo cambio de frontend debe pasar `node --check` sobre el JS extraído (`python _jscheck.py; node --check _extracted.js`).
- `python -m pytest` debe seguir en 32/32 verde.
- `python -m py_compile app.py` debe pasar.
- Tema oscuro elegante, sin frameworks CSS.
- Toda entrada dinámica en HTML debe pasar por `escHtml` y los handlers inline deben usar `data-*` + `this.dataset` (nunca literales JS concatenados).

## Review Focus

- Nombres de sistema/ROM/subcarpeta con comillas (`'`, `"`) no deben romper atributos ni inyectar HTML.
- El índice de ROM al filtrar/ordenar debe resolver siempre a la ROM correcta (por `filename`, no por índice de la lista filtrada).
- El `onclick` inline no puede referenciar variables locales de una función (deben vivir en `window`).
- Rutas de fichero manipuladas por el usuario (`system`, `slug`, `filename`) no deben escapar de su base.
- No introducir re-render completo en cada interacción (causa parpadeo/lentitud).

---

### Task 1: Layout base (sidebar fijo + CSS vars tema oscuro)

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: nada (primera tarea).
- Produces: variables CSS globales (`--bg`, `--bg2`, `--panel`, `--text`, `--text2`, `--text3`, `--accent`, `--border`, `--green`, `--yellow`, `--red`, `--purple`, `--mono`) y contenedor `.app` con `grid-template-columns: 260px 1fr` que las tareas siguientes reutilizan.

- [ ] **Step 1: Inspeccionar la estructura actual** de `templates/index.html` (cabecera, `<style>`, contenedores de tabs, `<script>`).

- [ ] **Step 2: Añadir/ajustar el bloque `:root`** con las variables CSS listadas en Interfaces (valores del spec: bg `#0f1116`, bg2 `#161923`, panel `#1d2133`, text `#e6e9ef`, text2 `#9aa0c0`, accent `#6ea8fe`, border `#2b314d`, green `#3fb950`, yellow `#d29922`, red `#f85149`, purple `#6b3fa0`).

- [ ] **Step 3: Envolver el contenido en `.app` con sidebar fijo** (`position: sticky; top: 0; height: 100vh`) y nav con los botones de sección existentes.

- [ ] **Step 4: Verificar JS válido**

Run: `python _jscheck.py; node --check _extracted.js`
Expected: sin errores de sintaxis.

- [ ] **Step 5: Verificar backend/tests**

Run: `python -m pytest` → 32 passed. `python -m py_compile app.py` → sin salida.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html
git commit -m "feat(ui): layout base con sidebar fijo y variables CSS del tema oscuro"
```

---

### Task 2: KPIs de hardware (CPU/GPU/RAM/Disco/Red/ES)

**Files:**
- Modify: `templates/index.html`
- Modify: `app.py` (solo si falta algún campo en `/api/stats`)

**Interfaces:**
- Consumes: variables CSS de Task 1.
- Produces: función JS `renderKpis(stats)` que pinta 6 tarjetas a partir del payload de `/api/stats`.

- [ ] **Step 1: Confirmar el payload de `/api/stats`** (cpu, gpu, memory, disk, network, es) y anotar los campos exactos.

- [ ] **Step 2: Añadir una fila `.kpi`** con 6 tarjetas (CPU/temp, GPU/VRAM, RAM, Disco, Red/IP, ES/puerto) usando las variables CSS.

- [ ] **Step 3: Implementar `renderKpis(stats)`** que rellena las tarjetas; usar `textContent` para valores numéricos.

- [ ] **Step 4: Verificar JS válido** (`python _jscheck.py; node --check _extracted.js`).

- [ ] **Step 5: Verificar tests** (`python -m pytest` → 32 passed).

- [ ] **Step 6: Commit**

```bash
git add templates/index.html app.py
git commit -m "feat(ui): tarjetas KPI de hardware en el panel principal"
```

---

### Task 3: Grid de sistemas (logos, estado, BIOS, color estable)

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: `renderRomSystems(systems)` existente.
- Produces: helper `cardColor(s)` (color estable por nombre, `hwColors` si `s.hardware` existe).

- [ ] **Step 1: Escribir un test Node** que cargue `renderRomSystems` con un sistema cuyo `name` contenga `'` y compruebe que el HTML resultante no rompe el atributo `data-system` (usar `escHtml`).

- [ ] **Step 2: Ejecutar el test y verlo fallar** si el escapado no está.

- [ ] **Step 3: Asegurar que el grid usa `data-system` + `this.dataset.system`** y `cardColor(s)` para el color; estado (vacío/ROMs) y aviso BIOS visibles.

- [ ] **Step 4: Verificar JS válido** y **tests** (`python -m pytest` → 32 passed).

- [ ] **Step 5: Commit**

```bash
git add templates/index.html tests/
git commit -m "feat(ui): grid de sistemas con color estable y estado/BIOS visibles"
```

---

### Task 4: Lista de ROMs con filtro/ordenado correctos

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: `renderRoms(list)`, `filterRoms()`, `sortRoms()`, `showRomDetail(filename)`.
- Produces: sin nuevas interfaces públicas (solo corrección de índices).

- [ ] **Step 1: Escribir un test Node** que llame `showRomDetail('x.zip')` tras un filtrado y verifique que resuelve la ROM correcta por `filename`.

- [ ] **Step 2: Ejecutar y verlo fallar** si aún indexa por posición.

- [ ] **Step 3: Confirmar que botones Ver/Renombrar/Eliminar y navegación de subcarpetas usan `data-*`** (no literales con comillas).

- [ ] **Step 4: Verificar JS válido** y **tests**.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html tests/
git commit -m "fix(ui): resolver ROM por filename en la lista filtrada"
```

---

### Task 5: Scraper/Batch y BIOS UI

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: `/api/scraper/batch/*`, `/api/bios/missing`, `/api/bios/missing/skip` (POST).
- Produces: panel de batch con progreso y tabla BIOS faltantes/presentes con acción "Ignorar" (POST) y estado de skip.

- [ ] **Step 1: Revisar los endpoints** `/api/bios/missing` y `/api/bios/missing/skip` para confirmar el contrato.

- [ ] **Step 2: Ajustar la tabla BIOS** para mostrar faltantes vs presentes, MD5 y botón Ignorar que llama `POST /api/bios/missing/skip` y refresca.

- [ ] **Step 3: Ajustar el panel de batch** (progreso, contadores OK/fallos, errores vía `window._batchErrorsText`).

- [ ] **Step 4: Verificar JS válido** y **tests**.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html
git commit -m "feat(ui): paneles de scraper/batch y BIOS con skip persistente"
```

---

### Task 6: Servicios / custom.sh y logs

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: `/api/service/status`, `/api/service/read-sh`, `/api/service/install`, `/api/service/restart`.
- Produces: vista de servicios con preview de `custom.sh` y estado de autostart.

- [ ] **Step 1: Confirmar rutas y payloads** de servicios.
- [ ] **Step 2: Ajustar la vista** (estado, preview, botones) sin romper las llamadas existentes.
- [ ] **Step 3: Verificar JS válido** y **tests**.
- [ ] **Step 4: Commit**

```bash
git add templates/index.html
git commit -m "feat(ui): vista de servicios y custom.sh"
```

---

### Task 7: Rendimiento (menos re-render)

**Files:**
- Modify: `templates/index.html`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: sin nuevas interfaces; reducción de reescrituras de `innerHTML`.

- [ ] **Step 1: Identificar los puntos que reescriben `innerHTML` en cada interacción** (búsqueda/orden/scroll).
- [ ] **Step 2: Aplicar delegación de eventos** en contenedores estáticos y actualizar solo las filas afectadas cuando sea viable.
- [ ] **Step 3: Verificar JS válido** y **tests**.
- [ ] **Step 4: Commit**

```bash
git add templates/index.html
git commit -m "perf(ui): delegación de eventos y menos re-render"
```

---

### Task 8: Verificación final

**Files:**
- Modify: ninguno (verificación).

- [ ] **Step 1: Extraer y validar JS**

Run: `python _jscheck.py; node --check _extracted.js`
Expected: sin errores.

- [ ] **Step 2: Suite completa**

Run: `python -m pytest`
Expected: 32 passed (o más si se añadieron tests).

- [ ] **Step 3: Compilación**

Run: `python -m py_compile app.py`
Expected: sin salida.

- [ ] **Step 4: Lint**

Run: `python -m ruff check app.py --select F,E9`
Expected: sin errores críticos nuevos.

- [ ] **Step 5: Commit** (si hubo ajustes)

```bash
git add -A
git commit -m "chore: verificación final del rediseño"
```
