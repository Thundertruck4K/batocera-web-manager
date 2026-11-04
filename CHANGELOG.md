# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el versionado sigue [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Cambiado
- **La versión del manager pasa a 1.5.** `APP_VERSION` (en `app.py`) es la única fuente de la
  versión y ahora coincide con la release publicada.
- **README reescrito con el funcionamiento actual.** La sección de características separa lo que
  ya está en la SPA de lo que sigue sólo en la interfaz clásica, el diagrama de arquitectura
  incluye el bundle de React, la tabla de secciones de «Uso» lista las reales del menú y se
  explica **por qué se unificaron los dos repositorios**.

### Añadido
- **Capturas nuevas de la interfaz actual** (`docs/screenshots/`): panel de control, Sistemas
  Personalizados, Añadir sistema, Depuración y Configuración, tomadas sobre una instalación real
  de Batocera 43.1. Las 13 capturas anteriores, de la interfaz clásica, se sustituyen por estas.

## [1.5] — 2026-11-03

### Cambiado
- **El proyecto vuelve a vivir en un solo repositorio.** Durante un tiempo se mantuvo en dos
  repositorios independientes con el mismo backend: la interfaz React + Tailwind CSS y la variante
  «Python puro» (interfaz de un solo fichero). La variante se retira: su repositorio
  `Thundertruck4K/batocera-web-manager` se elimina y todo el trabajo sigue aquí, en
  `Thundertruck4K/batocera-web-manager-react`.
  - La **interfaz clásica** (`templates/index.html`) no desaparece: se queda como **respaldo** y el
    backend la sirve automáticamente cuando el bundle compilado no está en la consola.
  - La documentación (README, AGENTS, CHANGELOG y MEMORY) describe ya un único proyecto, sin
    referencias al repositorio hermano ni a la sincronización de dos `app.py`.
  - `APP_REPO` no cambia: sigue apuntando a este repositorio.

### Añadido
- 12 tests nuevos (`tests/test_install_sh.py`) que cubren la fase de validación de
  utilidades: git y node presentes, ausentes (con aviso e instalación desde un espejo local de
  micromamba), sha256 que no cuadra, canal de conda, `BM_GIT=skip` y el bloque `# [batocera-git]`
  de `custom.sh`.
- **Git opcional en el `install.sh`**: el instalador comprueba si hay git y, si no lo encuentra,
  avisa de que es necesario instalarlo y lo instala. Batocera es Buildroot (sin gestor de
  paquetes ni compilador), así que se hace con **micromamba**, un binario estático, contra el
  canal `conda-forge`: se **verifica el sha256 de micromamba contra el hash fijado en el propio
  script** (si no cuadra, no se descomprime nada), se crea el entorno en
  `$BASE_DIR/mamba/envs/git` con `micromamba create` —que a su vez comprueba el sha256 de cada
  paquete— se enlaza `git` en `/usr/bin`, se borra la caché de paquetes (cientos de MB) y se
  escribe un bloque `# [batocera-git]` en `custom.sh` para que el enlace se recree en cada
  arranque (`/usr` es un overlay que se pierde al reiniciar).
  - Variables nuevas: `BM_GIT` (`auto` / `install` / `skip`), `BM_GIT_DIR`, `BM_GIT_BIN_DIR`,
    `BM_MICROMAMBA_URL`, `BM_MICROMAMBA_VERSION`, `BM_MICROMAMBA_SHA256` y `BM_CONDA_CHANNEL`.
- **Proceso de validación de utilidades** en el `install.sh` (v1.6): antes de instalar nada se
  comprueban **git** y **node**. Si ya están, la instalación continúa sin preguntar nada; si
  faltan, se avisa («no se encontró X en el sistema: es necesario instalarlo para continuar») y
  se instalan. Con `BM_GIT=skip` / `BM_NODE=skip` se salta la instalación de esa utilidad, y con
  `=install` se fuerza aunque ya esté. Que falte git **no** impide instalar el manager: la web
  funciona igual, sólo se pierde la actualización con `git pull`.
- **Node.js opcional en el `install.sh`**: el instalador detecta si hay Node y, si no lo encuentra,
  ofrece instalarlo: descarga el tarball oficial de nodejs.org (la última LTS por defecto, o la que
  fije `BM_NODE_VERSION`), **comprueba el sha256 contra el `SHASUMS256.txt` oficial antes de
  descomprimir nada**, lo deja en `$BASE_DIR/node/current`, enlaza `node`, `npm`, `npx` y `corepack`
  en `/usr/bin` y escribe un bloque `# [batocera-node]` en `custom.sh` para que los enlaces se
  recreen en cada arranque (`/usr` es un overlay que se pierde al reiniciar) y para persistir
  `npm_config_prefix` y `npm_config_cache` en la SD. **Sigue siendo opcional**: el frontend se
  despliega ya compilado, así que el manager funciona igual sin Node.
- **Tarjetas «Información del sistema» e «Instrucciones»** en *Configuración* de la versión React:
  versión del manager, qué interfaz se está sirviendo (SPA de React o interfaz clásica), versión de
  Python y de Node, disponibilidad de Pillow, puerto, carpeta del bundle compilado y ruta de
  `custom.sh`; y las instrucciones de acceso, de instalación/actualización y de recompilación del
  frontend, coherentes con el stack React + Tailwind (antes el manual de la interfaz clásica se
  quedaba corto y con rutas de un proyecto que ya no es el que se despliega).
- **`GET /api/system-info`**: endpoint nuevo con esos mismos datos del entorno, para la pantalla de
  Configuración.
- **Bloque de arranque automático con `pkill`**: el bloque de `custom.sh` empieza matando la
  instancia anterior del manager, de modo que la nueva no se queda sin puerto si el servicio ya
  estaba levantado a mano.
- 21 tests nuevos (`tests/test_autostart_block.py` y ampliación de `tests/test_install_sh.py`) que
  cubren el bloque de `custom.sh`, el contrato del servicio, la validación del puerto y la
  instalación de Node contra un espejo local de nodejs.org (sin red).
- **Vista de depuración en vivo** (`/depuracion`): nueva entrada en el sidebar con el componente
  `LogStream` de [overtrue/ui](https://ui.overtrue.xyz/components/log-stream), instalado con el CLI de
  shadcn (`frontend/components.json` guarda la configuración del registro). El backend mantiene un
  historial circular de 500 eventos con nivel y los empuja por SSE (`GET /api/logs/stream`), así que
  cada petición, acción y aviso aparece en vivo, con filtros por nivel (debug, info, aviso, error) y
  por texto, y con el historial de la interfaz clásica intacto.
- **Node.js opcional en el dispositivo**: la Batocera de desarrollo ya tiene Node v26 LTS
  (`/userdata/system/node/current`, enlazado en `/usr/bin/node`), instalado desde el tarball oficial
  porque Batocera es Buildroot y no tiene gestor de paquetes. Permite recompilar el frontend en la
  propia consola; el bundle sale con los mismos hashes que el versionado. **Sigue sin ser necesario**:
  el despliegue normal es subir `frontend/dist/` ya compilado.
- **Backend unificado con la versión Python pura**: el `app.py` de este repositorio pasa a ser
  **idéntico** al del repositorio hermano (`batocera-web-manager`), salvo la constante `APP_REPO` (el
  repo del que se leen las releases). Los dos proyectos comparten backend y API sin riesgo de
  divergencia: un comprobador automático verifica que los dos ficheros siguen siendo iguales.
- **Proceso de desarrollo documentado**: el README y AGENTS.md explican ahora la relación entre las dos
  instancias, los puertos en uso (`:5001` React / `:5000` Python / `:5173` Vite), los comandos
  habituales y la política de ramas: nunca `push` directo a `master`, siempre rama + pull request.
- **El proyecto se independiza en su propio repositorio**: `batocera-web-manager-react`. A partir de
  aquí este repositorio contiene la versión con interfaz **React + Tailwind CSS**; la versión Python
  pura (interfaz de un solo fichero, sin build ni dependencias) se queda en
  `Thundertruck4K/batocera-web-manager`, con el mismo backend y la misma API.
  - Las URLs públicas (README, `install.sh`, feed de actualizaciones, instrucciones del panel y
    sus tests) apuntan al repositorio nuevo.
- **Frontend React + Tailwind CSS** (`frontend/`): la interfaz del manager se reescribe como SPA en
  React 19 + TypeScript + Vite 6 + Tailwind CSS v4, con el design system **amicro-design-system**
  (tokens `--color-card` / `--color-stage` / `--color-chart-1..4`, tema claro y oscuro, curva de
  movimiento `cubic-bezier(0.16, 1, 0.3, 1)`, Recharts con `animationDuration={280}`).
  - Pantallas nuevas: **panel de control** (CPU/RAM/temperatura/disco con gráficos, procesos, red,
    ventiladores, GPU, batería, almacenamiento, juego al azar y más jugados, con refresco automático
    configurable), **sistemas** (listado con búsqueda, alta/edición/borrado, vista del XML generado),
    **formulario de sistema** (catálogo de referencia de Batocera buscable, vista previa del XML en
    vivo contra `/api/preview`, simulación sin escritura) y **configuración** (tema, rutas, claves de
    RetroAchievements y arranque automático).
  - `app.py` sirve `frontend/dist/` cuando está compilado y cae a la interfaz clásica si no lo está.
    Las rutas del enrutador del cliente (`/sistemas`, `/configuracion`…) se resuelven con un fallback
    a `index.html`, así que recargar no devuelve 404.
  - El bundle compilado (`frontend/dist/`) se versiona en el repositorio: el dispositivo Batocera no
    tiene Node y despliega el bundle tal cual.
  - **La API no cambia**: el frontend consume los mismos endpoints `/api/*`. `frontend/src/lib/normalize.ts`
    rellena los campos que el backend deja vacíos cuando no hay `/proc` ni `/sys` (fuera de Linux) para
    que la interfaz degrade en lugar de quedar en blanco.
- **Tarjetas del panel rediseñadas al estilo «mono»**: cada tarjeta del manager pasa a un contenedor
  redondeado de 24 px con su propio color de acento, cabecera en mayúsculas con el icono en píldora y
  un «stage» interior de 14 px donde viven los gráficos. Los visualizadores (velocímetro de 240°,
  sparkline de área, donut de reparto y barras redondeadas) están escritos en CSS/JS puro en la
  interfaz clásica: ni React ni Recharts ni ningún paso de build, el proyecto sigue sin dependencias
  **en el backend y en la interfaz clásica**.
- 13 tests nuevos (`tests/test_mono_charts.py`) para el design system mono, sus tokens por tema y los
  visualizadores.
- **Tema claro/oscuro para la web del manager**: en *Configuración → Tema de la interfaz* se elige
  claro, oscuro o "seguir al sistema", y el botón del sidebar alterna al instante. La preferencia se
  guarda en los ajustes del manager (no en el navegador), así que se aplica igual desde el móvil o el
  PC, y se inyecta en el HTML al servir la página: no hay parpadeo al cargar. La paleta clara cumple
  contraste WCAG AA (verificado por tests).
- 48 tests nuevos (`tests/test_ra_key_mask.py`, `tests/test_ui_theme.py` y ampliación de
  `tests/test_theme_contrast.py`).
- **Verificación de actualizaciones mayores**: el dashboard comprueba las releases publicadas del propio repositorio (feed Atom de GitHub, cacheado 1 h) y avisa con un banner visual cuando aparece una versión **mayor** (2.0, 3.0...). Endpoint nuevo `/api/app-update`; sin conexión el aviso simplemente no aparece y la app sigue igual. El descarte se recuerda por versión, así que al llegar la 3.0 vuelve a avisar aunque el usuario ya cerrara el aviso de la 2.0.
- 16 tests nuevos para el sistema de actualización (`tests/test_app_update.py`).
- 20 tests nuevos (`tests/test_scraper_secrets.py`) para el enmascarado de las credenciales del
  scraper.
- 8 tests nuevos para las correcciones de la revisión (inyección en `batocera.conf`, lista
  blanca de la config pública, listener del modo "auto" y borrado accidental de la key de RA).

### Cambiado
- **«Sistemas» pasa a llamarse «Sistemas Personalizados»** en el sidebar y en el título de la página,
  con el subtítulo «N sistema(s) añadido(s) manualmente a EmulationStation»: son los sistemas
  agregados a mano al manager, no el catálogo de sistemas de Batocera.
- **`install.sh` v1.5**: valida el puerto (debe ser un número entre 1 y 65535) y avisa si ya está
  ocupado por otro servicio; al ejecutarlo con el manager corriendo, para la instancia anterior y
  arranca la nueva, que si no seguiría sirviendo el código de antes de la actualización. El bloque de
  `custom.sh` se **reescribe** en cada instalación: antes se quedaba con el puerto y la ruta
  antiguos.
- **El estado del servicio tiene una forma única**: `/api/service/status` devuelve siempre
  `registered`/`installed`, `manual_mode`, `cmd` y `block` para el arranque automático, y `running`,
  `pids`, `pid`, `port` y `cmd` para el proceso. La interfaz clásica y la React leen lo mismo.
- Contador de tests del README actualizado a 461.
- El tacho con aguja (CPU/GPU/RAM) y el tanque de líquido (disco) los sustituyen el velocímetro y el
  donut con paleta; el gráfico de actividad pasa a ser un área monótona con degradado. Se elimina el
  código y el CSS de los gráficos antiguos.

### Corregido
- **La tarjeta «Disco Principal» del panel mostraba siempre 100 %**: el centro del donut pintaba la
  suma de los porcentajes de todas las particiones (que siempre suma 100) en lugar del valor
  destacado, y sólo se corregía al pasar el ratón por la tarjeta. Ahora el centro muestra el uso real
  del disco principal y el resto de los valores se leen al pasar el ratón.
- **El estado del servicio en *Configuración* era siempre «Inactivo / Detenido / —»**: el frontend
  pedía `autostart.installed` y `process.pid`, pero el backend devolvía `autostart.registered` y
  `process.pids`, así que los tres campos salían vacíos aunque el manager estuviera en marcha. El
  contrato se ha igualado en ambos lados.
- **El bloque de arranque automático se quedaba con el puerto o la ruta antiguos**: `install.sh`
  ahora reescribe el bloque en vez de dejarlo como estaba, y el botón «Reiniciar» de *Configuración*
  también lo reescribe con los valores actuales, de forma que `custom.sh` nunca pide arrancar el
  manager en un puerto que ya no es el configurado.
- **La tarjeta «Flujo de eventos» de *Depuración* tenía un borde más claro** que las de encima: el
  componente `LogStream` pinta su propio borde con el color actual; ahora la tarjeta usa el mismo
  `border-border` que las demás. **Sus líneas divisorias internas** (la barra de filtros, la del pie y
  el borde del botón «Pausa») también heredaban ese color claro: llevan `border-border`, el mismo
  token que la tarjeta que las contiene.
- El tema claro dejaba ilegibles algunos elementos: el modal (translucido sobre
  el scrim negro), el chip de codigo del aviso de servicio y los degradados de
  texto del dashboard. Ahora cada uno tiene su variable de tema.
- Una mascara de la Web API Key que venia de otro dispositivo se guardaba como
  si fuera la key nueva, dejando la credencial rota en silencio. Ahora se
  detecta la mascara por su forma, no comparandola con la key actual.
- Las Web API Keys de menos de 12 caracteres se ocultan enteras: con el umbral
  anterior, una key de 9 se mostraba en 8 de sus 9 posiciones.
- `tests/test_install_sh.py` asumia que Git estaba en `C:\Program Files\Git`:
  ahora deriva el `bash` real de la ruta de `git.exe`, asi que sus 10 tests no
  se saltan si Git esta instalado en otro sitio.
- El modo "auto" del tema ya no pisa un tema explicito elegido despues (el listener de
  `matchMedia` seguia escribiendo encima) y ya no se acumula en cada cambio de tema.
- La Web API Key de RetroAchievements solo se borra si el usuario vacia el campo a proposito:
  un guardado rapido, antes de que llegue la mascara, ya no puede borrarla.
- El formulario de credenciales del scraper (pestaña "Configuración" del modal) se carga tambien
  al entrar en esa pestaña: antes dependia de haber pasado antes por otra.

### Seguridad
- La **Web API Key de RetroAchievements ya no se sirve en claro** por `/api/settings`: se devuelve
  enmascarada (`abcd••••••••wxyz`) junto con un indicador `ra_api_key_set` de si está configurada.
  Al guardar se comporta como solo-escritura: si no tocas el campo, la key se conserva; si lo vacías,
  la borra. Además `/api/settings` solo expone claves conocidas, para que el fichero de ajustes
  (editable a mano) no pueda inyectar campos extra en la respuesta.
- Las **credenciales del scraper (ScreenScraper, TheGamesDB e IGDB) ya no se sirven en claro** por
  la API: `/api/scraper/config` y el campo `cfg` de `/api/scraper/search` las devuelven
  enmascaradas, con un indicador `<campo>_set` de si cada una está configurada. Al guardar se
  comportan como solo-escritura: si no tocas el campo, la credencial no se pierde; si lo vacías,
  se borra. Además, una máscara que llegue del cliente nunca se guarda ni se envía a las APIs
  externas: manda la credencial que tiene el servidor.
- Un valor con salto de linea en el formulario del scraper ya no puede inyectar directivas
  nuevas en `batocera.conf`: el servidor escribe ese fichero con permisos de root y una sola
  línea de más creaba una clave espuria.
- La config publica del scraper usa lista blanca de campos, igual que `/api/settings`: un
  campo nuevo no puede colarse en la respuesta en claro.

## [1.4] - 2026-10-18

### Añadido
- Monitor de ROMs & BIOS: los sistemas se agrupan por tipo de equipo (Arcade, Consolas, Portátiles, Ordenadores, Otros) en secciones plegables, con filtros combinables por tipo y por fabricante en forma de chips. El tipo/fabricante se lee de `es_systems.cfg` y, si el slug no aparece, se deduce del nombre del sistema.
- 25 tests nuevos para el panel de ROMs & BIOS (`tests/test_roms_ui.py`): estructura del grid multicolumna, chips de filtrado y clasificación por tipo/fabricante.

### Cambiado
- Dashboard rediseñado: tarjetas CPU/GPU/RAM más compactas (tacómetros más chicos); Almacenamiento y Ventiladores en una sola fila; eliminadas las tarjetas de Red y Procesos.
- La tarjeta de "Noticias" ahora muestra las actualizaciones oficiales de Batocera (releases de GitHub) en formato compacto, y se añadió una segunda tarjeta con información de EmulationStation (estado, PID, puerto, uptime, reinicio).
- Tacómetros reemplazados por anillos radiales (más compactos) y se quitó parte del texto informativo de las tarjetas CPU/GPU/RAM. Tarjetas de ventiladores mucho más pequeñas.
- Contador de tests actualizado a 320.
- README sincronizado con el estado actual: conteo de tests (320), descripción del dashboard (anillos radiales, ventiladores, tarjetas de actualizaciones de Batocera y de EmulationStation) y del panel ROMs & BIOS (agrupación por tipo de equipo y filtros por fabricante).

### Corregido
- Los chips de **TIPO** y **FABRICANTE** del panel ROMs & BIOS sólo mostraban "Todos / Otros": el endpoint `/api/rom-systems` devolvía una lista recortada de campos en la que faltaban `type` y `manufacturer`, justo los que alimentan los filtros. La serialización se centraliza ahora en `rom_system_summary()`, que los incluye (junto a `platform`/`release`/`fullname`).
- El servidor ya no puede cerrar la conexión sin enviar respuesta (`net::ERR_EMPTY_RESPONSE`): cualquier excepción no controlada en un handler (`GET`/`POST`/`DELETE`) ahora se responde como **500 en JSON** y el *traceback* se imprime en la consola, en lugar de dejar al navegador con una respuesta vacía. Además, un sistema problemático (permisos, fichero que desaparece…) ya no tumba la lista completa de BIOS faltantes.
- `/api/bios/missing` devolvía una respuesta vacía (`ERR_EMPTY_RESPONSE`) cuando un sistema tenía BIOS pero ninguna faltaba: el `append` había quedado fuera del bucle y leía variables no asignadas. Se extrajo la lógica a `collect_missing_bios()`, ahora cubierta por tests.
- El grid de sistemas del monitor de ROMs ya no se muestra en una sola columna: las cabeceras de tipo ocupan todo el ancho del grid y las tarjetas vuelven a fluir en varias columnas.
- Los chips de filtrado (tipo/fabricante) no filtraban nada porque `filterRomSystems` estaba definida dos veces y la segunda definición (sin filtros) sobrescribía la primera; se eliminó la duplicada y se restauraron `populateRomFilters`, `toggleRomTypeFilter` y `toggleRomMfrFilter`.

## [1.3] - 2026-10-17

### Añadido
- README completo en español: badges (licencia, Batocera, Python, tests, estrellas, último commit, tamaño), capturas reales, GIF de demostración, instalación paso a paso con opciones del instalador, API REST, FAQ, roadmap, contribuir y donaciones (PayPal).
- 13 capturas reales del panel (`docs/screenshots/`) y un GIF de presentación (`docs/media/demo.gif`, 680×458, 17 s).
- Sección "Actualizar a la última versión" en el README (con y sin git).
- `APP_VERSION = "1.3"` como única fuente de la versión: la portada la recibe del servidor (`{{app_version}}`), el banner la imprime desde ahí.
- Release v1.3 publicada en GitHub con tarball adjunto (`batocera_web.tar.gz`).

### Cambiado
- `install.sh` ahora es ejecutable (`./install.sh` funciona directamente).
- La consola deja de imprimir cada petición correcta (2xx/3xx); solo registra errores (≥400) y excepciones.
- Los comandos de instalación/actualización del README apuntan al tarball de la release (`releases/latest/download/...`).
- Contador de tests actualizado a 281.

### Corregido
- El panel de Configuración mostraba el puerto de *otro* proceso Python en escucha (5357, típicamente wsdd) en vez del del manager (5000). `get_process_status()` leía «el primer python» de `ss -tlnp`; ahora lee el puerto de `/proc/<pid>/cmdline` (`--port N`) con fallback al socket en LISTEN del propio PID.
- Máscara del usuario de RetroAchievements en las capturas (y de la IP local).

## [1.2] - 2026-06-17

### Añadido
- Gestor de sistemas personalizados: crear, editar y borrar sistemas con formulario completo, vista previa del XML y registro de lo que se escribe en disco.
- Panel de control en vivo: CPU, GPU, RAM, disco, red y estado/PID de EmulationStation (leídos de `/proc` y `/sys`), con refresco automático.
- Juego al azar con carátula, ficha y descripción; estadísticas de juego y ranking de más jugados.
- Integración con RetroAchievements (perfil, récords personales, ajustes).
- Monitor de ROMs y BIOS: inventario por sistema y detección de BIOS faltantes, con subida manual, descarga automática y lista de omisiones.
- Scraper multi-fuente: ScreenScraper.fr, TheGamesDB e IGDB (Twitch), con imágenes guardadas como EmulationStation espera.
- Temas y assets: temas instalados, tema activo, estructura de assets y subida de logos.
- Arranque automático vía `custom.sh` (bloque marcado) con aviso de modo manual.
- Instrucciones integradas en la web.
- API REST propia (sistemas, ROMs, BIOS, scraper, RetroAchievements, servicio, ES).
- `install.sh` interactivo (Python, Pillow opcional, ficheros, arranque automático).

### Cambiado
- Rediseño "Aurora Glass": tokens de color, glassmorphism, sidebar con iconos, layout a 2 columnas.
- Sidebar reagrupado con iconos SVG y estado activo acentuado.
- Contraste de la paleta oscura ajustado a WCAG AA.

### Corregido
- Sanitización de rutas y seguridad (path traversal, quoting de comandos, XSS, XXE, lectura de body).
- Scraper de ScreenScraper reparado (JSON malformado, progreso real por ROM).
- Reinicio manual de EmulationStation y flag de cambios pendientes.
- Detección de la ruta de `configgen` sin fijar la versión de Python.
- Persistencia en disco de los skips de BIOS faltantes.
- Filtro de directorios de medios y `_info.txt` en los listados de ROMs.

### Pruebas
- 281 tests con `pytest` (backend stdlib + ayudantes de UI extraídos por regex).

[1.0] - 2026-06-17

### Añadido
- Primera versión: servidor HTTP puro (stdlib), sin dependencias, gestor de sistemas personalizados, dashboard básico, monitor de ROMs/BIOS, scraper, temas y arranque automático.
- Licencia MIT.

[Unreleased]: https://github.com/Thundertruck4K/batocera-web-manager-react/compare/v1.5...HEAD
[1.5]: https://github.com/Thundertruck4K/batocera-web-manager-react/releases/tag/v1.5
[1.4]: https://github.com/Thundertruck4K/batocera-web-manager-react/releases/tag/v1.4
[1.3]: https://github.com/Thundertruck4K/batocera-web-manager-react/releases/tag/v1.3

> Las versiones anteriores a v1.3 no están etiquetadas en Git; se referencian por
> su commit inicial (`44effde` para v1.2, `589bfc7` para el README v1.2).
