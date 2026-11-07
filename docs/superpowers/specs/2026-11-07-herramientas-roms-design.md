# Estrategia: herramientas de ROMs (formatos y renombrado)

**Fecha:** 2026-11-07
**Estado:** implementada
**Alcance:** backend (`app.py` + paquete `romtools/`), SPA (`frontend/src/`), instalador (`install.sh`), consola Batocera real

---

## 1. Punto de partida

El menú lateral tenía seis entradas y ninguna servía para trabajar con los ficheros de la
biblioteca. Dos tareas se repitían a mano:

1. **Convertir y preparar imágenes** (BIN+CUE ↔ ISO, PBP, XISO, CHD…) para que el emulador las
   entendiera.
2. **Renombrar la biblioteca** con la convención de los sets, que es lo que hacen Romulus Manager y
   las collections de GoodTools.

La petición concrete: un grupo nuevo **Herramientas** en el sidebar, con **Formatos** dentro, que
permita convertir, parchear, comprimir y gestionar ROMs de PS1, PS2, Xbox, GameCube, Wii, Saturn,
Sega CD y más; un sistema de renombrado que respete las convenciones de set; y un flujo en
`install.sh` que baje los DAT de cada sistema que maneja Batocera.

### 1.1 Referencias y qué se toma de cada una

| Referencia | Qué se toma | Qué **no** se toma |
|---|---|---|
| [`M5Devs/OpenROM`](https://github.com/M5Devs/OpenROM) | La idea de detectar el formato por la cabecera y puntuar variantes de un mismo juego | **Nada de su código**: es Dart/Flutter y GPL v3. Se cita como inspiración |
| [Romulus Manager](https://www.romulusgames.com/) | El criterio de renombrado: el nombre del DAT manda | Su interfaz y su código |
| Redump / No-Intro | Los DAT: lista de juegos con el nombre oficial y los hashes | Las ROM, que son con copyright |

`OpenROM` no aloja DAT: consume Redump y No-Intro en línea. Eso obliga a resolver el punto 2.

---

## 2. De dónde salen los DAT

Es la parte con más decisiones, porque las fuentes que se ajustaron al principio no
sirvieron.

### 2.1 Lo que se descartó y por qué

| Fuente | Motivo |
|---|---|
| `libretro/libretro-dats` | **No existe** (404). El nombre correcto es `libretro/libretro-database` |
| `good-db.com` | **No resuelve DNS** desde el entorno |
| `redump.org` | Sólo por HTTP y no accesible desde este entorno |
| No-Intro | Exige un POST de términos y hay que scrapear la ruta |
| `hugo19941994/auto-datfile-generator` | Rebuild diario: `redump.zip` (27 MB) y `no-intro.zip` (106 MB). Se queda como **alternativa** |

### 2.2 La fuente elegida

El **espejo de `libretro-database`** en GitHub, con los DAT sueltos (no el ZIP):

```
https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/redump/<Nombre>.dat
https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/<Nombre>.dat
```

Dos formatos conviven y **los dos hay que leer**:

- **Logiqx** (XML): es lo que usa Redump.
- **clrmamepro** (texto, *no* es XML): es lo que usa No-Intro y también algunas entradas de
  libretro. Por eso el parser propio, que recorre los bloques contando paréntesis (los valores van
  entre comillas y pueden contener paréntesis).

Los DAT traen `size`, `crc`, `md5`, `sha1` y `serial`.

### 2.3 Correcciones a la convención (que había que tener claras)

- **`!` es el volcado bueno**: «verificado». El volcado **malo** es `[b]`, no `[!]`.
- `[f]` (arreglado) y `[t]` (traducido) suman; `[h]` (truncado) y `[p]` (pirata) restan.
- **Romulus no renombra**: copia el `ROMNAME` del DAT, validando por CRC32 y tamaño. El serial va
  en el campo `serial` del DAT (libretro), no en el nombre del fichero.
- La etiqueta `<machine>` ya no existe.

**Consecuencia de diseño:** el nombre destino es **el del DAT**. La composición propia
(`naming.compose_name`) es el respaldo para cuando no hay DAT.

---

## 3. Arquitectura

El backend ya era un fichero de 7.344 líneas. Meter el motor de DAT, identificación, nombres y
formatos dentro de `app.py` lo habría hecho inmanejable, así que se crea el **paquete `romtools/`**
en la raíz, con Python de la librería estándar como el resto del proyecto.

```
app.py            HTTP, dashboard, scraper, BIOS, y el enrutador /api/tools/*
romtools/
  dats.py         fuentes, descarga, caché, parseo (clrmamepro + Logiqx) e índice
  identify.py     hashes, firmas de disco, similitud de títulos
  naming.py       gramática de los nombres de set
  sets.py         puntuación de variantes y elección de variante
  rename.py       plan, aplicación, journal y deshacer
  formats.py      detección, conversión, compresión y parches
  __main__.py     CLI: python3 -m romtools dats --install
```

La importación es **protegida** (`HAS_ROMTOOLS`): si el paquete no está en la consola, la API de
herramientas responde con un error claro y **el resto de la app no se cae**.

### 3.1 Los 57 sistemas

`dats.SYSTEM_DAT` mapea los sistemas de Batocera al nombre exacto del DAT, y se verificó contra los
índices reales del espejo.

---

## 4. Identificación: cómo se empareja un fichero con su juego

De más fiable a menos. Cada paso da su confianza y su método, y el plan lo enseña.

| Método | Confianza | Coste |
|---|---|---|
| Nombre + tamaño | 0,95 | Ninguno (no toca el disco) |
| Hash (md5/sha1/crc32) | 1,00 | Lee el fichero entero |
| Serial del disco | 0,90 | Lee la cabecera |
| Título (similitud) | 0,00–1,00 | Ninguno |

**El hash tiene presupuesto.** Hashear 42 GB es eterno: el plan lleva un presupuesto de **512 MB por
tanda**. Lo que no cabe, se empareja por nombre o por título y se avisa («no se ha verificado por
hash: la biblioteca es muy grande»).

**Las firmas de disco** están verificadas con sus offsets reales:

| Plataforma | Firma | Offset |
|---|---|---|
| GameCube | `0xC2339F3D` | `0x1C` |
| Wii | `0x5D1C9EA3` | `0x18` |
| Saturn | `SEGA SEGASATURN` | cabecera |
| Sega CD | `SEGADISCSYSTEM` | cabecera |
| Xbox | `MICROSOFT*XBOX*MEDIA` | cabecera |
| PS1/PS2 | `PLAYSTATION` | `0x8000–0x8800` |

---

## 5. El renombrado

### 5.1 La gramática

Título, región e idioma, número de disco, serial entre corchetes y marcas de volcado:

```
Ridge Racer (USA) (Track 1) [SLUS-00237]
Grandia (Europe) (Disc 1) [SLES-02248]
Zelda - Ocarina of Time (USA) [!].z64
```

### 5.2 Elegir la variante: el fallo que se corrigió

La primera implementación elegía la «mejor variante» con `sets.pick_best`, que ordena por región,
revisión y marcas. **Eso compara juegos distintos**, y en la consola real falló:

```
Ballz - The Director's Cut (1995) (Panasonic) (US) [!].iso
  → proponía: D's Diner - The Director's Cut (Japan) (Disc A).iso
```

La causa: `Ballz - The Director's Cut (World) (En,Ja)` y `D's Diner - The Director's Cut (Japan)
(Disc A)` comparten subtítulo; el segundo tiene mejor región (`japan` +10 frente a `world` +5) y
ganaba.

**La corrección** es que **la identidad de un juego es su título y su disco, no su región**
(`sets.game_key`): el título y el disco identifican un juego; la región es una variante *dentro* de
él. Los candidatos se agrupan por juego y sólo se comparan los del mismo juego; entre ellos decide la
puntuación de variante.

Con eso:

- «Ballz» y «D's Diner» son juegos distintos → nunca se mezclan.
- «Ballz (World)» y «Ballz (USA)» son el mismo juego → gana la región que se prefiera.
- «… (Disc A)» y «… (Disc B)» son juegos distintos → el disco del fichero decide.

La comparación por títulos ignora las etiquetas entre paréntesis, y la similitud mezcla secuencia
de caracteres y coincidencia de palabras (`SequenceMatcher` + Jaccard + palabras clave).

### 5.3 Nada a ciegas

El plan se enseña entero antes de tocar nada. Al aplicar se renombran también el CUE, la M3U y el
resto de acompañantes. Cada tanda deja un journal en `/userdata/system/batocera_manager_renames.json`
y hay un botón de **deshacer**.

---

## 6. Formatos

Detección por extensión y por cabecera: BIN+CUE, ISO, PBP, XISO, GCM, GCISO, CHD, WBFS, WIA, RVZ,
MDF/CCD/IMG, G64/NDD, 3DO, WAD, NSP, ZIP, IPS/BPS.

Conversiones: BIN/CUE ↔ ISO (con un ISO 9660 válido reescrito: PVD, tablas y directorio), PBP ↔
BIN/CUE, XDVDF → ISO, GCM → ISO, CHD v5 (zlib) → BIN con los offsets de MAME. Compresión ZIP y
descompresión. Parches IPS, con aplicar y revertir (`.bak`).

---

## 7. La SPA

El sidebar admite **grupos** (`NAV_GROUPS`): cada grupo lleva título y sus entradas. **Herramientas**
agrupa:

- **Formatos** (`/herramientas/formatos`): selector de sistema, lista de ficheros con el formato
  detectado, y un modal con convertir, comprimir y parchear.
- **Renombrado** (`/herramientas/renombrado`): estado del DAT (y descarga si falta), el plan antes /
  después con método y confianza, aplicar con confirmación y deshacer.

Las dos páginas siguen el lenguaje de tarjetas del resto de la app.

---

## 8. El instalador

`install.sh` copia el paquete `romtools/` y añade el **paso 7 · DAT de los sistemas**, con
`BM_DATS=auto|all|skip`: en `auto` pregunta (s = sí, n = no), en `all` baja todos, en `skip` no
pregunta. La descarga es `python3 -m romtools dats --install`.

---

## 9. Legal

La app **no aloja ni descarga ROMs**. Los DAT son metadatos públicos (una lista de juegos con sus
hashes). Las conversiones, compresiones y parches se hacen sobre los ficheros que ya están en la SD
del usuario, y el renombrado sólo cambia nombres.

---

## 10. Verificación

- **729 tests** en verde (692 previos + 37 nuevos de `romtools`).
- `tsc -b --noEmit` limpio y el bundle compilado.
- En la consola real (Batocera 43.1, `192.168.1.94`): 57 sistemas con DAT, DAT de 3DO descargado
  (684 juegos, 0,9 s) y plan de 97 ROMs en 3,1 s. Antes, sin presupuesto de hash, la misma operación
  hasheaba 42 GB y se colgaba.
- El falso positivo de «Ballz» reproducido con el DAT real de 3DO y corregido.
