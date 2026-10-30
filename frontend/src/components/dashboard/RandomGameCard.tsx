import { motion } from 'motion/react'
import { Dices, Gamepad2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { PanelCard } from '@/components/ui/Card'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import type { RandomGame } from '@/lib/types'

interface RandomGameCardProps {
  game: RandomGame | null
  loading?: boolean
  onRoll: () => void
}

const EASE = [0.16, 1, 0.3, 1] as const

export function RandomGameCard({ game, loading, onRoll }: RandomGameCardProps) {
  const [imageFailed, setImageFailed] = useState(false)

  const imageUrl = game?.has_art
    ? `/api/rom-image/${encodeURIComponent(game.system)}/${encodeURIComponent(game.filename)}`
    : null

  const roll = () => {
    triggerHaptic('medium')
    setImageFailed(false)
    onRoll()
  }

  return (
    <PanelCard
      title="Juego al azar"
      subtitle={game ? game.system_name : 'Elige una ROM de tu biblioteca'}
      icon={<Dices className="size-4" />}
      actions={
        <Button size="sm" variant="secondary" onClick={roll} disabled={loading}>
          {loading ? 'Girando…' : 'Girar'}
        </Button>
      }
    >
      {!game ? (
        <div className="flex h-40 items-center justify-center text-xs text-muted-foreground">
          Pulsa «Girar» para elegir una ROM al azar.
        </div>
      ) : (
        <motion.div
          key={`${game.system}/${game.filename}`}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.25, ease: EASE }}
          className="space-y-3"
        >
          <div className="stage relative aspect-[16/10] w-full overflow-hidden">
            {imageUrl && !imageFailed ? (
              <img
                src={imageUrl}
                alt={game.name}
                loading="lazy"
                onError={() => setImageFailed(true)}
                className="size-full object-cover"
              />
            ) : (
              <div className="flex size-full items-center justify-center bg-gradient-to-br from-muted via-muted/60 to-background">
                <Gamepad2 className="size-10 text-muted-foreground/40" />
              </div>
            )}
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">
              {game.name}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{game.system_name}</p>
            {game.meta?.desc && (
              <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                {game.meta.desc}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-1.5">
              {game.meta?.genre && (
                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {game.meta.genre}
                </span>
              )}
              {game.meta?.year && (
                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {game.meta.year}
                </span>
              )}
              {game.meta?.publisher && (
                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {game.meta.publisher}
                </span>
              )}
              {game.meta?.playcount ? (
                <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {game.meta.playcount} partida(s)
                </span>
              ) : null}
            </div>
          </div>
        </motion.div>
      )}
    </PanelCard>
  )
}
