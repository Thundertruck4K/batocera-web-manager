# Utilidades de conversión de formatos

Esta es la lista de programas que hacen falta para convertir entre los formatos
de imagen que usa Batocera, con cuatro datos para cada uno: **para qué sirve**,
**qué licencia tiene**, **si la consola lo trae** y **cómo conseguirlo**.

Todo está comprobado: la consola real (Batocera 43.1, `x86_64`), el árbol de
*buildroot* de Batocera (`batocera-linux/buildroot`), el árbol de paquetes
(`batocera-linux/batocera.linux`, rama `batocera-43.1`), la base de datos de
`pacman` (`store.batocera.org`) y los repositorios de cada herramienta.

---

## 1. Las que ya trae la consola

| Utilidad | Para qué sirve | Licencia | En la consola |
|---|---|---|---|
| **chdman** (MAME) | Crear y extraer **CHD**, el formato comprimido de MAME: CHD ↔ ISO y CHD ↔ BIN/CUE | GPL-2.0-or-later | Sí: `/usr/bin/chdman` (el paquete `mame` se compila con `TOOLS=1`) |
| **7-Zip** (p7zip) | Comprimir y descomprimir en **7Z**, que squeeze más que el ZIP | LGPL-2.1-or-later, con la restricción de unRAR | Sí: `/usr/bin/7z`, `/usr/bin/7zr` |
| **Info-ZIP** | Comprimir y descomprimir en **ZIP** | BSD-like (Info-ZIP) | Sí: `/usr/bin/zip`, `/usr/bin/unzip` |
| **unrar** | Extraer `.rar` | unrar (no libre) | Sí |
| **GNU libcdio** | Leer ISO (`iso-info`, `isosize`, `iso-read`) | GPL / LGPL | Sí |
| **gzip / bzip2 / zstd / xz** | Comprimidos sueltos | varios | Sí |
| **VICE** | El `c1541`, para los disquetes del Commodore 64 | GPL-2.0-or-later | Sí (como emulador) |
| **Flycast, PPSSPP, DuckStation, PCSX2, Snes9x** | Emuladores: sirven para **comprobar** que el fichero convertido arranca | varios | Sí |

El `chdman` es el motor de CHD: es el mismo que usa MAME, así que los CHD que
hace el manager son idénticos a los que hace el propio MAME.

## 2. Las que hacen falta y no vienen

Tres de ellas **se instalan solas** la primera vez que se ejecuta el `install.sh`
(el [§6](#6-las-utilidades-que-instala-el-installsh) explica cómo). Las demás
hay que instalarlas a mano o no hacen falta.

| Utilidad | Para qué sirve | Licencia | Dónde está | Cómo se consigue |
|---|---|---|---|---|
| **rom-converto** | **La más completa**: CSO, ZSO, CHD, RVZ, WBFS, WIA, GCZ, XISO, NSP, XCI, 3DS (CIA/CCI/Z3DS), PBP, ZAR, PS3, NDS | MIT | [DevYukine/rom-converto](https://github.com/DevYukine/rom-converto) | **Se instala sola.** Publica binarios para Linux `x86_64`, `aarch64` y `armv7l`, con su `sha256` al lado |
| **nodtool** (nod) | Crea y extrae los comprimidos de Dolphin: **CISO, GCZ, RVZ, WBFS, WIA y GCM** | Apache-2.0 | [encounter/nod](https://github.com/encounter/nod) | **Se instala sola.** Publica binarios **estáticos** para `x86_64`, `aarch64` e `i686` |
| **3dstool** | Empaqueta el contenido de un **3DS** en un CIA | MIT | [dnasdw/3dstool](https://github.com/dnasdw/3dstool) | **Se instala sola**, pero sólo en consolas `x86_64` (es la única build que publica) |
| **dolphin-tool** | Crea y extrae **RVZ**, el comprimido de Dolphin (GameCube y Wii). La wiki de Batocera lo marca como **el recomendado** | GPL-2.0-or-later | [dolphin-emu/dolphin](https://github.com/dolphin-emu/dolphin) | No se puede con lo que hay: el `dolphin-emu` de Batocera es la interfaz gráfica y el paquete **no** construye la herramienta de línea de comandos (`-DENABLE_CLI_TOOL=OFF`) |
| **wiitool** | Crea y extrae **WBFS** y **WIA**, los formatos de Wii | GPL-3.0-or-later | [Dolphin: herramientas externas](https://github.com/dolphin-emu/dolphin/wiki/ExternalTools) | Hay que compilarlo: **no hay repositorio oficial ni release con binarios**. Su equivalente actual es el [Wiimms ISO Tools](https://wit.wiimm.de/), que publica tarballs para Linux pero sin suma de comprobación |
| **extract-xiso** | Extrae **XDVDF** (Xbox) a ISO | Sin licencia declarada en el repositorio | [XboxDev/extract-xiso](https://github.com/XboxDev/extract-xiso) | El manager ya lo hace en Python, sin él |
| **maxcso** | Comprime la ISO en **CSO, CSO2, ZSO o DAX** (PSP y PS2) | ISC | [unknownbrackets/maxcso](https://github.com/unknownbrackets/maxcso) | El manager ya lo hace en Python, sin él (y la release sólo trae el binario de Windows) |
| **ndstool** | Convierte una ROM de **Nintendo DS** a cartucho (NOA/GB) y saca su contenido | MIT o GPL-3.0-or-later (dual) | [devkitPro/ndstool](https://github.com/devkitPro/ndstool) | Hay que compilarlo: no hay release con binarios |
| **xorriso** | Monta y extrae **XDVDF** (Xbox) y otras imágenes de disco | GPL-3.0-or-later | [gnu.org/software/xorriso](https://www.gnu.org/software/xorriso/) | Sólo se publica el código fuente: hay que compilarlo |
| **cdrdao** | Convierte **NRG / MDS / CCD / IMG** a ISO | GPL-2.0 | [cdrdao/cdrdao](https://github.com/cdrdao/cdrdao) | El manager lo hace en Python, sin él (la release sólo trae el binario de Windows) |
| **makecue** | Escribe la hoja **CUE** que acompaña al BIN | GPL-2.0 | [makecue.org](https://www.makecue.org/) | El manager la escribe él mismo |
| **xdelta3** | ParchesIPS y BSD | Apache-2.0 | [jmacd/xdelta](https://github.com/jmacd/xdelta) | El manager ya los aplica en Python |

### Herramientas que **no** sirven aquí

| Herramienta | Por qué no |
|---|---|
| **GoodTools** | Sólo Windows: no hay build para Linux |
| **N64 Rom Center** | Sólo Windows |
| **GDIbuilder** | Windows y macOS; reconstruye el GDI, que es lo contrario de lo que hace falta |
| **amitools** (`xdftool`) | Es Python 2 y el Python de Batocera es 3 |
| **RVZSharp** | C#: necesita .NET, que no está en Batocera |
| **PSXPackager** | C#: necesita .NET |
| **`ecm`/`unecm` de Batocera** | El paquete `ecm` de Batocera es *extra-cmake-modules* de KDE, **no** la herramienta de compresión de imágenes |

## 3. Proyectos que ya agrupan todo esto

| Proyecto | Licencia | Linux | Veredicto |
|---|---|---|---|
| **[rom-converto](https://github.com/DevYukine/rom-converto)** | MIT | Binarios para `linux-x64`, `linux-arm64` y `linux-arm7` | **El mejor candidato**: cubre casi todos los formatos, en un binario sin dependencias de ejecución, con licencia MIT (compatible con este proyecto) y con su `sha256` publicado |
| **[OpenROM](https://github.com/M5Devs/OpenROM)** | GPL-3.0 | CLI headless (`openrom-core`) | Es un **orquestador**, no un implementador: delega en `chdman`, `maxcso`, `nodtool`, `ecm` y `xdelta3`. Adoptarlo es implementar cada parte |
| **[Game-Format-Converter](https://github.com/Mr-Shizzy/Game-Format-Converter)** | GPL-3.0 | CLI `chdm` (el autor marca Linux como experimental) | Trae **tkinter**, así que no sirve como librería en un servidor |
| **[compressatorium](https://github.com/pacnpal/compressatorium)** | — | Docker | Sirve de referencia del catálogo de herramientas |

## 4. Cómo se instala en Batocera

Batocera es **Buildroot**: la imagen se compila entera, así que las utilidades
del sistema (el `chdman`, el `7z`, el `zip`) ya vienen dentro y no hay nada que
instalar.

- El **store de Batocera** (`batocera-store`, o *Configuración → Paquetes* en
  EmulationStation) **no sirve para esto**: su base de datos tiene 106 paquetes
  y son todos bezeles y temas. Ni el `chdman` ni el `7z` aparecen en ella
  porque vienen de la imagen, no del repositorio.
- Lo que sí está en el *buildroot* (`p7zip`, `unrar`, `libcdio`) se puede
  instalar con `pacman -S <paquete>` si el repositorio lo publica.
- Lo que no está en ninguna parte (el `dolphin-tool`, el `wiitool`, el
  `ndstool`, el `xorriso`) hay que instalarlo **a mano**: copiar
  el binario a `/usr/bin`, darle permisos de ejecución y, si se quiere que
  sobreviva a las actualizaciones, añadir un paquete al *buildroot* de Batocera.
- El caso fácil es el de las que **publican binario**: el `rom-converto`, el
  `nodtool` y el `3dstool`. Esas las instala el propio `install.sh` la primera
  vez, con su `sha256` comprobado (el [§6](#6-las-utilidades-que-instala-el-installsh)
  explica el mecanismo y el apartado 7 la receta manual, por si hay que
  hacerlo a mano).

## 5. Qué hace el manager y qué no

El manager **no finge**: si la utilidad que hace falta no está en la consola, la
conversión aparece en la interfaz **desactivada**, con el nombre de lo que
falta y el motivo. Nunca se da por hecha una conversión que no se ha hecho.

Las conversiones que **hace el propio manager**, en Python de la librería
estándar y sin depender de nada externo:

| Conversión | Notas |
|---|---|
| ISO ↔ BIN/CUE | Escribe el CUE y el BIN al lado del original |
| ISO ↔ PBP | Formato de PlayStation |
| ISO ↔ **CSO** (PSP) y **CISO** | Compresión con `zlib` de la librería estándar |
| ISO ↔ **GCZ** (GameCube) | |
| XDVDF → ISO | Xbox |
| GCM → ISO | GameCube |
| **GDI / MDS / CCD** → ISO | Dreamcast, Alcohol 120% y CloneCD, leyendo el descriptor y la imagen |
| Nintendo 64 entre `.n64`, `.z64` y `.v64` | Los tres *byte orders* |
| Super Nintendo entre `.sfc`, `.smc` y `.fig` | Con y sin cabecera |
| ZIP | Con la biblioteca estándar (`zipfile`) |
| Parches IPS | Y deshacerlos |

Las que dependen de un binario externo: **CHD** (el `chdman`) y **7Z** (el
`7z`). Las que dependen de una utilidad que la consola no trae: **RVZ**,
**WBFS** y **WIA** (con el `rom-converto`, el `nodtool`, el `dolphin-tool` o el
`wiitool`).

Con el **rom-converto** instalado, el manager convierte de verdad a **RVZ**
(el formato que recomienda la wiki de Batocera para GameCube y Wii) y saca
el **WBFS** de un RVZ de Wii. Lo que el rom-converto **no** sabe hacer, el
manager no lo ofrece: no crea WBFS desde una ISO (sólo desde un RVZ) ni
genera WIA (sólo la lee).

## 6. Las utilidades que instala el `install.sh`

Tres utilidades externas pueden bajarse solas, con binario publicado y suma de
comprobación. El `install.sh` las deja listas **la primera vez que se ejecuta**,
así que no hay que buscar nada a mano.

| Utilidad | Release | Asset | Arquitecturas | `sha256` |
|---|---|---|---|---|
| **rom-converto** | `v0.24.0` | `rom-converto-cli-linux-x64` | `x86_64` | `0d4abd56cfec477ff447f68b656d45ca48f670f464363bca2d895b1eee2c356d` |
| | | `rom-converto-cli-linux-arm64` | `aarch64` | `990286bc3367342b0e04ab6dd0d28d8e95c3133ac2b4c5d6440a119e541b0b43` |
| | | `rom-converto-cli-linux-arm7` | `armv7l` | `00b4cf7a454ae4539459cc5f908f3b42603b59b1035b8b046c6ef5ae1982247f` |
| **nodtool** | `v2.0.0-alpha.12` | `nodtool-linux-x86_64` | `x86_64` | `ee8345c004248eb82a86dd0c6068e0fcf3dc75baf68d18fe949bf4589822f5a5` |
| | | `nodtool-linux-aarch64` | `aarch64` | `33e801c0e4aee7e714ad84e89521f50e2f79005571b9d4779b695e44ea21ff99` |
| | | `nodtool-linux-i686` | `i686` | `efaa034f4d32a14856d5150c7eee45876ec38c07f75572cb6b4c33423c5850ce` |
| **3dstool** | `v1.2.6` | `3dstool_linux_x86_64.tar.gz` | `x86_64` | `d42e3de7766ee552b3609ac5acb7ad3f07209dd91bc45a21d3fc2b049790ede2` |

Las sumas **están fijadas en el código** (`romtools/utilidades.py`), no se
bajan de la red: un release que cambiase no puede colar un binario distinto
del esperado. El `3dstool` viene en un `tar.gz` y de dentro se saca sólo el
binario.

### Qué hace el instalador

1. Baja el asset de la release oficial a `/userdata/system/bin` (que sobrevive
   a los reinicios), mostrando el **porcentaje de descarga**.
2. Calcula su `sha256` y lo compara con el fijado en el código. Si no
   coincide, **no instala nada** y lo dice.
3. Le da permisos de ejecución y lo deja en su sitio.
4. Lo enlaza en `/usr/bin`, que es lo que lleva el `PATH`.
5. Escribe el bloque `# [batocera-tools]` en el `custom.sh` para que el enlace
   se vuelva a hacer en cada arranque (`/usr` es un overlay que se pierde al
   reiniciar).

### Cómo se controla

El modo lo manda la variable `BM_UTILS`:

| `BM_UTILS` | Qué hace |
|---|---|
| `auto` (por defecto) | Instala las que falten |
| `all` | Las reinstala todas, aunque ya estén |
| `skip` | No instala ninguna |

A mano, sin tocar el instalador:

```bash
cd /userdata/system/batocera_web
python3 -m romtools utilidades --list                    # qué se puede instalar
python3 -m romtools utilidades --install                 # instala las que falten
python3 -m romtools utilidades --install rom-converto    # sólo una
python3 -m romtools utilidades --remove nodtool          # quita una
```

Lo que queda instalado se apunta en
`/userdata/system/bin/.utilidades.json`, con la versión y la suma de cada
binario.

### Las que no se pueden instalar solas

Y el motivo de cada una:

| Utilidad | Por qué no |
|---|---|
| **dolphin-tool** | Dolphin no publica releases con binarios sueltos, y el paquete de Batocera compila con `-DENABLE_CLI_TOOL=OFF`: hay que tocar el *buildroot* |
| **wiitool** | No hay repositorio oficial ni release con binarios. Su equivalente actual, el [Wiimms ISO Tools](https://wit.wiimm.de/), publica tarballs para Linux pero sin suma de comprobación |
| **ndstool** | No hay release con binarios. El único precompilado va dentro del paquete de BlocksDS y necesita el cargador musl de `/opt/wonderful`, así que no funciona solo |
| **extract-xiso** | El repositorio no declara licencia, así que no se instala solo. Además el manager ya extrae el XDVDF en Python |
| **maxcso** | La release sólo trae el binario de Windows. El manager ya comprime en CSO, CSO2, ZSO y DAX en Python |
| **xorriso** | Sólo se publica el código fuente: hay que compilarlo |
| **cdrdao** | No hay binario de Linux en ninguna release (la que hay es de Windows). El manager ya convierte NRG, MDS, CCD e IMG en Python |
| **makecue** | No hay binario precompilado. El manager escribe el CUE el mismo |

## 7. Instalar el rom-converto a mano

**Con el `install.sh` esto ya no hace falta**: el instalador lo deja listo solo
(con el `sha256` comprobado) la primera vez que se ejecuta. El camino manual
sigue aquí por si hay que hacerlo a mano, y es el que se ha probado en la
consola real (Batocera 43.1, `x86_64`). El binario es de la release
**v0.24.0**: enlaza contra la glibc de la consola y no necesita nada más.

```bash
# 1. Descargar el binario y su suma de comprobación
cd /tmp
wget -O rom-converto https://github.com/DevYukine/rom-converto/releases/download/v0.24.0/rom-converto-cli-linux-x64
wget -O rom-converto.sha256 https://github.com/DevYukine/rom-converto/releases/download/v0.24.0/rom-converto-cli-linux-x64.sha256

# 2. Comprobar que es el binario de verdad (sha256 publicado: 0d4abd56…)
sha256sum -c rom-converto.sha256

# 3. Instalarlo donde sobrevive a los reinicios
mkdir -p /userdata/system/bin
install -m 755 rom-converto /userdata/system/bin/rom-converto

# 4. Enlazarlo en el PATH
ln -sf /userdata/system/bin/rom-converto /usr/bin/rom-converto
rom-converto --version
```

El paso 4 se repite en cada arranque, porque `/usr` es un overlay que se
pierde al reiniciar. Para que no haya que hacerlo a mano, el `install.sh`
escribe un bloque `# [batocera-tools]` en el `custom.sh` que enlaza en
`/usr/bin` todo lo ejecutable que haya en `/userdata/system/bin`:

```bash
# [batocera-tools]
# Utilidades de conversion (opcional) - enlaces al PATH
TOOLS_HOME="/userdata/system/bin"
TOOLS_BIN="/usr/bin"
if [ -d "$TOOLS_HOME" ]; then
  for t in "$TOOLS_HOME"/*; do
    [ -x "$t" ] || continue
    if [ -L "$t" ]; then continue; fi
    if [ -w "$TOOLS_BIN" ]; then ln -sf "$t" "$TOOLS_BIN/$(basename "$t")"; fi
  done
fi
# [/batocera-tools]
```

Los enlaces que ya estén en `/userdata/system/bin` (como el `npsget`) **no se
tocan**: el bloque sólo enlaza los ficheros de verdad que se hayan puesto
ahí, para no pisar lo que ya haya en `/usr/bin`.

**Qué se puede hacer con él** (comprobado sobre la consola, con un juego de
GameCube y otro de Wii de verdad):

| Conversión | Comando | Tiempo |
|---|---|---|
| ISO de GameCube → **RVZ** | `rom-converto dol compress juego.iso -o juego.rvz` | 968 MiB → 519 MiB en 18 s |
| WBFS de Wii → **RVZ** | `rom-converto rvl compress juego.wbfs -o juego.rvz` | 90 MiB → 77 MiB en 2,4 s |
| GCZ o WIA → **RVZ** | `rom-converto dol migrate` / `rvl migrate` | |
| RVZ → **ISO** | `rom-converto dol decompress` / `rvl decompress` | |
| RVZ de Wii → **WBFS** | `rom-converto rvl decompress juego.rvz -o juego.wbfs` | |

El **nivel de compresión** es el que trae la herramienta (22, calidad de
archivo); Dolphin recomienda el 5, que va mucho más rápido.

## 8. Referencias

- Wiki de Batocera, sistemas: <https://wiki.batocera.org/systems> — los
  formatos que admite cada sistema.
- Wiki de Batocera, compresión de disco: `disk_image_compression` — qué formato
  comprimido recomienda cada sistema.
- Buildroot de Batocera: <https://github.com/batocera-linux/buildroot> — de
  dónde sale cada binario de la imagen.
- Paquetes de Batocera: <https://github.com/batocera-linux/batocera.linux> — la
  rama `batocera-43.1` con los `.mk` de cada emulador y utilidad.
