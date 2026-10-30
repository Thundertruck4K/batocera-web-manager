import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { ChartTooltip } from './ChartTooltip'

export interface DonutSegment {
  name: string
  value: number
}

interface DonutChartProps {
  data: DonutSegment[]
  height?: number
  /** Texto del centro cuando no hay segmento resaltado. */
  centerLabel?: string
  /** Formatea el valor del centro. */
  formatValue?: (value: number) => string
}

/** Donut con tapas redondeadas y escala monocroma (skill §1). */
export function DonutChart({
  data,
  height = 170,
  centerLabel = 'Total',
  formatValue = (v) => `${v.toFixed(1)}%`,
}: DonutChartProps) {
  const [hover, setHover] = useState<number | null>(null)
  const total = data.reduce((acc, item) => acc + item.value, 0)
  const shades = [
    'var(--color-chart-1)',
    'var(--color-chart-2)',
    'var(--color-chart-3)',
    'var(--color-chart-4)',
  ]

  return (
    <div className="relative w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip
            content={
              <ChartTooltip formatter={(value) => formatValue(Number(value))} />
            }
            cursor={false}
          />
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="58%"
            outerRadius="92%"
            paddingAngle={4}
            cornerRadius={8}
            strokeLinecap="round"
            animationDuration={280}
            onMouseEnter={(_, idx) => setHover(idx)}
            onMouseLeave={() => setHover(null)}
          >
            {data.map((entry, index) => (
              <Cell
                key={`${entry.name}-${index}`}
                fill={shades[index % shades.length]}
                stroke="var(--color-stage)"
                strokeWidth={2}
                style={{
                  transform: hover === index ? 'scale(1.04)' : 'scale(1)',
                  transformOrigin: 'center center',
                  transition: 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold tabular-nums text-foreground">
          {hover !== null ? formatValue(data[hover].value) : formatValue(total)}
        </span>
        <span className="mt-0.5 max-w-[70%] truncate text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          {hover !== null ? data[hover].name : centerLabel}
        </span>
      </div>
    </div>
  )
}
