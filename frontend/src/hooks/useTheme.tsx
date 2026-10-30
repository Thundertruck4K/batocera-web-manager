import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '@/lib/api'
import type { UiTheme } from '@/lib/types'

const STORAGE_KEY = 'bm_ui_theme'

type Resolved = 'dark' | 'light'

interface ThemeContextValue {
  /** Modo elegido por el usuario: dark | light | auto. */
  mode: UiTheme
  /** Tema efectivamente aplicado tras resolver `auto`. */
  resolved: Resolved
  setMode: (mode: UiTheme) => void
  /** Alterna entre oscuro y claro (resuelve `auto` al revés de lo actual). */
  toggle: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(resolved: Resolved) {
  const root = document.documentElement
  root.classList.toggle('dark', resolved === 'dark')
  root.classList.toggle('light', resolved === 'light')
  root.style.colorScheme = resolved
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<UiTheme>(() => {
    if (typeof window === 'undefined') return 'dark'
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as UiTheme | null
      if (saved === 'dark' || saved === 'light' || saved === 'auto') return saved
    } catch {
      /* sin localStorage: se usa el valor por defecto */
    }
    return 'dark'
  })

  const [systemDark, setSystemDark] = useState(systemPrefersDark)

  useEffect(() => {
    if (!window.matchMedia) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const resolved: Resolved = mode === 'auto' ? (systemDark ? 'dark' : 'light') : mode

  useEffect(() => {
    applyTheme(resolved)
  }, [resolved])

  // Si el usuario no ha tocado el tema en este dispositivo, se adopta el que
  // tenga configurado en el manager (así el móvil y el PC coinciden).
  useEffect(() => {
    if (mode !== 'dark') return
    let cancelled = false
    const stored = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
    if (stored) return
    api
      .getSettings()
      .then((s) => {
        if (cancelled) return
        if (s.ui_theme === 'light' || s.ui_theme === 'auto') setModeState(s.ui_theme)
      })
      .catch(() => {
        /* Backend no disponible (p. ej. sólo frontend): se queda en oscuro. */
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setMode = useCallback((next: UiTheme) => {
    setModeState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* sin persistencia local el tema sigue funcionando en memoria */
    }
    // Se guarda también en el manager para que el tema se aplic igual desde
    // el móvil o el PC. Si el backend no está, no es un error.
    void api.saveTheme(next).catch(() => undefined)
  }, [])

  const toggle = useCallback(() => {
    const current = mode === 'auto' ? (systemDark ? 'dark' : 'light') : mode
    setMode(current === 'dark' ? 'light' : 'dark')
  }, [mode, systemDark, setMode])

  const value = useMemo(
    () => ({ mode, resolved, setMode, toggle }),
    [mode, resolved, setMode, toggle],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme debe usarse dentro de <ThemeProvider>')
  return ctx
}
