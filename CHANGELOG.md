# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el versionado sigue [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Añadido
- **Backend unificado con la versión React**: el `app.py` de este repositorio pasa a ser **idéntico**
  al del repositorio hermano (`batocera-web-manager-react`), salvo la constante `APP_REPO` (el repo del
  que se leen las releases). Los dos proyectos comparten backend y API sin riesgo de divergencia: un
  comprobador automático verifica que los dos ficheros siguen siendo iguales.
- **Proceso de desarrollo documentado**: el README y AGENTS.md explican ahora la relación entre las dos
  instancias, los puertos en uso (`:5000` Python / `:5001` React / `:5173` Vite), los comandos
  habituales y la política de ramas: nunca `push` directo a `master`, siempre rama + pull request.
- **El proyecto se independiza**: la versión con interfaz **React + Tailwind CSS** pasa a su propio
  repositorio, `Thundertruck4K/batocera-web-manager-react`. Este repositorio se queda con la versión
  Python pura (interfaz de un solo fichero, sin build ni dependencias), con el mismo backend y la
  misma API. Se añade una nota en el README y en AGENTS.md que enlaza las dos versiones.
- **Tarjetas del panel rediseñadas al estilo «mono»**: cada tarjeta del manager pasa a un contenedor
  redondeado de 24 px con su propio color de acento, cabecera en mayúsculas con el icono en píldora y
  un «stage» interior de 14 px donde viven los gráficos. Los visualizadores (velocímetro de 240°,
  sparkline de área, donut de reparto y barras redondeadas) están escritos en CSS/JS puro: ni React
  ni Recharts ni ningún paso de build, el proyecto sigue sin dependencias.
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
- Contador de tests del README actualizado a 438.
- El tacho con aguja (CPU/GPU/RAM) y el tanque de líquido (disco) los sustituyen el velocímetro y el
  donut con paleta; el gráfico de actividad pasa a ser un área monótona con degradado. Se elimina el
  código y el CSS de los gráficos antiguos.

### Corregido
- `install.sh` se quedaba con finales **CRLF** en el working copy de Windows (por `core.autocrlf`), y
  bash no encontraba el intérprete al desplegar en Linux. Se añade `.gitattributes` con
  `install.sh text eol=lf` y el fichero se renormaliza a LF.
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

[Unreleased]: https://github.com/Thundertruck4K/batocera-web-manager/compare/v1.4...HEAD
[1.4]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.4
[1.3]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.3

> Las versiones anteriores a v1.3 no están etiquetadas en Git; se referencian por
> su commit inicial (`44effde` para v1.2, `589bfc7` para el README v1.2).
