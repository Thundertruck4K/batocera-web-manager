# Task 2: KPIs de hardware (panel dashboard)

Working directory: **C:\Users\folk3\Downloads\batocera_web** (usa rutas absolutas / workdir).

## Files
- Modify: `C:\Users\folk3\Downloads\batocera_web\templates\index.html`
- Modify (solo si falta algún dato): `C:\Users\folk3\Downloads\batocera_web\app.py`

## Contexto
El panel `#panel-dashboard` (aprox. línea 622 de templates/index.html) ya existe y hay CSS
`.dash-card`, `.dash-grid`, `.metric-big`, `.metric-sub`, `.gauge-*`, `.bar-*`, `.net-iface`,
`.disk-item`, `.temp-ok/.temp-warn/.temp-hot`. NO empieces de cero: inspecciona primero
qué pinta hoy el JS del dashboard (busca funciones tipo `renderDashboard`, `loadStats`,
`/api/stats`) y mejóralo.

## Goal
Que el panel principal muestre a primera vista 6 KPIs claros y agradables:
CPU (uso + temperatura), GPU (uso + temp + VRAM), RAM (usado/total + %), Disco (usado/total),
Red/IP (interfaz activa + IP), y Estado EmulationStation (activo/puerto).

## Steps
1. Localiza en `app.py` el handler de `/api/stats` y anota los campos EXACTOS que devuelve
   (cpu, gpu, memory, disk, network, es, fans...). Si algún KPI pedido no tiene dato,
   NO inventes endpoints nuevos salvo que sea imprescindible; usa lo disponible.
2. En `templates/index.html`, asegura que `#panel-dashboard` tenga una fila `.dash-grid` con
   6 tarjetas `.dash-card` (una por KPI). Conserva/mejora los gauges/barras existentes.
3. Implementa/ajusta la función de render del dashboard para rellenar esas tarjetas.
   - Usa `textContent` para valores (números) cuando sea posible.
   - Colores de temperatura: `.temp-ok` (<60), `.temp-warn` (60-79), `.temp-hot` (>=80).
   - Si el dato no existe, muestra `--` (no rompas con `undefined`).
4. No dupliques la carga de `/api/stats`: si ya hay una función que lo llama, reutilízala.
5. No cambies el contrato JSON de las rutas existentes.

## Verification (obligatorio; pega la salida en el report)
```
cd C:\Users\folk3\Downloads\batocera_web
python _jscheck.py
node --check _extracted.js
python -m pytest
python -m py_compile app.py
```
Esperado: `node --check` sin errores; `pytest` → **32 passed** (o más si añades tests);
`py_compile` sin salida.

## Report
Escribe el reporte en `C:\Users\folk3\Downloads\batocera_web\.superpowers\sdd\dashboard-redesign\task2-report.md`
y devuelve SOLO: status (DONE/DONE_WITH_CONCERNS/NEEDS_CONTEXT/BLOCKED), commit hash,
resumen de tests en una línea, y dudas.

## Reglas
- NO lances subagentes.
- Toda entrada dinámica en HTML pasa por `escHtml`.
- Commit: `git add templates/index.html app.py && git commit -m "feat(ui): KPIs de hardware claros en el panel principal"`.
