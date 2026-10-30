import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ChartTooltip } from './ChartTooltip'

export interface TrendPoint {
  label: string
  value: number
}

interface AreaTrendProps {
  data: TrendPoint[]
  height?: number
  formatValue?: (value: number) => string
}

/** Área monótona para series temporales (actividad de juego, I/O…). */
export function AreaTrend({ data, height = 160, formatValue }: AreaTrendProps) {
  const gradientId = 'bm-area-gradient'

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
        <AreaChart data={data} margin={{ top: 8, right: 6, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-chart-2)" stopOpacity={0.45} />
              <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--color-chart-3)', fontSize: 10 }}
            minTickGap={16}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: 'var(--color-chart-3)', fontSize: 10 }}
            width={34}
          />
          <Tooltip
            cursor={{ stroke: 'var(--color-chart-3)', strokeWidth: 1 }}
            content={<ChartTooltip formatter={formatValue ? (v) => formatValue(Number(v)) : undefined} />}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="var(--color-chart-1)"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            animationDuration={280}
            dot={false}
            activeDot={{ r: 3, fill: 'var(--color-chart-1)', stroke: 'none' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
