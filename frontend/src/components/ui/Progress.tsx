import { cn } from '@/lib/utils'

export interface ProgressProps {
  /** El porcentaje ya calculado (0 a 100). */
  value: number
  /** Texto a la izquierda de la barra. */
  label?: React.ReactNode
  className?: string
}

/**
 * Barra de progreso.
 *
 * La usan los trabajos largos (el plan de renombrado de una biblioteca
 * grande): para que se vea que la aplicacion sigue viva y el usuario no
 * la cierre creyendo que se ha colgado.
 */
export function Progress({ value, label, className }: ProgressProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value || 0)))
  return (
    <div className={cn('w-full', className)}>
      {(label || pct > 0) && (
        <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
          <span className="min-w-0 truncate text-muted-foreground">{label}</span>
          <span className="shrink-0 font-semibold tabular-nums text-foreground">{pct}%</span>
        </div>
      )}
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
