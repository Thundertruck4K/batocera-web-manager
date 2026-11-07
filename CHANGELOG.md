# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el versionado sigue [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Añadido
- **El plan de renombrado va en segundo plano y con barra de progreso.** En un sistema grande
  (miles de juegos, o ISOs de 4 GB que hay que hashear) el cálculo del plan tardaba tanto que la
  página se quedaba en silencio y parecía congelada: el usuario cerraba la ventana y perdía el
  trabajo. Ahora:
  - **El cálculo va en un hilo aparte** (el paquete nuevo `romtools/jobs.py`): el endpoint devuelve
    el identificador del trabajo y el frontend va preguntando por su estado. Los endpoints
    antiguos (`GET /api/tools/rename/plan` y `POST /api/tools/rename/apply`) siguen funcionando.
  - **La barra se mueve por bytes leídos**, no sólo por ficheros: hashear una ISO es un solo
    fichero y se lleva el 90 % del tiempo, así que con un contador de ficheros la barra se quedaba
    parada justo en lo que más tarda.
  - **Endpoints nuevos**: `GET /api/tools/rename/plan/start`, `POST /api/tools/rename/apply/start`
    y `GET /api/tools/rename/job?id=…` (el estado del trabajo: cuántos ficheros lleva, cuál está
    mirando y qué porcentaje).
  - El **renombrado** (que también recalcula el plan) va en segundo plano, y el `gamelist.xml` y
    la media se actualizan con el mismo mecanismo.
- **La sección de conversiones se rehace de arriba abajo.** La radiografía de la consola real
  (2.378 ficheros) decía que el 64 % de la biblioteca se detectaba como «formato desconocido» y que
  sólo el 3DO tenía DAT: el mapa de sistemas usaba los slugs de libretro (`gc`, `dc`, `segacd`…) en
  vez de los de Batocera (`gamecube`, `dreamcast`, `megacd`…), y la detección miraba la extensión
  antes que la cabecera. Ahora:
  - **La detección decide por la cabecera**: CHD, WBFS, WIA, RVZ, PBP, XDVDF, GCZ, CISO, CSO, NSP,
    XCI, 3DS, 3DO, N64, SNES, Mega Drive y el ISO 9660 (que además dice **de qué consola es**:
    GameCube, Wii, PS1 o PS2).
  - **Conversiones nuevas**: Nintendo 64 entre sus tres byte orders (`.n64`, `.z64`, `.v64`), Super
    Nintendo entre `.sfc`, `.smc` y `.fig`, ZIP a carpeta, ISO a CSO, CISO y GCZ (y de vuelta), y CHD
    con el `chdman` de MAME, que ya viene en Batocera.
  - **El mapa de DAT** se rehizo con los 122 slugs reales de la consola y se añadieron dos fuentes
    más (la carpeta `dat/` de `libretro-database` y el rebuild diario). Para los sistemas que no están
    en el mapa, el DAT se busca **por nombre** contra el catálogo real, y la interfaz dice **cómo se
    resolvió** cada uno (`mapa` o `nombre`) y con qué confianza.
  - **La conversión en lote** (endpoint nuevo `POST /api/tools/formats/batch`): convierte todos los
    ficheros de un sistema que admitan el destino elegido, con filtro opcional por formato de
    origen, y devuelve un resumen (convertidos, fallidos y el motivo de cada fallo).
- **`THIRD_PARTY.md`**: las referencias de terceros (Game-Format-Converter, OpenROM, Dolphin,
  Romulus Manager), el `chdman` de MAME y de dónde salen los DAT, con la licencia de cada uno.
- **Sección **Herramientas** en el menú lateral, con dos páginas nuevas: **Formatos** y **Renombrado**.
  El backend que las sostiene es el paquete nuevo `romtools/` (Python de la librería estándar, sin
  dependencias), importado de forma protegida: si no está en la consola, la API responde con un error
  claro y el resto de la app sigue funcionando.
- **Formatos**: lista los ficheros de un sistema con el formato detectado (BIN+CUE, ISO, PBP, XISO,
  GCM, CHD, WBFS, WIA, RVZ, MDF/CCD, G64/NDD, 3DO, WAD, NSP, ZIP, IPS…) y deja **convertir**
  (BIN/CUE ↔ ISO, PBP ↔ BIN/CUE, XDVDF → ISO, GCM → ISO, CHD v5 → BIN), **comprimir** y
  **descomprimir** en ZIP, y **parchear** con IPS (y deshacer el parche). El resultado se escribe
  siempre al lado del original, nunca encima.
- **Renombrado**: ordena la biblioteca con la convención de los sets (título, región e idioma, disco,
  serial, marcas de volcado), al estilo de Romulus Manager. El **nombre destino es el del DAT**, que
  es la convención de facto; la composición propia sólo se usa cuando no hay DAT.
  - Los **DAT** (Redump y No-Intro) se descargan del espejo de `libretro-database` y se cachean en
    `/userdata/system/batocera_manager_dats/`. Son metadatos: la lista de juegos con sus hashes, sin
    ninguna ROM. El instalador puede bajarlos de entrada (nuevo paso 7, con `BM_DATS=auto|all|skip`).
  - El **emparejamiento** va de más fiable a menos: nombre y tamaño (no toca el disco), hash (md5,
    sha1 y crc32 en una sola pasada), serial del disco y, como último recurso, similitud de títulos.
    El hash lleva un **presupuesto de 512 MB por tanda**: con bibliotecas de 40 GB se avisa y se sigue.
  - El **plan se enseña entero** antes de tocar nada (nombre actual, propuesto, método y confianza),
    renombra también el CUE y la M3U, y cada tanda deja journal con un botón de **deshacer**.
  - **Los discos de Wii se identifican por el código de juego**: el volcado (WBFS, WIA) y
    la ISO llevan dentro el código de juego (`REXP`), el código de fabricante y el hash MD5 del
    propio juego. Como el DAT de Wii guarda ese código en el serial (`RVL-REXP-EUR`), el cruce
    es exacto: no hay que hashear los 620 MB del volcado ni fiarse del nombre del fichero. El
    plan enseña los dos lados del cruce (el MD5 del juego y el crc32/md5/sha1 del DAT).
  - **Los juegos que viven en una carpeta**: en Wii cada juego es una carpeta
    (`Juego [REXP01]/REXP01.wbfs`). El plan los ve, renombra la carpeta con el nombre del DAT
    (conservando el sufijo con el código del disco) y actualiza la ruta del `gamelist.xml`.
  - **Renombrar regenera el `gamelist.xml`**: al aplicar, el motor actualiza el `<path>` de cada
    ficha, renombra la media que acompaña al juego (`images/`, `videos/`, `manuals/`, `downloads/`)
    y repunta las etiquetas (`image`, `video`, `marquee`, `thumbnail`…), conservando el resto de
    metadatos. Sin esto, el `gamelist.xml` se quedaba con los nombres viejos y EmulationStation
    mostraba la biblioteca descuadrada. El `gamelist.xml` original se guarda en el journal, así que
    **deshacer** lo restaura íntegro, y al terminar se recarga EmulationStation (los tiene en
    memoria).
- **El botón *Reparar* ya sirve de algo**: cuando el contenido de una BIOS no está en la propia
  consola, el manager ofrece las dos vías que quedan: **buscarlo en Google** o **subir el archivo**.
  Antes el botón sólo reparaba lo que ya estaba en la SD, así que en una consola nueva no tenía
  ninguna utilidad.
  - **El hash no decide el estado**: Batocera tampoco es rígido con el hash de las BIOS (las de
    triforce o hikaru lanzan los juegos con el hash que traía la tarjeta). La comprobación es de
    **presencia y estructura**: que el fichero esté donde el catálogo lo espera y que el ZIP lleve
    dentro los ficheros que exige. El md5 se calcula y se enseña como dato, pero ya no hay estado
    «hash distinto»: una BIOS presente con otro hash es una BIOS correcta.
  - **Enlace directo a Google**: cada BIOS y cada sistema llevan su enlace de búsqueda (el nombre
    exacto del fichero entrecomillado, y las BIOS del sistema), calculados por el backend
    (`busqueda_fichero_url()` y `busqueda_sistema_url()`).
  - **Subida manual**: el fichero que sube el usuario se coloca en la ruta exacta que pide el
    catálogo y se comprueba que queda bien. Si es un ZIP, hay que subir el ZIP completo.
  - La reparación local va siempre primero y es instantánea: si el contenido ya está en la consola
    (dentro de otro ZIP o en otra carpeta), se reúne y se coloca sin tocar la red.
  - **Legal**: la app no descarga nada por su cuenta ni aloja colecciones de BIOS. Son ficheros con
    copyright y la decisión es del usuario.
- `POST /api/bios/repair` reparaba con `source`: `"local"`, `"archive"` o un candidato. Ahora el
  parámetro desaparece: sólo hay una fuente, la propia consola.
- **Sección de BIOS en la SPA** (la de *ROMs y BIOS*, que deja de estar marcada como *Pronto*): una
  tarjeta por sistema con el icono temático, el nombre del catálogo de Batocera, el estado y la
  cobertura; el orden es por criticidad (lo que impide jugar primero), por nombre o por cobertura, y
  se filtra por texto y por estado (con problemas, reparables, completos).
  - El **modal de detalle** enseña cada BIOS con su estado, el md5 que publica Batocera, el md5 que
    hay en el disco, el tamaño y la ruta de destino, y ofrece: reparar, subirla a mano, copiar el
    hash y omitirla. La reparación en lote deja el sistema entero arreglado de una vez.
  - Los avisos de éxito y de error usan el mismo sistema de notificaciones que el resto de la app.
- **El catálogo oficial de BIOS es la fuente de verdad**: la lista de BIOS que exige Batocera cambia
  con la versión, así que ahora se lee de la propia consola:
  - `/usr/bin/batocera-systems` (el script oficial) es la fuente principal: trae el slug del sistema,
    su nombre legible, la ruta de cada BIOS, su md5 y **qué fichero tiene que ir dentro de cada ZIP**
    (el campo `zippedFile`).
  - `/usr/share/batocera/datainit/bios/readme.txt` es el respaldo (no trae slugs ni los miembros de
    los ZIP: se empareja con el catálogo embebido por conjunto de rutas).
  - El `BIOS_DB` embebido en `app.py` es el último recurso (instalaciones mínimas y desarrollo).
- **Los estados de cada BIOS**: `correcta`, `sin verificar`, `hash distinto`, `falta un fichero`,
  `reparable` (el contenido está dentro de otro ZIP o en otra carpeta), `ausente`, `omitida` e
  `ilegible`. Con ellos, las tarjetas se ordenan por criticidad y se sabe qué se puede arreglar sin
  salir de la consola.
- **Reparar una BIOS sin salir de la consola**: `POST /api/bios/repair` reúne en el ZIP de destino
  los ficheros que exige el catálogo (buscándolos dentro de otros ZIP de la propia SD) o mueve el
  fichero que ya estaba en otra carpeta. Siempre **verifica** el resultado contra el catálogo y, si
  tenía que sustituir algo, deja el original en `/userdata/bios/.quarantine/`. Si no encuentra el
  contenido, **no toca el destino**.
- `GET /api/bios/catalog` (catálogo + estado + resumen), `GET /api/bios/summary` (sólo el resumen) y
  `POST /api/bios/scan` (fuerza el escaneo del disco).
- **Los juegos que son una carpeta se escrapean por su nombre**: en algunos sistemas el juego no es
  un fichero sino una carpeta (ScummVM: `Myst.scummvm/`, DOSBox: `Alone in the Dark.pc/`, MUGEN:
  `kof94.pc/`). Es la convención de EmulationStation: si el nombre de la carpeta lleva una extensión
  del sistema, la carpeta **es** el juego, y el `gamelist.xml` guarda su ruta (`<path>./Myst.scummvm
  </path>`). Ahora el manager:
  - detecta las carpetas-juego leyendo las extensiones del sistema del `es_systems.cfg` (el del
    usuario si define ese sistema, el oficial si no) y también por el fichero marcador de ScummVM
    (`Myst.scummvm/myst.scummvm`), y las lista como ROMs (`is_game_folder`), no como carpetas;
  - las **escrapea por el nombre de la carpeta** (sin la extensión), que es el título del juego;
  - no intenta hashearlas (una carpeta no tiene hash) y guarda la ficha con la ruta de la carpeta.
- **Caché de los datos de RetroAchievements**: el resumen se guarda **en disco**, junto a los
  ajustes del manager (`/userdata/system/batocera_manager_ra_cache.json`), así que entrar en la
  sección *Logros* ya no llama a la API aunque el manager se haya reiniciado. Los datos se sirven
  durante 6 horas (`ra_cache_ttl` en los ajustes) y **entre dos descargas a la red hay siempre un
  intervalo mínimo de 60 s**, incluso cuando se pide un refresco forzado. La sección indica de dónde
  salen los datos («datos guardados · actualizados hace 2 h»).
- `GET /api/retroachievements/games?force=1` fuerza la descarga de datos frescos (si ha pasado el
  intervalo mínimo entre peticiones).
- El sistema `dos` queda mapeado en ScreenScraper (plataforma 135, *PC Dos*), que es donde están sus
  juegos.
- **El panel de control pide un juego al azar al cargar**: la tarjeta *Juego al azar* ya no se queda
  vacía a la espera de que se pulse «Girar»; muestra la carátula, el sistema y los metadatos del
  juego. El botón «Girar» sigue ahí para pedir otro.
- `GET /api/info` expone `disk_games_count` y `disk_systems_count`: los juegos y los sistemas que hay
  de verdad en el disco (no sólo los catalogados en el `gamelist.xml`).
- **Sección de Scraper en la SPA**: la sección *Scraper* deja de estar marcada como *Pronto*.
  - Los sistemas de la biblioteca se muestran en tarjetas con un **icono temático** (palanca para
    los arcade, mando para las consolas, pantalla para los portátiles, disco para las consolas de CD…),
    el nombre del sistema, una breve descripción y el **número de ROMs**. Los filtros acotan por
    texto, por tipo de equipo y por estado (con media, sin media, vacíos, con gamelist) y el orden
    es por nombre, por número de ROMs o por cobertura de carátulas.
  - Al abrir un sistema, la pantalla cambia con un **fundido de fusión** y sus ROMs se reparten en
    **media presente** y **media ausente**, con las carátulas que dejó el scraper. Se puede entrar en
    las subcarpetas con las migas de pan.
  - El **scraping va en modales flotantes**: uno para el sistema completo (con el progreso del
    trabajo por lotes en vivo) y otro para un juego suelto (búsqueda, descarga de la imagen y
    edición de metadatos). Los tres botones del pie son **Actualizar** (releer y verificar la
    configuración del servidor), **Editar** (las credenciales) y **Guardar** (validar, persistir y
    cerrar el modal, volviendo a la lista de sistemas).
  - Se pueden usar las **tres fuentes** —ScreenScraper, TheGamesDB e IGDB—: la que no tenga
    credenciales queda marcada y avisa de lo que falta.
  - **Las credenciales nunca se muestran**: la interfaz sólo sabe si hay alguna guardada (el backend
    devuelve los valores enmascarados y los indicadores `_set`), y al scrapear no se envía ninguna.
  - La tarjeta de cada sistema indica cuántos juegos tienen ya su imagen, contando las entradas
    `<image>` del `gamelist.xml` de los ROMs que siguen en la carpeta (nuevo campo `image_count` en
    `GET /api/rom-systems`, con caché de 60 s). Antes se contaba la carpeta `media/`, que
    EmulationStation no usa, y por eso salía siempre a 0.
  - **La carátula se ve en el modal de un juego**: se sirve por un proxy del backend
    (`GET /api/scraper/image`), porque ScreenScraper no entrega sus imágenes si la petición no
    llega con su referer. El proxy **cachea en memoria** (24 imágenes / 3 MB máximo) y la búsqueda
    la pide en segundo plano, así que la carátula aparece al instante en lugar de tardar más de diez
    segundos; mientras llega, el modal avisa con «Cargando carátula…».
  - **Las fuentes se eligen por orden de prioridad**: en el modal de un juego aparecen numeradas
    (1 ScreenScraper, 2 TheGamesDB, 3 IGDB) y se pueden activar o desactivar una a una. La búsqueda
    **prueba ScreenScraper primero** y, si esa fuente no tiene datos del juego, continúa con
    TheGamesDB e IGDB: gana el primer resultado y se indica de qué fuente salió y cuáles no
    tenían información. El scrape de un sistema completo tiene la misma cadena, con la opción de
    «usar las demás fuentes como respaldo».
  - **El botón de volver está siempre en pantalla**: pasa a la barra superior (que ahora admite
    contenido a la izquierda del título), así que no hay que subir hasta arriba para cambiar de
    sistema.
  - **Avisos en modal del scraping**: al guardar un juego, un modal confirma el éxito y se cierra
    solo a los pocos segundos; si algo falla, el modal se queda en pantalla con **el log del error**
    y un botón **Cerrar** para confirmarlo. El scrape de un sistema completo avisa igual cuando
    termina el trabajo por lotes.
  - **La tabla de ROMs se actualiza al guardar**: la vista se queda en el sistema y el juego pasa de
    *media ausente* a *media presente* sin recargar la página.
  - **Se puede editar el nombre de búsqueda**: cuando ninguna fuente encuentra el juego con el
    nombre del archivo, el modal lo pone en un campo editable para acotar la búsqueda (por ejemplo,
    «007: Agent Under Fire»). El ROM no se renombra: los datos se siguen guardando en el fichero
    original.
  - **Un juego que ya tiene ficha no se vuelve a scrapear**: al pincharlo en la lista se abre su
    información local (la del `gamelist.xml`) con su carátula de la biblioteca, sin gastar una sola
    petición a las fuentes. Se puede editar a mano o forzar el scraping con «Escapear». El scrape de
    un sistema completo ya trabaja sólo sobre los ROMs que no tienen imagen.
- **Dashboard de logros en la SPA**: la sección *Logros* deja de estar marcada como *Pronto* y muestra
  los juegos de RetroAchievements en los que más has desbloqueado, en tarjetas con **la carátula que
  dejó el scraper** en tu biblioteca, el porcentaje de completitud y el estado de cada juego
  (dominado, completado, batido, en progreso). Se puede ordenar por logros obtenidos, por porcentaje
  o por logros totales.
  - Si no hay usuario o Web API Key configurados, la sección avisa y lleva a *Configuración*; si la
    integración está apagada, avisa de eso también.
  - Cada juego se empareja con un ROM de la biblioteca local por título normalizado (se ignoran las
    etiquetas de región y disco, como «(USA)», y los acentos), prefiriendo el que tiene carátula. Si
    no hay coincidencia, la tarjeta usa el icono de RetroAchievements y el panel indica cuántos
    juegos han quedado emparejados.
  - Endpoint nuevo `GET /api/retroachievements/games`, que reutiliza la caché de la API de
    RA (10 min en memoria en aquella versión; ahora 6 h y también en disco). El rango de juegos sube
    de 20 a 100; la interfaz clásica sigue mostrando los 5 primeros.

### Cambiado
- **La BIOS que falta se busca en Google, no en GitHub**: el enlace ya no es una búsqueda de código
  en repositorios, sino una búsqueda en `google.com` con el nombre del fichero **entrecomillado**
  (`"neogeo.zip"`), que es una coincidencia exacta y además mira en toda la web: foros, espejos de
  colecciones y páginas de emulación. El enlace del sistema busca el nombre entrecomillado con la
  palabra `bios` (`"Coleco Adam" bios`). El flujo no cambia en lo demás: la app sigue sin alojar ni
  descargar nada; sólo enlaza y el usuario sube el fichero.
  - Los nombres de las funciones del backend pasan de `github_bios_search_url()` y
    `github_sistema_url()` a `busqueda_fichero_url()` y `busqueda_sistema_url()`, y el campo del
    catálogo de `github` a `busqueda`.

### Corregido
- **El renombrado no se podía aplicar desde la interfaz**: el modal de confirmación estaba escrito,
  pero ningún botón llamaba a `setConfirmar(true)`, así que se veía el plan y no había forma de
  aplicarlo. Ahora, con el plan calculado, aparece el botón **«Aplicar N»**, que abre el modal con
  la lista de los cambios (y, si hay coincidencias dudosas, una segunda opción para incluirlas).
- **El botón de conversión se equivocaba de destino**: comparaba etiquetas de texto («¿es "Convertir a
  BIN/CUE"?»), así que con más de un destino posible la acción iba al formato equivocado o no
  aparecía. Ahora cada fichero devuelve sus conversiones como identificadores (`iso`, `bin-cue`,
  `pbp`, `chd`, `cso`, `gcz`, `ciso`, `zip`, `extraer`, `n64`, `z64`, `v64`, `sfc`, `smc`, `fig`…), y
  la interfaz los compara por identificador.
- **El renombrado sólo funcionaba en el 3DO**: el mapa de DAT usaba los slugs de libretro y sólo
  coincidían tres con los de Batocera. Con el mapa rehecho con los slugs reales (validados contra
  `es_systems.cfg` y contra las carpetas que existen) el renombrado tiene DAT para 122 sistemas.
- **La magia de Nintendo 64 tenía dos de las tres cambiadas**: `37 80 40 12` (la byte swapped) se
  tomaba por little endian y `80 37 12 40` (la little endian) por big endian, así que el cambio de
  byte order salía mal. Ahora cada byte order se reconoce por su magia, no por el nombre del fichero
  (hay volcados que se llaman `.v64` y están en big endian).
- **El ISO que salía de un BIN/CUE tenía el directorio raíz vacío**: el juego estaba dentro, pero el
  sistema de ficheros no lo tenía, así que un emulador de PlayStation no veía nada. Ahora, al volver
  de un BIN/CUE, si los datos traen su propio descriptor de volumen el ISO se reconstruye byte a byte
  (y sale idéntico al original); si no, se monta el esqueleto de ISO 9660 de toda la vida.
- **El ISO se cargaba entero en memoria**: con un DVD de 4,7 GB la consola se quedaban sin RAM. Ahora
  se escribe sector a sector.
- **El emparejamiento por nombre daba falsos positivos**: «Wolfenstein - Enemy Territory» se
  emparejaba con «Wolfenstein 3D». Ahora el DAT tiene que **cubrir todas** las palabras del sistema y
  la confianza tiene que ser de 0,7 o más.
- **El índice del DAT se guardaba enorme**: cada hash repetía el juego entero
  (con su lista de roms y sus hashes), así que el índice del DAT de Super
  Nintendo pesaba **2,1 GB** y llenaba la tarjeta de la consola. Ahora los mapas
  guardan la posición del juego y la lista va una sola vez: el mismo índice
  ocupa unos pocos megas.
- **El estado de los DAT se comía la memoria de la consola**: para saber de
  dónde salía cada DAT y cuántos juegos tenía, se leía el índice entero, que
  lleva la lista de juegos dentro. Con el índice de un DAT grande, el manager
  llegó a usar 5 GB de RAM y lo mató el sistema (el `oom-kill` está en el
  `dmesg` de la consola). Ahora los metadatos van en su propio fichero
  (`.meta.json`) y el índice sólo se lee cuando hace falta renombrar.
- **La lista de ficheros de un sistema incluía los que no son juegos**: `_info.txt`, `gamelist.xml`,
  guardadas (`.srm`, `.psv`, `.state`), capturas, música y notas. Ahora sólo se listan los juegos.
- **Las conversiones nunca se comían el original**: si ya existía el fichero de salida, se numeraba
  («Juego (1).chd») en vez de sobrescribir.
- **El README arrastraba endpoints que ya no existen**: la tabla de la API REST seguía incluyendo
  `/api/bios/sources`, `/api/bios/sources/search` y `/api/bios/install` (los de archive.org, quitados
  al dejar la búsqueda en repositorios). También se ha puesto al día el contador de tests (692).
- **El modal de BIOS no se actualizaba al subir una BIOS a mano**: el índice del disco se cachea
  5 minutos, así que el catálogo seguía viendo la SD como estaba y había que cerrar el modal y
  abrirlo de nuevo para ver los cambios. Ahora, al subir (o reparar o descargar) una BIOS se
  invalida el índice, y el modal guarda el slug del sistema en vez de una copia: se actualiza solo.
- **El catálogo de BIOS cambiaba solo de un momento a otro**: cuando la SD fallaba al leer
  `/usr/bin/batocera-systems`, el manager caía al `readme.txt` (372 rutas frente a las 362 del
  script) y todos los estados cambiaban de golpe (297 → 307 BIOS «en su sitio», con el total del
  catálogo bailando entre 362 y 372). Ahora el script se lee con reintentos y se guarda el último
  catálogo bueno en disco, que es el respaldo.
- **El botón *Reparar* era un botón inerte**: si el sistema no tenía ninguna BIOS reparable, el
  botón de lote aparecía deshabilitado. Ahora sólo se muestra cuando hay algo que reparar.
- **Una BIOS con otro hash ya no se marca como incorrecta**: el estado se decide por presencia y
  estructura, no por el md5. Batocera no es rígido con el hash de las BIOS —las de triforce o hikaru
  lanzan los juegos con el hash que traía la tarjeta—, así que un md5 distinto marcaba como
  «incorrecta» una BIOS que funcionaba. En la consola de desarrollo, 3 BIOS pasaron de «hash
  distinto» a correctas y las 290 correctas son ahora 293.
- **Las BIOS se verificaban por el hash equivocado**: el manager comparaba el md5 del **ZIP** con el
  que da el catálogo, pero Batocera exige que el ZIP **lleve dentro** unos ficheros concretos con su
  md5 (el campo `zippedFile` del catálogo oficial). Como el md5 de un ZIP es el de ese ZIP concreto,
  83 BIOS que estaban **bien** se marcaban como incorrectas: en la consola de desarrollo, 204
  «correctas» y 86 «con hash distinto» eran en realidad 287 correctas y 3 con hash distinto. Ahora se
  abre el ZIP y se comprueba lo que lleva dentro, que es lo que mira Batocera.
- **La lista de ROMs ya no enseña ficheros que no son juegos**: en cada carpeta de sistemas hay un
  `_info.txt` que documenta los formatos del sistema, además del `gamelist.xml` y de los guardados de
  estado (`Lagoon (Europe).srm`, `azumanga.dat`, `Steam_Big_Picture.sh.keys`). Salían en la sección
  «Otros ficheros» y se podían escrapear. Ahora el criterio es el de EmulationStation: un fichero es
  un juego si su extensión es una de las del sistema (`es_systems.cfg`) —más la lista global de
  extensiones de ROM para no perder nada—, y lo demás no se lista.
  - La declaración del sistema manda sobre la lista de extensiones que no son juego: los `.dat` de
    **naomi**, atomiswave y systemsp son el juego, no un guardado, así que siguen apareciendo. Un caso
    real: el `azumanga.dat` de naomi son 80 MB de datos del juego y se listing como tal.
  - Los ficheros de configuración de los emuladores quedan fuera siempre, aunque el sistema los
    declare: `citron_config.xci_config`, `eden_config.xci_config`… no son juegos.
- **La tarjeta *Sistemas* del panel contaba los sistemas equivocados**: enseñaba `systems_count`, los
  sistemas **personalizados** que gestiona el manager (4), en vez de los sistemas con juegos de la
  biblioteca. Ahora el número es el de sistemas con juegos y los personalizados van en el texto de
  apoyo.
- **La tarjeta *Juegos* del panel no cuadtaba con el disco**: enseñaba el total del `gamelist.xml`
  (los juegos catalogados) en vez de los juegos que hay de verdad en la SD. Ahora cuenta los ficheros
  que son juego y las carpetas de juegos.
- **Las listas desplegables ya siguen el esquema de colores**: los `<select>` nativos pintan su
  propio fondo (blanco con letras pálidas) e ignoran el `bg-transparent` del tema. Ahora usan
  `appearance-none`, el fondo de la app y su propia flecha, y la lista de opciones se pinta con el
  `color-scheme` del tema (afecta a *Tipo de equipo* e *Identidad del sistema* en «Añadir sistema»
  y al *Tema* en «ROMs y extensiones»).
- **Los interruptores son simétricos**: la bola no tenía `left`, así que el navegador la colocaba
  centrada y, al activarse, se salía del carril. Ahora va anclada a la izquierda y el recorrido es
  simétrico (2 px de margen a cada lado). Además su color sale de los tokens del tema, porque la
  bola blanca se perdía en el tema claro.
- **La búsqueda por nombre de ScreenScraper se perdía**: cuando el sistema no está mapeado en
  ScreenScraper, la consulta sin platform id tarda más de un minuto (busca en todas las plataformas) y
  el timeout de 20 s la cortaba, así que el juego no aparecía nunca. Ahora la búsqueda por nombre tiene
  75 s de margen, y el sistema `dos` queda mapeado en la plataforma 135 (*PC Dos*), que es donde
  están sus juegos.
- **La búsqueda por nombre devolvía el juego equivocado**: es una búsqueda difusa y su primer
  resultado no siempre es el buscado («Doom» devolvía «Hugo III: Jungle of Doom»). Ahora, si alguno
  de los candidatos tiene exactamente el título buscado, ese gana.
- **El juego ya no se quedaba en «media ausente» después de escrapearlo**: al guardar, los
  metadatos y la imagen se escribían en la entrada **equivocada** del `gamelist.xml` (el mismo juego
  puede estar catalogado en la raíz del sistema y en una subcarpeta, y se casa con la primera que
  coincide por nombre). Ahora la coincidencia exacta con la ruta relativa va primero, así que la
  entrada de la ROM real es la que se actualiza. Además, al listar una subcarpeta sin gamelist
  propio se lee el de la raíz del sistema, que es donde están las rutas de sus juegos.
- **Las URLs de las carátulas ya no viajan con las credenciales**: ScreenScraper devuelve las URLs
  de sus medios con la contraseña y la credencial de desarrollador incrustadas, y la SPA las recibía
  tal cual (con la contraseña dentro, en la respuesta JSON). Ahora se mandan limpias y es el
  servidor el que las firma al descargarlas; la interfaz clásica, que muestra la imagen
  directamente, las pide explícitamente.
- **El respaldo de TheGamesDB encuentra los juegos**: la búsqueda era demasiado estricta con el nombre
  del ROM (buscaba «007 Agent Under Fire» y no encontraba el «007: Agent Under Fire» de
  TheGamesDB), así que la cadena de fuentes se quedaba sin respuesta aunque el juego estuviera
  catalogado. Ahora prueba variantes del nombre y, si hace falta, busca sin filtro de plataforma y
  se queda con el juego de la plataforma del sistema.
- **El instalador limpia el bundle anterior**: los assets del bundle llevan hash en el nombre, así que
  los de la versión anterior se quedaban ocupando sitio en la SD sin usarse. Ahora el bundle se copia
  a un temporal y se sustituye la carpeta entera, de modo que no quedan restos (y sin borrar el bundle
  de origen cuando el instalador se ejecuta dentro de la propia carpeta de destino).

## [1.5] — 2026-11-03

### Cambiado
- **La versión del manager pasa a 1.5.** `APP_VERSION` (en `app.py`) es la única fuente de la
  versión y ahora coincide con la release publicada.
- **README reescrito con el funcionamiento actual.** La sección de características separa lo que
  ya está en la SPA de lo que sigue sólo en la interfaz clásica, el diagrama de arquitectura
  incluye el bundle de React, la tabla de secciones de «Uso» lista las reales del menú y se
  explica **por qué se unificaron los dos repositorios**.
- **El proyecto vuelve a vivir en un solo repositorio.** Durante un tiempo se mantuvo en dos
  repositorios independientes con el mismo backend: la interfaz React + Tailwind CSS y la variante
  «Python puro» (interfaz de un solo fichero). La variante se retira: su repositorio
  `Thundertruck4K/batocera-web-manager` se elimina y todo el trabajo sigue aquí, en
  `Thundertruck4K/batocera-web-manager-react` (que después recuperó ese mismo nombre corto; ver
  [Unreleased]).
  - La **interfaz clásica** (`templates/index.html`) no desaparece: se queda como **respaldo** y el
    backend la sirve automáticamente cuando el bundle compilado no está en la consola.
  - La documentación (README, AGENTS, CHANGELOG y MEMORY) describe ya un único proyecto, sin
    referencias al repositorio hermano ni a la sincronización de dos `app.py`.
  - `APP_REPO` no cambia: sigue apuntando a este repositorio.
- **El repositorio se renombra a `batocera-web-manager`.** Este repositorio, que hasta ahora se
  llamaba `batocera-web-manager-react`, recupera el nombre corto: es el que ya se compartía en la
  comunidad y el que no debe convertirse en un 404 para quien ya lo tiene enlazado. GitHub guarda
  una redirección desde el nombre antiguo, así que los enlaces compartidos antes del renombrado
  siguen funcionando.
  - La constante `APP_REPO` del `app.py` pasa a apuntar al nombre nuevo (de ahí se leen las
    releases para la comprobación de actualizaciones), igual que la URL de clone del `install.sh`,
    las instrucciones de la interfaz clásica de respaldo y los tests que las verifican.
  - El historial no se toca: el `master` de la variante «Python puro» —el repositorio que se
    eliminó al unificar— sigue siendo un ancestro directo de este.

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
- **Capturas nuevas de la interfaz actual** (`docs/screenshots/`): panel de control, Sistemas
  Personalizados, Añadir sistema, Depuración y Configuración, tomadas sobre una instalación real
  de Batocera 43.1. Las 13 capturas anteriores, de la interfaz clásica, se sustituyen por estas.
- **Banner del proyecto** (`docs/media/banner.png`): sustituye al logo como cabecera del README.
  Resume lo que hace el manager (gestión de sistemas, panel en vivo, depuración con SSE, ROMs y
  BIOS, scraper y arranque automático) con las etiquetas de la pila técnica.

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

[Unreleased]: https://github.com/Thundertruck4K/batocera-web-manager/compare/v1.5...HEAD
[1.5]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.5
[1.4]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.4
[1.3]: https://github.com/Thundertruck4K/batocera-web-manager/releases/tag/v1.3

> Las versiones anteriores a v1.3 no están etiquetadas en Git; se referencian por
> su commit inicial (`44effde` para v1.2, `589bfc7` para el README v1.2).
