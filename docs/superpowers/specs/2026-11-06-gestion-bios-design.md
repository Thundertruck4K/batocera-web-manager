# Estrategia: gestión de BIOS

**Fecha:** 2026-11-06
**Estado:** propuesta para implementación
**Alcance:** backend (`app.py`), SPA (`frontend/src/`), consola Batocera real

---

## 1. Diagnóstico: qué pasa hoy en la consola

Todo lo de esta sección está medido sobre la consola real (Batocera 43.1), no supuesto.

### 1.1 La lista oficial que exige Batocera

La propia consola lleva la lista de BIOS que necesita, **versionada con ella**:

- `/usr/share/batocera/datainit/bios/readme.txt` (33 KB): por sistema, las rutas y los md5.
  ```
  3DO:
  f47264dd47fe30f73ab3c010015c155b bios/panafz1.bin
  51f2f43ae2f3508a14d9f56597e2d3ce bios/panafz10.bin

  Coleco Adam:
   bios/adam.zip
  01bba3bcd46d8a586dd6ec555accc133 bios/adam.zip
  feabe33e8f2dab88da1458b4d27f3faa bios/adam.zip
  ```
  Una línea con md5 vacío significa «este fichero sirve, pero no hay hash publicado».
  Varias líneas con la misma ruta = variantes regionales aceptadas (cualquiera de ellas vale).
- `/usr/bin/batocera-systems`: la herramienta oficial; sabe qué sistemas existen y qué BIOS faltan.
- El wiki oficial documenta, sistema a sistema, la ruta y el md5 de cada BIOS.

El `BIOS_DB` que hay hoy en `app.py` se generó de ese mismo catálogo oficial
(`batocera-systems`, 108 sistemas con BIOS, 705 entradas), pero **es una copia congelada**: no
sabe qué versión de Batocera corre la consola ni qué rutas exige hoy.

### 1.2 Estado real medido

Medido con la regla correcta (la del catálogo oficial, ver 1.3):

| Medida | Valor |
|---|---|
| Sistemas con BIOS según la lista oficial | 108 |
| Ficheros únicos esperados | 362 |
| Ficheros que hay en `/userdata/bios` | 3.436 (1.372 MiB) |
| **Correctos** (ruta exacta + el contenido que pide el catálogo) | **287** |
| Presentes sin hash publicado | 10 |
| Presentes con hash distinto | 3 |
| **Ausentes** | **62** |
| Ficheros que la lista oficial no pide | 3.145 |

Los 3.145 «extra» son `dolphin-emu` (2.523), `Machines` (296), hashes de MAME, `config.ini` y
guardados: no son BIOS de Batocera, pero ocupan sitio y confunden.

### 1.3 La clave: `zippedFile`

El catálogo oficial (`/usr/bin/batocera-systems`) no sólo da el md5 de cada BIOS: da el **miembro
exacto que debe ir dentro de cada ZIP**:

```python
{ "md5": "01bba3bcd46d8a586dd6ec555accc133",
  "zippedFile": "alf @1 rev 57 e3d5.u8",
  "file": "bios/adam.zip" }
```

Es decir: Batocera no compara el hash del ZIP (que es el de un ZIP cualquiera), sino el hash de lo
que va **dentro**. Sin ese dato, comparar el md5 del fichero con el esperado marca como incorrectos
ficheros que están perfectamente bien: con la regla naïve salían **204 correctas y 86 con hash
distinto**; con la regla del catálogo son **287 correctas y 3 con hash distinto**. De esos 83
ficheros «arreglados», la mayoría son ZIP con sus miembros dentro.

De aquí salen las dos reglas que ordenan todo el trabajo:

1. **Verificar por contenido, nunca por nombre**: el md5 de un ZIP de archive.org nunca coincidirá
   con el canónico; hay que abrirlo y mirar dentro (el catálogo dice qué miembro buscar).
2. **La biblioteca es reparable sin red**: se pueden reunir los miembros exigidos desde los ZIP que
   ya están en la consola y rehacer el ZIP en su ruta exacta.

### 1.4 Fuentes en archive.org

| Item | Colección | Ficheros | Tamaño | Autor |
|---|---|---|---|---|
| `emularity_bios_v1` | emularity / emulation | 159 | 260 MiB | Emularity Team |
| `jsmess_bios_v2` | emulation | 42 | 3 MiB | JSMESS Team |

La API pública da el **md5 y el tamaño de cada fichero** sin descargarlo
(`https://archive.org/metadata/<identifier>`), así que se puede filtrar candidatos antes de
transferir nada. Los ficheros van en ZIP por sistema (`snes.zip`, `neogeo.zip`, `c64.zip`…) más
algunos sueltos (`seabios.bin`, `vgabios.bin`, `tos-1.04-us.rom`, `Palm-III-3.5-en.bin`).

El propio item de Emularity avisa de que sus imágenes **son distintas de las canónicas**, lo que
confirma el punto 1.3: hay que verificar el contenido, no el ZIP.

**Aviso legal.** Ni `emularity_bios_v1` ni `jsmess_bios_v2` declaran `licenseurl` en sus metadatos,
y parte de las BIOS que.catalogan son firmware con copyright (PlayStation, Saturn, Mega Drive…).
La app debe tratarlo así:

- El **catálogo** se puede leer siempre (son metadatos).
- La **descarga automática** se ofrece con un interruptor explícito y un aviso una sola vez.
- Se prioriza siempre la **reparación local**, que no tiene ninguna implicación.
- Lo que se descarga se verifica contra el md5 oficial: sólo se instala el fichero exacto que
  Batocera pide.

---

## 2. Modelo de datos: tres capas

```
┌─ Capa 1 · Catálogo esperado ─────────────────────────────────────────┐
│  /usr/share/batocera/datainit/bios/readme.txt   (autoritativo)       │
│  BIOS_DB embebido en app.py                      (respaldo / dev)    │
│  → sistema (slug + nombre legible) → ficheros → rutas + md5         │
└──────────────────────────────────────────────────────────────────────┘
┌─ Capa 2 · Estado real ───────────────────────────────────────────────┐
│  /userdata/bios → índice {ruta: (tamaño, md5)}                       │
│  + índices inversos: por nombre y por md5  (para encontrar lo que   │
│    está «en otro sitio»)                                             │
└──────────────────────────────────────────────────────────────────────┘
┌─ Capa 3 · Fuentes ───────────────────────────────────────────────────┐
│  local   : ZIP ya presentes en la propia consola (reparar sin red)   │
│  archive : catálogo de items en archive.org (emularity, jsmess)      │
│  url     : enlace que da el usuario (descarga automática posterior)  │
│  subida  : fichero que sube el usuario                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 Capa 1: el catálogo

Se parsea el `readme.txt` de la consola (caché 1 h) y se cae al `BIOS_DB` embebido si no existe
(entorno de desarrollo en Windows, o una instalación mínima).

Mejoras frente a la tabla actual:

- **Nombre legible del sistema** («Coleco Adam», «3DO»), que hoy no se tiene y hace falta para la UI.
- **Md5 vacío** ≠ «verificado»: es «presente, sin hash publicado», un estado propio.
- **Md5 múltiples** para la misma ruta = variantes regionales aceptadas; se muestran todos.
- Se puede **cruzar con `batocera-systems`** para saber qué sistemas existen en esta versión y
  filtrar la lista a los que la consola tiene o puede tener.

### 2.2 Capa 2: el índice del disco

Un escaneo construye `{ruta_relativa: (tamaño, md5)}` de `/userdata/bios`, más los índices
inversos por nombre y por md5. Con ellos se responde a las tres preguntas que hoy no se responden:

| Pregunta | Cómo se responde |
|---|---|
| ¿está en su sitio? | ruta exacta en el índice |
| ¿está en otro sitio? | mismo md5 en otra ruta → hay que **mover** |
| ¿está dentro de un ZIP? | se abre el ZIP y se busca el md5 → hay que **extraer** |

Coste medido en la consola: el escaneo completo (3.436 ficheros, 1,4 GiB) tarda unos segundos con
md5 en streaming; se cachea 60 s y hay un botón de «reverificar».

---

## 3. Estados y heurística de ordenación

### 3.1 Estado de cada BIOS esperada

| Estado | Significado | Acción por defecto |
|---|---|---|
| `ok` | En su ruta y con md5 aceptado | — |
| `sin_verificar` | En su ruta, Batocera no publica md5 | — (aviso leve) |
| `reparable_zip` | El md5 esperado está dentro de un ZIP presente | **Extraer y colocar** |
| `reparable_ruta` | El mismo contenido está en otra carpeta | **Mover** |
| `hash_distinto` | Presente con un md5 que no es ninguno de los aceptados | Buscar fuente |
| `ausente` | No está en ninguna parte | **Descargar / Subir / Enlazar** |
| `omitida` | El usuario la marcó como no necesaria | — (persistente) |
| `no_requerida` | Hay algo en `/userdata/bios` que Batocera no pide | Revisar (opcional: limpiar) |

Los estados son **excluyentes y ordenados por gravedad**: `ausente` > `hash_distinto` >
`reparable_*` > `sin_verificar` > `ok`. Los `omitida` y `no_requerida` se listan aparte, porque no
son problemas.

### 3.2 Ordenación

El criterio es «que se vea primero lo que impide jugar»:

- **Por sistema**, una puntuación de criticidad:
  ```
  criticidad = 3 × (ausentes obligatorias) + 2 × (ausentes) + 1,5 × (reparables) + 1 × (hash distinto)
  ```
  Orden descendente por criticidad; a igualdad, alfabético por nombre. Los sistemas sin problema
  se van al final, no desaparecen.
- **Dentro del sistema**, agrupado por gravedad (ausentes → reparables → hash distinto → ok) y
  dentro del grupo por ruta.
- **En la ficha de cada BIOS**: nombre, ruta destino, extensión, tamaño, md5 esperado (copiable,
  con las variantes si hay varias), md5 real si el fichero existe, obligatoriedad, plataforma,
  y el motivo del estado («md5 distinto», «está dentro de `advision.zip`»).

### 3.3 Definición de plataforma

Para los filtros por tipo de equipo y fabricante se reutiliza `_classify_system()` (ya existe) y se
enriquece con el nombre legible del catálogo. Con eso las tarjetas pueden llevar el mismo icono
temático por familia que usa ya la sección de sistemas.

---

## 4. Reparación: cuatro vías, en este orden

Se intenta siempre la vía más barata y más segura antes de tocar la red.

1. **Extraer de un ZIP local** (sin red, sin dudas legales).
   Se abre el ZIP, se busca el miembro cuyo md5 sea uno de los aceptados, se extrae a la ruta
   exacta y se verifica. Si el destino ya existe, **no se sobrescribe**: se comprueba y se avisa.
2. **Mover / renombrar** si el contenido ya está en otra ruta.
3. **Descargar** de una fuente (archive.org o URL del usuario), con el mismo criterio: si lo
   descargado es un ZIP, se busca dentro el miembro con el md5 esperado; si es el fichero suelto,
   se verifica directamente. Se instala **sólo si el md5 coincide**.
4. **Subida manual** del usuario: la UI indica la ruta exacta de destino y el md5 que tiene que
   tener; se acepta el fichero, se verifica y se coloca.

### 4.1 Enlaces externos (descarga automática)

El usuario puede dejar una URL para una BIOS que falta. Queda guardada como **origen** de ese
fichero:

- la app la descarga en segundo plano, la verifica y la coloca;
- si la descarga falla, se reintenta con backoff y se avisa;
- el estado del enlace se ve en la ficha («origen automático: esperando / descargando / listo /
  falló»), y el sistema puede avisar cuando la BIOS que le faltaba llegue a estar disponible.

Es la vía para quien tiene la BIOS en su NAS, en un servidor propio o en cualquier sitio.

---

## 5. Fuentes: archive.org como primaria

### 5.1 Catálogo

```
GET https://archive.org/advancedsearch.php?q=collection:(emularity+OR+emulation)
                                          &fl[]=identifier&rows=50&output=json
GET https://archive.org/metadata/<identifier>      → ficheros con md5, tamaño y url
GET https://archive.org/download/<identifier>/<file> → descarga
```

El catálogo se guarda en local (`bios_sources.json`, caché 7 días) con: item, fichero, md5, tamaño,
URL y si el item declara licencia. Un escaneo completo son 2 peticiones, no 159 descargas.

### 5.2 Emparejamiento

Para cada BIOS que falta:

1. **Ficheros sueltos**: si el md5 del fichero de archive.org coincide con el md5 esperado → es un
   candidato directo.
2. **ZIP**: el md5 del ZIP nunca coincidirá con el canónico → se marca como *candidato por
   inspeccionar* y se comprueba descargando (o por rango) y abriendo el índice central del ZIP.
   Se cachea el resultado (md5 de cada miembro) para no volver a abrirlo.
3. Se propone **el mejor candidato** por estos criterios, en orden:
   1. coincide por md5 directo;
   2. es el ZIP del sistema correcto;
   3. el tamaño se parece al del md5 esperado;
   4. el item declara licencia libre.

### 5.3 Etiqueta legal por fichero

- `free`: el item declara `licenseurl` con licencia libre o dominio público → descarga automática
  permitida si el usuario lo ha activado.
- `unknown`: sin licencia declarada → la app **propone** el candidato y el usuario lo confirma con
  un clic (una vez por item, no por fichero).
- Nunca se borra ni se modifica lo que ya hay en la consola: sólo se añaden ficheros nuevos.

---

## 6. Interfaz en la SPA

Sección **ROMs y BIOS** (la última que sigue como *Pronto*), con el mismo lenguaje visual del
resto: tokens del tema, tarjetas, modales, toasts. Nada de colores sueltos.

### 6.1 Resumen arriba

Tarjeta de cobertura: `BIOS verificadas 204 · ausentes 62 · reparables 86 · no requeridas 3.145`,
con una barra de progreso por sistema y un botón de «reverificar».

### 6.2 Tarjetas por sistema

Una tarjeta por sistema con BIOS, ordenada por criticidad:

- icono temático por familia de equipo (el mismo mapa que usa la sección de sistemas);
- nombre legible y tipo de equipo;
- **badge de estado**: verde (todo ok), ámbar (reparable), rojo (faltan), gris (sin BIOS);
- contadores `12/14 · 2 ausentes · 1 reparable`;
- barra de cobertura;
- al hacer clic se abre el **modal de detalle**.

### 6.3 Modal de detalle

- Cabecera: sistema, cobertura, y acciones en lote: **«Reparar lo reparable»**,
  **«Descargar lo disponible»**, **«Reverificar»**.
- Tabla de ficheros: estado (icono + color), nombre, ruta destino, tamaño, md5 esperado (copiable),
  md5 real, extensión, obligatoriedad, motivo y **acción** por fila.
- Acciones por fila: `Extraer y colocar`, `Mover`, `Descargar`, `Subir`, `Usar enlace`, `Omitir`.
- Pestaña **Fuentes**: candidatos de archive.org para ese sistema con su md5, tamaño, licencia y
  el botón de usar; los candidatos que son «por inspeccionar» lo dicen claramente.

### 6.4 Notificaciones y progreso

- Éxito: «`adam.zip` colocado en `/userdata/bios/` (md5 verificado)».
- Error: «No se pudo descargar `x.bin`: timeout», «El fichero subido no coincide con el md5 esperado».
- Los trabajos en lote muestran progreso en vivo (patrón ya usado por el scraping por lotes del
  Scraper): `12/62 · 3 errores`, con los errores desplegables al final.

### 6.5 Iconografía

Lucide, como en el resto de la SPA: `CheckCircle2` (ok), `AlertTriangle` (hash distinto),
`Wrench` (reparable), `Download`, `Upload`, `Link2`, `SkipForward`, `PackageSearch` (ausente),
`Trash2` (no requerida). Los iconos de familia de sistema, reutilizados de la sección de sistemas.

---

## 7. API

Se reutiliza lo que ya existe (`/api/bios/all`, `/api/bios/missing`, `/api/bios/upload`,
`/api/bios/fetch`, `/api/bios/missing/skip|unskip|skipped`) y se añade:

| Endpoint | Qué hace |
|---|---|
| `GET /api/bios/catalog` | Catálogo oficial + estado real, con el resumen por estado |
| `POST /api/bios/scan` | Relanza el escaneo del disco y devuelve el resumen |
| `GET /api/bios/sources?system=` | Candidatos de archive.org para un sistema (catálogo cacheado) |
| `POST /api/bios/repair` | Extrae / mueve / descarga y **verifica** un fichero → `{ok, dest, md5, estado}` |
| `POST /api/bios/batch` | Trabajo en lote (reparar o descargar) → `{job_id}` |
| `GET /api/bios/job/<id>` | Progreso del trabajo: `{done, total, errores[]}` |
| `POST /api/bios/link` | Guarda una URL como origen automático de una BIOS |
| `GET /api/bios/summary` | Totales por estado (para las tarjetas) |

Reglas transversales:

- Nada se sobrescribe sin comprobación previa; antes de reemplazar se guarda una copia en
  `/userdata/bios/.quarantine/`.
- Toda escritura va a la ruta exacta que exige el catálogo, no a la que elija el usuario.
- Toda descarga pasa por el límite de tamaño que ya existe (64 MiB) y por `safe_path_under()`
  para no escribir fuera de `/userdata/bios`.

---

## 8. Fases

| Fase | Qué | Entregable | Estado |
|---|---|---|---|
| **0. Verdad** | Catálogo oficial (script `batocera-systems`), caché, estructura de estados, escaneo real con índices inversos, detección de «dentro de un ZIP» | `/api/bios/catalog`, `/api/bios/scan`, `/api/bios/summary` | **hecha** |
| **1. Reparar local** | Reunir el ZIP con sus miembros / mover el fichero, con verificación y cuarentena | `/api/bios/repair` + 22 tests | **hecha** |
| **2. Fuentes** | Catálogo de archive.org, caché, emparejamiento por contenido, descarga verificada | `/api/bios/sources`, descarga en `/api/bios/repair` | pendiente |
| **3. SPA** | Tarjetas, modales, toasts, filtros, subida manual, omitir | Sección ROMs y BIOS en la SPA | **hecha** (sin enlaces externos) |
| **4. Pulido** | Badge en el menú, informe de lo no requerido, limpieza con doble confirmación, orígenes automáticos | Detalles | pendiente |

Cada fase es un PR propio, con sus tests, como el resto del historial del repo.

### 8.1 Lo que se ha hecho ya (Fases 0, 1 y 3)

- El catálogo se lee del **script oficial** (`/usr/bin/batocera-systems`, un Python que se parsea con
  `ast` sin ejecutarlo) y trae slug, nombre legible, ruta, md5 y el miembro de cada ZIP. El
  `readme.txt` es el respaldo (sin slugs ni miembros: se empareja por conjunto de rutas con el
  catálogo embebido) y el `BIOS_DB` de `app.py` el último recurso.
- El escaneo completo de la consola (3.436 ficheros, 1,4 GiB) tarda **2,7 s** y está cacheado 5 min.
- La reparación reúne los miembros exigidos desde otro ZIP del disco y rehace el ZIP en su ruta
  exacta; si no encuentra el contenido **no toca el destino** (la cuarentena sólo se hace cuando ya
  se sabe que hay algo que escribir).
- La SPA tiene la sección *ROMs y BIOS* con tarjetas por sistema (ordenadas por criticidad), modal
  de detalle con md5, tamaño, ruta y estado, reparación en lote, subida manual, copiar hash y
  omitir.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Sobrescribir una BIOS buena | Nunca se escribe sobre un destino válido; cuarentena previa; el hash se verifica **después** de escribir y se revierte si no cuadra |
| Sobrecargar archive.org | Caché local de 7 días, un escaneo por sesión, descargas secuenciales con pausa, y sólo se descarga lo que hace falta |
| ZIP malicioso (ruta absoluta o `..`) | Se ignoran miembros con ruta absoluta o `..`, y todo se escribe con `safe_path_under()` |
| ZIP bomba | Límite de tamaño (64 MiB ya existe) y ratio de compresión |
| Falsos positivos | Un md5 vacío nunca se marca como «verificado», sino como «sin verificar» |
| Fechas de versión | El catálogo se lee siempre del `readme.txt` local, que es el de la versión instalada |
| Legal | Verificación por hash, aviso único, interruptor de descarga automática, prioridad a la reparación local |

---

## 10. Criterios de aceptación

1. «Verificar» sobre la consola real devuelve los cuatro estados medidos: 204 correctas,
   86 reparables, 62 ausentes, 3.145 no requeridas.
2. Extraer de un ZIP deja el fichero con el md5 exacto en la ruta exacta (probado con `adam.zip`
   y `advision.zip`).
3. Descargar de archive.org coloca un BIOS ausente y lo verifica antes de instalarlo.
4. La SPA muestra las tarjetas con el recuento correcto, el modal con el detalle de cada BIOS
   (tamaño, hash, extensión, plataforma) y las cuatro vías de reparación, con avisos de éxito y
   error.
5. Un enlace externo se descarga solo, en segundo plano, y aparece en la ficha como origen.
6. Ninguna BIOS existente se borra ni se sobrescribe sin confirmación.
