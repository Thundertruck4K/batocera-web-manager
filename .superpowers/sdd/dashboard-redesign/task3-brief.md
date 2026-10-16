# Task 3: Grid/lista de sistemas (visual, color estable, estado + BIOS)

Working directory: **C:\Users\folk3\Downloads\batocera_web** (rutas absolutas / workdir).

## Files
- Modify: `C:\Users\folk3\Downloads\batocera_web\templates\index.html`
- Modify (solo si falta dato): `C:\Users\folk3\Downloads\batocera_web\app.py`

## Contexto
El panel de sistemas se pinta con funciones JS tipo `renderRomSystems` / `loadSystems` /
`openSystem` sobre `#panel-list`. Ya existe CSS `.system-card`, `.system-card-icon`,
`.system-card-info`, `.system-card-actions`, `.badge*`. NO empieces de cero.

## Goal
Que la gestión de sistemas sea clara y visual:
1. Cada sistema muestra: nombre, nº de ROMs, si tiene logo, y aviso de BIOS faltante
   (`has_bios` ya lo devuelve el backend).
2. Búsqueda/filtro rápido por nombre (input que filtra en vivo, sin recargar).
3. Orden estable: por nombre A-Z por defecto; permitir alternar por nº de ROMs.
4. Color de acento ESTABLE por sistema (mismo sistema = mismo color siempre). Si el
   payload trae `hardware`, usarlo; si no, derivar del nombre con un hash determinista
   (helper `cardColor(name)`).
5. Sistema vacío (0 ROMs) visualmente distinguible; sistema con BIOS faltante, aviso visible.

## Steps
1. Localiza la función que pinta los sistemas y el endpoint que la alimenta
   (probablemente `/api/systems` o similar). Anota los campos exactos.
2. Añade el input de filtro + selector de orden en `#panel-list` (encima de la lista).
3. Implementa `cardColor(name)` determinista (hash simple -> paleta de acentos ya existente).
4. Asegura que TODA interacción usa `data-*` + `this.dataset.*` (nunca `onclick="fn('${x}')"`),
   porque los nombres de sistema pueden tener comillas. El escapado HTML de `escHtml`
   NO basta para un literal JS: por eso `data-*`.
5. Mantén el contrato del endpoint.

## Tests
Añade al menos 1 test en `tests/` que cubra `cardColor` es determinista (mismo input ->
mismo output) y distinto para dos nombres distintos, si es viable hacerlo sin DOM.
Si no es viable, documenta por qué y cubre el orden/filtro por otra vía.

## Verification (obligatorio; pega salida)
```
cd C:\Users\folk3\Downloads\batocera_web
python _jscheck.py
node --check _extracted.js
python -m pytest
python -m py_compile app.py
```
Esperado: node OK; pytest **>=37 passed**; py_compile sin salida.

## Report
`C:\Users\folk3\Downloads\batocera_web\.superpowers\sdd\dashboard-redesign\task3-report.md`
Devuelve SOLO: status, commit hash, tests en una línea, dudas.

## Reglas
- NO subagentes. No rompas JS existente. Commit:
  `git add templates/index.html app.py tests && git commit -m "feat(ui): grid de sistemas con filtro, orden y color estable por sistema"`.
