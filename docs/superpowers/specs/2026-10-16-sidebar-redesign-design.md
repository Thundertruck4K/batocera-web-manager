# Diseño: Refinamiento de paleta + rediseño estético del sidebar (Batocera Manager)

**Fecha:** 2026-10-16
**Autor:** sesión de rediseño (asistida)
**Estado:** aprobado para implementación (2026-10-16)
**Ámbito:** solo frontend (`templates/index.html`), sin tocar `app.py` ni la API.
Incluye el **refinamiento de la paleta global (`:root`) aplicado a toda la app** *y* el
**rediseño del sidebar**.

---

## 1. Contexto

`C:\Users\folk3\Downloads\batocera_web` es un gestor web ligero para una instalación de
**Batocera**: backend Python **solo stdlib** (`http.server`, `app.py`) y frontend SPA de un
único fichero `templates/index.html` (HTML + CSS + JS vanilla, sin build step). Todo el CSS
vive en un `<style>` embebido; las variables de tema están en `:root` (líneas ~10-33).

El sidebar actual (líneas ~570-612 de `index.html`) ya está **agrupado en 4 secciones** y usa
**emojis** como iconos:

| Sección | Items (`showPanel`) |
|---|---|
| Principal | Dashboard (`dashboard`), Agregar Sistema (`add`), Sistemas Creados (`list`) |
| Visual | Temas & Assets (`themes`), Vista Previa XML (`preview`) |
| Contenido | ROMs & BIOS (`roms`) |
| Sistema | BIOS Faltante (`biosmissing`), Configuración (`settings`) |

El pie del sidebar muestra el tema activo (`#sb-theme`).

**Problemas:**
- **Estético (sidebar):** los emojis se ven distintos según SO/navegador y delatan "app genérica";
  jerarquía pobre (labels apenas diferenciados), el item activo es un relleno plano
  (`background:var(--accent2)`) sin acento ni profundidad, y las secciones no tienen separadores.
- **Paleta (global):** algunos tonos de texto (`--text2` `#9aa0c0`, `--text3` `#6b7394`) tienen
  contraste bajo sobre los fondos oscuros; los acentos pueden afinarse. Afecta a toda la app.

## 2. Objetivo

Hacer la app **más atractiva y más legible**:
1. **Refinar la paleta `:root`** (contraste de texto y acentos) para **toda la app**, sin cambiar
   la identidad de color.
2. **Rediseñar el sidebar** (iconos SVG, jerarquía, item activo, separadores), inspirándose en la
   estética limpia de **explee.com** (planitud, jerarquía por espacio y peso, radios pequeños)
   pero sobre la paleta oscura existente y con el nivel de efectos "Equilibrio".

Manteniendo toda la funcionalidad y el contrato de navegación intactos.

## 3. Requisitos (fase de brainstorming)

- **Iconos:** SVG inline estilo **Lucide/Feather** (línea, ~2px de trazo, 16-18px). Sin
  dependencias externas ni webfonts (el dispositivo puede estar offline).
- **Nivel de efectos "Equilibrio":** base plana + acentos sutiles (`~160ms` de transición,
  gradientes tenues, glow discreto en el item activo).
- **Item activo — Variante C:** fondo con gradiente tenue (`rgba(accent,.18) → rgba(accent2,.06)`),
  borde 1px de acento (`~rgba(110,168,254,.45)`), sombra interior sutil y glow exterior suave;
  icono y texto toman el acento.
- **Paleta (alcance app completa):** se mantienen las variables `:root` y sus **tonos de
  identidad**, pero se **refinan globalmente** (contraste de texto, acentos), aplicándose a toda
  la app además del sidebar. No se reemplaza la identidad de color.
- **Agrupación:** se conserva la estructura existente (Principal · Visual · Contenido · Sistema).
- **Prioridad UX:** **menos re-render**. Casi todo es CSS; el toggle de activo ya lo hace
  `showPanel`, no se añade trabajo en JS.
- **Ágil y útil:** se mantienen los badges numéricos ya presentes.

## 4. No-objetivos

- No se renombran ni eliminan rutas `/api/*` ni paneles.
- No se toca `app.py` ni el backend.
- No se introduce ningún framework, bundler ni dependencia nueva.
- No se cambia el layout general (sidebar fijo a la izquierda) ni la **identidad** de color.
- No se añade un sistema de temas nuevo (multi-tema) más allá del chip existente.

## 5. Anti-objetivos (qué haría fracasar esto aunque "funcione")

- Un sidebar **más pesado** (animaciones continuas, blur costoso, partículas) que ralentice el
  render o el cambio de panel.
- Romper el bloque `UI-HELPERS` que extrae `tests/test_systems_ui.py`.
- **Refinar la paleta y empeorar** el contraste en alguna superficie (p. ej. texto sobre tarjetas
  o badges), o dejar colores hardcodeados que ya no casen con las nuevas variables.
- Iconos que dependan de red (CDN) o de una fuente que no exista en el dispositivo.
- Un item activo con contraste tan bajo que no se distinga qué panel está abierto.

## 6. Restricciones técnicas

- Fichero único `templates/index.html`; CSS embebido.
- Los `onclick="showPanel('<id>',this)"` deben seguir viviendo en el `<button class="nav-item">`
  (el `this` es el botón). Añadir `<svg>` **dentro** del botón es seguro; no envolver el botón.
- Las clases existentes `sidebar`, `nav`, `nav-item`, `nav-section-label`, `nav-badge`,
  `sidebar-footer`, `theme-chip` se conservan y **se estilizan**.
- Mantener el bloque marcado `UI-HELPERS` intacto.
- El refinamiento de `:root` debe **respetar los literales ya hardcodeados** que no salen de
  variables (p. ej. hay un azul `rgba(88,166,255,…)` suelto): revisar que sigan casando o
  migrarlos a variables de forma consistente.
- Sin `file://`: la verificación visual se sirve por el servidor dev (`:5000`).

## 7. Decisiones (tomadas con el humano)

1. **Iconos:** SVG inline tipo Lucide. *(decidido)*
2. **Nivel de efectos:** Equilibrio. *(decidido)*
3. **Paleta:** variables actuales **refinadas, con alcance app completa (`:root`)**. *(decidido)*
4. **Item activo:** Variante C (cristal + borde acento + glow). *(decidido)*
5. **Agrupación:** se conserva la existente de 4 secciones. *(decidido)*
6. **"Fondos de paneles"** = secciones/items **del sidebar**, no los paneles de contenido. *(aclarado)*
7. **Logo del sidebar (🕹️):** entra en el rediseño (se sustituye por SVG coherente). *(llamada del builder, revisable)*
8. **Icono por item** (propuesta, ajustable):
   - Dashboard → `layout-dashboard`
   - Agregar Sistema → `plus-circle`
   - Sistemas Creados → `list`
   - Temas & Assets → `palette`
   - Vista Previa XML → `eye`
   - ROMs & BIOS → `gamepad-2`
   - BIOS Faltante → `puzzle` (o `cpu`)
   - Configuración → `settings` (engranaje)
   - Logo → un icono de marca (p. ej. `gamepad-2`) en color acento.
   - Footer / chip de tema → mantener el chip actual.

## 8. Enfoque de implementación

1. **`:root` (app completa):** subir el contraste de `--text2`/`--text3`, afinar `--accent`/
   `--accent2` y, si hace falta, `--border`. Cambios **pequeños y medibles**; revisar que ningún
   panel (dashboard, tarjetas, formularios, tablas, badges) pierda legibilidad. Migrar literales
   sueltos incoherentes a variables si aparecen.
2. **CSS del sidebar:** reglas para `.nav-item svg`, `.nav-section-label` (con separador `::after`
   degradado), `.nav-item.active` (Variante C), hover, y `.nav-badge` en estado activo.
3. **HTML del sidebar:** sustituir los 8 `<span class="icon">emoji</span>` (y el emoji del logo)
   por `<svg>` inline (paths Lucide, `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`,
   `stroke-width="2"`).
4. **JS:** sin cambios de lógica. Verificar que `showPanel` sigue funcionando; alinear emojis de
   la **topbar** es **opcional y por defecto NO** (fuera del alcance acordado).
5. Commits atómicos: (a) refinamiento `:root`; (b) CSS del sidebar; (c) HTML/iconos del sidebar.
6. Verificación visual en el servidor dev antes de desplegar.

## 9. Verificación

- `python -m pytest` en verde (incluye `tests/test_systems_ui.py`, que extrae `UI-HELPERS`).
- `python -m py_compile app.py` (no se toca, pero comprobar que no rompimos nada).
- `node --check` sobre el JS embebido extraído (`_jscheck.py` o equivalente del proyecto).
- **Recorrido visual completo** por `:5000` a causa del alcance app-wide: sidebar (normal, hover,
  activo en una sección distinta a Dashboard, p. ej. Configuración) **y** al menos Dashboard,
  ROMs/BIOS y Configuración para confirmar que el refinamiento de paleta no degrada contraste.
- Comprobar que cada `showPanel` sigue cambiando de panel tras el cambio de markup.

## 10. Llamadas del builder (marcadas como tales, reversibles)

- Valores concretos del refinamiento de `:root` (cuánto sube el contraste de `--text2`/`--text3`).
- Icono definitivo de "BIOS Faltante" (`puzzle` vs `cpu`), de "ROMs & BIOS" (`gamepad-2`) y del logo.
- Radio exacto (`8px`), duración de transición (`~160ms`) y opacidades del glow.
- Si se armonizan o no los emojis de la **topbar** — por defecto **no**.

## 11. Historial / notas

- El resumen de sesión previo describía erróneamente un sidebar de "12 items planos"; el estado
  real del fichero (verificado por lectura directa) son **8 items en 4 grupos**. Este documento
  refleja el estado real.
- Revisión del builder (subagente) el 2026-10-16: cerró dudas de estructura/JS; su pregunta de
  alcance de paleta se resolvió como **app completa (`:root`)**.
