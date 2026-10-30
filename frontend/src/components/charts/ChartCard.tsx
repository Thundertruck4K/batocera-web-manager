import { cn } from '@/lib/utils'

interface ChartCardProps {
  /** Etiqueta en mayúsculas del gráfico. */
  label: string
  /** Chip descriptivo (tipo de visualización). */
  tag?: string
  /** Cifra grande bajo la etiqueta. */
  value?: React.ReactNode
  /** Texto pequeño junto a la cifra. */
  caption?: React.ReactNode
  /** Gráfico: se pinta dentro del escenario. */
  children: React.ReactNode
  /** Pie con leyenda o notas. */
  footer?: React.ReactNode
  className?: string
}

/**
 * Tarjeta de gráfico: cabecera, escenario y pie (arquitectura de las tarjetas
 * mono del catálogo, skill §2).
 */
export function ChartCard({
  label,
  tag,
  value,
  caption,
  children,
  footer,
  className,
}: ChartCardProps) {
  return (
    <section className={cn('card card-hover flex flex-col overflow-hidden', className)}>
      <header className="px-4 pt-4 pb-3 sm:px-5 sm:pt-5">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            {label}
          </span>
          {tag && (
            <span className="shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              {tag}
            </span>
          )}
        </div>
        {(value || caption) && (
          <div className="mt-1 text-xl font-bold tracking-tight tabular-nums text-foreground">
            {value}
            {caption && (
              <span className="ml-1.5 text-xs font-normal text-muted-foreground">{caption}</span>
            )}
          </div>
        )}
      </header>

      <div className="stage mx-4 flex flex-1 items-center justify-center overflow-hidden p-2 sm:mx-5">
        {children}
      </div>

      {footer && (
        <footer className="mt-4 flex items-center justify-between gap-3 border-t border-border px-4 py-2.5 text-[11px] text-muted-foreground sm:px-5">
          {footer}
        </footer>
      )}
    </section>
  )
}
