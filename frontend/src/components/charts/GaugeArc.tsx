import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts'

interface GaugeArcProps {
  /** Valor entre 0 y 100. */
  value: number
  /** Texto bajo la cifra (p. ej. "de uso"). */
  caption?: string
  /** Altura del gráfico. */
  height?: number
  /** Sufjo de la cifra (p. ej. "°C"). */
  suffix?: string
  /** Decimales de la cifra. */
  decimals?: number
}

/**
 * Velocímetro de 240° (arco de 210° a -30°). Escala monocroma: el valor va
 * en blanco/negro y el resto en la misma tinta con menos opacidad.
 */
export function GaugeArc({ value, caption, height = 140, suffix = '%', decimals = 0 }: GaugeArcProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
  const data = [
    { name: 'Uso', value: clamped },
    { name: 'Resto', value: Math.max(0, 100 - clamped) },
  ]

  return (
    <div className="relative w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="58%"
            startAngle={210}
            endAngle={-30}
            innerRadius="68%"
            outerRadius="100%"
            cornerRadius={10}
            paddingAngle={3}
            strokeLinecap="round"
            animationDuration={280}
            isAnimationActive
          >
            <Cell fill="var(--color-chart-1)" stroke="none" />
            <Cell fill="var(--color-chart-4)" stroke="none" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pt-4">
        <span className="text-2xl font-bold tabular-nums tracking-tight text-foreground">
          {clamped.toFixed(decimals)}
          {suffix}
        </span>
        {caption && (
          <span className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            {caption}
          </span>
        )}
      </div>
    </div>
  )
}
