# Diseño: Landing animado + Rediseño del dashboard

**Fecha:** 2026-10-16
**Autor:** sesión de rediseño (asistida) — el usuario delegó el diseño ("diseñas tú")
**Estado:** aprobado para implementación (opt-out de preguntas de brainstorming)

---

## 1. Contexto

El gestor (`app.py` + `templates/index.html`, Python stdlib, sin dependencias) abre
directo en el panel *Dashboard*, una rejilla densa de KPIs (CPU/GPU/RAM/Disco/Red/ES),
ventiladores, almacenamiento, RSS, red y procesos. El usuario lo describe como
"avasallante" para alguien común y quiere que el proyecto sea atractivo para quien llega
desde GitHub. Se apoya en la referencia visual de un dashboard crypto oscuro/glass
(muz.li → Dribbble 27690535).

El usuario pidió, en una sola fase:
1. Un **landing** con icono animado de carga + información.
2. Un **rediseño completo del dashboard**: hero, card de preview de un juego al azar
   (scraper API v2, priorizando arte de usuario), analítica de juegos más usados y
   gráficas fluidas de horas de uso.

El proyecto 2 (reagrupación del sidebar) ya dejó la navegación en 5 bloques / 6 destinos
y las fusiones (BIOS Faltante como pestaña, Vista Previa dentro de crear/editar).

---

## 2. Objetivo

Que abrir el gestor se sienta como un **centro de mando amable**: una bienvenida breve y
viva que orienta, y un dashboard que en el primer vistazo responde "¿está todo bien?",
"¿qué jugué?" y "¿cómo va mi tiempo de juego?", sin perder la profundidad técnica (que
queda a un clic).

## 3. Requisitos (del usuario)

- Landing con loader animado e información.
- Dashboard con hero, card de preview de juego al azar (arte de usuario primero),
  analítica de juegos más usados y gráficas de horas de uso.
- Conservar gráficas y monitoreo (los actuales siguen siendo útiles).
- Lo delicado, opcional y no obligatorio (aquí: el landing se puede saltar; el
  monitoreo técnico no desaparece).
- Sin dependencias nuevas. Commits atómicos. TDD para el código.

## 4. Ámbito

**Dentro:**
- Overlay de landing (`#landing`) al abrir, con animación e info real.
- Rediseño del panel Dashboard: cabecera *hero*, card de juego al azar, analítica de uso
  (más usados + actividad + horas cuando existan), y las gráficas actuales re-estilizadas
  y conservadas.
- Backend nuevo: escaneo de estadísticas de juego desde `gamelist.xml`, selección de un
  juego al azar con arte, y endpoints.

**Fuera (para fases posteriores):**
- RetroAchievements (proyecto 4).
- Scraping automático de BIOS (proyecto 5).
- Limpieza/commit/zip/deploy remoto (proyecto 6).
- Cualquier descarga de arte nueva desde el dashboard (solo se *muestra* arte existente).

## 5. Enfoque técnico

### 5.1 Datos: qué existe y qué no

`gamelist.xml` puede traer `<playcount>`, `<lastplayed>` y `<playtime>` (segundos).
Hoy la app **no parsea ninguno**. EmulationStation/Batocera escriben `playcount` y
`lastplayed` de forma fiable; `playtime` depende de la versión.

**Decisión (mía):** parsear los tres y **degradar con honestidad**:
- Si hay `playtime` → "horas de uso" reales (total, por sistema, y reparto).
- Si no hay `playtime` pero sí `playcount` → mostrar **partidas** y **actividad por fecha**
  (derivada de `lastplayed`), rotulando claramente "tiempo no registrado".
- Nunca inventar horas.

### 5.2 Backend (funciones puras y testables por inyección de rutas)

- `collect_play_stats(roms_base, systems=None) -> dict`
  Recorre los `gamelist.xml` de los sistemas del usuario y agrega:
  ```json
  {
    "ok": true, "updated": 1729000000.0,
    "totals": {"games": 42, "playcount": 310, "playtime_s": 90000, "systems": 7},
    "has_playtime": true,
    "top_games": [{"system","name","path","playcount","lastplayed","playtime_s","image"}],
    "by_system": [{"system","playcount","playtime_s","games"}],
    "activity":  [{"date":"2026-10-12","count":3}]
  }
  ```
- `pick_random_game(roms_base, systems=None) -> dict | None`
  Elige un juego al azar entre los que tienen imagen disponible y devuelve
  `{"system","name","filename","subpath","image_url_ready":true}`.
- `find_user_art(system, rom_path) -> list[Path]`
  Orden de preferencia **arte de usuario primero**: `media/images/`, `images/`,
  `mixrbv2`, `mixrbv1`, `fanart`, `screenshots`, `named_boxarts`, `boxart`, `wheels`,
  `marquees`, y por último el `<image>` del gamelist. Devuelve rutas candidatas.
- Reutiliza `_serve_rom_image` para servir la imagen de la card (ya respeta subpath).

**Endpoints nuevos:**
- `GET /api/game-stats` → `collect_play_stats(...)`.
- `GET /api/random-game` → `pick_random_game(...)`.

### 5.3 Frontend — Landing (`#landing`)

Overlay a pantalla completa insertado antes de `<div class="app">`, con:
- Logo SVG animado (aro/joystick con trazo que se dibuja + pulso suave).
- Info real traída en paralelo: versión de Batocera, nº de sistemas, estado de ES,
  BIOS faltantes, temas. Skeleton mientras carga.
- Botón **Entrar** (y auto-entrada cuando termina la carga, ~1.2 s), tecla `Esc`/clic para
  saltar, y **"no volver a mostrar"** recordado en `localStorage`. El landing es un extra
  opcional, no un muro: nunca bloquea la app (los timers de fondo arrancan igual).

### 5.4 Frontend — Dashboard rediseñado

Sobre los mismos endpoints, en `dash-card`s:
1. **Hero**: saludo según hora, versión Batocera, uptime, pill de estado de ES, y 3-4
   cifras grandes (juegos en biblioteca, partidas, horas o "—", BIOS faltantes).
2. **Juego al azar** (`#dash-random-game`): fondo con la imagen del juego (arte de usuario
   primero, `object-fit:cover` + degradado), nombre, sistema y botón "otro" (re-pide
   `/api/random-game`), y "ver detalle" (abre el modal ROM existente si está en la ruta).
3. **Analítica** (`#dash-playstats`): top de juegos más usados (barras), reparto por
   sistema, y **gráfica fluida de actividad/uso** (SVG + área con degradado, siguiendo el
   idioma `tacho`/`tank`/braille ya existente). Si no hay `playtime`, la gráfica de
   actividad usa `lastplayed` y se rotula en consecuencia.
4. **Monitoreo técnico**: se **conservan** las tarjetas y gráficas actuales (KPIs, tachos,
   tanque de disco, ventiladores, red, procesos), reordenadas bajo el hero y con el estilo
   glass del rediseño.

### 5.5 Estilo

Reutilizar los tokens `:root` (no renombrar), añadir un fondo con degradado radial sutil,
`.dash-card` con blur/borde suave y la barra de acento superior que ya existe. Sin fuentes
ni assets externos.

## 6. Decisiones (mías, revisables)

- **Landing saltable y recordable** (`localStorage`), no un muro obligatorio.
- **Nada de datos inventados**: si falta `playtime`, se dice.
- **Sin dependencias**; animaciones y gráficas en SVG/CSS.
- **Conservar** todo el monitoreo técnico actual.
- El landing **no bloquea** `init()` ni los sondeos de fondo.
- Los endpoints nuevos devuelven `{ok:bool,...}` como el resto de la app.

## 7. Verificación

- Tests Python: `collect_play_stats` (con gamelist de ejemplo en `tmp_path`), `pick_random_game`
  (determinista vía `random` monkeypatcheado), `find_user_art` (orden de preferencia),
  y tests de estructura HTML (landing existe, endpoints cableados, navegación intacta).
- `python -m pytest` completo en verde + `node --check` del JS extraído.
- Verificación en vivo con `browser.evaluate` (overlay visible/oculto, card con imagen,
  gráficas con datos) y sin errores JS en consola.

## 8. Riesgos / notas

- Sin `playtime` en la máquina del usuario, las "horas" no aparecerán hasta que su ES las
  escriba; el diseño lo maneja sin romper nada.
- El arte "de usuario primero" solo reordena *preferencias de visualización*; no reescribe
  archivos ni borra nada.
- Mantener el contrato del harness de tests: `showPanel(id,this)`, `.panel.active`,
  `.nav-item.active`, marcadores `UI-HELPERS`, nombres de tokens `:root`.

## 9. Historial / notas

- 2026-10-16: diseño escrito tras opt-out de preguntas del usuario ("diseñas tú").
