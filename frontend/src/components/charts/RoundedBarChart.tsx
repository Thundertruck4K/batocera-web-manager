import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TONE_COLOR, type Tone } from '@/lib/tones'
import { ChartTooltip } from './ChartTooltip'

export interface BarDatum {
  label: string
  value: number
}

interface RoundedBarChartProps {
  data: BarDatum[]
  height?: number
  /** Formatea el valor en el tooltip. */
  formatValue?: (value: number) => string
  /** Acento de color de las barras. */
  tone?: Tone
}

/**
 * Barras verticales redondeadas con rejilla tenue. Sin tono, la primera barra
 * destaca y las demás se apagan; con `tone` las barras llevan el acento de su
 * tarjeta, la primera a plena y las demás cada vez más tenues.
 */
export function RoundedBarChart({ data, height = 180, formatValue, tone }: RoundedBarChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        Sin datos
      </div>
    )
  }
  const opacidades = [1, 0.55, 0.38, 0.26]

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: -18 }}>
          <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--color-chart-3)', fontSize: 10 }}
            interval={0}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--color-chart-3)', fontSize: 10 }}
            width={38}
          />
          <Tooltip
            cursor={{ fill: 'var(--color-chart-grid)' }}
            content={<ChartTooltip formatter={formatValue ? (v) => formatValue(Number(v)) : undefined} />}
          />
          <Bar dataKey="value" radius={[8, 8, 4, 4]} animationDuration={280} maxBarSize={44}>
            {data.map((entry, index) => (
              <Cell
                key={`${entry.label}-${index}`}
                fill={tone ? TONE_COLOR[tone] : index === 0 ? 'var(--color-chart-1)' : 'var(--color-chart-3)'}
                fillOpacity={
                  tone ? opacidades[index % opacidades.length] : undefined
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
