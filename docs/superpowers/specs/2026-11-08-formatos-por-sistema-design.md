# Formatos por sistema: que la app ofrezca lo que cada sistema admite

**Fecha:** 2026-11-08
**Estado:** implementada
**Alcance:** backend (`app.py` + paquete `romtools/`), SPA (`frontend/src/`), documentación

---

## 1. Qué fallaba

El motor de formatos (`romtools/formats.py`) es un catálogo **por formato**: la entrada
`"iso": ("ISO 9660", ["bin-cue", "chd", "zip"])` dice que de una ISO se puede pasar a CHD o a ZIP.
Es cierto, pero no dice **para qué sistema** es esa ISO, y ahí está el fallo:

| Sistema | Conversión que se ofrecía | Qué pasa |
|---|---|---|
| PSP | comprimir en ZIP | el PSP no admite ZIP: el fichero no se ve |
| GameCube | convertir a CHD | el GameCube no admite CHD: el emulador no lo ve |
| GameCube | comprimir en ZIP | tampoco lo admite |
| PSP | sin CSO | el CSO es **el** formato recomendado del PSP y no se ofrecía |

La raíz de que no se ofreciera el CSO es la misma: el catálogo de `formats.py` no distingue el ISO de
un PSP del ISO de un GameCube, así que la lista de destinos era la misma para todos.

## 2. De dónde sale el mapa

Hay dos fuentes y **manda la de la consola**:

1. **`/usr/share/emulationstation/es_systems.cfg`** — el mismo fichero que usa EmulationStation, con
   253 sistemas y su etiqueta `<extension>`. Ya lo leía `app.py` (`get_system_extensions()`) para
   saber qué es un juego, así que no hace falta ninguna fuente nueva. También trae los sistemas
   personalizados del usuario, que es lo justo: un sistema nuevo definido a mano enseña sus formatos
   sin tocar el código.
2. **La wiki oficial de Batocera** (<https://wiki.batocera.org/systems>), leída sistema a sistema
   (252 páginas). De ahí sale lo que el `es_systems.cfg` no dice: **qué formato recomienda cada
   sistema** y qué avisos hay.

Lo que dice la wiki, y el mapa lo recoge:

| Sistema | Formato recomendado | Aviso |
|---|---|---|
| GameCube, Wii | **RVZ** | comprimido de Dolphin |
| PS2 | **CHD** (desde la v31; antes CSO) | |
| PSX | **CHD** | el PBP es de Sony y la wiki no lo recomienda; el formato depende del emulador (el PCSX-ReARMed no lee el ISO, el DuckStation sí) |
| PSP | **CSO** | pero el core libretro-ppsspp **no** lo lee |
| 3DO, Saturn, Dreamcast, Mega CD, Neo Geo CD, PC Engine CD | **CHD** | el Opera (3DO) no carga multidisco desde un `.m3u` |
| Cartuchos (SNES, NES, N64, GB, GBA, MD…) | **ZIP** | y el 7Z |

La tabla curada (`romtools/formatos_sistemas.py`, 80 sistemas) es el **respaldo**: sirve para cuando
el `es_systems.cfg` no dice nada del sistema, y para traer la nota y el formato preferido, que el
fichero de la consola no tiene.

## 3. El diseño

`formatos_sistemas.acciones_para(info, sistema, extensiones)` devuelve las conversiones de un
fichero **en su sistema**, con tres filtros:

1. **las que se pueden hacer desde el formato detectado** — el catálogo de `formats.py` sigue siendo
   la fuente de qué se puede convertir desde qué formato;
2. **las que el sistema admite** — si el destino no está en los formatos del sistema, **no se
   ofrece**: es trabajo que luego no sirve;
3. **las compresiones que el sistema admite** — ZIP y 7Z no dependen del formato del fichero sino del
   sistema: si el sistema admite `.zip`, se ofrece para cualquier ROM.

Cada acción sale con cuatro campos nuevos:

| Campo | Qué significa |
|---|---|
| `admite` | el sistema admite el formato de destino |
| `disponible` | la utilidad que hace falta está en la consola |
| `falta` | el nombre de la utilidad que falta |
| `motivo` | el texto para el usuario |

`app.py` calcula las acciones con `tools_acciones()`, que lee las extensiones del sistema con
`get_system_extensions()` (el `es_systems.cfg` de la consola) y las pasa al módulo. El endpoint
nuevo `GET /api/tools/formats/sistemas` devuelve, para cada sistema de la biblioteca, sus formatos
admitidos, su preferido, su nota y sus compresiones, más el inventario de utilidades con si están
disponibles ahora mismo.

## 4. La compresión es una propiedad del sistema

Es el cambio de fondo: antes la compresión estaba atada al formato (`"zip"` salía de la lista de
destinos del catálogo) y ahora sale del sistema. En una SNES el ZIP ahorra mucho espacio y se
ofrece; en un PSP, donde no se lee, no aparece.

## 5. Las utilidades: las que hay y las que faltan

Comprobado en la consola real (Batocera 43.1, `x86_64`), en el *buildroot* de Batocera y en la base de
datos de `pacman`:

**Ya en la consola**: `chdman` (MAME, `/usr/bin/chdman`), `7z`/`7zr` (p7zip), `zip`/`unzip` (Info-ZIP),
`unrar`, `gzip`, `bzip2`, `zstd`, la libcdio (`iso-info`, `isosize`), VICE (con su `c1541`) y los
emuladores sirven para comprobar que el resultado arranca.

**Faltan**: el `rom-converto` (MIT, con binarios estáticos para Linux: el más completo de todos), el
`nodtool` (Apache-2.0), el `dolphin-tool`, el `wiitool`, el `ndstool`, el `3dstool`, el `xorriso`, el
`maxcso`, el `extract-xiso` y el `cdrdao`.

Dos conclusiones que se saben mirando y que cambian el texto de la interfaz:

- El **store de Batocera no sirve para esto**: su base de datos tiene 106 paquetes y son todos bezeles
  y temas. Ni el `chdman` ni el `7z` están ahí porque vienen de la imagen (Buildroot), no del
  repositorio.
- El **`dolphin-tool` no se puede instalar en Batocera**: el paquete de Dolphin está, pero no construye
  la herramienta de línea de comandos (`TOOLS=1` no está activado). La vía buena es el `rom-converto`.

Por eso el texto de «cómo instalarla» en la interfaz **no dice «instálalo desde Configuración >
Paquetes»**: eso sería mentira.

## 6. Lo que se implementa y lo que no

**Lo hace el manager** (Python de la librería estándar, sin nada externo): ISO ↔ BIN/CUE, ISO ↔ PBP,
ISO ↔ CSO/CISO/GCZ, XDVDF → ISO, GCM → ISO, **GDI/MDS/CCD → ISO**, N64 entre sus tres *byte orders*,
SNES entre `.sfc`/`.smc`/`.fig`, ZIP y los parches IPS.

**Lo hace una utilidad externa**: el CHD (con el `chdman`) y el 7Z (con el `7z`).

**Lo que falta y se avisa**: el RVZ (necesita el `rom-converto`, el `nodtool` o el `dolphin-tool`) y el
WBFS/WIA (el `wiitool` o el `rom-converto`). Esos botones salen **desactivados, en ámbar**, con el
motivo y el nombre de lo que falta. **Nunca se finge una conversión que no se ha hecho.**

## 7. Verificación

- La suite completa del backend en verde.
- El `es_systems.cfg` de la consola real leído y contrastado con el mapa (PSP: `chd cso iso pbp`;
  GameCube: `ciso dol elf gcm gcz iso json m3u rvz wbfs`; SNES: `7z bsx dx2 fig gd3 gd7 sfc smc swc
  zip`).
- El inventario de binarios de `/usr/bin` de la consola, para no prometer lo que no está.
- Comprobado en el navegador sobre la consola real: en el PSP sólo aparecen CSO, ISO, PBP y CHD; el
  ZIP y el 7Z desaparecen, y el panel de utilidades dice qué falta y por qué.
