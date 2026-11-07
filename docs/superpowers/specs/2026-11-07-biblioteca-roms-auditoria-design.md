# La biblioteca de ROMs vista como conjunto: duplicados y auditoría

**Fecha:** 2026-11-07
**Estado:** implementada
**Alcance:** backend (`app.py` + paquete `romtools/library.py`), SPA (`frontend/src/`), consola Batocera real

---

## 1. El problema

La ruta `/roms` (que en el menú se llama «ROMs y BIOS») montaba **una sola página: la de las BIOS**.
Todo lo que tenía que ver con los ficheros de juegos —la biblioteca— no tenía sitio: no había forma de
ver qué hay, cuánto ocupa, qué está repetido ni qué está roto.

La incoherencia era doble:

- **De nombre**: la sección promete ROMs y solo enseña BIOS.
- **De función**: ni siquiera lo que sí había (las BIOS) estaba junto a lo que faltaba, así que
  administrar la biblioteca exigía resortear a mano por SSH.

## 2. Lo que se decidió

Ocho ideas se recogieron y se priorizaron. La tanda 1 es la que va de verdad:

1. **Buscador de duplicados** con huella rápida y cuarentena. ✅ esta tanda
2. **Auditoría de integridad** (fichas fantasma, vacíos, sobras, limpiar el gamelist). ✅ esta tanda
3. Verificación contra el DAT. ⏳
4. Plan de ahorro de espacio (CHD/CSO). ⏳
5. Biblioteca muerta (nunca jugados). ⏳
6. Multigame y archivos sospechosos. ⏳
7. Búsqueda global. ⏳
8. «Qué me falta». ⏳

La estructura de la interfaz se decidió también: **una página con dos pestañas** (ROMs | BIOS), en vez
de dos entradas en el menú. La de BIOS ya existía y se queda igual; la de ROMs es la nueva.

---

## 3. El tamaño manda

La biblioteca de la consola real del autor: **257 sistemas, 2.770 juegos, 1.805,6 GB**. La radiografía
completa tardó **37,6 s** con el hash rápido.

Hasharla entera son **horas**: una ISO de GameCube son 4,7 GB y hay 574 ficheros en ese sistema solo.
Por eso la regla es:

> **Nunca se hashea la biblioteca.**

### 3.1 La huella rápida

`huella_rapida()` = md5 del **tamaño** + los primeros **64 KB** + los últimos **64 KB**. Dos ficheros
con la misma huella son casi seguro el mismo, y leer 128 KB de 1,8 TB es gratis.

La búsqueda va en tres pasos, de barato a caro:

1. **Agrupar por tamaño**: solo los grupos con más de un fichero siguen adelante.
2. **Huella rápida** de cada candidato: 128 KB por fichero.
3. **Hash completo** (md5) solo de los que coinciden.

### 3.2 El presupuesto de la confirmación

El paso 3 es el caro, así que tiene un **presupuesto de bytes** (`PRESUPUESTO_CONFIRMAR = 8 GB`). Los
grupos que no caben **se devuelven igual**, pero marcados `confirmado: false`: la huella coincide, pero
el fichero entero no se ha leído.

Esto es una decisión de interfaz, no un detalle: la pantalla dice **«hash confirmado»** o **«candidato
(sin confirmar)»**. Preferimos decir menos a fingir que se sabe.

### 3.3 Las carpetas también son juegos

Un juego puede ser una carpeta (Wii: `Juego [REXP01]/REXP01.wbfs`; ScummVM: `Myst.scummvm/`;
Lindbergh: `outr2sdx/`, que es el juego entero).

La primera versión hasheaba **el fichero grande de dentro** y fue un error: en ScummVM y en DOSBox ese
fichero es el **motor**, que es el mismo para todos los juegos, así que la consola real devolvió cuatro
duplicados falsos (`kq3`, `pq2`, `qfg2` y `sq2` de ScummVM) y tres más de DOSBox.

La regla buena es comparar la **carpeta entera**:

- la **huella rápida** de una carpeta es el md5 de sus **nombres y tamaños** (sin leer el contenido);
- la **confirmación** lee el contenido entero;
- la **agrupación** es por el **tamaño total** de la carpeta.

Con eso, la consola real pasó de 10 duplicados (5 falsos) a **5**, y los 5 son reales: el mismo juego en
dos byte orders de Nintendo 64, y una traducción que es un parche.

---

## 4. Nada se borra

Es la regla que gobierna toda la sección, y la razón por la que se puede actuar sobre una biblioteca de
1,8 TB sin miedo.

| Qué | Cómo |
|---|---|
| Ficheros que sobran | Se mueven a `/userdata/roms/.quarantine/<sistema>/` |
| El `gamelist.xml` | Se guarda el **texto original** antes de tocarlo |
| Las dos cosas | Quedan en un journal: `/userdata/system/batocera_manager_library.json` |

La cuarentena está **dentro de la propia biblioteca**, así que el `move` es un renombrado: instantáneo
y sin copiar 63 GB (el sistema `switch_update` pesa 63 GB y no se va a copiar nunca).

**Deshacer** (`POST /api/library/undo`) devuelve la última tanda a su sitio. El journal guarda las 20
tandas últimas.

### 4.1 La ruta se comprueba

Un `sistema/../importante.txt` en la petición no puede sacar ficheros de la biblioteca: `_dentro_de()`
compara la ruta real con la raíz de la biblioteca antes de mover nada.

---

## 5. La media huérfana, con cuidado

La media de Batocera se llama `<tallo>-<etiqueta>.png` (`image`, `marquee`, `thumb`, `screenshot`…). Si
el juego ya no está, esa imagen no le corresponde a nadie.

El matching ingenuo (comparar el tallo con el nombre del juego) falla con títulos largos, así que el
matching acepta tres formas:

| Caso | Cómo se reconoce |
|---|---|
| El nombre de la media es el del juego | Igualdad exacta (normalizada) |
| El nombre de la media está **cortado** | Un juego empieza por el tallo de la media |
| El juego se **renombró** a algo más largo | El tallo de la media empieza por un juego |

Los dos últimos casos se resuelven con búsqueda binaria sobre la lista ordenada de tallos (sin coste
cuadrático), y con una longitud mínima de 4 caracteres para no dar por bueno un prefijo cualquiera.

---

## 6. El contrato

### 6.1 Los endpoints

| Endpoint | Qué hace |
|---|---|
| `GET /api/library/summary` | Resumen rápido (sistemas, juegos, bytes). No hashea nada |
| `GET /api/library/audit/start` | Arranca la radiografía **en segundo plano** y devuelve el id del trabajo |
| `GET /api/library/job?id=…` | El estado del trabajo (qué hace, qué %, cuál es el fichero actual) |
| `GET /api/library/journal` | Las tandas que se pueden deshacer |
| `POST /api/library/quarantine` | Mueve ficheros a la cuarentena (`{"ficheros": ["sistema/ruta", …]}`) |
| `POST /api/library/gamelist/clean` | Quita las fichas rotas del `gamelist.xml` de un sistema |
| `POST /api/library/undo` | Deshace la última tanda |

### 6.2 La radiografía va en segundo plano

Como el plan de renombrado, la auditoría **no se sirve en la petición**: se arranca como trabajo
(`romtools/jobs.py`) y el frontend sondea el estado cada 400 ms. La barra mide **bytes leídos dentro
del fichero** (`romtools/progress.py`), porque hashear una ISO es un solo fichero y se lleva el 90 % del
tiempo.

### 6.3 Dónde vive cada cosa

- `romtools/library.py`: la radiografía (inventario, duplicados, auditoría, cuarentena, journal).
- `app.py`: **solo enruta**. Le pasa al módulo las extensiones que son juego en cada sistema
  (`system_game_extensions()`), para que la regla de «qué es un juego» no esté duplicada en dos sitios.

---

## 7. La interfaz

`/roms` → `pages/RomsBios.tsx`, que decide qué pestaña se ve:

- `pages/Roms.tsx` — la nueva: resumen, auditoría con barra, duplicados con selección, fichas rotas,
  vacíos, sobras, media huérfana, repetidos entre sistemas, espacio por sistema y deshacer.
- `pages/Bios.tsx` — la de siempre, con la barra de pestañas encima.

Cada página pinta su propia `Topbar` (el título y el subtítulo cambian con la pestaña), y las pestañas
son un componente compartido (`components/layout/SectionTabs.tsx`).

La **selección es explícita**: nada se mueve a la cuarentena sin que el usuario marque los ficheros. Y
el botón de mover enseña cuántos son.

---

## 8. Verificación

- **810 tests** en verde (33 nuevos: `tests/test_library.py`).
- `tsc -b` limpio y el bundle recompilado.
- En la consola real (257 sistemas, 2.745 juegos, 1.802,2 GB): la radiografía completa tarda
  **28 s** y encuentra **5 duplicados exactos** (todos confirmados con el hash completo), **53
  ficheros de 0 bytes**, **1.248 fichas** de `gamelist.xml` sin fichero, **323 ficheros que no son
  juegos** y **263 media huérfana** (con el matching del §5; la heurística ingenua daba 1.917).

### 8.1 Lo que no se ha hecho

- **La media huérfana sigue dando falsos positivos** con títulos muy largos: el matching del §5
  mejoró el conteo de 1.917 a 263, pero el número sigue siendo una estimación, no una verdad.
- **Los duplicados entre carpetas no salen** si las carpetas tienen tamaños distintos: la agrupación
  es por tamaño total, así que dos revisiones del mismo juego (OutRun 2 SDX y su versión G) se
  quedan fuera. No son duplicados (el contenido difiere), pero el espacio que se podría liberar
  mirando el nombre no se ve aquí: eso es lo de «el mismo juego en varios sistemas».
- **La verificación contra el DAT** (idea 3) queda para otra tanda: necesita el DAT instalado, que
  hoy solo hay en cinco sistemas de la consola de pruebas.
- **La biblioteca muerta** (idea 5) necesita el historial de partidas, que EmulationStation no guarda
  de forma fiable.
