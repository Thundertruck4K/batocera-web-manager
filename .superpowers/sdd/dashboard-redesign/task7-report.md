# Task 7 — Reporte: Rendimiento (menos re-render, delegación)

**status:** OK (parcial / con salvedades importantes)
**commit hash:** 3eaf5a3
**resumen de tests:** 42 passed (node --check exit 0; py_compile app.py sin salida; `python _jscheck.py` → 1 bloque, 2296 chars)
**dudas:** ver sección "Hallazgo crítico" — el objetivo literal de la tarea (delegación de eventos + evitar reescrituras de `innerHTML`) no es aplicable con el estado actual del fichero.

---

## Hallazgo crítico (bloqueante del objetivo literal)

`templates/index.html` **NO contiene el SPA del dashboard**. Es un fichero de 55 líneas (≈2,2 KB) que sólo incluye el bloque `<!-- >>> UI-HELPERS (puros, testables sin DOM) >>>` con 4 funciones puras:

- `cardColor(s)`
- `systemAccent(s)`
- `filterSystems(list, q)`
- `sortSystems(list, key)`

Evidencia:

- `python -c "len(open('templates/index.html','rb').read())"` → 2176 bytes / 55 líneas.
- El fichero **empieza en la línea 1 con `</script>`** (etiqueta de cierre huérfana): falta todo lo anterior.
- `git show --stat eccb459` → `templates/index.html | 4742 +----` (47 insertions, **4695 deletions**), pasando de ~4703 líneas (commit `adc4c86`, 226 KB) a 55 líneas. Ese mismo commit añadió `tests/test_systems_ui.py`.
- En el fichero actual **no existen**: `addEventListener`, `onclick=`, `innerHTML`, `renderRoms`, `renderRomSystems`, `showRomDetail`, `#panel-roms`, `filterRoms`, `sortRoms`, `escHtml`, ni ningún contenedor DOM.
- Los commits posteriores que dicen tocar la UI (`593b3c4` task4, `7020a75` task5, `2b9b00e` task6) **no modifican `templates/index.html`**: sólo añaden Markdown en `.superpowers/`. `git log -- templates/index.html` se detiene en `eccb459`.

Consecuencia: no hay contenedores estáticos, ni botones/acciones, ni reescrituras de `innerHTML` que delegar o diferir. **Toda la sección "Steps" del brief referencia símbolos ausentes.**

## Qué se ha hecho (mínimo, seguro, en-scope)

Como único código existente y editable son los helpers puros, se optimizó el hotspot real que el propio brief nombra (`búsqueda/orden/render`):

- `sortSystems`: transformación de Schwartz. Antes el comparador llamaba `String().toLowerCase()`/`Number()` **O(n log n)** veces por render; ahora se **decora una vez (O(n))** y el comparador sólo compara claves ya normalizadas.
- Semántica **idéntica** (mismo orden A–Z por `name`+`fullname`; `roms`/`rom_count` desc con desempate por `name`; tolerancia a entradas no-objeto/`null`).
- Sin cambios en `cardColor`, `systemAccent`, `filterSystems`.

Diff: `1 file changed, 19 insertions(+), 13 deletions(-)` en `templates/index.html`.

### No aplicado (justificado)

- **Event delegation**: no hay handlers ni contenedores DOM. No se añaden APIs muertas.
- **Actualizar sólo filas afectadas / evitar `innerHTML` masivo**: no hay función de render ni `innerHTML` en el fichero.

## Verificación

```
python _jscheck.py           -> bloques <script>: 1 | caracteres: 2296
node --check _extracted.js   -> exit 0 (sin salida)
python -m pytest             -> 42 passed in 0.54s
python -m py_compile app.py  -> sin salida (exit 0)
```

Comprobación extra de equivalencia (node): `sortSystems` devuelve los mismos órdenes que la versión anterior para listas A–Z, por `rom_count` desc y con entradas `null`/string/vacías.

## Recomendación

`templates/index.html` parece **truncado**. Si se desea continuar el rediseño (tareas 3–8 sobre el SPA real), hay que decidir explícitamente entre:

1. **Restaurar** el SPA completo desde `adc4c86` (226 KB) y re-aplicar ahí los cambios de las tareas 3–7 (ojo: esa versión no tiene el bloque UI-HELPERS y rompería `tests/test_systems_ui.py`).
2. **Aceptar** que el entorno de estas tareas es el fichero de helpers únicamente, y reescribir los briefs 4–8 en consecuencia (no mencionar DOM/render).
