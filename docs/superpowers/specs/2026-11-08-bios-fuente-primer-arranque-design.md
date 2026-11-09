# BIOS: fuente fiable, primer arranque y botón de reescanear

Fecha: 2026-11-08

## Qué se pide

1. Una **fuente fiable de BIOS** que se use para descargar lo que falte en la
   consola del usuario:
   `http://rgsretro1986.ds78102.seedhost.eu/update/Batocera/bios/`
2. Que la descarga **muestre una barra de progreso** (si no, el usuario cierra
   la ventana creyendo que la aplicación se ha colgado).
3. Un **botón para reescanear** el sistema a mano, cuando quiera.
4. Las **tarjetas de la sección BIOS son demasiado grandes**: hay que
   reducirlas. Después del primer escaneo la sección debería quedar vacía
   salvo alguna BIOS rara que falte.
5. Y el punto clave, corrigiendo el planteamiento inicial: **el escaneo de BIOS
   no se hace en la instalación**. Se hace **en el primer arranque del sistema
   por web**: ahí se escanea, se informa de lo que se encontró y lo que no, y
   se deja el botón para escanear a mano.

## Decisión: el escaneo ocurre en la web, no en install.sh

`install.sh` **no** escanea ni descarga BIOS. Lo único que hace es **armar** la
comprobación: borra el marcador de «ya comprobado» para que el primer arranque
del manager la haga, y lo dice en su salida final.

Motivo: el escaneo necesita el catálogo de BIOS de la consola (que sólo existe
cuando el manager está instalado yarrancado) y el progreso sólo se puede
enseñar en la interfaz. Meterlo en el instalador dejaría al usuario mirando
una consola durante minutos sin poder ver nada, que es justo lo que la barra de
progreso evita.

## La fuente

Es un **índice de directorios de Apache**: una página HTML con la lista de
ficheros y carpetas. En la raíz hay 458 ficheros sueltos y 62 carpetas, y
dentro de esas carpetas hay más (el árbol entero tiene unos 15.900 ficheros).

Los nombres coinciden con los que Batocera espera:

| Lo que Batocera espera | Donde está en la fuente |
|---|---|
| `Acorn/basic2.rom` | `Acorn/basic2.rom` |
| `bk/DISK_327.ROM` | `bk/DISK_327.ROM` |
| `enterprise/ep128emu/roms/exos21.rom` | `enterprise/ep128emu/roms/exos21.rom` |
| `Oric/basic11.rom` | `Oric/basic11.rom` |

O sea: **la ruta relativa dentro de la fuente es la misma ruta que Batocera
espera bajo `/userdata/bios`**. La descarga es, por tanto, «copiar el fichero a
la misma ruta».

### Índice dirigido, no índice completo

Indexar el árbol entero son ~64 peticiones HTTP y varios minutos en la consola:
no vale la pena para lo que se busca.

El índice se construye **sólo con las carpetas que hacen falta**: se parte de las
rutas que faltan y se bajan sus carpetas (una petición por carpeta distinta, y
sólo las que existen en la raíz). Para las 51 BIOS que faltaban en la consola
de desarrollo son **6 peticiones**: la raíz y cinco carpetas.

### Cómo se empareja

Para cada BIOS que falta (ruta tipo `bk/DISK_327.ROM`), en este orden:

1. **Ruta exacta** dentro de las carpetas indexadas.
2. **Ruta exacta ignorando mayúsculas** (`DISK_327.rom` == `DISK_327.ROM`).
3. **Por nombre de fichero**: si `basic2.rom` está en la raíz de la fuente y
   Batocera lo pide en `Acorn/`, se usa el de la raíz.

Lo que no aparece, **no aparece**: se informa de que esa BIOS no está en la
fuente y se deja como estaba. No se busca en otro sitio ni se inventa.

### Medido en la consola de desarrollo

- 51 BIOS faltaban, **49 se encontraron** en la fuente.
- Las 2 que no (`BBCMicro/dfs-2.26.rom` y `BBCMicro/os12.rom`) no están en la
  fuente: la carpeta `BBCMicro/` no existe en ella.

Con el trabajo terminado yendo de verdad a la consola (108 sistemas, 362 BIOS en
el catálogo del usuario): **357 BIOS revisadas, 49 bajadas** y **2 que no están
en la fuente**. La sección de BIOS quedó con una sola tarjeta (BBC Micro, con sus
dos BIOS raras) y el resto de sistemas, sin problema, desaparecieron del filtro
«con problemas».

## El marcador de «ya comprobado»

Fichero: `/userdata/system/batocera_manager_bios_first.json`.

```json
{"fecha": 1794100000.0, "resumen": {...}, "fuente": "http://..."}
```

- Si **no existe**, la comprobación está pendiente.
- `install.sh` lo **borra** al terminar: así, tras instalar o reinstalar, la
  comprobación se vuelve a hacer en el primer arranque.
- El backend lo escribe **cuando la comprobación llega a su fin** (es decir, cuando
  la fuente respondió). Si la fuente no respondió (se fue el internet), no se
  escribe y la próxima vez se repite.
- **Una BIOS que no está en la fuente NO es motivo para volver a preguntar en
  cada arranque**: eso se deja para el botón de escanear. (La primera versión
  escribía el marcador sólo si no había ningún fallo, y con eso el modal
  volvía a salir en cada recarga de página: un fallo de experiencia.)

## El trabajo en segundo plano

La comprobación es un **trabajo** (`romtools/jobs.py`), igual que el plan de
renombrado o la auditoría de la biblioteca:

- `GET  /api/bios/firstcheck` → si está pendiente, y con qué fuente.
- `POST /api/bios/descargar/start` → arranca el trabajo y devuelve su id.
- `GET  /api/bios/job?id=…` → estado (hechos, total, actual, porcentaje) y, al
  terminar, el resultado.

El progreso cuenta **ficheros**, con el nombre del que se está bajando ahora.
Cada fichero se baja entero en memoria (con el tope de 64 MiB que ya usa el
asistente de BIOS), se comprueba y se escribe en su sitio.

**Un trabajo sólo está «listo» cuando su función ha devuelto el resultado.** Que
la barra llegue al 100 % no lo termina: la comprobación de BIOS, por ejemplo,
sigue revisando cuando la descarga ya ha terminado. Antes de arreglarlo, el
cliente veía un trabajo terminado **sin resultado** y se quedaba con el modal en
blanco (`romtools/jobs.py`, `Job.progreso()`).

### Qué hace el trabajo, paso a paso

1. **Escanear**: `scan_bios()` dice qué BIOS pide el catálogo y cuáles están.
2. **Indexar la fuente**: sólo las carpetas que hacen falta.
3. **Emparejar**: cada BIOS que falta con su fichero en la fuente.
4. **Descargar**: uno a uno, con el progreso.
5. **Verificar**: se vuelve a escanear y cada BIOS descargada se comprueba con
   el mismo criterio que el resto (`ok` o `sin_verificar`).
6. **Informar**: cuántas se encontraron, cuántas se descargaron, cuántas no
   están en la fuente y cuáles fallaron.

## La interfaz

### Primer arranque

Un **modal** en el shell de la aplicación (aparece en cualquier página, no sólo en
la de BIOS) que:

1. Al cargar, pregunta si la comprobación está pendiente.
2. Si lo está, **la arranca** y enseña la **barra de progreso** con el nombre
   del fichero que se está bajando y el porcentaje.
3. Al terminar, informa: «N BIOS revisadas, M estaban donde debían, K se
   han descargado, J no están en la fuente».
4. Deja el **botón «Escanear el sistema»** para repetirla a mano.

Si la comprobación ya está hecha, el panel **no aparece**: la sección de BIOS
se queda como estaba, con su botón de reescanear.

### La sección BIOS

- **Botón «Escanear el sistema»** visible, no sólo un icono: es la acción que
  el usuario va a usar.
- **Tarjetas más pequeñas**: la rejilla pasa a más columnas y la tarjeta baja
  de alto (icono más pequeño, sin la franja grande de proportions). Después
  del primer escaneo la sección queda vacía salvo que falte alguna BIOS rara,
  así que las tarjetas no tienen que ocupar media pantalla para enseñar cuatro
  líneas.
- El estado vacío («Ninguna BIOS con problemas») **explica** que se comprobó
  todo y ofrece el botón de reescanear.

## Lo que no se hace

- **No se descarga de ninguna otra fuente.** La del usuario es la que se usa.
- **No se afirma nada que no se sepa**: si una BIOS no está en la fuente, se
  dice que no está, y se puede seguir buscando a mano (el botón de Google que
  ya hay en el modal de cada sistema).
- **No se borra ni se sobrescribe nada** que ya esté bien: una BIOS que está
  en su sitio no se vuelve a bajar.

## Reglas

- **Un trabajo largo enseña su progreso**: si la interfaz se queda en silencio,
  el usuario cierra la ventana creyendo que la app se ha colgado.
- **La fuente se indexa dirigida**: sólo las carpetas que hacen falta, nunca el
  árbol entero.
- **Si algo no está en la fuente, se dice**: no se busca en otro sitio ni se
  inventa.
- **El marcador se escribe cuando la comprobación llega a su fin**: si la fuente
  no respondió, se repite la próxima vez. Pero una BIOS que no está en la fuente
  no vuelve a preguntar en cada arranque.
- **Un trabajo no termina con su barra llena**: termina cuando tiene resultado.
