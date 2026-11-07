import { motion } from 'motion/react'
import {
  CircleAlert,
  CircleCheck,
  Gamepad2,
  PackageSearch,
  RefreshCw,
  Search,
  Wrench,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { BiosSystemCard } from '@/components/bios/BiosSystemCard'
import { BiosSystemModal } from '@/components/bios/BiosSystemModal'
import { Button, IconButton } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pill, PillBar } from '@/components/ui/Pill'
import { useApi } from '@/hooks/useApi'
import { useNotify } from '@/hooks/useNotify'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import { esProblema, esReparable, peorEstado } from '@/lib/biosStates'
import type { BiosEstado, BiosFile } from '@/lib/types'
import { cn } from '@/lib/utils'

const EASE = [0.16, 1, 0.3, 1] as const

type StatusFilter = 'problemas' | 'all' | 'reparables' | 'completos'
type SortKey = 'criticidad' | 'nombre' | 'cobertura'

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'problemas', label: 'Con problemas' },
  { key: 'all', label: 'Todos' },
  { key: 'reparables', label: 'Reparables' },
  { key: 'completos', label: 'Completos' },
]

const SORTS: { key: SortKey; label: string }[] = [
  { key: 'criticidad', label: 'Criticidad' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'cobertura', label: 'Cobertura' },
]

/** Vista de un sistema con BIOS, ya calculada. */
interface BiosSystemView {
  slug: string
  name: string
  files: BiosFile[]
  total: number
  ok: number
  problemas: number
  reparables: number
  estado: BiosEstado
  /** Enlace para buscar las BIOS de este sistema en GitHub. */
  github?: string | null
  /** Criticidad: lo que impide jugar va primero. */
  crit: number
}

export function BiosPage() {
  const { openMenu } = useShell()
  const { showNotify } = useNotify()
  const { data, error, loading, refresh } = useApi(() => api.biosCatalog(), [])

  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('problemas')
  const [sort, setSort] = useState<SortKey>('criticidad')
  /** Slug del sistema abierto en el modal: el modal toma los datos de `systems`,
   *  así que se actualiza solo cuando cambia el catálogo (por ejemplo, tras
   *  subir una BIOS a mano). */
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)

  /* Sistemas con su estado ya calculado. */
  const systems = useMemo<BiosSystemView[]>(() => {
    const list: BiosSystemView[] = []
    for (const [slug, system] of Object.entries(data?.systems ?? {})) {
      const files = system.files ?? []
      const ok = files.filter((file) => file.estado === 'ok' || file.estado === 'sin_verificar').length
      const reparables = files.filter((file) => esReparable(file.estado)).length
      const problemas = files.filter((file) => esProblema(file.estado)).length
      const ausentes = files.filter((file) => file.estado === 'ausente').length
      list.push({
        slug,
        name: system.name || slug,
        files,
        total: files.length,
        ok,
        problemas,
        reparables,
        estado: peorEstado(files.map((file) => file.estado)),
        github: system.github,
        crit: ausentes * 3 + problemas * 2 + reparables * 1.5,
      })
    }
    return list
  }, [data])

  /** El sistema abierto en el modal, con los datos de ahora mismo. */
  const selected = useMemo(
    () => systems.find((system) => system.slug === selectedSlug) ?? null,
    [systems, selectedSlug],
  )

  /* Filtrado y orden. */
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const result = systems.filter((system) => {
      if (needle) {
        const haystack = `${system.slug} ${system.name}`.toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      switch (statusFilter) {
        case 'problemas':
          return system.problemas > 0
        case 'reparables':
          return system.reparables > 0
        case 'completos':
          return system.problemas === 0 && system.reparables === 0
        default:
          return true
      }
    })

    result.sort((a, b) => {
      switch (sort) {
        case 'criticidad':
          return b.crit - a.crit || a.name.localeCompare(b.name, 'es')
        case 'cobertura':
          return a.ok / Math.max(a.total, 1) - b.ok / Math.max(b.total, 1) || a.name.localeCompare(b.name, 'es')
        default:
          return a.name.localeCompare(b.name, 'es')
      }
    })

    return result
  }, [systems, query, statusFilter, sort])

  /* Totales de la biblioteca. */
  const totals = useMemo(() => {
    const files = systems.flatMap((system) => system.files)
    return {
      sistemas: systems.length,
      total: files.length,
      ok: files.filter((file) => file.estado === 'ok' || file.estado === 'sin_verificar').length,
      ausentes: files.filter((file) => file.estado === 'ausente').length,
      reparables: files.filter((file) => esReparable(file.estado)).length,
      extras: data?.extras ?? 0,
    }
  }, [systems, data])

  /** Relee el disco y el catálogo (fuerza el escaneo). */
  const rescan = async () => {
    setScanning(true)
    triggerHaptic('light')
    try {
      await api.biosScan()
      await refresh()
      showNotify({ variant: 'success', title: 'BIOS revisadas' })
    } catch (err) {
      showNotify({
        variant: 'error',
        title: 'No se pudo verificar',
        message: err instanceof Error ? err.message : undefined,
      })
    } finally {
      setScanning(false)
    }
  }

  /* Repara todo lo reparable de un sistema. */
  const repairSystem = async (system: BiosSystemView) => {
    const reparables = system.files.filter((file) => esReparable(file.estado))
    if (!reparables.length) return
    triggerHaptic('medium')
    let ok = 0
    let fail = 0
    for (const file of reparables) {
      try {
        await api.biosRepair({ system: system.slug, file: file.file })
        ok += 1
      } catch {
        fail += 1
      }
    }
    showNotify({
      variant: fail ? 'error' : 'success',
      title: fail ? `${ok} reparadas y ${fail} con problemas` : `${ok} BIOS reparadas`,
      message: fail
        ? 'Las que fallaron se pueden subir a mano.'
        : 'Colocadas donde Batocera las espera.',
    })
    await refresh()
  }

  return (
    <>
      <Topbar
        title="ROMs y BIOS"
        subtitle={`${totals.sistemas} sistemas · ${totals.ok} de ${totals.total} BIOS en su sitio`}
        onMenu={openMenu}
        actions={
          <IconButton label="Volver a verificar las BIOS" onClick={rescan}>
            <RefreshCw className={cn('size-4', (loading || scanning) && 'animate-spin')} />
          </IconButton>
        }
      />

      <PageContainer>
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">{error}</span>
            <Button size="sm" variant="outline" onClick={refresh}>
              Reintentar
            </Button>
          </div>
        )}

        {/* Resumen */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard label="Sistemas" value={totals.sistemas} icon={Gamepad2} />
          <MetricCard
            label="En su sitio"
            value={totals.ok.toLocaleString('es-ES')}
            icon={CircleCheck}
            accent="good"
            hint="donde las espera Batocera"
          />
          <MetricCard
            label="Ausentes"
            value={totals.ausentes.toLocaleString('es-ES')}
            icon={PackageSearch}
            accent="bad"
            hint="no están en la consola"
          />
          <MetricCard
            label="Reparables"
            value={totals.reparables.toLocaleString('es-ES')}
            icon={Wrench}
            hint="están en la consola"
          />
        </div>

        {/* Filtros */}
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar sistema…"
                aria-label="Buscar sistema"
                className={cn(
                  'h-10 w-full rounded-xl border border-input bg-transparent pl-9 pr-3 text-sm text-foreground',
                  'placeholder:text-muted-foreground/70 transition-colors duration-150',
                  'focus:border-ring focus:outline-none focus:ring-3 focus:ring-ring/40',
                )}
              />
              {query && (
                <button
                  type="button"
                  aria-label="Limpiar búsqueda"
                  onClick={() => setQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded-lg p-1.5 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>
            <p className="text-[11px] font-medium tabular-nums text-muted-foreground">
              {filtered.length} de {totals.sistemas} sistemas
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <PillBar>
              {STATUS_FILTERS.map((option) => (
                <Pill
                  key={option.key}
                  active={statusFilter === option.key}
                  onClick={() => {
                    triggerHaptic('light')
                    setStatusFilter(option.key)
                  }}
                >
                  {option.label}
                </Pill>
              ))}
            </PillBar>

            <PillBar>
              {SORTS.map((option) => (
                <Pill
                  key={option.key}
                  active={sort === option.key}
                  onClick={() => {
                    triggerHaptic('light')
                    setSort(option.key)
                  }}
                >
                  {option.label}
                </Pill>
              ))}
            </PillBar>
          </div>
        </div>

        {/* Tarjetas */}
        {loading && !data ? (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="card h-72 animate-pulse bg-muted/40" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              icon={<CircleCheck className="size-5" />}
              title={statusFilter === 'problemas' ? 'Ninguna BIOS con problemas' : 'Ningún sistema coincide'}
              description={
                statusFilter === 'problemas'
                  ? 'Todas las BIOS que pide Batocera están donde deben.'
                  : 'Prueba con otro texto o cambia los filtros.'
              }
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery('')
                    setStatusFilter('all')
                  }}
                >
                  Quitar filtros
                </Button>
              }
            />
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {filtered.map((system, index) => (
              <motion.div
                key={system.slug}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.25,
                  ease: EASE,
                  delay: Math.min(index * 0.015, 0.05),
                }}
              >
                <BiosSystemCard
                  slug={system.slug}
                  name={system.name}
                  total={system.total}
                  ok={system.ok}
                  problemas={system.problemas}
                  reparables={system.reparables}
                  estado={system.estado}
                  onOpen={() => {
                    triggerHaptic('light')
                    setSelectedSlug(system.slug)
                  }}
                  onRepair={() => repairSystem(system)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </PageContainer>

      <BiosSystemModal
        open={Boolean(selected)}
        onClose={() => setSelectedSlug(null)}
        slug={selected?.slug ?? ''}
        name={selected?.name ?? ''}
        files={selected?.files ?? []}
        github={selected?.github}
        onRepaired={refresh}
      />
    </>
  )
}
