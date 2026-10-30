import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
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

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={cn(CONTROL, 'h-10 cursor-pointer pr-8', className)} {...props}>
        {children}
      </select>
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
            'absolute top-0.5 size-5 rounded-full bg-white shadow-sm transition-transform duration-200',
            checked ? 'translate-x-[1.375rem]' : 'translate-x-0.5',
          )}
        />
      </button>
    </label>
  )
}
