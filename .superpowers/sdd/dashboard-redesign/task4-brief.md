# Task 4: Lista de ROMs con filtro/ordenado correctos (resolver por filename)

Working directory: **C:\Users\folk3\Downloads\batocera_web** (usa rutas absolutas / workdir).

## Files
- Modify: `C:\Users\folk3\Downloads\batocera_web\templates\index.html`
- Modify (test): añadir tests si hace falta `tests/` (aunque el plan original los mencionaba, prioriza pasar JS válido + no romper tests existentes)

## Contexto
La UI de ROMs es `#panel-roms` + función `renderRoms(list)`, `filterRoms()`, `sortRoms()`,
`showRomDetail(filename)`. Ya había correcciones antiguas para usar `data-*`, pero tras el
rediseño/reestructura, hay riesgo de que `showRomDetail` vuelva a indexar por posición de
la lista renderizada (filtrada/ordenada).

## Goal
- Al mostrar ROMs (filtradas/ordenadas), los clicks/botones deben resolverse por `filename`
  de la ROM (camino seguro), nunca por índice numérico de la lista visible.
- Búsqueda: filtrar por nombre/archivo (case-insensitive).
- Ordenación: mantener el criterio anterior o añadir A-Z / tamaño / extensión. Conservador.
- Subcarpetas: navegación fluida (usar `data-*`, nunca literales JS con comillas).
- Botones Ver/Renombrar/Eliminar: usar `data-filename`/`data-system`/`data-path` según
  corresponda.
- No re-render completo ineficiente (si es posible, delegación). Mínimos cambios.

## Steps
1. Inspecciona `renderRoms`, `showRomDetail`, `navigateToFolder`/`renameRom`/`deleteRom`
   en `templates/index.html`. Identifica si usan índice.
2. Cambia `showRomDetail(x)` para resolver: `const i = currentRoms.findIndex(r=>r.filename===x)`
   (o comparar contra el filename tal como viene). No usar índice de lista filtrada.
   También funciona para los botones (usar `data-filename` del elemento).
3. Añade filtros/orden en `#panel-roms` encima de la tabla/lista (input + select).
4. Revisa cualquier uso de `onclick="..."` con interpolación de strings: reemplázalo por
   `data-*` + event delegation. Si hay que mantener API mínima, haz el cambio más local posible.
5. Añade un test Node/JS vía pytest si existe patrón, o añade un test simple en Python que
   valide el comportamiento mediante el helper de extracción. El objetivo NO es romper tests existentes.

## Tests
Si puedes extraer el JS y probar por Node (`node -e '...'` desde pytest), hazlo. Si no
es directo, al menos documenta la verificación.

## Verification (obligatorio; pega salida)
```
cd C:\Users\folk3\Downloads\batocera_web
python _jscheck.py
node --check _extracted.js
python -m pytest
python -m py_compile app.py
```
Esperado: node OK; pytest **>=42 passed**; py_compile sin salida.

## Report
`C:\Users\folk3\Downloads\batocera_web\.superpowers\sdd\dashboard-redesign\task4-report.md`
Devuelve SOLO: status, commit hash, tests en una línea, dudas.

## Reglas
- NO subagentes. Prioriza no romper funcionalidad. Commit:
  `git add templates/index.html tests/ && git commit -m "fix(ui): resolver ROM por filename en lista filtrada; mejorar filtros ROMs"`.
