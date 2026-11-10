import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { TONE_COLOR, type Tone } from '@/lib/tones'
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
  /**
   * Valor del centro cuando no hay segmento resaltado. Por defecto, la suma de
   * los segmentos: en un reparto (usado/libre) esa suma siempre es 100 y no
   * dice nada, así que quien lo usa debe pasar el valor que quiere destacar.
   */
  centerValue?: number
  /** Formatea el valor del centro. */
  formatValue?: (value: number) => string
  /** Acento de color del anillo. */
  tone?: Tone
}

/**
 * Donut con tapas redondeadas. Sin tono es monocromo (skill §1); con `tone`
 * el primer segmento lleva el acento y los demás se apagan en la misma
 * tinta, para que se lean como un reparto y no como una lista de colores.
 */
export function DonutChart({
  data,
  height = 170,
  centerLabel = 'Total',
  centerValue,
  formatValue = (v) => `${v.toFixed(1)}%`,
  tone,
}: DonutChartProps) {
  const [hover, setHover] = useState<number | null>(null)
  const total = data.reduce((acc, item) => acc + item.value, 0)
  const headline = centerValue ?? total
  const shades = [
    'var(--color-chart-1)',
    'var(--color-chart-2)',
    'var(--color-chart-3)',
    'var(--color-chart-4)',
  ]
  // Con acento, los segmentos se apagan por pasos: el primero manda.
  const opacidades = [1, 0.5, 0.32, 0.2]

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
                fill={tone ? TONE_COLOR[tone] : shades[index % shades.length]}
                fillOpacity={tone ? opacidades[index % opacidades.length] : undefined}
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
          {hover !== null ? formatValue(data[hover].value) : formatValue(headline)}
        </span>
        <span className="mt-0.5 max-w-[70%] truncate text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          {hover !== null ? data[hover].name : centerLabel}
        </span>
      </div>
    </div>
  )
}
