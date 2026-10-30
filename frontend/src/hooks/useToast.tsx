import { AnimatePresence, motion } from 'motion/react'
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

export type ToastVariant = 'info' | 'success' | 'error'

interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  showToast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const EASE = [0.16, 1, 0.3, 1] as const

const ICONS: Record<ToastVariant, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  error: AlertCircle,
}

const ACCENTS: Record<ToastVariant, string> = {
  info: 'text-muted-foreground',
  success: 'text-emerald-500',
  error: 'text-destructive',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const showToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = nextId.current++
    setToasts((prev) => [...prev.slice(-2), { id, message, variant }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3200)
  }, [])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-4 sm:bottom-4 sm:items-end">
        <AnimatePresence initial={false}>
          {toasts.map((toast) => {
            const Icon = ICONS[toast.variant]
            return (
              <motion.div
                key={toast.id}
                layout
                initial={{ opacity: 0, y: 12, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.97 }}
                transition={{ duration: 0.22, ease: EASE }}
                className="pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-2xl border border-border bg-popover px-4 py-3 text-popover-foreground shadow-[0_8px_28px_-6px_rgba(0,0,0,0.4)]"
                role="status"
              >
                <Icon className={cn('size-4 shrink-0', ACCENTS[toast.variant])} />
                <p className="text-sm font-medium tracking-[-0.011em]">{toast.message}</p>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast debe usarse dentro de <ToastProvider>')
  return ctx
}
