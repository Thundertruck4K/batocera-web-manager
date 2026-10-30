import { motion } from 'motion/react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/nav'
import { APP_VERSION } from '@/lib/version'

const EASE = [0.16, 1, 0.3, 1] as const

interface SidebarProps {
  onNavigate?: () => void
  /** Versión de Batocera mostrada en el pie. */
  version?: string
  esRunning?: boolean
}

export function Sidebar({ onNavigate, version, esRunning }: SidebarProps) {
  return (
    <div className="flex h-full flex-col gap-6 p-4 sm:p-5">
      <div className="flex items-center gap-3 px-1 pt-1">
        <span className="flex size-9 items-center justify-center rounded-xl border border-border bg-muted text-base">
          🕹️
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">
            Batocera Manager
          </p>
          <p className="truncate text-[11px] font-medium text-muted-foreground">
            {version ? `Batocera ${version}` : 'Sistema Manager Web'}
          </p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item, index) => {
          const Icon = item.icon
          if (item.pending) {
            return (
              <div
                key={item.to}
                aria-disabled="true"
                className="flex cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground opacity-45"
              >
                <Icon className="size-4 shrink-0" />
                <span className="flex-1 truncate">{item.label}</span>
                <span className="rounded-full border border-border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide">
                  Pronto
                </span>
              </div>
            )
          }

          return (
            <motion.div
              key={item.to}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, ease: EASE, delay: Math.min(index * 0.015, 0.05) }}
            >
              <NavLink
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-150',
                    'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                    isActive
                      ? 'bg-accent text-accent-foreground font-semibold'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="size-4 shrink-0" />
                    <span className="flex-1 truncate">{item.label}</span>
                    {isActive && (
                      <motion.span
                        layoutId="nav-active"
                        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                        className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-foreground"
                      />
                    )}
                  </>
                )}
              </NavLink>
            </motion.div>
          )
        })}
      </nav>

      <div className="rounded-2xl border border-border bg-muted/50 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'size-2 shrink-0 rounded-full',
              esRunning ? 'bg-emerald-500' : 'bg-muted-foreground/50',
            )}
          />
          <span className="text-[11px] font-medium text-muted-foreground">
            EmulationStation {esRunning ? 'activo' : 'detenido'}
          </span>
        </div>
        <p className="mt-1.5 text-[10px] text-muted-foreground/80">
          Manager v{APP_VERSION}
        </p>
      </div>
    </div>
  )
}
