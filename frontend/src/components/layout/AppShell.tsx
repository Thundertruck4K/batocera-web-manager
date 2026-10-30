import { AnimatePresence, motion } from 'motion/react'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Sidebar } from './Sidebar'

const EASE = [0.16, 1, 0.3, 1] as const

interface ShellContextValue {
  /** Abre el cajón de navegación (sólo relevante en móvil). */
  openMenu: () => void
}

const ShellContext = createContext<ShellContextValue | null>(null)

export function useShell(): ShellContextValue {
  const ctx = useContext(ShellContext)
  if (!ctx) throw new Error('useShell debe usarse dentro de <AppShell>')
  return ctx
}

interface AppShellProps {
  children: ReactNode
  version?: string
  esRunning?: boolean
}

/**
 * Estructura general: sidebar fija en escritorio y cajón con desenfoque en
 * móvil (skill §3). Cada página pinta su propia <Topbar> dentro del área
 * principal.
 */
export function AppShell({ children, version, esRunning }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  const openMenu = useCallback(() => setMobileOpen(true), [])

  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mobileOpen])

  const value = useMemo(() => ({ openMenu }), [openMenu])

  return (
    <ShellContext.Provider value={value}>
      <div className="min-h-dvh bg-background">
        {/* Sidebar de escritorio */}
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-[268px] border-r border-border bg-card lg:block">
          <Sidebar version={version} esRunning={esRunning} />
        </aside>

        {/* Cajón móvil */}
        <AnimatePresence>
          {mobileOpen && (
            <div className="fixed inset-0 z-50 lg:hidden">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.14, ease: EASE }}
                onClick={() => setMobileOpen(false)}
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              />
              <motion.aside
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ duration: 0.25, ease: EASE }}
                className="absolute inset-y-0 left-0 w-[280px] border-r border-border bg-card shadow-2xl"
              >
                <Sidebar
                  version={version}
                  esRunning={esRunning}
                  onNavigate={() => setMobileOpen(false)}
                />
              </motion.aside>
            </div>
          )}
        </AnimatePresence>

        <div className="lg:pl-[268px]">{children}</div>
      </div>
    </ShellContext.Provider>
  )
}

/**
 * Contenedor de página con las medidas del catálogo (skill §2).
 */
export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1800px] px-4 pt-5 pb-16 sm:px-6 sm:pt-4 lg:px-10 xl:px-14">
      {children}
    </div>
  )
}
