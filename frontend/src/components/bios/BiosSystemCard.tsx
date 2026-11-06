import { motion } from 'motion/react'
import { Wrench } from 'lucide-react'
import { BIOS_ESTADOS } from '@/lib/biosStates'
import { systemIcon } from '@/lib/systemIcons'
import type { BiosEstado } from '@/lib/types'
import { cn } from '@/lib/utils'

interface BiosSystemCardProps {
  /** Slug del sistema (`adam`, `snes`…). */
  slug: string
  /** Nombre legible del catálogo de Batocera. */
  name: string
  /** Ficheros de BIOS que exige el catálogo. */
  total: number
  /** Los que están bien. */
  ok: number
  /** Los que faltan o están mal. */
  problemas: number
  /** Los que se pueden arreglar con lo que hay en la consola. */
  reparables: number
  /** El estado más grave del sistema. */
  estado: BiosEstado
  /** Abre el detalle del sistema. */
  onOpen: () => void
  /** Repara todo lo reparable de una vez. */
  onRepair: () => void
}

/**
 * Tarjeta de un sistema con BIOS: su icono temático, el nombre, el estado
 * general y la cobertura de la lista oficial de Batocera.
 */
export function BiosSystemCard({
  slug,
  name,
  total,
  ok,
  problemas,
  reparables,
  estado,
  onOpen,
  onRepair,
}: BiosSystemCardProps) {
  const Icon = systemIcon({ name: slug, type: '', manufacturer: '', fullname: name })
  const info = BIOS_ESTADOS[estado]
  const EstadoIcon = info.icon
  const coverage = total > 0 ? Math.min(100, (ok / total) * 100) : 0

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        // Los botones interiores (el de reparar) gestionan su propio teclado.
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
          {slug}
        </span>

        <span
          className={cn(
            'absolute right-3 top-3 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold backdrop-blur',
            info.badge,
          )}
        >
          <EstadoIcon className="size-3" />
          {info.label}
        </span>

        {reparables > 0 && (
          <button
            type="button"
            aria-label={`Reparar las BIOS de ${name}`}
            title="Reparar lo reparable"
            onClick={(event) => {
              event.stopPropagation()
              onRepair()
            }}
            className={cn(
              'absolute bottom-3 right-3 z-10 inline-flex size-9 cursor-pointer items-center justify-center',
              'rounded-full border border-border bg-background/80 text-muted-foreground backdrop-blur',
              'transition-colors duration-150 hover:bg-brand hover:text-primary-foreground',
              'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
            )}
          >
            <Wrench className="size-4" />
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">{name}</h3>
          <p className="truncate text-[11px] font-medium text-muted-foreground">
            {total} {total === 1 ? 'BIOS' : 'BIOS'} en el catálogo de Batocera
          </p>
        </div>

        <div className="flex items-end justify-between gap-3">
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-semibold tabular-nums tracking-[-0.02em] text-foreground">
              {ok}
              <span className="text-muted-foreground">/{total}</span>
            </span>
            <span className="text-[11px] font-medium text-muted-foreground">correctas</span>
          </div>
          {problemas > 0 && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-destructive">
              {problemas} con problemas
            </span>
          )}
        </div>

        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <motion.div
            className={cn('h-full rounded-full', coverage > 0 ? 'bg-brand' : 'bg-foreground/20')}
            initial={{ width: 0 }}
            animate={{ width: `${coverage}%` }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] font-medium text-muted-foreground">
          <span>{reparables > 0 ? `${reparables} reparables sin red` : 'Sin nada que reparar'}</span>
        </div>
      </div>
    </article>
  )
}
