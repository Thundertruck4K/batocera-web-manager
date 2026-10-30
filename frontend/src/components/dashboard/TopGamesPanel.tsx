import { Trophy } from 'lucide-react'
import { PanelCard } from '@/components/ui/Card'
import type { GameStats } from '@/lib/types'
import { humanDuration } from '@/lib/utils'

export function TopGamesPanel({ stats }: { stats: GameStats | null }) {
  const top = stats?.top_games ?? []

  return (
    <PanelCard
      title="Más jugados"
      subtitle={
        stats?.has_playtime
          ? `${stats.totals.playcount} partidas · ${humanDuration(stats.totals.playtime_s)}`
          : 'Sin datos de juego'
      }
      icon={<Trophy className="size-4" />}
    >
      {top.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Ningún gamelist.xml registra partidas jugadas todavía.
        </p>
      ) : (
        <ol className="space-y-1">
          {top.slice(0, 6).map((game, index) => (
            <li
              key={`${game.system}-${game.path}-${index}`}
              className="flex items-center gap-3 rounded-xl px-2 py-1.5 transition-colors duration-150 hover:bg-muted"
            >
              <span className="w-4 shrink-0 text-[11px] font-bold tabular-nums text-muted-foreground">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-foreground">
                  {game.name}
                </span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {game.system}
                  {game.lastplayed ? ` · ${game.lastplayed}` : ''}
                </span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block text-sm font-semibold tabular-nums text-foreground">
                  {game.playcount}
                </span>
                <span className="block text-[10px] text-muted-foreground">
                  {humanDuration(game.playtime_s)}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </PanelCard>
  )
}
