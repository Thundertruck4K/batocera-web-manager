import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const CONTROL =
  'w-full rounded-xl border border-input bg-transparent px-3 text-sm text-foreground placeholder:text-muted-foreground/70 transition-colors duration-150 focus:border-ring focus:outline-none focus:ring-3 focus:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-50'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return <input ref={ref} className={cn(CONTROL, 'h-10', className)} {...props} />
})

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return <textarea ref={ref} className={cn(CONTROL, 'min-h-24 py-2.5 leading-relaxed', className)} {...props} />
  },
)

/**
 * Lista desplegable. El `<select>` nativo pinta su propio fondo (blanco con
 * letras pálidas) e ignora el `bg-transparent` del tema, así que se le quita
 * el aspecto nativo (`appearance-none`), se le da el fondo de la app y se le
 * dibuja la flecha. La lista de opciones ya la pinta el navegador con el
 * `color-scheme` declarado en index.css.
 */
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <span className="relative block w-full">
        <select
          ref={ref}
          className={cn(CONTROL, 'h-10 cursor-pointer appearance-none pr-9', className)}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
      </span>
    )
  },
)

interface FieldProps {
  label: string
  hint?: string
  error?: string | null
  htmlFor?: string
  className?: string
  children: React.ReactNode
}

export function Field({ label, hint, error, htmlFor, className, children }: FieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label
        htmlFor={htmlFor}
        className="block text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground"
      >
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs font-medium text-destructive">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}

/** Interruptor con etiqueta y descripción. */
export function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled,
}: {
  checked: boolean
  onChange: (next: boolean) => void
  label: string
  description?: string
  disabled?: boolean
}) {
  return (
    <label
      className={cn(
        'flex items-start justify-between gap-4 rounded-xl border border-border bg-transparent p-3 transition-colors duration-150',
        disabled && 'opacity-50',
      )}
    >
      <span className="min-w-0">
        <span className="block text-sm font-medium text-foreground">{label}</span>
        {description && <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative mt-0.5 h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
          checked ? 'bg-primary' : 'bg-muted',
          disabled && 'cursor-not-allowed',
        )}
      >
        <span
          className={cn(
            // La bola va anclada a la izquierda (left-0.5) para que el
            // recorrido sea simétrico: 2 px de margen a cada lado del carril
            // de 44 px. Sin `left` el navegador la colocaba centrada y, al
            // activarse, se salía del carril.
            'absolute left-0.5 top-0.5 size-5 rounded-full shadow-sm transition-all duration-200',
            checked ? 'translate-x-5 bg-primary-foreground' : 'translate-x-0 bg-foreground',
          )}
        />
      </button>
    </label>
  )
}
