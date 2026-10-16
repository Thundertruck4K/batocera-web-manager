# Task 2 — Report: KPIs de hardware (panel dashboard)

- **Status:** DONE_WITH_CONCERNS
- **Working directory:** `C:\Users\folk3\Downloads\batocera_web`
- **Commit:** `adc4c8605c10f385b963d3185263bb99a4434c16`
  - Mensaje: `feat(ui): KPIs de hardware claros en el panel principal`
  - Cambios: `app.py` (+69/-2), `templates/index.html` (+203/-0), `tests/test_dashboard.py` (+48/-0)
- **Resumen de tests:** `python _jscheck.py` → 1 bloque / 136764 chars; `node --check _extracted.js` → sin salida (exit 0); `python -m pytest` → **37 passed** (32 existentes + 5 nuevos); `python -m py_compile app.py` → sin salida (exit 0).

---

## 1. Objetivo y alcance

Mostrar en el panel principal (`#panel-dashboard`) **6 KPIs de hardware a primera vista**
en una fila de 6 tarjetas `.dash-card`: CPU, GPU, RAM, Disco, Red/IP y EmulationStation.

No se partió de cero: se **añadió** una fila KPI nueva (`#dash-kpis`) reutilizando las clases
existentes (`.dash-grid`, `.dash-card`, `.metric-*`-análogas, `.bar-*`, `.kv-*`, `.temp-*`,
`.status-dot`) y **consumiendo el mismo fetch** que ya existía. Las filas y tarjetas previas
(tacómetros CPU/RAM/GPU, almacenamiento/tanques, ventiladores, noticias, red/procesos) se
**conservan intactas**.

## 2. Contrato real de datos (hallazgo importante)

El brief y el plan hablan de `/api/stats`, pero **esa ruta no existe**. El dashboard ya se
alimenta de **`/api/dashboard`** (`app.py` → `def get_dashboard()` línea 2344; ruta en línea 3325),
cargada por `loadDashboard()` (index.html:3895) → `fetchJson('/api/dashboard')`.

Campos EXACTOS que devuelve `get_dashboard()` (verificados en el código, no inventados):

| Clave | Origen | Campos |
|---|---|---|
| `cpu` | `get_cpu_info` + `get_cpu_usage` + `get_cpu_temp` | `model, cores, usage, temp, temp_src` |
| `gpu` | `get_gpu_info` | `available, name, temp, util, mem_used, mem_total, power, gpus[]` (cada gpu: `name,temp,util,mem_used,mem_total,power,vendor,is_nvidia`) |
| `memory` | `get_memory` | `total_mb, used_mb, free_mb, used_pct, swap_total_mb, swap_used_mb` |
| `disk` | `get_disk` (cache diaria 18:00) | lista de `{fs, mount, size_gb, used_gb, free_gb, pct}` |
| `network` | `get_network` | lista de `{iface, rx, tx, rx_raw, tx_raw}` → **+`ip` (nuevo, ver §4)** |
| `es` | `get_es_status` | `running, pid` → **+`port` (nuevo, ver §4)** |
| extras | — | `batocera_version, uptime, disk_updated, disk_io, battery, processes, fans` |

Se respetó la instrucción **“NO dupliques la carga”**: no se creó ningún `fetch` nuevo ni función
de carga nueva; `renderKpis(d)` se invoca desde `renderDashboard(d)` con el payload ya obtenido.

## 3. Cambios en `templates/index.html`

### 3.1 HTML — fila KPI
Añadida dentro de `#panel-dashboard`, justo tras la cabecera:

```html
<!-- Fila 0: KPIs de hardware — 6 tarjetas a primera vista -->
<div class="dash-grid grid-kpi" id="dash-kpis"></div>
```

### 3.2 CSS — rejilla de 6 columnas
Añadido tras `.dash-grid` (misma especificidad, posterior en origen ⇒ gana; con responsive):

```css
.grid-kpi{grid-template-columns:repeat(6,minmax(0,1fr))}
.kpi-val{font-size:30px;font-weight:700;line-height:1.1;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi-sub{font-size:11px;color:var(--text3);margin-top:3px;min-height:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(max-width:1400px){.grid-kpi{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:820px){.grid-kpi{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.grid-kpi{grid-template-columns:1fr}}
```

### 3.3 JS — `renderKpis(d)` + helpers
Nuevo bloque entre `renderDashboard()` y `renderRow1()`. Patrón de **skeleton estático una sola
vez + actualización por `textContent`** (como `_tachos`), para evitar parpadeo/re-render (alineado
con la Task 7 del plan):

- `kpiSkeleton()` — construye las 6 tarjetas una vez (HTML estático, **sin datos dinámicos**).
- `kpiSet(id, txt)` — pinta valores con **`textContent`**; si el valor es `null`/`undefined`/`''`
  muestra **`--`** (nunca `undefined`).
- `kpiBar(id, pct, color)` — barra `.bar-fill` (0–100%) + color.
- `kpiTempClass(t)` / `kpiTemp(id, t)` — color por umbral **`.temp-ok` (<60), `.temp-warn` (60–79),
  `.temp-hot` (≥80)**; `--` si no hay dato.
- `kpiRamp(pct)` — color verde/ámbar/rojo por tramos 60/80.
- `kpiGb(mb)` — MB→GB legible; `kpiPrimaryDisk(disk)` — partición principal (`/`, si no la mayor).

Contenido de cada tarjeta (según el Goal del brief):

| # | Tarjeta | Métrica principal | Detalle |
|---|---|---|---|
| 1 | ⚙ CPU | `usage%` + barra | Temperatura (color por umbral), fuente Tº, nº núcleos |
| 2 | 🎨 GPU | `util%` + barra | Nombre, Temperatura, VRAM (`mem_used / mem_total`), Potencia; acento N verde/AMD naranja/otro púrpura |
| 3 | 🧠 RAM | `used_pct%` + barra | Usada y Total (GB/MB) |
| 4 | 💾 Disco | `pct%` + barra | Montaje, Usado / Total (GB) |
| 5 | 🌐 Red / IP | IPv4 grande | Interfaz activa, ↓ Recepción, ↑ Envío |
| 6 | 🎮 EmulationStation | Activo/Detenido + dot | PID, Puerto; acento verde/rojo |

La interfaz activa se elige como la primera con `ip` (`net.find(n => n.ip) || net[0]`).

## 4. Cambios en `app.py` (solo datos que faltaban)

Dos KPIs pedidos no tenían dato. Se **añadieron campos a rutas existentes** (compatible hacia
atrás: añadir claves no rompe el contrato JSON; no se crearon endpoints nuevos):

1. **Red/IP** — `get_network()` no devolvía IP. Añadido helper `_ipv4_map()` que hace **una sola**
   llamada `ip -4 -o addr show` y devuelve `{interfaz: IPv4}`; cada iface incluye ahora `"ip"`.
   Si `ip` no existe (p. ej. fuera de Linux) devuelve `{}` y el KPI muestra `--`.
2. **ES/puerto** — `get_es_status()` devolvía `{running, pid}`. Añadido `"port"` vía helper
   `_es_listen_port(pid)`, que **sin subprocesos** lee `/proc/net/tcp{,6}` (estado `0A` = LISTEN,
   mapa inode→puerto) y resuelve el inode por `/proc/<pid>/fd/*` (`socket:[inode]`). Devuelve
   `None` si no hay listener/sin permisos/sin `/proc`; el KPI muestra `--`.
   Se implementó sin `_run` **a propósito**: el test existente `test_es_status_uses_full_cmdline_pattern`
   asume que `get_es_status()` sólo invoca `_run` una vez (rastrea el último comando); añadir
   subprocesos rompería ese test.

## 5. Tests añadidos (`tests/test_dashboard.py`, +5)

- `test_es_status_includes_port_key` — `get_es_status()` expone `port`.
- `test_es_status_not_running_has_port_none` — detenido ⇒ `port is None`.
- `test_es_listen_port_tolerates_bad_pid` — pid `None`/`""`/no numérico ⇒ `None` (sin excepción).
- `test_ipv4_map_parses_ip_output` — parseo de `ip -4 -o addr show` sin máscara.
- `test_ipv4_map_empty_without_ip_command` — sin `ip` ⇒ `{}`.

**Nota:** el brief permitía “32 passed (o más si añades tests)”. Se añadieron tests porque las
funciones nuevas leen `/proc`/`ip` y conviene blindarlas; el resultado es **37 passed**. Por eso
el commit incluye además `tests/test_dashboard.py` (el brief sugería `git add templates/index.html app.py`;
se añadió el test file por coherencia — ver Dudas).

## 6. Verificación (obligatoria)

```
PS C:\Users\folk3\Downloads\batocera_web> python _jscheck.py
bloques <script>: 1 | caracteres: 136764

PS C:\Users\folk3\Downloads\batocera_web> node --check _extracted.js
(node exit = 0, sin salida)

PS C:\Users\folk3\Downloads\batocera_web> python -m pytest
.....................................                                    [100%]
37 passed in 0.18s

PS C:\Users\folk3\Downloads\batocera_web> python -m py_compile app.py
(py_compile exit = 0, sin salida)
```

Extra (no exigido por el brief, pero aplicado):

- `python -m ruff check app.py tests/test_dashboard.py --select F,E9` → **All checks passed!**
- **Runtime check del JS de KPIs** con un DOM mínimo simulado en Node
  (`_kpicheck`): con payload completo pinta `42%`, `55°C` (temp-ok), `81°C` (temp-hot),
  `2048 MB / 4096 MB`, `4.0 GB`, `192.168.1.5`, `Activo`, `1234`; con payload vacío todos los
  valores quedan en `--`/`0%`/`Detenido` **sin `undefined` ni `NaN`**. Resultado: `KPI CHECK: OK`.
  (El `node --check` sólo valida sintaxis; esto valida comportamiento.)

## 7. Decisiones y notas

- **Endpoint real `/api/dashboard`**, no `/api/stats` (el brief/plan citan la ruta equivocada).
  No se tocó el contrato: sólo se añadieron las claves `network[].ip` y `es.port`.
- Se **conservan** los gauges/tacómetros y barras existentes (Fila 2 CPU/RAM/GPU, tanques de
  almacenamiento, braille de red) tal pide el brief.
- Skeleton KPI estático + `textContent` para valores: sin reescritura de `innerHTML` en cada poll
  de 5 s; los valores numéricos nunca se interpolan en HTML.
- Toda entrada dinámica de HTML sigue pasando por `escHtml`; en las tarjetas KPI **no hay** HTML
  dinámico (todo `.textContent`), por lo que no aplica.

## 8. Dudas / concerns

1. **“Puerto” de EmulationStation**: no existe en el repo ningún concepto de puerto de ES. Se
   interpretó como *el puerto TCP en LISTEN del proceso ES* (best-effort vía `/proc`). En instalaciones
   donde ES no abre ningún socket, el KPI mostrará `--`. Si el brief se refería a otro puerto
   (p. ej. el del propio servidor web, ya mostrado en la vista de Servicios con `get_process_status`),
   avísame y lo cambio. → motivo del status `DONE_WITH_CONCERNS`.
2. **IP por interfaz**: `_ipv4_map()` usa `ip` (iproute2). Si Batocera no lo trae, el KPI Red/IP
   mostrará `--` (sin fallback a `hostname -I`, que no mapea interfaz↔IP). Se puede añadir un
   fallback si se confirma que hay equipos sin `ip`.
3. **Commit con tests**: el brief daba `git add templates/index.html app.py`, pero también permitía
   añadir tests; se incluyó `tests/test_dashboard.py` en el mismo commit. Si se prefiere el commit
   literal sin tests, se puede separar.
4. Fila 1 sigue mostrando un resumen de ES (estado + uptime) que ahora se solapa con la tarjeta KPI
   de ES. Se dejó así para no eliminar información existente; se puede simplificar si se desea.
