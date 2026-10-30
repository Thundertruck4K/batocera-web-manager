import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  label: string
  value: React.ReactNode
  unit?: string
  hint?: React.ReactNode
  icon?: LucideIcon
  /** Franja de color de acento (barra inferior). */
  accent?: 'default' | 'good' | 'warn' | 'bad'
  className?: string
}

const ACCENTS: Record<NonNullable<MetricCardProps['accent']>, string> = {
  default: 'bg-chart-1/25',
  good: 'bg-emerald-500/70',
  warn: 'bg-amber-500/70',
  bad: 'bg-destructive/70',
}

/** Tarjeta compacta de indicador. */
export function MetricCard({
  label,
  value,
  unit,
  hint,
  icon: Icon,
  accent = 'default',
  className,
}: MetricCardProps) {
  return (
    <div className={cn('card card-hover relative overflow-hidden px-4 py-3.5 sm:px-5', className)}>
      <div className="flex items-start justify-between gap-2">
        <span className="truncate text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
          {label}
        </span>
        {Icon && <Icon className="size-3.5 shrink-0 text-muted-foreground" />}
      </div>
      <div className="mt-1.5 flex items-baseline gap-1">
        <span className="text-2xl font-bold tracking-tight tabular-nums text-foreground">{value}</span>
        {unit && <span className="text-xs font-medium text-muted-foreground">{unit}</span>}
      </div>
      {hint && <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{hint}</p>}
      <span
        className={cn(
          'absolute inset-x-0 bottom-0 h-0.5 rounded-b-3xl opacity-70',
          ACCENTS[accent],
        )}
      />
    </div>
  )
}
