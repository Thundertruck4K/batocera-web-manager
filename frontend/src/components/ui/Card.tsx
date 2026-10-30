import { cn } from '@/lib/utils'

/** Tarjeta base del catálogo (skill §2). */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('card', className)} {...props} />
}

interface PanelCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode
  subtitle?: React.ReactNode
  icon?: React.ReactNode
  actions?: React.ReactNode
  /** Cuerpo con padding por defecto. */
  bodyClassName?: string
}

/** Tarjeta con cabecera (título, subtítulo, icono y acciones). */
export function PanelCard({
  title,
  subtitle,
  icon,
  actions,
  className,
  bodyClassName,
  children,
  ...props
}: PanelCardProps) {
  const hasHeader = title || subtitle || icon || actions
  return (
    <section className={cn('card card-hover overflow-hidden', className)} {...props}>
      {hasHeader && (
        <header className="flex items-start justify-between gap-3 px-5 pt-4 pb-3">
          <div className="flex min-w-0 items-start gap-3">
            {icon && (
              <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                {icon}
              </span>
            )}
            <div className="min-w-0">
              {title && (
                <h3 className="truncate text-[15px] font-semibold tracking-[-0.015em] text-foreground">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="mt-0.5 truncate text-xs font-medium text-muted-foreground">{subtitle}</p>
              )}
            </div>
          </div>
          {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={cn('px-5 pb-5', hasHeader && 'pt-0', bodyClassName)}>{children}</div>
    </section>
  )
}

/** Escenario de previsualización (skill §1). */
export function Stage({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('stage', className)} {...props} />
}

/** Fila etiqueta/valor usada en las fichas de detalle. */
export function StatRow({
  label,
  value,
  hint,
}: {
  label: React.ReactNode
  value: React.ReactNode
  hint?: React.ReactNode
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate text-right text-sm font-medium tabular-nums text-foreground">
        {value}
      </span>
      {hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}
    </div>
  )
}
