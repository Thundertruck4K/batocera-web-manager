import { motion } from 'motion/react'
import { CircleAlert, CircleCheck } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { cn } from '@/lib/utils'

export type NotifyVariant = 'success' | 'error'

export interface NotifyOptions {
  /** `success` se cierra solo; `error` espera a que se confirme. */
  variant: NotifyVariant
  title: string
  /** Texto breve del aviso. */
  message?: string
  /** Log del error: se muestra en un bloque con el detalle. */
  detail?: string
  /** Milisegundos hasta el cierre automático (sólo en el éxito). */
  autoCloseMs?: number
}

interface NotifyContextValue {
  showNotify: (options: NotifyOptions) => void
}

const NotifyContext = createContext<NotifyContextValue | null>(null)

/** Tiempo por defecto del aviso de éxito antes de cerrarse solo. */
const AUTO_CLOSE_MS = 2500

/**
 * Avisos en modal, para lo que necesita una confirmación: el éxito del
 * scraping se muestra unos segundos y se cierra solo; el error se queda
 * hasta que se pulsa «Cerrar», con el log a la vista.
 */
export function NotifyProvider({ children }: { children: ReactNode }) {
  const [notify, setNotify] = useState<NotifyOptions | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const close = useCallback(() => {
    window.clearTimeout(timer.current)
    timer.current = undefined
    setNotify(null)
  }, [])

  const showNotify = useCallback((options: NotifyOptions) => {
    window.clearTimeout(timer.current)
    setNotify(options)
    if (options.variant === 'success') {
      timer.current = window.setTimeout(() => {
        timer.current = undefined
        setNotify(null)
      }, options.autoCloseMs ?? AUTO_CLOSE_MS)
    }
  }, [])

  useEffect(() => () => window.clearTimeout(timer.current), [])

  const value = useMemo(() => ({ showNotify }), [showNotify])

  const esError = notify?.variant === 'error'

  return (
    <NotifyContext.Provider value={value}>
      {children}
      <Modal
        open={Boolean(notify)}
        onClose={close}
        title={notify?.title ?? ''}
        className="max-w-md"
        footer={
          esError ? (
            <Button variant="primary" size="sm" onClick={close}>
              Cerrar
            </Button>
          ) : undefined
        }
      >
        {notify && (
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <span
                className={cn(
                  'mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full',
                  esError
                    ? 'bg-destructive/15 text-destructive'
                    : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
                )}
              >
                {esError ? <CircleAlert className="size-5" /> : <CircleCheck className="size-5" />}
              </span>
              <div className="min-w-0 flex-1">
                {notify.message && notify.message !== notify.title && (
                  <p className="text-sm leading-relaxed text-foreground">{notify.message}</p>
                )}
              </div>
            </div>

            {notify.detail && (
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-border bg-muted/50 p-3 text-[11px] leading-relaxed text-muted-foreground">
                {notify.detail}
              </pre>
            )}

            {!esError && (
              <div className="h-1 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className="h-full rounded-full bg-emerald-500"
                  initial={{ width: '100%' }}
                  animate={{ width: '0%' }}
                  transition={{ duration: (notify.autoCloseMs ?? AUTO_CLOSE_MS) / 1000, ease: 'linear' }}
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </NotifyContext.Provider>
  )
}

export function useNotify(): NotifyContextValue {
  const ctx = useContext(NotifyContext)
  if (!ctx) throw new Error('useNotify debe usarse dentro de <NotifyProvider>')
  return ctx
}
