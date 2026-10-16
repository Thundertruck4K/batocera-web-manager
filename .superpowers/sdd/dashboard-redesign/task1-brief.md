# Task 1: Layout base (sidebar fijo + CSS vars tema oscuro)

Working directory: **C:\Users\folk3\Downloads\batocera_web** (usa rutas absolutas).

## Files
- Modify: `C:\Users\folk3\Downloads\batocera_web\templates\index.html`

## Goal
Reestructurar `templates/index.html` para que tenga un layout con **sidebar fijo** (navegación de secciones) y un **tema oscuro elegante** basado en variables CSS, **preservando toda la lógica JS existente** (no romper ninguna función ni endpoint).

## Produces (lo que usarán las tareas siguientes)
- Variables CSS en `:root`:
  - `--bg:#0f1116`, `--bg2:#161923`, `--bg3:#20263a`, `--panel:#1d2133`,
    `--text:#e6e9ef`, `--text2:#9aa0c0`, `--text3:#6b7394`,
    `--accent:#6ea8fe`, `--border:#2b314d`,
    `--green:#3fb950`, `--yellow:#d29922`, `--red:#f85149`, `--purple:#6b3fa0`,
    `--mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
- Layout `.app` con `display:grid; grid-template-columns: 260px 1fr; min-height:100vh`
- `.sidebar` sticky/fijo con la marca y los botones de sección.

## Steps
1. Lee `templates/index.html` completo y localiza: `<head><style>`, la barra superior/tabs actuales, los contenedores de cada sección y el bloque `<script>`.
2. Añade/ajusta `:root` con las variables de arriba.
3. Envuelve el contenido en `<div class="app">` con `<aside class="sidebar">…</aside>` y `<main>…</main>`. La sidebar contiene la marca ("🕹️ Batocera Manager") y botones que llaman a la función de cambio de sección **ya existente** (no inventes una nueva si ya hay una; reutilízala).
4. Ajusta el CSS para que el tema sea oscuro elegante y el contenido tenga `padding` y jerarquía claros.
5. **No toques** las funciones JS de datos/API; solo HTML/CSS y, si hace falta, el nombre de la función de navegación ya existente.

## Verification (obligatorio, pega la salida en el report)
```
cd C:\Users\folk3\Downloads\batocera_web
python _jscheck.py
node --check _extracted.js
python -m pytest
python -m py_compile app.py
```
Esperado: `node --check` sin errores; `pytest` → **32 passed**; `py_compile` sin salida.

## Report
Escribe el reporte completo en `C:\Users\folk3\Downloads\batocera_web\.superpowers\sdd\dashboard-redesign\task1-report.md`
y devuelve solo: status (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), commits, resumen de tests en una línea, y dudas.

## Reglas
- NO lances subagentes.
- Commitea al terminar: `git add templates/index.html && git commit -m "feat(ui): layout base con sidebar fijo y variables CSS del tema oscuro"`.
- Toda entrada dinámica en HTML debe seguir usando `escHtml`.
