# Diseño: Enmascarar la Web API Key de RA + modo claro/oscuro del manager

**Fecha:** 2026-10-25
**Autor:** sesión de trabajo (asistida) — el usuario delegó el diseño y lo aprobó explícitamente
**Estado:** aprobado para implementación (respuesta: `key-only` + `theme` + `approve`)

---

## 1. Contexto

Dos ramas de trabajo independientes sobre `batocera_web` v1.4 (backend stdlib puro en
`app.py`, SPA de un solo fichero en `templates/index.html`).

**Rama A — credencial expuesta.** El gestor guarda la Web API Key de RetroAchievements en
`batocera_manager_settings.json` y la sirve **en claro** por `GET /api/settings`
(`app.py`: el handler devuelve el dict de ajustes tal cual). Como el servidor no tiene
autenticación, cualquiera en la LAN puede leer `/api/settings` y quedarse con la key. La key
es revocable desde `retroachievements.org/settings`, pero el README y el propio panel
prometen que "se guarda solo en este equipo", y hoy eso no es cierto.

**Rama B — tema claro.** La UI usa la paleta "Aurora Glass" oscura declarada en `:root`
(`templates/index.html`). El Roadmap del README incluye "Modo claro/oscuro y temas para la
propia web". La web del manager se usa a menudo desde el móvil con la tele apagada o con
luz ambiente fuerte: un tema claro es una mejora real de legibilidad.

## 2. Objetivo

Cerrar la exposición de la credencial sin romper el flujo de configuración, y añadir un
tema claro usable que contraste con WCAG AA, sin parpadeo al cargar y sin duplicar la
paleta en dos sitios.

## 3. Requisitos (del usuario)

- **Rama A — solo enmascarar la key.** El usuario eligió explícitamente `key-only`:
  ocultar la Web API Key de RetroAchievements. **No** se añade autenticación a la API.
- **Rama B — modo claro/oscuro y temas para la web del manager.** El usuario eligió `theme`.
- El usuario aprobó el alcance y autorizó a escribir spec + plan e implementar.

## 4. No-objetivos y anti-objetivos

- **No** añadir autenticación, usuarios, contraseñas, sesiones ni HTTPS. La rama A es
  exclusivamente sobre *cómo se sirve* la credencial ya existente.
- **No** mover la key a otro fichero ni cifrarla en reposo. Se descarta explícitamente la
  alternativa "conf-only" del cuestionario: no aporta nada frente a "no servirla", ya que
  el fichero de ajustes sigue siendo legible para quien tenga acceso al disco.
- **No** rediseñar la UI. Solo se añade un conmutador de tema y su paleta.
- **No** tocar la paleta oscura. El tema actual es el predeterminado y debe quedar
  **pixel-idéntico** a como está hoy.

## 5. Restricciones

- Cero dependencias: solo stdlib de Python 3 y CSS/JS inline.
- Un solo fichero de frontend: todo el CSS/JS va en `templates/index.html`.
- El servidor se renderiza con sustitución de cadenas `{{variable}}` (`render_index()`).
- Convenciones del repo: comentarios en español, identificadores de UI conservados (los
  tests extraen helpers por regex), `pytest` sin linting ni typechecking.
- `tests/test_theme_contrast.py` ya verifica contraste WCAG AA de `--text2`/`--text3`
  sobre `--bg`/`--panel` leyendo el bloque `:root`.

## 6. Enfoques considerados

### 6.1 Rama A — cómo servir la key

| Enfoque | Qué trade-off |
|---|---|
| **A. Enmascarar en la respuesta + write-only en la escritura** ✅ elegido | La key nunca sale en claro por la API. El campo de la UI muestra una máscara y "Guardar" sin tocarlo no pisa la key real. No toca el resto de la API. |
| B. Autenticación básica opcional | Cierra de raíz la exposición de *toda* la API, pero obliga a designing de sesión, token, flujo de login y a decidir qué pasa con el modo anónimo. El usuario lo descartó en el cuestionario. |
| C. Guardar la key en un fichero aparte | Evita que viaje en el JSON de ajustes, pero quien pueda leer el disco lo lee igual. No aporta frente a A. |

### 6.2 Rama B — dónde persiste la elección de tema

| Enfoque | Qué trade-off |
|---|---|
| **A. Servidor como fuente de verdad, valor inyectado en el HTML** ✅ elegido | `render_index()` ya lee los ajustes en cada petición: basta inyectar `data-theme` en `<html>`. Sin parpadeo, y la preferencia sigue al usuario entre móvil y PC. |
| B. `localStorage` en el navegador | Cero cambios de backend, pero la preferencia es por dispositivo: si la pones en el móvil no se aplica en el PC. En un gestor al que se entra desde varios dispositivos, molesta. |
| C. Server + `localStorage` como caché | El mejor de los dos, pero añade un segundo estado que puede divergir del servidor. Sobredimensionado para lo que se pide. |

**Decisión de sub-detalle: "Sistema" (auto).** La opción *Sistema* no se resuelve con CSS
(`prefers-color-scheme` duplicaría la paleta). Se resuelve en JS: el script inline del
`<head>` lee el atributo `data-theme="auto"` y lo sustituye por `light`/`dark` según
`matchMedia('(prefers-color-scheme: light)')`, quedándose escuchando los cambios. Así la
paleta clara existe **una sola vez** en el CSS.

## 7. Diseño — Rama A: enmascarar la Web API Key

### 7.1 Backend (`app.py`)

Dos helpers nuevos, a nivel de módulo (testeables sin levantar el servidor):

- `mask_ra_api_key(key: str) -> str` — devuelve una máscara legible
  (`"abcd••••••••wxyz"`) para keys de 12+ caracteres; para claves más cortas devuelve
  `"••••••••"`. Cadena vacía → cadena vacía.
- `public_settings(settings: dict) -> dict` — devuelve una **copia** de los ajustes con
  `ra_api_key` sustituido por la máscara y un booleano nuevo `ra_api_key_set` que indica
  si hay key guardada.

`GET /api/settings` pasa a devolver `public_settings(s)` en lugar de `s`. Ningún otro
endpoint expone la key: `/api/retroachievements` y `/api/retroachievements/test` devuelven
`configured`/`ok`/`user`, nunca la credencial.

`POST /api/settings` mantiene la semántica *write-only* para `ra_api_key`:

| Valor enviado | Efecto |
|---|---|
| La clave no aparece en el payload | Se conserva la key guardada |
| La máscara que devolvió el GET (p. ej. `"abcd••••••••wxyz"`) | Se conserva la key guardada |
| Cadena vacía | **Borra** la key guardada |
| Cualquier otro valor | Sustituye la key guardada |

El caso "vacía = borra" es deliberado: es la única forma de quitar una key sin añadir un
botón extra. La UI lo explica con un hint explícito.

### 7.2 Frontend (`templates/index.html`)

- `loadRASettings()` deja de rellenar el input con la key real: ahora pinta la máscara.
- Se añade un hint bajo el campo que indica si hay key configurada y que vaciarlo la borra.
- `saveRASettings()` no cambia: sigue enviando el valor del campo. Es el backend quien
  decide, y así el frontend no duplica la lógica de escritura.
- `toggleRAKey()` (el botón 👁) se mantiene: alterna `password`/`text` sobre la máscara.

## 8. Diseño — Rama B: modo claro/oscuro

### 8.1 Paleta

`--bg/--bg2/--bg3/--panel/--text/--text2/--text3/--accent/--border/--green/--yellow/
--red/--purple` + derivadas. El bloque oscuro de `:root` **no se toca**. Se añade un
bloque `:root[data-theme="light"]` con la paleta clara.

Paleta clara (contraste WCAG AA verificado ≥ 4.5:1 en todas las combinaciones):

| Variable | Claro | Ratio principal |
|---|---|---|
| `--bg` | `#F4F6FB` | — |
| `--bg2` | `#FFFFFF` | — |
| `--bg3` | `#EDF1F8` | — |
| `--panel` | `#FFFFFF` | — |
| `--text` | `#141824` | 16.38 sobre `--bg` |
| `--text2` | `#454E63` | 7.70 sobre `--bg` |
| `--text3` | `#5B6478` | 5.49 sobre `--bg` |
| `--accent` | `#3B5BDB` | 5.24 sobre `--bg` |
| `--green` | `#14804A` | — |
| `--yellow` | `#8A5D00` | — |
| `--red` | `#C92A2A` | — |
| `--purple` | `#5F3DC4` | — |
| `--border` | `#D8DEEA` | — |

### 8.2 Variables "glass" dependientes del tema

El CSS tiene 28 usos de `rgba(255,255,255,…)` que asumen fondo oscuro (superficies
"glass", hover de nav, chips, spinner, rejilla del gráfico de red). Con el tema claro,
esas superficies quedarían invisibles o con texto blanco sobre blanco.

Se sustituyen por variables semánticas definidas en `:root` y sobreescritas en el bloque
claro:

| Variable | Oscuro | Claro |
|---|---|---|
| `--glass` / `--glass2` | `rgba(255,255,255,.06)` / `.02` | `rgba(20,24,36,.035)` / `.012` |
| `--glass-soft` / `--glass2-soft` | `rgba(255,255,255,.04)` / `.015` | `rgba(20,24,36,.025)` / `.008` |
| `--hover-bg` | `rgba(255,255,255,.055)` | `rgba(20,24,36,.045)` |
| `--active-bg` / `--active-fg` | `rgba(255,255,255,.085)` / `#fff` | `rgba(20,24,36,.07)` / `var(--text)` |
| `--chip-hover-bg` / `--chip-hover-fg` | `rgba(255,255,255,.13)` / `#fff` | `rgba(20,24,36,.08)` / `var(--text)` |
| `--badge-bg` / `--badge-fg` | `rgba(255,255,255,.2)` / `#fff` | `rgba(20,24,36,.14)` / `var(--text)` |
| `--spinner-track` / `--spinner-top` | `rgba(255,255,255,.2)` / `#fff` | `rgba(20,24,36,.15)` / `#3B5BDB` |
| `--grid-line` | `rgba(255,255,255,.025)` | `rgba(20,24,36,.05)` |
| `--on-accent` | `#fff` | `#fff` |
| `--on-photo` | `#fff` | `#fff` |
| `--fx-dot` / `--fx-spark` | `rgba(255,255,255,.28)` / `.45` | `rgba(20,24,36,.16)` / `.26` |

**También pasan por variable:** `.fx__bubble` / `.fx__spark` (`--fx-dot` / `--fx-spark`)
y el texto de `.dash-random-ph span` (`--on-photo`). Los tres viven sobre fondos
propios, pero la capa aurora se apoya en `var(--bg)`, que en el tema claro sí es
claro: sus velos blancos se habrían desvanecido. El degradado de la portada
genérica (`radial-gradient(...,#1b1530,#141021 55%,#171018)`) sí es siempre oscuro,
por eso `--on-photo` vale `#fff` en los dos temas.

### 8.3 Mecánica

1. `<html lang="es" data-theme="{{ui_theme}}">` — `render_index()` inyecta el valor
   guardado. **Cero parpadeo**: el tema correcto está en el primer byte del HTML.
2. Script inline en `<head>` (antes de que se pinte el body): si `data-theme="auto"`, lo
   resuelve a `light`/`dark` con `matchMedia` y se queda escuchando los cambios del sistema.
3. Botón conmutador en la cabecera del sidebar (visible en todos los paneles): alterna
   claro/oscuro al instante, guarda en el backend y actualiza el icono.
4. Selector de 3 opciones en *Configuración* (Claro / Oscuro / Sistema) que escribe
   `ui_theme` en los ajustes.

### 8.4 Persistencia

`ui_theme` es una clave nueva de `DEFAULT_SETTINGS` (por defecto `"dark"`). El backend
acepta `"dark"`, `"light"` y `"auto"`; cualquier otro valor se normaliza a `"dark"`.

## 9. Verificación

- Tests nuevos en `tests/test_ra_key_mask.py` (rama A) y `tests/test_ui_theme.py` (rama B).
- Se amplía `tests/test_theme_contrast.py` para comprobar el contraste AA **de la paleta
  clara** (hoy solo mira `:root`).
- La suite completa (336 tests) debe seguir en verde.

## 10. Decisiones tomadas por el implementador (llamadas propias)

1. **Máscara con los primeros y últimos 4 caracteres** (`abcd••••••••wxyz`) en vez de
   puntos fijos: permite al usuario reconocer si está mirando su key sin revelarla.
2. **"Vaciar = borrar"** en vez de un botón "Borrar key": menos UI, y la clave del
   write-only sigue siendo inequívoca porque la máscara nunca es una cadena vacía.
3. **`ui_theme` se persiste en el backend, no en `localStorage`**: una preferencia de
   interfaz que se pierde al cambiar de dispositivo es una preferencia rota.
4. **`auto` se resuelve en JS, no con `@media (prefers-color-scheme)`**: evita duplicar
   la paleta clara en dos sitios, que es exactamente donde dos temas se desincronizan.
5. **El conmutador del sidebar alterna claro/oscuro, no auto**: el auto solo se elige en
   Configuración, donde tiene sentido como preferencia permanente.

## 11. Lo que queda al implementador

Nada que requiera decisión del usuario: los nombres de variables, los identificadores de
UI y el texto de los hints están fijados arriba. El implementador elige la redacción
exacta de los textos visibles y el orden de las tareas.
