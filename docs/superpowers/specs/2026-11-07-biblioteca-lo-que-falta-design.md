# Lo que falta: las otras versiones de los juegos que ya tienes

- **Fecha**: 2026-11-07
- **Rama**: `feature/biblioteca-lo-que-falta`
- **Estado**: implementada y verificada en consola real

## El problema

La seccion «ROMs y BIOS» ya hace la radiografia de la biblioteca (duplicados,
fichas rotas, ficheros vacios, sobras, media huerfana, repetidos entre
sistemas). Todo eso mira **lo que sobra** o **lo que esta roto**.

Falta el otro lado: **lo que falta**. El DAT de un sistema es la lista de todos
los juegos de ese sistema con el nombre y el tamano de cada fichero, asi que
comparandolo con la biblioteca se sabe que tienes y que te falta.

## Por que no se lista «todo lo que falta»

Porque no informa de nada. En la consola de desarrollo:

| Sistema | Juegos en el DAT | Ficheros en la biblioteca |
|---|---|---|
| scummvm | 36.474 | 9.008 |
| switch | 15.690 | 179 |
| ps2 | 13.618 | 354 |
| psx | 13.407 | 49 |
| wii | 3.817 | 77 |
| n64 | 2.268 | 1.093 |

Decir «te faltan 36.000 juegos» es ruido: es lo mismo que decir que no tienes
la coleccion completa. Lo que si es accionable es lo contrario:

- **de los juegos que ya tienes, que otras versiones hay**. Si tienes
  «Super Mario 64 (Japan)» y el DAT tiene tambien la americana y la europea,
  quiza te interesa la americana.
- **que discos faltan de un juego con varios discos**. Si el DAT tiene
  «Juego (Disc 1)», «Juego (Disc 2)» y «Juego (Disc 3)» y tu solo tienes el
  primero, ese disco si falta de verdad.
- **que version es mejor que la que tienes**. Si tienes un volcado con datos
  malos (`[b]`) y el DAT tiene el verificado (`[!]`), eso es una mejora real.

Por eso la seccion se titula **«Lo que falta»** y lista **las variantes de los
juegos que ya tienes**: el dato es util porque el juego ya te interesa.

## Decision: sistema a sistema, no todo junto

Cargar los 17 indices a la vez son ~55 MB de JSON (el de scummvm son 18 MB
solo), que en la consola se convierten en varios cientos de MB de objetos de
Python. Una vez fue un `oom-kill` por un indice de 2,1 GB.

La comparacion es **por sistema**, a peticion: se elige un sistema, se carga
solo su indice, se compara y se sueltan. El indice se relee del disco en cada
comparacion (`dats.load_index()`), que es lo que hace el trabajo lento pero
also honesto: si el DAT se ha cambiado, la comparacion ve la version nueva sin tener que reiniciar nada.

## Como se empareja cada juego

Se reutiliza `identify.identify()`, que ya sabe emparejar por este orden:

1. **Nombre y tamano** — no toca el disco y es lo que mas se da.
2. **Codigo de juego** (Wii) — se lee de la cabecera del volcado.
3. **Hash** — la prueba definitiva, pero obliga a leer el fichero entero, asi
   que va con **presupuesto de bytes** (512 MB por sistema, como el plan de
   renombrado). Lo que se queda fuera no se hashea y se empareja por el
   nombre o por el titulo.
4. **Serial del disco**.
5. **Titulo** — heuristica, y se marca como tal.

Cada coincidencia dice **como** se ha emparejado, porque una coincidencia por
nombre no es lo mismo que una por hash. En el caso de los juegos que viven en
una carpeta (Wii, ScummVM) se identifica el **fichero de dentro**, que es
donde esta el codigo de juego, y el nombre que se ensena es el de la carpeta.

### Dos claves, no una

`sets.game_key()` deja la region, la revision y las marcas fuera, pero
**conserva la etiqueta de disco**: «Juego (Disc 1)» y «Juego (Disc 2)» son
claves distintas. Eso vale para renombrar (el disco es parte de la identidad),
pero aqui hace falta saber que son el mismo juego con dos discos.

Por eso se usan dos claves:

- `game_key` → la **variante** (mismo disco, distinta region o revision).
- Una clave **sin disco** → el **juego**, que agrupa sus discos.

## Cuantas coincidencias y de que calidad

Una coincidencia por titulo es una heuristica, asi que hay **tres clases** de
resultado, y las decide **el nombre**, no el parecido:

| Clase | Cuando | Que dice la interfaz |
|---|---|---|
| **Emparejado** | el **titulo pelado** (sin etiquetas) es el mismo Y la **region que declara el nombre** es la misma en los dos lados | «tienes» esta variante, con la region y la revision |
| **Quiza** | el titulo pelado es el mismo, pero solo uno de los dos dice su region | es el mismo juego pero no se sabe que variante: **no se afirma** ni que lo tienes ni que te falta |
| **Sin DAT** | el titulo pelado no es el mismo | es otro juego (un mod, una traduccion, homebrew) |

El parecido (>= 0,85 para el titulo pelado, >= 0,80 para identificar el
juego) es el suelo, no la regla.

### Por que la region y no el parecido

El parecido entre caracteres tiene un sesgo: **el nombre con menos etiquetas
gana**. «Super Mario 64» se parece mas a «Super Mario 64 (USA)» (0,881) que a
«Super Mario 64 (Japan)» (0,758), asi que un fichero sin region se
emparejaba con seguridad como si fuera el americano. No es verdad: es el mismo
juego, pero no se sabe que variante es. Por eso la region que declara el
nombre va **por delante** del parecido.

Y con el titulo pelado hacen falta las dos cosas: «Tomb Raider  I» y «Tomb
Raider (USA)» se parecen mucho (0,879) y son **juegos distintos**.

**Los dudosos no se cuentan como «sin DAT»**: son juegos que quiza ya tienes,
y mezclarlos haria que el recuento de «lo que no sale en el DAT» mintiera.

### Las palabras de la busqueda

Las palabras con las que se buscan los candidatos salen del titulo **pelado**
de la consulta. Con la query entera, «(USA)» comparte palabra con un cuarto
de los titulos del DAT de PlayStation 2 (2.260 candidatos de 11.065) y la
busqueda se iba a 0,3 s por fichero: comparar ps2 entero tardaba 33 s. Con el
titulo pelado, 4 s, y el resultado es **el mismo**.

## Los motivos

Para cada version que falta se dice **por que** falta, comparandola con la
mejor version que ya tienes:

| Motivo | Cuando |
|---|---|
| `te falta el disco N` | la version es un disco que no tienes |
| `otra region (X)` | la region es distinta a la que tienes |
| `otra revision` | cambia el `(Rev N)` |
| `otro idioma` | cambian los codigos de idioma (`(En,Fr,De)`) |
| `otra version` | ninguna de las anteriores (revisiones, marcas de volcado) |

Y aparte, la marca **`mejor`**: la version que falta puntua mas alta que la que
tienes con `sets.score_entry()` (la region cuenta, la revision suma, `[b]`
resta y `[!]` suma). Es el caso de verdad util: «tienes un volcado con datos
malos y hay uno verificado».

## Lo que no se hace

- **No se borra ni se escribe nada.** Es informacion.
- **No se afirma lo que no se sabe**: una coincidencia por titulo se marca
  como tal, y lo que no se ha verificado por hash se dice.
- **Un filtro cuenta lo que el filtro muestra**: el numero de «mejores
  versiones» de la pastilla cuenta los **juegos**, no las versiones, porque
  eso es lo que se enseña al filtrar.
- **No se lista lo que falta del todo** (juegos del DAT que no te interesan):
  seria ruido.

## La interfaz

En la pagina «ROMs y BIOS», seccion **«Lo que falta»**:

- Un selector con los sistemas que tienen DAT instalado (y cuantos juegos
  tiene el DAT de cada uno).
- Boton **«Comparar con el DAT»**: arranca el trabajo y la barra de progreso
  va ensenando el avance, como el plan de renombrado.
- El resultado son tarjetas por juego: lo que tienes (con como se ha
  emparejado), lo que falta (con el motivo) y, si procede, el aviso de que
  hay una version mejor.
- Filtros: **todo**, **solo los que faltan discos** y **solo mejores
  versiones**.

## Endpoints

| Metodo | Ruta | Que hace |
|---|---|---|
| GET | `/api/library/missing/systems` | los sistemas con DAT y cuantos juegos tiene |
| GET | `/api/library/missing/start?system=…` | arranca la comparacion, devuelve el trabajo |
| GET | `/api/library/job?id=…` | el estado del trabajo (el de siempre) |

## Memoria

Los indices de DAT son grandes y el de scummvm son 18 MB: cargarlos todos a
la vez es lo que tumbó la consola otra vez. Aqui se carga **uno por sistema**,
a peticion, y se suelta al terminar.
