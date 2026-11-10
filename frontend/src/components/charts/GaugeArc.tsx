import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { TONE_COLOR, type Tone } from '@/lib/tones'

interface GaugeArcProps {
  /** Valor entre 0 y 100. */
  value: number
  /** Texto bajo la cifra (p. ej. "de uso"). */
  caption?: string
  /** Altura del gráfico. */
  height?: number
  /** Sufijo de la cifra (p. ej. "°C"). */
  suffix?: string
  /** Decimales de la cifra. */
  decimals?: number
  /** Acento de color del arco. */
  tone?: Tone
}

/**
 * Velocímetro de 240° (arco de 210° a -30°). Sin tono es monocromo: el valor
 * va en blanco/negro y el resto en la misma tinta con menos opacidad. Con
 * `tone` el arco toma el acento de su tarjeta y el resto se apaga.
 */
export function GaugeArc({
  value,
  caption,
  height = 140,
  suffix = '%',
  decimals = 0,
  tone,
}: GaugeArcProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
  const data = [
    { name: 'Uso', value: clamped },
    { name: 'Resto', value: Math.max(0, 100 - clamped) },
  ]
  const principal = tone ? TONE_COLOR[tone] : 'var(--color-chart-1)'
  const resto = tone ? TONE_COLOR[tone] : 'var(--color-chart-4)'

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
            <Cell fill={principal} fillOpacity={tone ? 1 : undefined} stroke="none" />
            <Cell fill={resto} fillOpacity={tone ? 0.25 : undefined} stroke="none" />
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
