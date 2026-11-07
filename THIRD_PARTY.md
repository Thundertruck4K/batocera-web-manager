# Terceros

Este proyecto es software libre (MIT). Lo que se lista aquí son **referencias y herramientas de
terceros**: ninguna se distribuye dentro del repositorio, salvo que se diga lo contrario.

## Software consultado (sin código copiado)

| Proyecto | Licencia | Para qué se consultó | Qué se hizo |
|---|---|---|---|
| [Mr-Shizzy/Game-Format-Converter](https://github.com/Mr-Shizzy/Game-Format-Converter) | GPL-3.0-or-later | Catálogo de formatos de disco y de conversiones | **Sus ideas, reimplementadas.** No se copia ni se vendoriza nada: es GPL y el proyecto es MIT. Su motor de CHD es `chdman` de MAME, y aquí también |
| [M5Devs/OpenROM](https://github.com/M5Devs/OpenROM) | GPL-3.0 | Detección de formato por cabecera y elección de variante | Referencia de diseño. Nada de su código (es Dart/Flutter) |
| [Dolphin](https://github.com/dolphin-emu/dolphin) (DiscIO) | GPL-2.0+ | Formato de disco de GameCube y Wii | Referencia de formato. Nada de su código |
| [Romulus Manager](https://www.romulusgames.com/) | Closed source | Convención de nombres de set | Se sigue la **convención** (el nombre del DAT manda), no su código ni su interfaz |

## Binarios externos que se usan en la consola

| Herramienta | Licencia | Dónde está | Para qué |
|---|---|---|---|
| `chdman` (de MAME) | GPL-2.0+ | `/usr/bin/chdman` en Batocera | Crear y leer CHD. Se invoca como proceso, no se enlaza ni se redistribuye |

Si el `chdman` no está en la consola, la conversión a CHD **no se simula**: se explica que hace falta
el binario.

## Datos que se descargan (no se distribuyen)

| Fuente | Licencia / condiciones | Qué se baja |
|---|---|---|
| [libretro-database](https://github.com/libretro/libretro-database) | BSD-3-Clause | Los DAT de Redump y No-Intro, y su catálogo |
| [Redump](http://redump.org/) | Metadatos de uso público | Los DAT con los nombres y los hashes de los discos |
| [No-Intro](https://www.no-intro.org/) | Metadatos de uso público | Los DAT con los nombres y los hashes de las cartuchos |

Los DAT son **metadatos**: la lista de juegos con sus nombres y sus hashes, sin ninguna ROM. Se
descargan en la consola del usuario y no forman parte de este repositorio ni de la release.

## Licencia de este proyecto

MIT. Ver [LICENSE](LICENSE).
