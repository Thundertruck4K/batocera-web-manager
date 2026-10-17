# Diseño: Restyle «Aurora Glass» del gestor completo

**Fecha:** 2026-10-16
**Autor:** sesión de rediseño (asistida) — el usuario eligió la propuesta **A** entre tres maquetas
**Estado:** aprobado e implementado (restyle completado; 231 tests verdes)

---

## 1. Contexto

El gestor (`app.py` + `templates/index.html`, Python stdlib, sin dependencias, 5464 líneas)
usa hoy un tema oscuro funcional pero plano: tokens en `:root` (línea 10), CSS principal en
el bloque `<style>` de las líneas 8-668, un segundo bloque minúsculo (1819-1821, `shimmer`),
y el JS con el bloque marcado `<!-- >>> UI-HELPERS` (1864-1997).

El usuario pidió un rediseño gráfico del sitio. Se le presentaron **tres maquetas navegables**
(pestaña del compañero visual) con el contenido real del dashboard y eligió la **A · Aurora
Glass**, con alcance **todo el sitio**: los 6 paneles, los modales y las tablas.

Maqueta de referencia (no versionada): `.superpowers/brainstorm/design1/content/propuestas-1.html`.

## 2. Objetivo

Que todo el gestor se sienta como un panel premium: fondo con aurora sutil, superficies de
cristal, tipografía Inter/JetBrains Mono, sombras profundas y tarjetas que se materializan al
entrar — **sin perder densidad de información, legibilidad ni fluidez** en la tele del Batocera.

## 3. Requisitos (del usuario)

- Fuentes tipo macOS/retina y JetBrains; efectos, sombras y colores nuevos (paleta propuesta).
- Tarjetas que «aparecen de la nada» (materialización); burbujas y chispas.
- Aplicado a **todo el sitio**, modales y tablas incluidos.
- (vigentes) Sin dependencias nuevas; commits atómicos; no romper lo que ya funciona.

## 4. No-objetivos y anti-objetivos

**No-objetivos (fuera de alcance):**
- Cambiar estructura, IDs, clases o lógica JS de los paneles. (Sí se ajustan los **literales de
  color** en estilos en línea y en cadenas de JS: ver §7.8.)
- Selector de tema / modo claro del sitio.
- Rediseñar el landing (se conserva; solo hereda tokens y aparece con el nuevo fondo).
- Tocar `app.py`, endpoints o datos.

**Anti-objetivos (sería un fracaso aunque técnicamente funcione):**
- Romper cualquiera de los 231 tests.
- Texto por debajo de contraste AA.
- Tirones por `backdrop-filter` o partículas en el navegador de la tele.
- Que el aspecto dependa de tener internet.

## 5. Restricciones y contrato del harness de tests

Estas cadenas/estructuras **no se tocan** (varios tests las leen por regex):

- Marcadores `<!-- >>> UI-HELPERS` … `<!-- <<< UI-HELPERS` intactos.
- `function showPanel(name, btn)` conserva `.nav-item`, `remove('active')`, `add('active')`;
  su cuerpo no debe contener `'biosmissing'` ni `'preview'`.
- Regla `.nav-item.active { … }` cuyo cuerpo contenga `gradient` y `border`.
- Regla `.nav-item.active svg { … }` cuyo cuerpo contenga `var(--accent)` y `stroke`.
  **Ojo:** el regex casa hasta el primer `}`, así que el cuerpo no puede anidar llaves.
- `<aside class="sidebar">` con `<nav class="nav">`: 6 `.nav-item`, ≥6 `<svg>`, sin emojis en
  el nav, 5 secciones (Estado, Contenido, Sistemas, Personalización, Ajustes) y los badges
  `badge-count` / `badge-biosmissing`.
- `--text2` y `--text3` con ratio ≥ 4.5 sobre `--bg` y `--panel` (`test_theme_contrast`).
  Valores propuestos: `--text2:#98A2C0` (7.77 vs `#07080D`, 7.12 vs `#101423`) y
  `--text3:#8B93AD` (6.54 y 5.99). El propio test es la puerta final.
- Los nombres de los tokens `:root` **no se renombran**.

## 6. Lo que decidió el usuario

La propuesta **A · Aurora Glass**: paleta, fuentes, cristal, aurora, burbujas, chispas y
materialización. Nada más se le preguntó; el resto son decisiones de quien escribe (sección 8).

## 7. Enfoque técnico

### 7.1 Tokens (`:root`) — tabla de sustitución

| token | actual | nuevo |
|---|---|---|
| `--bg` | `#0f1116` | `#07080D` |
| `--bg2` | `#161923` | `#0B0E15` |
| `--bg3` | `#20263a` | `#151A28` |
| `--bg4` | `#2a3150` | `#1E2436` |
| `--panel` | `#1d2133` | `#101423` |
| `--text` | `#e6e9ef` | `#E9ECF5` |
| `--text2` | `#9aa0c0` | `#98A2C0` |
| `--text3` | `#868fb2` | `#8B93AD` |
| `--accent` | `#6ea8fe` | `#7C9CFF` |
| `--accent2` | `#4a76d4` | `#4A5BD4` |
| `--border` | `#2b314d` | `rgba(255,255,255,.10)` |
| `--border2` | `#3a4166` | `rgba(255,255,255,.18)` |
| `--green` | `#3fb950` | `#3FD68B` |
| `--yellow` | `#d29922` | `#F2C46B` |
| `--red` | `#f85149` | `#FF6B6B` |
| `--purple` | `#6b3fa0` | `#7A5BD4` |
| `--purple2` | `#b18cf0` | `#A98BFF` |
| `--orange` | `#e08b4c` | `#FFA76B` |
| `--radius` | `8px` | `12px` |
| `--radius2` | `12px` | `20px` |
| `--shadow` | `0 8px 32px rgba(0,0,0,.45)` | `0 22px 60px -26px rgba(0,0,0,.9), inset 0 1px 0 rgba(255,255,255,.06)` |
| `--font` | `'Segoe UI',system-ui,…` | `'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif` |
| `--mono` | `ui-monospace,…` | `'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace` |

**Token nuevo:** `--aurora:#22D3EE` — el cian de la propuesta, usado **solo en degradados
decorativos** (blobs, cifras del hero, barras de acento, sparkline). No se usa como fondo de
botón con texto blanco.

### 7.2 Capa de fondo (aurora + grano)

Un único `<div class="fx" aria-hidden="true">` insertado como primer hijo de `.app` (o de
`body`), con `position:fixed; inset:0; z-index:0; pointer-events:none`:

- 3 «blobs» (`border-radius:50%`, `filter:blur(95px)`, opacidad .34–.5) con degradados
  radiales `--accent`, `--aurora` y `#FB7185`, animados con `transform` (barato) en bucle
  alterno de ~26 s.
- Una capa de grano fino (data-URI SVG `feTurbulence`) a baja opacidad.

El contenido (`.app`) sube a `position:relative; z-index:1`. Los blobs quedan **detrás** de
todo, así que se ven sobre todo en los márgenes y a través de las superficies translúcidas.

### 7.3 Superficies

- **Cristal real** (`backdrop-filter:blur(20px) saturate(150%)`, fondo translúcido, borde de
  1 px `rgba(255,255,255,.10)`) en **4 superficies y solo 4**: sidebar, topbar, overlay de
  modal y hero. Es lo caro; se acota a propósito.
- **Tarjetas** (`.card`, `.dash-card`, `system-card`, `fan-card`, `service-status-box`):
  panel **sólido** `--panel` + un brillo superior
  `linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.012))`. Sin
  `backdrop-filter` (rendimiento) pero con la misma lectura de cristal. Las tarjetas opacas
  garantizan que el texto no compita con los blobs del fondo.
- Radios `--radius`/`--radius2`; se conserva la barra de acento superior de `.dash-card::before`
  (recoloreada con `--card-accent`).

### 7.4 Movimiento (materialización)

- `@keyframes mat` (opacidad 0→1, `translateY(22px)→0`, `scale(.955)→1`, `blur(14px)→0`).
- Se aplica en **CSS puro** a los hijos del panel activo:
  `.panel.active .card, .panel.active .dash-card, .panel.active .dash-hero { animation:mat … }`
  con escalonado por `:nth-child` (hasta ~12) vía `animation-delay`.
- Como los paneles inactivos están ocultos y al activarse la regla pasa a casar, la animación
  **se re-dispara sola** al cambiar de panel: no hace falta JS.

### 7.5 Partículas (burbujas y chispas)

Dentro de `.fx`: ~8 burbujas (círculos translúcidos que suben) y ~6 chispas (estrella de 4
puntas con `clip-path`, parpadeo). Cantidades **fijas y bajas** (no aleatorias en cada carga)
y bajo coste (solo `transform`/`opacity`).

### 7.6 Fuentes

`<link rel="preconnect">` ×2 + `<link>` a Google Fonts (Inter 400-900, JetBrains Mono 400-700)
en el `<head>`, con la pila de sistema como respaldo: si no hay internet, el sitio sigue
viéndose bien, solo cambia la tipografía.

### 7.7 Alcance por componente (todo el sitio)

Sidebar y nav · topbar (título, subtítulo, botones, pill «cambios sin aplicar») · botones
(`btn`, `btn-primary`, `btn-ghost`, `btn-sm`) · inputs, selects, checkboxes, labels · badges ·
pestañas de panel · `.card` y `.dash-card` · hero y cifras · rejillas KPI · tablas (roms,
sistemas, BIOS, procesos) y sus cabeceras/`hover` · modales (overlay + caja + cabecera) ·
cajas de log/pre/consola · skeletons y chips de tema · ventiladores, almacenamiento y red.

### 7.8 Unificación de la paleta fuera de `:root`

La paleta nueva se aplica **en todo el sitio**, no solo en los tokens. Los colores escritos a
fuego se tratan en tres frentes, sin tocar estructura, IDs, clases ni lógica:

1. **CSS suelto** — badges, `input:focus`, degradados de `.nav-item.active` y `.dash-hero`,
   radial del landing, estilos «pending» amarillos, tachos: se sustituyen los literales por los
   tokens nuevos.
2. **Acentos estáticos en estilos en línea** — las tarjetas KPI llevan
   `style="--card-accent:#f0883e"`: se recolorean desde CSS con reglas por `id` y `!important`,
   que ganan al estilo en línea sin editarlo (p. ej. `#kpi-cpu{--card-accent:var(--orange)!important}`).
3. **Cadenas de color en JS** — estado de ES (`#238636`/`#da3633`) y colores de las gráficas SVG
   de tacho/red: se editan **solo los literales de color** de esas cadenas, sin tocar la lógica
   ni los nombres de funciones. Lo cubren los tests de UI-HELPERS.

Criterio: que un color quede sin unificar ha de ser una decisión consciente, no un descuido.
Al terminar, un barrido (`grep`) de literales `#`/`rgba(` en CSS, HTML y JS debe quedar reducido
a los tokens y a los pocos colores semánticos que se decidan.

## 8. Decisiones mías (revisables)

1. **Fuentes por CDN con respaldo**, no empaquetadas: no añadir binarios al repo.
2. **`backdrop-filter` en 4 superficies**; tarjetas con brillo en vez de blur (rendimiento).
3. **Animaciones apagadas con `prefers-reduced-motion`** y partículas con tope fijo.
4. **Sin modo claro**: A es oscura.
5. **`--accent2` se queda oscuro** (`#4A5BD4`) porque `btn-primary` lo usa de fondo con texto
   blanco; el cian `#22D3EE` entra como token nuevo `--aurora` solo en degradados.
6. **JetBrains Mono solo donde ya se usa `--mono`** (números, rutas, logs); el resto, Inter.
7. **La paleta se unifica en todo el sitio** (decisión del usuario, «opción 2»): se ajustan
   también los literales de color en estilos en línea y en cadenas de JS (§7.8).
8. **El cristal del modal va en la caja `.modal`**, no en el fondo `.modal-overlay`, que sigue
   siendo el oscurecido de la página.
9. **La fuente se carga sin bloquear** el dibujado (`&display=swap` en la URL de Google Fonts):
   si no hay internet se ve con la tipografía de sistema, no en blanco.

## 9. Verificación

- `python -m pytest` completo en verde (231). Canarios: `test_theme_contrast`,
  `test_sidebar_ui`, `test_landing_dashboard`, `test_nav_merge`.
- `node --check` del bloque JS extraído (como ya se hacía).
- Recorrido visual con el navegador: los 6 paneles, un modal abierto y una tabla, sin errores
  en consola, comprobando en cada uno que las tarjetas se materializan y que nada desaparece.
- Comprobar `prefers-reduced-motion` (sin animaciones) y que el fondo no da tirones.
- Barrido final de literales de color (`grep` de `#`/`rgba(` en CSS, HTML y JS) para confirmar
  que solo quedan tokens y los colores semánticos decididos (§7.8).

## 10. Riesgos y notas

- **Contraste:** `--bg`/`--panel` se oscurecen; los `--text*` propuestos suben de ratio, pero
  la puerta es el test (ver §5).
- **Rendimiento:** el blur es lo caro; acotado a 4 superficies y desactivable por
  `prefers-reduced-motion`.
- **Regex de tests:** el cuerpo de `.nav-item.active` no puede anidar `}`.
- **Landing:** no se rediseña; comprobar que sigue funcionando y legible con el nuevo fondo.
- **Sin tocar JS de lógica:** cualquier necesidad de animación se resuelve en CSS.

## 11. Historial

- 2026-10-16: el usuario elige A · Aurora Glass y fija el alcance en «todo el sitio».
  Diseño escrito a partir de la maqueta navegable y del contrato de tests.
- 2026-10-16: revisión de construcción independiente; única pregunta abierta: alcance de la
  paleta fuera de `:root`. El usuario elige la **opción 2 (unificar todo el sitio)** → §7.8 y
  decisiones 7-9.
- 2026-10-17: implementado en 8 commits. Nota: la paleta fuera de `:root` se unificó
  sustituyendo **directamente** los literales de color en estilos en línea (y hex en cadenas
  JS), en vez de con reglas por `id` + `!important`: igual de efectivo y sin `!important`.
