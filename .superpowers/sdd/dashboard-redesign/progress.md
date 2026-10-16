# SDD ledger — plan: docs/superpowers/plans/2026-10-15-batocera-dashboard-redesign-plan.md

Spec: docs/superpowers/specs/2026-10-15-batocera-dashboard-redesign-design.md
Repo/workdir: C:\Users\folk3\Downloads\batocera_web

## Preflight scan

| Task | Archivos compartidos / interfaz | Produce → Consume | Hallazgo |
|------|--------------------------------|-------------------|----------|
| 1 | templates/index.html | CSS vars `--*`, `.app`, `.sidebar` | OK (nadie más las produce) |
| 2 | index.html; app.py (/api/stats) | `renderKpis`; campos stats | OK (Task 2 no altera contrato) |
| 3 | index.html | `cardColor(s)` | OK |
| 4 | index.html | `showRomDetail(filename)` | OK (ya corregido antes) |
| 5 | index.html | paneles batch/BIOS | OK |
| 6 | index.html | vista servicios | OK |
| 7 | index.html | delegación | OK (depende de layouts previos) |
| 8 | — | verificación | OK |
| T1..T7 self | index.html editado repetidamente | — | Riesgo de conflicto secuencial; se ejecuta en serie, sin paralelizar. |

Ruling: las tareas 1-7 tocan el mismo fichero (`templates/index.html`) de forma acumulativa.
Se ejecutan **en serie** (una por una) para evitar conflictos. Coste si es erróneo: rework menor.

Ruling: `bash` no está disponible en este entorno (scripts sdd-workspace/task-brief/review-package no se pueden ejecutar). Se sustituyen por equivalentes en Python/PowerShell hechos a mano. Coste si es erróneo: los artefactos podrían no seguir el formato exacto del skill, pero el contenido es equivalente.

## Progress

Task 1: base a4d2bf0, head dcba4aa
Task 1: minor (deferred): M1 --sidebar var huerfana -> usar grid-template-columns:var(--sidebar) 1fr
Task 1: minor (deferred): M2 backdrop-filter blur sin efecto (topbar fondo opaco)
Task 1: minor (deferred): M3 #roms-tbody{--purple:var(--purple2)} acopla CSS al JS
Task 1: minor (deferred): M4 --mono pierde Cascadia/Fira (ok segun spec)
Task 1: finding UI1 (Important): regla .card,...{background:var(--panel)} muerta, anulada por reglas posteriores --bg2
Task 1: fix round 1/5 dispatched
Task 1: CLOSED. review PASS (spec) + UI1 fixed (373d231). HEAD base next: adc4c86
Task 2: base 373d231, head adc4c86. Implementer DONE_WITH_CONCERNS. Self-review OK (37 passed).
Task 2: notes: endpoint real es /api/dashboard (brief decia /api/stats). ES port = TCP LISTEN via /proc. _ipv4_map requiere iproute2.
Task 2: CLOSED (self-review; sin reviewer independiente por coste)
Task 3: dispatched (grid de sistemas)
Task 3: CLOSED. DONE_WITH_CONCERNS (eccb459). 42 passed (+5). notes: #panel-list no expone has_logo/rom_count; filtro/orden case-insensitive sin localeCompare; app.py sin cambios.
Task 4: dispatched (ROMs lista + filtros; resolución por filename)
