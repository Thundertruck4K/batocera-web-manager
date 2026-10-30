interface NameValue {
  name?: string | number
  value?: number | string
  dataKey?: string | number
  color?: string
  fill?: string
  payload?: unknown
}

export interface ChartTooltipProps {
  active?: boolean
  payload?: NameValue[]
  label?: string | number
  formatter?: (value: number | string | undefined, name: string) => React.ReactNode
}

/**
 * Tooltip de los gráficos. Usa variables CSS en vez de un prop `theme`, así
 * que sigue al tema de la interfaz sin rerenders extra.
 */
export function ChartTooltip({ active, payload, label, formatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null

  const items = payload as NameValue[]

  return (
    <div className="pointer-events-none z-50 rounded-xl border border-border bg-popover/95 px-3 py-2 text-xs shadow-[0_8px_28px_-6px_rgba(0,0,0,0.45)] backdrop-blur-md">
      {label !== undefined && label !== '' && (
        <div className="mb-1.5 border-b border-border pb-1.5 font-medium tracking-tight text-foreground">
          {label}
        </div>
      )}
      <div className="flex flex-col gap-1">
        {items.map((item, idx) => {
          const color = item.color || item.fill || 'var(--color-chart-1)'
          const display = formatter
            ? formatter(item.value, String(item.name ?? item.dataKey ?? ''))
            : typeof item.value === 'number'
              ? item.value.toLocaleString('es-ES')
              : item.value

          return (
            <div key={idx} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <span
                  className="size-2 rounded-full ring-1 ring-white/20"
                  style={{ backgroundColor: color }}
                />
                {item.name ?? item.dataKey}
              </span>
              <span className="font-semibold tabular-nums text-foreground">{display}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
