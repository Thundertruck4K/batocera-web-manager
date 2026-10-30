import {
  Gamepad2,
  Gauge,
  Palette,
  Plus,
  Settings,
  Sparkles,
  Trophy,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Si es `true`, la sección todavía no está implementada. */
  pending?: boolean
  /** Coincidencia exacta de ruta en lugar de prefijo. */
  end?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Panel de control', icon: Gauge, end: true },
  { to: '/sistemas', label: 'Sistemas', icon: Gamepad2 },
  { to: '/sistemas/nuevo', label: 'Añadir sistema', icon: Plus },
  { to: '/roms', label: 'ROMs y BIOS', icon: Sparkles, pending: true },
  { to: '/scraper', label: 'Scraper', icon: Palette, pending: true },
  { to: '/retroachievements', label: 'Logros', icon: Trophy, pending: true },
  { to: '/configuracion', label: 'Configuración', icon: Settings },
]
