# Motor de formatos y DAT: la segunda vuelta

**Fecha:** 2026-11-07
**Estado:** implementada
**Alcance:** backend (`app.py` + paquete `romtools/`), SPA (`frontend/src/`), consola Batocera real

---

## 1. Qué fallaba

La sección **Herramientas** de la entrega anterior funcionaba, pero sólo en una esquina de la biblioteca.
La radiografía de la consola real (`192.168.1.94`, Batocera 43.1) lo dejó claro:

| Medida | Antes |
|---|---|
| Ficheros de la biblioteca | 2.378 |
| Ficheros cuyo formato se reconocía | 855 (36 %) |
| Ficheros marcados como «desconocido» | 1.523 (64 %) |
| Sistemas con DAT descargado | 1 de 57 (sólo 3DO) |

Dos causas, y ninguna era de la interfaz:

1. **El mapa de DAT usaba los slugs de libretro** (`gc`, `dc`, `segacd`, `atari-800`, `pce`) y **no los
   de Batocera** (`gamecube`, `dreamcast`, `megacd`, `atari800`, `pcengine`). El renombrado, que se
  GUIDaba por el DAT, sólo podía funcionar en los tres sistemas que casaban por casualidad.
2. **La detección miraba la extensión primero** y las cabeceras después, con lo que un `.iso` de
   GameCube acababa siendo «ISO 9660» a secas y un `.v64` mal puesto se tomaba por lo que decía su
   nombre.

Además, el botón de conversión comparaba **etiquetas de texto** («¿la acción es "Convertir a BIN/CUE"?»),
así que desde que el catálogo tenía más de un destino, el botón se equivocaba de destino o no aparecía.

---

## 2. Game-Format-Converter: qué se toma y qué no

[`Mr-Shizzy/Game-Format-Converter`](https://github.com/Mr-Shizzy/Game-Format-Converter) es un gestor
gráfico de formatos de disco muy completo (CHD, CUE/BIN, GDI, PBP, CDI, VCD, MDS/MDF/NRG, CSO/ZSO,
RVZ/WIA/WBFS/GCZ/CISO, XISO, NSP/XCI…). Es la referencia que pedía la sección de conversión, pero **no
se puede integrar tal cual**:

- Está bajo **GPL-3.0-or-later** (y su código de GameCube/Wii es un port del DiscIO de Dolphin,
  GPL-2.0+). Este proyecto es MIT: copiarlo o vendorizarlo obligaría a cambiar la licencia.
- Es un **monolito de GUI**: un único `CHD_Manager.pyw` de 13.192 líneas con `import tkinter` a nivel de
  módulo. Su «CLI» también crea un `tk.Tk()`, así que **no se puede usar como librería sin pantalla**.

Lo que se toma son **las ideas**, que se reimplementan:

| Idea de upstream | Cómo queda aquí |
|---|---|
| Matriz de capacidades por fichero | `formats.CAPACIDADES` + `formats.FORMAT_CATALOGUE`: cada formato dice a qué se puede convertir, por **identificador** |
| Formato intermedio canónico | El ISO de 2.048 bytes por sector es el punto de paso de todo lo demás |
| Detección por cabecera con *stride* | `detect_format()` mira la firma antes que la extensión (CD, CHD, WBFS, PBP, GCZ, CISO, CSO, PFS0, XCIH, 3DO, N64, SNES…) |
| CD o DVD según el tamaño | 737.280.000 bytes: a partir de ahí, `createdvd` en vez de `createcd` |
| Numerar las colisiones de salida | `_salida_libre()`: «Juego.chd», «Juego (1).chd»… |
| Escritura temporal y renombrado atómico | Se escribe a un nombre libre y nunca se pisa el original |
| Verificar después de escribir | El resultado se comprueba (tamaño y cabecera) antes de darlo por bueno |

Y, como hace el propio upstream, el motor de CHD es **el `chdman` de MAME**, que ya está en la consola
(`/usr/bin/chdman`, 0.285): no se reimplementa un formato de disco entero.

---

## 3. El motor de conversiones

### 3.1 Los formatos que se reconocen ahora

Se decide por **cabecera**, y sólo después por extensión:

| Formato | Cómo se reconoce |
|---|---|
| CHD | `MComprHD` |
| WBFS | `WBFS` (y WUX/WUD) |
| WIA / RVZ | `WIA\0` / `RVZ\0` |
| PBP | `PBP\x01` |
| XDVDF (Xbox) | `MICROSOFT*XBOX*MEDIA` |
| GCZ / CISO / CSO | `\x01\xc0\x0b\xb1` / `CISO` / `CSO!` |
| NSP / XCI | `PFS0` / `XCIH` |
| 3DS | `NCSD` / `NCCH` |
| **N64** | la magia de 4 bytes: `40 12 37 80` (nativa), `80 37 12 40` (z64), `37 80 40 12` (v64) |
| 3DO | `\x01ZZZZZ\x01` o «CD-ROM» en `0x28` |
| SNES / Mega Drive | «aa bb» en `0x08` |
| ISO 9660 | `CD001` en el sector 16, y de qué consola es (GameCube `0x1C`, Wii `0x18`, PS2 `BOOT2`, PS1 `BOOT`) |

### 3.2 El fallo de la magia de Nintendo 64

La detección anterior tenía **dos de las tres magicas cambiadas**: `37 80 40 12` (que es la byte
swapped) se tomaba por little endian, y `80 37 12 40` (la little endian) por big endian. Con eso, el
cambio de byte order salía mal y el fichero de salida no lo reconocía ningún emulador.

Las conversiones son, con las magicas bien:

| De | A | Qué se hace |
|---|---|---|
| `.n64` ↔ `.z64` | | se invierte cada grupo de 4 bytes |
| `.n64` ↔ `.v64` | | se invierte cada grupo de 4 bytes **y** se intercambian los bytes de cada palabra de 16 bits |
| `.z64` ↔ `.v64` | | se intercambian los bytes de cada palabra de 16 bits |

### 3.3 Super Nintendo

Las tres variantes son la misma ROM con otra cabecera delante: la `.sfc` va pelada, la `.smc` lleva una
cabecera de copista de 512 bytes con el «aa bb» en el 8, y la `.fig` lleva su propia cabecera de 512
bytes (que empieza por «FIG »). Se convierte entre las tres conservando el cuerpo.

### 3.4 CSO, CISO y GCZ

El CSO y el CISO son el ISO troceado en bloques de 2.048 bytes, cada uno con delante cuatro bytes con
el tamaño de los datos. Si ese tamaño es el del bloque, los datos van **sin comprimir**; si no, van
comprimidos con deflate. El GCZ es un gzip con cuatro bytes de magia delante.

Se escribe **CSO versión 1** (deflate): la versión 2 usa LZ4 y la consola no tiene la librería.

### 3.5 El CHD, con `chdman`

Verificado en la consola real:

- `chdman createcd -i juego.iso -o juego.chd -c cdzl` **acepta un ISO suelto** y produce un CHD de CD.
- `chdman createdvd` hace lo mismo con un DVD (a partir de 737.280.000 bytes).
- `chdman extractcd` **no sirve** para esto: escribe un `.iso` que es sólo la tabla de contenidos y un
  `.bin` aparte. Se usa `chdman extractraw`, que saca las unidades del disco en crudo, y luego se quita
  la cabecera de cada sector para dejar un ISO de 2.048 bytes.

Las unidades son de 2.448 bytes en un CD (el sector con su corrección de errores) y de 2.048 en un
DVD; el propio `chdman info` lo dice y así se decide.

La ida y la vuelta se ha comprobado byte a byte: un ISO de 40 sectores vuelve **idéntico** desde su CHD.

### 3.6 El ISO se reconstruye fiel

El `build_iso` anterior montaba un ISO 9660 con el **directorio raíz vacío**: el juego estaba dentro,
pero el sistema de ficheros no lo tenía, así que un emulador de PlayStation no veía nada.

Ahora, al volver de un BIN/CUE, se comprueba si los datos **traen su propio descriptor de volumen**: si
lo traen, el ISO se reconstruye **byte a byte** (el resultado es el original). Si no lo traen (un BIN de
Redump, que no es un ISO con sistema de ficheros), se monta el esqueleto de ISO 9660 de toda la vida.

Además, el ISO se escribe **sector a sector**, sin cargarlo entero en memoria: un DVD de 4,7 GB no cabe
en la RAM de la consola.

---

## 4. El mapa de DAT

La clave del mapa es **el nombre de la carpeta en `/userdata/roms`**, que es lo que usa
`system_dir()` para abrir el sistema. Ni los slugs de libretro ni los del `batocera_systems.json` del
propio repo (que usa otra convención) sirven para eso.

- `SYSTEM_DAT` se rehízo con los **122 slugs reales** de la consola, validados contra
  `/etc/emulationstation/es_systems.cfg` y contra las carpetas que existen de verdad.
- Se añadieron tres fuentes: el espejo de `libretro-database` (Redump y No-Intro), su carpeta `dat/`
  (53 DAT sueltos por sistema) y el **rebuild diario** (60 DAT de Redump + 334 de No-Intro).
- Para los sistemas que **no** están en el mapa, se busca por nombre contra el catálogo real: gana el
  DAT que más palabras comparte, pero sólo si **cubre todas** las palabras del sistema y con una
  **confianza de 0,7 o más**. Antes se aceptaba con una sola palabra, y eso emparejaba
  «Wolfenstein - Enemy Territory» con «Wolfenstein 3D».
- `batocera_systems.json` **no se toca**: el alias se resuelve dentro de `romtools`.

El estado que ve la SPA dice, para cada sistema, **cómo** se resolvió su DAT (`mapa` o `nombre`), con
qué confianza, y si está descargado.

---

## 4 bis. El índice del DAT

El índice que se guarda junto al DAT (el `.json`) es lo que permite emparejar una ROM con su juego.
La primera versión guardaba **el juego entero** en cada entrada de los mapas: cada hash, cada serial y
cada nombre repetían la lista de roms del juego al que pertenecían. Con el DAT de Super Nintendo
(miles de juegos) el índice pesaba **2,1 GB**, y el instalador lo habría hecho por cada sistema con
DAT de la consola.

Ahora los mapas guardan **la posición del juego** y la lista de juegos va una sola vez:

```text
{
  "juegos": [ {name, description, region, serial, roms: [...]}, ... ],
  "by_hash":  {"sha1:1f0c…": 42, ...},
  "by_serial": {"SLUS-00001": 7, ...},
  "by_name":  {"juego usa": 42, ...},
  "by_name_size": {"juego usa": 1234, ...},
  "by_title": {"juego usa": [42, 43]}
}
```

Al leerlo, `load_index()` resuelve las posiciones y devuelve exactamente lo que esperaba el resto del
código (el juego entero). El mismo DAT de Super Nintendo deja de ocupar 2,1 GB y pasa a ocupar unos
pocos megas.

---

## 5. El contrato

### 5.1 Las acciones son identificadores

Cada fichero devuelve sus conversiones como una lista de objetos `{id, label, nota}`, donde `id` es una
clave de `CAPACIDADES` (`iso`, `bin-cue`, `pbp`, `chd`, `cso`, `gcz`, `ciso`, `zip`, `extraer`, `n64`,
`z64`, `v64`, `sfc`, `smc`, `fig`…). El frontend **compara identificadores**, nunca textos: por eso el
botón de «Convertir a BIN/CUE» ya no puede equivocarse de destino.

### 5.2 La conversión en lote

`POST /api/tools/formats/batch` convierte todos los ficheros de un sistema que **admitan** el destino
elegido, con filtro opcional por formato de origen. Cada fichero va con su resultado, y el lote acaba
con un resumen (cuántos convertidos, cuántos fallidos y por qué). El tope es de 50 ficheros por lote:
un CHD de un juego de GameCube tarda minutos, y un lote sin tope sería una conversión colgada.

### 5.3 Los ficheros que no son juegos

La lista de ficheros de un sistema ya no trae `_info.txt`, `gamelist.xml`, las guardadas (`.srm`,
`.psv`, `.state`), las capturas, la música ni las notas.

---

## 6. Verificación

- **751 tests** en verde (729 previos + 22 nuevos entre `romtools` y el contrato de la API).
- `tsc -b` limpio y el bundle compilado.
- En la consola real: `chdman` verificado con las tres rutas (`createcd`, `createdvd`, `extractraw`),
  con ida y vuelta de un ISO comprobada byte a byte, y el formato de los hunks y de las unidades
  leído del propio CHD generado.
