# Diseño: sección de Scraper en la SPA

**Fecha:** 2026-11-05
**Estado:** aprobado (diseño delegado por el usuario)

## Objetivo

Una sección **Scraper** en la SPA con la misma API que ya usa Batocera por
debajo (ScreenScraper, TheGamesDB e IGDB), **sin mostrar las credenciales en el
dashboard**. Con varios filtros, con modales flotantes para escrapear sistemas
completos, con las tarjetas del set de colores de la app y un icono temático
por sistema; al abrir un sistema, otra pantalla con efecto fusión fade que
reparte sus ROMs en «media presente» y «media ausente»; y en el modal, los
botones Actualizar, Guardar y Editar para confirmar su validez: una vez
guardado y validado, el modal desaparece y se vuelve a la lista principal.

## Decisiones

1. **La API ya existía; no se toca el contrato de scraping.** Se reutilizan
   `/api/scraper/config`, `/api/scraper/search`, `/api/scraper/download`,
   `/api/scraper/scrape-system`, `/api/scraper/batch` y
   `/api/scraper/save-config`. La sección es una cliente más de esa API, igual
   que la interfaz clásica.
2. **Las credenciales no se muestran ni viajan.** El backend ya devuelve los
   valores enmascarados junto con los indicadores `*_set`; la interfaz sólo
   usa esos indicadores («Configurado» / «Sin configurar») y al scrapear no
   envía ninguna credencial. Si la fuente elegida no tiene, el modal **no se
   cierra**: avisa y deja editar.
3. **Un solo endpoint nuevo, y es de lectura:** `GET /api/rom-systems` añade
   `image_count` (juegos con imagen). El resto de la sección se apoya en
   `/api/rom-folder/<sistema>`, que ya existía.
4. **El scraping de un sistema va por lotes** (`/api/scraper/batch`), no por el
   endpoint síncrono: el trabajo corre en un hilo del backend y la interfaz
   muestra el progreso en vivo, así que el manager no se bloquea.
5. **Icono temático por sistema**, con tres niveles: una tabla por nombre
   exacto (arcade, consolas de disco, FDS, PC Engine…), palabras clave sobre
   nombre + tipo + fabricante, y como último recurso el icono del tipo
   (`Arcade` → palanca, `Consolas` → mando, `Portátiles` → pantalla,
   `Ordenadores` → terminal).
6. **El tipo se normaliza en la interfaz:** el catálogo de Batocera deja
   algunos sistemas con la cadena literal `"None"`, que se muestra como
   «Otros».
7. **Dos modales, un mismo patrón de pie** (Actualizar / Editar / Guardar):
   uno para el sistema completo y otro para un juego suelto.
8. **Sin dependencias nuevas** y **sin tocar `templates/index.html`**.

## Contrato de la API

Lo que ya existía y se reutiliza:

| Endpoint | Uso en la sección |
|---|---|
| `GET /api/scraper/config` | Fuente activa, opciones guardadas y estado de las credenciales (enmascaradas) |
| `POST /api/scraper/search` | Buscar un ROM en la fuente elegida |
| `POST /api/scraper/download` | Descargar imagen y metadatos de un ROM |
| `POST /api/scraper/batch` | Escapear uno o varios sistemas en segundo plano |
| `GET /api/scraper/batch/<id>` | Progreso del trabajo (sondeo cada 1,5 s) |
| `POST /api/scraper/save-config` | Guardar fuente, región, idioma, tipo de imagen y credenciales |
| `GET /api/rom-folder/<sistema>` | Listado de ROMs con `has_image` (de aquí sale el reparto de media) |
| `GET /api/rom-image/<sistema>/<fichero>` | Carátula de un ROM |

Lo que cambia:

```json
// GET /api/rom-systems → un objeto por sistema
{
  "name": "gamecube", "rom_count": 574, "media_count": 0, "image_count": 99,
  "size_human": "779.8 GB", "is_empty": false, "has_gamelist": true,
  "has_bios": false, "bios_count": 0, "has_logo": false,
  "type": "Consolas", "manufacturer": "Nintendo", "platform": "gamecube",
  "release": "2001", "fullname": "GameCube"
}
```

`image_count` cuenta los juegos con `<image>` en su `gamelist.xml`, **sólo los
ROMs que siguen en la carpeta**. Antes la única cifra era `media_count`, que
cuenta los ficheros de la carpeta `media/` —que EmulationStation no usa— y por
eso salía siempre a 0, de modo que la tarjeta no cuadraba con el reparto de la
pantalla de ROMs.

## Backend (`app.py`)

- `count_systems_with_images(settings, systems)` → `{sistema: juegos con
  imagen}`. Lee el `<image>` de cada `gamelist.xml` y lo cruza con los ROMs
  presentes, con la misma regla de emparejamiento que `list_rom_folder`
  (nombre del fichero o del juego). Caché de 60 s, invalidada junto con
  `invalidate_rom_cache()`.
- `GET /api/rom-systems` rellena `image_count` antes de resumir cada sistema.

Coste medido en la consola real: 55 ms para los 257 sistemas (42 con
`gamelist.xml`).

## Frontend (`frontend/src`)

- `pages/Scraper.tsx`: la sección. Dos vistas (lista de sistemas y pantalla de
  ROMs) con la fusión fade entre ellas (`AnimatePresence` con `mode="wait"`,
  0,28 s, easing `[0.16, 1, 0.3, 1]`). Filtros: texto libre, tipo de equipo y
  estado (con ROMs, todos, con media, sin media, vacíos, con gamelist); orden
  por nombre, número de ROMs, menos ROMs, más media o cobertura. Por defecto
  se muestran sólo los sistemas con ROMs, y se indica «X de Y sistemas».
- `components/scraper/ScraperSystemCard.tsx`: la tarjeta. Icono temático,
  nombre, descripción (fabricante y año), número de ROMs, carátulas y
  cobertura. El botón de la esquina abre el modal de scrape del sistema.
- `components/scraper/RomFolderView.tsx`: los ROMs del sistema, con las
  migas de pan y las dos secciones (media presente / media ausente).
- `components/scraper/ScrapeSystemModal.tsx`: fuente, opciones, estado de las
  credenciales y progreso del trabajo por lotes.
- `components/scraper/ScrapeRomModal.tsx`: búsqueda, resultado, edición de
  metadatos y descarga.
- `lib/systemIcons.ts`: el mapa sistema → icono y la normalización del tipo.
- `lib/nav.ts`: la sección deja de estar marcada como *Pronto*.

## Tests

- `tests/test_scraper_folder.py`: el listado de ROMs y el campo `has_image`
  (reparto de media), las subcarpetas y el rechazo de rutas fuera del sistema.
- `tests/test_scraper_image_count.py`: el conteo de imágenes (sólo ROMs
  presentes, sólo ROMs de verdad, caché) y su exposición en el resumen.
- `tests/test_scraper_ui.py`: la sección existe en la SPA (ruta, menú sin
  *Pronto*, filtros, tarjetas, fundido, reparto de media), los tres botones
  de los modales y **que las credenciales ni se pintan ni se envían**.

## Fuera de alcance

- Cambiar la API de scraping: se reutiliza tal cual.
- Descarga de vídeos (el backend ya tiene el tipo, pero la sección no lo
  ofrece).
- Editar la lista de sistemas desde el modal.
- Escapear un sistema sin credenciales: el modal avisa y deja configurarlas.

---

# Segunda tanda: pulido (2026-11-05)

## Qué pedía el usuario

1. En el modal de scraping **sólo aparecía el texto y no la imagen**.
2. **No aparecían opciones de scraping por servicios** (qué fuente usar).
3. El flujo debía ser **ScreenScraper primero** y, si el primero no tiene datos,
   **TheGamesDB e IGDB como respaldo**.
4. El **botón de volver tenía que estar siempre en pantalla**, sin obligar a
   subir hasta arriba.

## Decisiones

9. **La cadena de fuentes va en el backend**, no en el navegador:
   `scrape_search_cascade()` prueba las fuentes en el orden pedido y gana el
   primer resultado. Así el modal de ROM y el scrape de sistema comparten
   exactamente el mismo criterio. `POST /api/scraper/search` acepta `sources`
   (lista, por orden de prioridad) y devuelve `source` (la que acertó) y
   `tried` (las que se probaron). Sin `sources` el contrato no cambia: la
   interfaz clásica se comporta como antes.
10. **Las fuentes son activables desde el modal**, con chips numerados que
    muestran el orden de prioridad y el estado (Activa / Inactiva / faltan
    credenciales). El scrape de sistema añade la opción «usar las demás
    fuentes como respaldo» (`fallback_sources`), activada por defecto en la
    SPA y no en la interfaz clásica.
11. **La carátula se sirve por un proxy del backend**
    (`GET /api/scraper/image?url=…`): ScreenScraper no entrega sus imágenes si
    la petición no llega con su referer. El proxy pone el referer, cachea la
    imagen en memoria (24 imágenes / 3 MB máximo) y sólo admite los hosts de
    las fuentes de scraping, para no ser un proxy abierto.
12. **La descarga se pide en segundo plano** al terminar la búsqueda
    (`warm_scraper_image`): cuando el modal abre la carátula, ya suele estar
    en la caché. Medido en la consola real: 7,4 s la primera vez y 0,00 s la
    segunda.
13. **El modal avisa mientras la imagen llega** (spinner + «Cargando
    carátula…»), en vez de dejar un hueco en blanco.
14. **El botón de volver vive en la barra superior** (`Topbar` acepta una
    prop `leading`), no en el contenido con scroll: así siempre está visible.
15. **Las URLs de medios no viajan con credenciales.** ScreenScraper las
    devuelve incrustadas (`devpassword`, `sspassword`…), así que al enviar el
    juego al navegador se quitan (`ss_media_public_url`) y el servidor las
    vuelve a poner al descargar (`ss_media_signed_url`). La interfaz clásica,
    que muestra la imagen directamente y puede estar usando credenciales sin
    guardar, lo pide explícitamente con `raw_media: true` en la búsqueda.
16. **La búsqueda en TheGamesDB tiene que ser tolerante.** Su API busca por
    título exacto: «007 Agent Under Fire» no encuentra el «007: Agent Under
    Fire» que hay catalogado. Se prueban variantes del nombre (sin el prefijo
    numérico, tras los dos puntos) y, si hace falta, se busca sin filtro de
    plataforma y se elige el juego de la plataforma del sistema. Sin esto, la
    cadena de fuentes se quedaba sin respuesta aunque el juego estuviera.
17. **El guardado tiene que dar con la entrada correcta del `gamelist.xml`.**
    El mismo juego puede estar catalogado en la raíz del sistema y en una
    subcarpeta: si se casa con la primera entrada que coincide por nombre, la
    ROM real se queda sin datos y su imagen no aparece en la tabla. La
    coincidencia exacta con la ruta relativa va primero; el nombre sólo es el
    plan B. Y al listar una subcarpeta sin gamelist propio se lee el de la
    raíz del sistema (allí están las rutas de sus juegos).
18. **Los avisos del scraping van en modal.** El éxito se muestra unos
    segundos y se cierra solo; el error se queda con el log y un botón de
    confirmación. Los avisos «verdes» de esquina (`Toast`) no sirven aquí:
    se leen de reojo y el error hay que poder leerlo con calma.
19. **Al guardar un juego la vista se queda en el sistema** (antes se volvía
    a la lista de sistemas): así se ve cómo el juego pasa de *media ausente* a
    *media presente* en la tabla. El botón «Volver» de la barra está siempre
    visible para salir.
20. **Si la búsqueda no encuentra el juego, se puede editar el nombre.** El
    nombre del archivo suele traer ruido («007 - Agent Under Fire (USA).iso»)
    y la fuente lo busca por título. El modal enseña un campo editable con el
    nombre actual («007: Agent Under Fire») y un botón «Buscar»; el backend
    ya cae a la búsqueda por nombre cuando el fichero no existe. El nombre
    editado sólo afecta a la búsqueda: los datos se siguen guardando en el
    fichero original. «Sin resultados» no se muestra como error, sino como
    invitación a afinar el nombre.
21. **Un juego que ya tiene ficha no se vuelve a scrapear.** Al pincharlo en
    la lista, el modal comprueba `has_image`: si ya está, **no se busca nada**
    (ni una petición a las fuentes) y se muestra su **información local** —la
    del `gamelist.xml`— con la **carátula de la biblioteca** (`/api/rom-image`).
    Se puede editar la ficha a mano («Guardar» sólo entonces actualiza el
    `gamelist.xml`, sin volver a descargar la imagen) o forzar el scraping con
    «Escapear». El scrape de un sistema completo ya trabaja sólo sobre los ROMs
    sin imagen (`only_missing`, activado por defecto).

## Contrato ampliado

```json
// POST /api/scraper/search  (con "sources": ["screenscraper","thegamesdb","igdb"])
{
  "ok": true,
  "source": "screenscraper",          // la fuente que encontró el juego
  "tried": ["screenscraper"],         // las que se probaron, en orden
  "image_url": "https://…/mediaJeu.php?systemeid=13&jeuid=4880&media=mixrbv1%28wor%29",
  "img_types": ["box-2D", "fanart", "mixrbv1", "mixrbv2", "ss", "wheel"],
  "game": { … }, "meta": { … }, "quota": { … }
}
```

`POST /api/scraper/batch` acepta `fallback_sources` para encadenar las
fuentes en el scrape de sistema.

## Tests

- `tests/test_scraper_sources.py`: credenciales por fuente, prioridad de
  ScreenScraper, cascada y salto de fuentes sin credenciales, el respaldo del
  scrape de sistema, el proxy (lista de hosts, caché, no cachear imágenes
  grandes) y **que las credenciales no lleguen al navegador**.
- `tests/test_scraper_ui.py`: los chips de fuentes, el aviso de carátula
  cargando, el botón de volver en la barra y la caché del proxy.
