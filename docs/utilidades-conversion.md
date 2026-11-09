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

| Utilidad | Para qué sirve | Licencia | Dónde está | Cómo se consigue |
|---|---|---|---|---|
| **rom-converto** | **La más completa**: CSO, ZSO, CHD, RVZ, WBFS, WIA, GCZ, XISO, NSP, XCI, 3DS (CIA/CCI/Z3DS), PBP, ZAR, PS3, NDS | MIT | [DevYukine/rom-converto](https://github.com/DevYukine/rom-converto) | **Publica binarios estáticos para Linux `x86_64`** (`rom-converto-cli-linux-x64`): hay que bajar el binario y copiarlo a `/userdata/system/bin` (ver [§7](#7-instalar-el-rom-converto)). Es la vía más fácil de todas |
| **nodtool** (nod) | Crea y extrae los comprimidos de Dolphin: **CISO, GCZ, RVZ, WBFS, WIA y GCM** | Apache-2.0 | [encounter/nod](https://github.com/encounter/nod) | Compilarlo (Rust) o bajar el binario |
| **dolphin-tool** | Crea y extrae **RVZ**, el comprimido de Dolphin (GameCube y Wii). La wiki de Batocera lo marca como **el recomendado** | GPL-2.0-or-later | [dolphin-emu/dolphin](https://github.com/dolphin-emu/dolphin) | No se puede con lo que hay: el `dolphin-emu` de Batocera es la interfaz gráfica y el paquete **no** construye la herramienta de línea de comandos |
| **wiitool** | Crea y extrae **WBFS** y **WIA**, los formatos de Wii | GPL-3.0-or-later | [WiiTools/wiitool](https://github.com/WiiTools/wiitool) | Compilarlo |
| **extract-xiso** | Extrae **XDVDF** (Xbox) a ISO | Sin licencia declarada en el repositorio | [XboxDev/extract-xiso](https://github.com/XboxDev/extract-xiso) | El manager ya lo hace en Python, sin él |
| **maxcso** | Comprime la ISO en **CSO, CSO2, ZSO o DAX** (PSP y PS2) | ISC | [unknownbrackets/maxcso](https://github.com/unknownbrackets/maxcso) | El manager ya lo hace en Python, sin él |
| **ndstool** | Convierte una ROM de **Nintendo DS** a cartucho (NOA/GB) y saca su contenido | MIT o GPL-3.0-or-later (dual) | [blocksds/ndstool](https://github.com/blocksds/ndstool) | Compilarlo |
| **3dstool** | Empaqueta el contenido de un **3DS** en un CIA | MIT | [dnasdw/3dstool](https://github.com/dnasdw/3dstool) | Compilarlo (necesita `libiconv`, `openssl` y `libcurl`) |
| **xorriso** | Monta y extrae **XDVDF** (Xbox) y otras imágenes de disco | GPL-2.0-or-later | [gnu.org/software/xorriso](https://www.gnu.org/software/xorriso/) | El paquete está en el *buildroot* pero **no está habilitado** en la build de Batocera: hay que compilarlo |
| **cdrdao** | Convierte **NRG / MDS / CCD / IMG** a ISO | GPL-2.0-or-later | [cdrdao.sourceforge.net](https://cdrdao.sourceforge.net/) | El manager lo hace en Python, sin él |
| **makecue** | Escribe la hoja **CUE** que acompaña al BIN | GPL-2.0-or-later | [makecue.org](https://www.makecue.org/) | El manager la escribe él mismo |
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
| **[rom-converto](https://github.com/DevYukine/rom-converto)** | MIT | Binarios estáticos `linux-x64` | **El mejor candidato**: cubre casi todos los formatos, en un binario sin dependencias, con licencia MIT (compatible con este proyecto) |
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
  `ndstool`, el `3dstool`, el `xorriso`) hay que instalarlo **a mano**: copiar
  el binario a `/usr/bin`, darle permisos de ejecución y, si se quiere que
  sobreviva a las actualizaciones, añadir un paquete al *buildroot* de Batocera.
- El caso fácil es **rom-converto**: un binario estático de Rust, sin
  dependencias de ejecución, que se copia a `/usr/bin` y ya está (el
  apartado 7 explica la receta que se sigue aquí, con la ruta que
  sobrevive a los reinicios).

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

## 7. Instalar el rom-converto

Es el camino que se ha probado en la consola real (Batocera 43.1, `x86_64`).
El binario es de la release **v0.24.0** y es estático: no necesita nada de
la consola.

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
if [ -d "$TOOLS_HOME" ]; then
  for t in "$TOOLS_HOME"/*; do
    [ -x "$t" ] || continue
    [ -w "/usr/bin" ] && ln -sf "$t" "/usr/bin/$(basename "$t")" || true
  done
fi
# [/batocera-tools]
```

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
