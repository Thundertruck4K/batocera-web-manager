import { motion } from 'motion/react'
import { Download, Image as ImageIcon } from 'lucide-react'
import type { RomSystemSummary } from '@/lib/types'
import { systemIcon, systemType } from '@/lib/systemIcons'
import { cn } from '@/lib/utils'

interface ScraperSystemCardProps {
  system: RomSystemSummary
  /** Abre la pantalla con los ROMs del sistema. */
  onOpen: () => void
  /** Abre el modal flotante para escrapear el sistema completo. */
  onScrape: () => void
}

/** Subtítulo de la tarjeta: fabricante y año de lanzamiento. */
function systemSubtitle(system: RomSystemSummary): string {
  const parts = [system.manufacturer, system.release].filter(Boolean)
  return parts.length ? parts.join(' · ') : system.type || ''
}

/**
 * Tarjeta de un sistema con el icono temático, su nombre, una breve
 * descripción y el número de ROMs que tiene.
 */
export function ScraperSystemCard({ system, onOpen, onScrape }: ScraperSystemCardProps) {
  const Icon = systemIcon(system)
  const title = system.fullname && system.fullname !== system.name ? system.fullname : system.name
  const subtitle = systemSubtitle(system)
  const type = systemType(system)
  const coverage = system.rom_count > 0 ? Math.min(100, (system.image_count / system.rom_count) * 100) : 0

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        // Los botones interiors (el de escrapear) gestionan su propio teclado.
        if (event.target !== event.currentTarget) return
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onOpen()
        }
      }}
      className={cn(
        'card card-hover group relative flex cursor-pointer flex-col overflow-hidden',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
      )}
    >
      {/* Escenario con el icono temático del sistema */}
      <div className="relative flex aspect-[16/10] w-full items-center justify-center overflow-hidden bg-gradient-to-br from-brand/15 via-muted/60 to-background">
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.18] [background-image:radial-gradient(circle_at_1px_1px,currentColor_1px,transparent_0)] [background-size:18px_18px]"
        />
        <Icon
          className="relative size-14 text-brand transition-transform duration-250 ease-out group-hover:scale-105"
          aria-hidden
        />

        <span className="absolute left-3 top-3 rounded-full bg-background/75 px-2.5 py-1 font-mono text-[11px] font-semibold text-foreground backdrop-blur">
          {system.name}
        </span>

        {type && (
          <span className="absolute right-3 top-3 rounded-full bg-background/75 px-2.5 py-1 text-[11px] font-semibold text-muted-foreground backdrop-blur">
            {type}
          </span>
        )}

        <button
          type="button"
          aria-label={`Escrapear ${title}`}
          title="Escrapear sistema"
          onClick={(event) => {
            event.stopPropagation()
            onScrape()
          }}
          className={cn(
            'absolute bottom-3 right-3 z-10 inline-flex size-9 cursor-pointer items-center justify-center',
            'rounded-full border border-border bg-background/80 text-muted-foreground backdrop-blur',
            'transition-colors duration-150 hover:bg-brand hover:text-primary-foreground',
            'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
          )}
        >
          <Download className="size-4" />
        </button>
      </div>

      {/* Detalle */}
      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">{title}</h3>
          <p className="truncate text-[11px] font-medium text-muted-foreground">
            {subtitle || system.platform || 'Sin descripción'}
          </p>
        </div>

        {/* ROMs y media */}
        <div className="flex items-end justify-between gap-3">
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-semibold tabular-nums tracking-[-0.02em] text-foreground">
              {system.rom_count.toLocaleString('es-ES')}
            </span>
            <span className="text-[11px] font-medium text-muted-foreground">
              {system.rom_count === 1 ? 'ROM' : 'ROMs'}
            </span>
          </div>
          <span className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
            <ImageIcon className="size-3" />
            {system.image_count} con media
          </span>
        </div>

        {/* Cobertura de media */}
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <motion.div
            className={cn('h-full rounded-full', coverage > 0 ? 'bg-brand' : 'bg-foreground/20')}
            initial={{ width: 0 }}
            animate={{ width: `${coverage}%` }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] font-medium text-muted-foreground">
          <span>{system.size_human}</span>
          {system.has_gamelist && (
            <span className="rounded-full bg-muted px-2 py-0.5">gamelist</span>
          )}
        </div>
      </div>
    </article>
  )
}
