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
}

/** Barras verticales redondeadas con rejilla tenue. */
export function RoundedBarChart({ data, height = 180, formatValue }: RoundedBarChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        Sin datos
      </div>
    )
  }

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
                fill={index === 0 ? 'var(--color-chart-1)' : 'var(--color-chart-3)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
