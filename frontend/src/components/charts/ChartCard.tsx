import { TONE_COLOR, TONE_SOFT, type Tone } from '@/lib/tones'
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
  /** Acento de color de la tarjeta: da tono al gráfico y a los bordes. */
  tone?: Tone
  className?: string
}

/**
 * Tarjeta de gráfico: cabecera, escenario y pie (arquitectura de las tarjetas
 * mono del catálogo, skill §2).
 *
 * Con `tone` la tarjeta respira color: un halo muy tenue en la esquina
 * superior, un filo de color que se apaga hacia la derecha y el chip de la
 * cabecera teñido. El resto sigue igual de limpio.
 */
export function ChartCard({
  label,
  tag,
  value,
  caption,
  children,
  footer,
  tone,
  className,
}: ChartCardProps) {
  return (
    <section className={cn('card card-hover relative flex flex-col overflow-hidden', className)}>
      {tone && (
        <>
          {/* Halo del acento: apenas se ve, pero quita la monotonía. */}
          <span
            aria-hidden
            className="pointer-events-none absolute -top-24 -left-20 size-64 rounded-full opacity-60 blur-3xl"
            style={{
              background: `radial-gradient(circle, ${TONE_SOFT[tone]} 0%, transparent 68%)`,
            }}
          />
          {/* Filo superior del color, que se apaga hacia la derecha. */}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 z-0 h-px"
            style={{
              background: `linear-gradient(90deg, ${TONE_COLOR[tone]}, transparent 72%)`,
            }}
          />
        </>
      )}

      <header className="relative z-10 px-4 pt-4 pb-3 sm:px-5 sm:pt-5">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            {label}
          </span>
          {tag && (
            <span
              className={cn(
                'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium',
                tone ? 'border-transparent' : 'border-border bg-muted text-muted-foreground',
              )}
              style={
                tone
                  ? { color: TONE_COLOR[tone], backgroundColor: TONE_SOFT[tone] }
                  : undefined
              }
            >
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

      <div className="stage relative z-10 mx-4 flex flex-1 items-center justify-center overflow-hidden p-2 sm:mx-5">
        {children}
      </div>

      {footer && (
        <footer className="relative z-10 mt-4 flex items-center justify-between gap-3 border-t border-border px-4 py-2.5 text-[11px] text-muted-foreground sm:px-5">
          {footer}
        </footer>
      )}
    </section>
  )
}
