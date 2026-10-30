import { AnimatePresence, motion } from 'motion/react'
import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

const EASE = [0.16, 1, 0.3, 1] as const

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  className?: string
}

export function Modal({ open, onClose, title, description, children, footer, className }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.14, ease: EASE }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.25, ease: EASE }}
            className={cn(
              'relative z-10 w-full max-w-lg overflow-hidden rounded-t-3xl border border-border bg-card shadow-[0_24px_60px_-12px_rgba(0,0,0,0.6)] sm:rounded-3xl',
              className,
            )}
          >
            <header className="flex items-start justify-between gap-4 px-5 pt-5 pb-3">
              <div className="min-w-0">
                <h2 className="text-base font-semibold tracking-[-0.019em] text-foreground">{title}</h2>
                {description && (
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Cerrar"
                className="-mt-1 -mr-1 cursor-pointer rounded-lg p-1.5 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <X className="size-4" />
              </button>
            </header>
            {children && <div className="px-5 pb-5">{children}</div>}
            {footer && (
              <footer className="flex items-center justify-end gap-2 border-t border-border bg-muted/40 px-5 py-3">
                {footer}
              </footer>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
