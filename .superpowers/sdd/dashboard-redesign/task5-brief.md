# Task 5: Scraper/Batch y BIOS UI (skip persistente, faltantes/presentes claros)

Working directory: **C:\Users\folk3\Downloads\batocera_web** (rutas absolutas / workdir).

## Files
- Modify: `C:\Users\folk3\Downloads\batocera_web\templates\index.html`
- Modify (solo si necesario): `C:\Users\folk3\Downloads\batocera_web\app.py`

## Contexto
Paneles existentes: `#panel-biosmissing` (tabla BIOS), y panel de Scraper/Batch. Ya hay
funciones para cargar BIOS faltantes, y el API `/api/bios/missing/skip` existe (POST).
Hay frontend ya parcheado antes (usa `window._batchErrorsText`, `data-*`, etc). Mejora UX.

## Goal
- BIOS: tabla clara (Sistema | Archivo | MD5 | Estado | Acción). Mostrar faltantes vs
  presentes. Botón "Ignorar" (POST `/api/bios/missing/skip`) que refresca la tabla.
  Mostrar el estado "skip" si aplica.
- Scraper/Batch: panel con selector de scraper, botón "Iniciar batch", barra/progreso,
  contadores OK/fallos, y listado de errores vía `window._batchErrorsText`.
- Usa `data-*` + delegación. No romper endpoints existentes.

## Steps
1. Inspecciona `#panel-biosmissing` y las funciones JS que lo cargan/refrescan.
2. Ajusta la tabla para diferenciar "Falta" vs "OK" (estilos), MD5 visible, botón Ignorar
   solo cuando falta.
3. Inspecciona panel de batch: `batchStatus`, `batchErrors`, `_batchErrorsText`.
4. Haz mínimas mejoras visuales coherentes con el tema nuevo, sin reescribir toda la UI.
5. Verifica llamadas no rompan (fetch con method POST correcto).

## Verification (obligatorio)
```
cd C:\Users\folk3\Downloads\batocera_web
python _jscheck.py
node --check _extracted.js
python -m pytest
python -m py_compile app.py
```
Esperado: node OK; pytest **>=42 passed**; py_compile sin salida.

## Report
`C:\Users\folk3\Downloads\batocera_web\.superpowers\sdd\dashboard-redesign\task5-report.md`
Devuelve SOLO: status, commit hash, tests en una línea, dudas.

## Reglas
- NO subagentes. Commits mínimos:
  `git add templates/index.html app.py && git commit -m "feat(ui): mejoras en panel BIOS (faltantes/presentes, skip persistente)"`
  `git add templates/index.html && git commit -m "feat(ui): mejoras en panel Scraper/Batch"`
  (si ambos cambian, puede ir en un commit; pero mejor atómico si claro). Si va todo junto:
  `git add templates/index.html app.py && git commit -m "feat(ui): BIOS y Scraper/Batch UX coherente con nuevo tema"`
