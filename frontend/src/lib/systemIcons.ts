import {
  BookOpen,
  Boxes,
  Calculator,
  CircleDot,
  Compass,
  Cpu,
  Disc3,
  Dices,
  Film,
  Flame,
  Gamepad2,
  Ghost,
  Glasses,
  HardDrive,
  Joystick,
  Library,
  Monitor,
  Moon,
  Music,
  Package,
  Rocket,
  Satellite,
  Skull,
  Sparkles,
  Sun,
  Tablet,
  Target,
  Terminal,
  Triangle,
  Tv,
  type LucideIcon,
} from 'lucide-react'
import type { RomSystemSummary } from './types'

/**
 * Icono temático de cada sistema de Batocera.
 *
 * La idea es que la tarjeta de un sistema se reconozca de un vistazo: un
 * arcade enseña una palanca, una consola un mando, un portátil una pantalla
 * y un ordenador un terminal. Cuando no hay un icono propio se cae al del
 * tipo (`Consolas`, `Ordenadores`, `Portátiles`, `Arcade`…).
 */

/** Sistemas con identidad propia: el icono no se deduce del tipo. */
const BY_NAME: Record<string, LucideIcon> = {
  /* Arcade y recreativas */
  arcade: Joystick,
  mame: Joystick,
  fbneo: Joystick,
  fba: Joystick,
  naomi: Joystick,
  naomi2: Joystick,
  atomiswave: Joystick,
  chihiro: Joystick,
  hikaru: Joystick,
  triforce: Joystick,
  daphne: Disc3,
  singe: Disc3,
  dice: Dices,
  zinc: Joystick,
  gaelco: Joystick,
  cave3rd: Joystick,
  nesica: Joystick,
  systemsp: Joystick,
  vpinball: CircleDot,
  neogeo: Joystick,

  /* Consolas de disco */
  psx: Disc3,
  ps2: Disc3,
  ps3: Disc3,
  ps4: Disc3,
  dreamcast: Disc3,
  saturn: Disc3,
  segacd: Disc3,
  megacd: Disc3,
  neogeocd: Disc3,

  /* Consolas con cartucho o disco de sobra */
  fds: HardDrive,
  pcengine: Cpu,
  pcenginecd: Cpu,
  pcfx: Cpu,
  supergrafx: Cpu,
  moonlight: Moon,

  /* Portátiles con vida propia */
  gameandwatch: Calculator,
  pokemini: Calculator,
  channelf: Calculator,
  ctvboy: Calculator,
  gamate: Calculator,
  virtualboy: Glasses,
  arduboy: Sparkles,
  vectrex: Triangle,

  /* Consolas de bolsillo y microconsolas */
  pico8: Cpu,
  pyxel: Cpu,
  tic80: Cpu,
  wasm4: Cpu,
  vircon32: Cpu,
  uzebox: Cpu,
  picotron: Cpu,

  /* Ordenadores y ports */
  scummvm: Compass,
  steam: Flame,
  pygame: Library,
  easyrpg: BookOpen,
  openjazz: Music,
  'openbor': Package,
  'snes-msu1': Music,
  'sgb-msu1': Music,
  kodi: Film,
  vlc: Film,
  dos: Monitor,
  windows: Monitor,
  flatpak: Boxes,

  /* Curiosidades */
  satellaview: Satellite,
  solarus: Sun,
  solar: Sun,
  doom3: Skull,
  xrick: Ghost,
  ports: Package,
}

/** Palabras clave que afinan el icono dentro de un mismo tipo. */
const BY_KEYWORD: { test: RegExp; icon: LucideIcon }[] = [
  { icon: Monitor, test: /\b(pc|dos|windows|steam|flatpak)\b/ },
  { icon: Terminal, test: /\b(c64|amiga|apple2|atari ?800|msx|spectrum|zx81|x1|x68000|ti99|trs80|coco|pdp1|fm7|fmtowns|pc88|pc98|bbc|archimedes|atom|electron|thomson|oric|vic20|pet|dragon|camplynx|bk|spectravideo)\b/ },
  { icon: Rocket, test: /\b(cosmi|dyna|scumm|open ?rpg)\b/ },
  { icon: Target, test: /\b(lovesick|ghostbusters|n Contra|zombie)\b/ },
  { icon: Tv, test: /\b(satellaview|satellite)\b/ },
  { icon: Disc3, test: /\b(daphne|singe|laserdisc)\b/ },
  { icon: Flame, test: /\b(doom|quake)\b/ },
  { icon: Music, test: /\b(msu1|jazz|openbor)\b/ },
]

/** Icono por defecto según el tipo declarado del sistema. */
function iconByType(type: string): LucideIcon {
  switch (type) {
    case 'Arcade':
      return Joystick
    case 'Portátiles':
      return Tablet
    case 'Ordenadores':
      return Terminal
    case 'port':
      return Package
    case 'library':
      return Library
    case 'pinball':
      return CircleDot
    default:
      return Gamepad2
  }
}

/**
 * Devuelve el icono temático de un sistema.
 *
 * `name` es el identificador de Batocera (`snes`, `megadrive`, `gb`…) y se
 * busca primero en la tabla exacta; si no aparece se prueban las palabras
 * clave y, como último recurso, el icono del tipo.
 */
export function systemIcon(system: Pick<RomSystemSummary, 'name' | 'type' | 'manufacturer' | 'fullname'>): LucideIcon {
  const slug = (system.name || '').toLowerCase()
  const exact = BY_NAME[slug]
  if (exact) return exact

  const haystack = [system.name, system.fullname, system.type, system.manufacturer]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  for (const rule of BY_KEYWORD) {
    if (rule.test.test(haystack)) return rule.icon
  }

  return iconByType(system.type)
}

/**
 * Tipo del sistema con un nombre presentable.
 *
 * El catálogo de Batocera deja algunos tipos sin valor o con la cadena
 * literal `"None"` (los sistemas que no encajan en ninguna categoría).
 */
export function systemType(system: Pick<RomSystemSummary, 'type'>): string {
  const type = (system.type || '').trim()
  if (!type || type === 'None') return 'Otros'
  return type
}

/** Nombre corto de la fuente de scraping, para las etiquetas de la interfaz. */
export const SCRAPER_SOURCES = [
  { id: 'screenscraper', label: 'ScreenScraper' },
  { id: 'thegamesdb', label: 'TheGamesDB' },
  { id: 'igdb', label: 'IGDB' },
] as const
