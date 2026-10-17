# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el versionado sigue [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

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

[Unreleased]: https://github.com/Thundertruck4K/batocera-web-manager/compare/v1.3...HEAD
[1.3]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.3

> Las versiones anteriores a v1.3 no están etiquetadas en Git; se referencian por
> su commit inicial (`44effde` para v1.2, `589bfc7` para el README v1.2).
