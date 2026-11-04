import { Award, Lock, Medal, Sparkles, Star, Trophy } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import type { RaGame } from '@/lib/types'
import { cn } from '@/lib/utils'

export interface AchievementStatus {
  icon: LucideIcon
  label: string
  /** Si el estado merece el color de acento de la marca. */
  accent: boolean
}

/**
 * Estado del juego en RetroAchievements y el icono que lo representa.
 *
 * - `mastered` / 100 % → trofeo
 * - `completed`        → medalla
 * - `beaten-*`         → premio
 * - >= 50 %            → estrella
 * - en progreso        → destello
 * - sin logros         → candado
 */
export function achievementStatus(game: RaGame): AchievementStatus {
  if (!game.num_awarded) return { icon: Lock, label: 'Sin logros', accent: false }
  if (game.award_kind === 'mastered' || game.percent >= 100) {
    return { icon: Trophy, label: 'Dominado', accent: true }
  }
  if (game.award_kind === 'completed') {
    return { icon: Medal, label: 'Completado', accent: true }
  }
  if (game.award_kind.startsWith('beaten')) {
    return { icon: Award, label: 'Batido', accent: true }
  }
  if (game.percent >= 50) return { icon: Star, label: 'A medio camino', accent: true }
  return { icon: Sparkles, label: 'En progreso', accent: false }
}

/** Anillo de progreso con el icono del estado en el centro. */
function ProgressRing({
  percent,
  accent,
  children,
}: {
  percent: number
  accent: boolean
  children: React.ReactNode
}) {
  const radius = 15
  const circumference = 2 * Math.PI * radius
  const value = Math.max(0, Math.min(100, percent))

  return (
    <div className="relative flex size-11 items-center justify-center">
      <svg viewBox="0 0 36 36" className="absolute inset-0 size-full -rotate-90">
        <circle
          cx="18"
          cy="18"
          r={radius}
          fill="none"
          strokeWidth="3"
          className="stroke-foreground/15"
        />
        <motion.circle
          cx="18"
          cy="18"
          r={radius}
          fill="none"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - (circumference * value) / 100 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className={accent ? 'stroke-brand' : 'stroke-foreground/45'}
        />
      </svg>
      <span className="relative flex size-full items-center justify-center">{children}</span>
    </div>
  )
}

/** URL de la carátula local que dejó el scraper. */
function coverUrl(game: RaGame): string | null {
  if (!game.local || !game.has_art || !game.system || !game.filename) return null
  const base = `/api/rom-image/${encodeURIComponent(game.system)}/${encodeURIComponent(game.filename)}`
  return game.subpath ? `${base}?subpath=${encodeURIComponent(game.subpath)}` : base
}

/** Tarjeta de un juego con su progreso en RetroAchievements. */
export function AchievementCard({ game }: { game: RaGame }) {
  const status = achievementStatus(game)
  const StatusIcon = status.icon
  const cover = coverUrl(game)
  const percent = Math.round(game.percent || 0)
  const date = (game.recent_date || game.award_date || '').slice(0, 10)

  return (
    <article className="card card-hover group flex flex-col overflow-hidden">
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-stage">
        {cover ? (
          <img
            src={cover}
            alt={game.title}
            loading="lazy"
            className="size-full object-cover transition-transform duration-250 ease-out group-hover:scale-[1.03]"
          />
        ) : game.icon ? (
          <div className="flex size-full items-center justify-center bg-gradient-to-br from-muted via-muted/60 to-background">
            <img src={game.icon} alt="" loading="lazy" className="size-20 object-contain opacity-90" />
          </div>
        ) : (
          <div className="flex size-full items-center justify-center bg-gradient-to-br from-muted via-muted/60 to-background">
            <Sparkles className="size-8 text-muted-foreground/50" />
          </div>
        )}

        <div className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-card/90 to-transparent" />

        <span className="absolute left-3 top-3 max-w-[60%] truncate rounded-full bg-background/70 px-2.5 py-1 text-[11px] font-semibold text-foreground backdrop-blur">
          {game.console || game.system_name || '—'}
        </span>

        <div
          className="absolute right-3 top-3 flex size-11 items-center justify-center rounded-full bg-background/70 backdrop-blur"
          title={`${game.num_awarded} de ${game.max_possible} logros (${percent} %)`}
        >
          <ProgressRing percent={percent} accent={status.accent}>
            <StatusIcon
              className={cn(
                'size-4',
                status.accent ? 'text-brand' : 'text-muted-foreground',
              )}
            />
          </ProgressRing>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">
            {game.title}
          </h3>
          <p className="truncate text-[11px] font-medium text-muted-foreground">
            {game.system_name || game.console || 'Sin ROM local'}
          </p>
        </div>

        <div>
          <div className="mb-1 flex items-baseline justify-between gap-2">
            <span className="text-[11px] font-semibold tabular-nums text-foreground">
              {game.num_awarded} / {game.max_possible}
              <span className="ml-1 font-medium text-muted-foreground">logros</span>
            </span>
            <span className="text-[11px] font-semibold tabular-nums text-muted-foreground">
              {percent} %
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <motion.div
              className={cn('h-full rounded-full', status.accent ? 'bg-brand' : 'bg-foreground/25')}
              initial={{ width: 0 }}
              animate={{ width: `${percent}%` }}
              transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
        </div>

        <div className="mt-auto flex flex-wrap items-center gap-x-2.5 gap-y-1 pt-0.5 text-[11px] font-medium text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <StatusIcon className={cn('size-3', status.accent && 'text-brand')} />
            {status.label}
          </span>
          {game.num_awarded_hardcore > 0 && (
            <>
              <span className="h-3 w-px bg-border" />
              <span className="tabular-nums">{game.num_awarded_hardcore} en hardcore</span>
            </>
          )}
          {date && (
            <>
              <span className="h-3 w-px bg-border" />
              <span className="tabular-nums">{date}</span>
            </>
          )}
        </div>
      </div>
    </article>
  )
}
