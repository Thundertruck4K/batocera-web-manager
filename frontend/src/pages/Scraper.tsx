import { AnimatePresence, motion } from 'motion/react'
import {
  ArrowLeft,
  CircleAlert,
  Download,
  Gamepad2,
  Image as ImageIcon,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { RomFolderView } from '@/components/scraper/RomFolderView'
import { ScrapeRomModal } from '@/components/scraper/ScrapeRomModal'
import { ScrapeSystemModal } from '@/components/scraper/ScrapeSystemModal'
import { ScraperSystemCard } from '@/components/scraper/ScraperSystemCard'
import { Button, IconButton } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pill, PillBar } from '@/components/ui/Pill'
import { useApi } from '@/hooks/useApi'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import { systemType } from '@/lib/systemIcons'
import type { RomFolderItem, RomSystemSummary, ScraperSource } from '@/lib/types'
import { cn } from '@/lib/utils'

const EASE = [0.16, 1, 0.3, 1] as const

type StatusFilter = 'with-roms' | 'all' | 'with-media' | 'without-media' | 'empty' | 'gamelist'
type SortKey = 'name' | 'roms-desc' | 'roms-asc' | 'media-desc' | 'coverage'

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'with-roms', label: 'Con ROMs' },
  { key: 'all', label: 'Todos' },
  { key: 'with-media', label: 'Con media' },
  { key: 'without-media', label: 'Sin media' },
  { key: 'empty', label: 'Vacíos' },
  { key: 'gamelist', label: 'Con gamelist' },
]

const SORTS: { key: SortKey; label: string }[] = [
  { key: 'name', label: 'Nombre' },
  { key: 'roms-desc', label: 'Más ROMs' },
  { key: 'roms-asc', label: 'Menos ROMs' },
  { key: 'media-desc', label: 'Más media' },
  { key: 'coverage', label: 'Cobertura' },
]

/** Fuente configurada en el servidor (con reserva a ScreenScraper). */
function activeSource(config: { scraper_source?: string } | null): ScraperSource {
  const value = config?.scraper_source
  if (value === 'thegamesdb' || value === 'igdb') return value
  return 'screenscraper'
}

/** ¿Alguna fuente tiene credenciales guardadas? */
function anySourceReady(config: {
  ss_user_set?: boolean
  ss_password_set?: boolean
  tgdb_apikey_set?: boolean
  igdb_client_id_set?: boolean
  igdb_client_secret_set?: boolean
} | null): boolean {
  if (!config) return true
  return Boolean(
    (config.ss_user_set && config.ss_password_set) ||
      config.tgdb_apikey_set ||
      (config.igdb_client_id_set && config.igdb_client_secret_set),
  )
}

export function ScraperPage() {
  const { openMenu } = useShell()
  const { data: systems, error, loading, refresh } = useApi(() => api.romSystems(), [])
  const { data: config, refresh: refreshConfig } = useApi(() => api.scraperConfig(), [])

  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('with-roms')
  const [sort, setSort] = useState<SortKey>('roms-desc')

  const [selected, setSelected] = useState<RomSystemSummary | null>(null)
  const [subpath, setSubpath] = useState('')
  const [scrapeOpen, setScrapeOpen] = useState(false)
  /** Sistemas a escrapear desde el modal. Vacío = sólo configuración. */
  const [scrapeSystems, setScrapeSystems] = useState<string[]>([])
  const [romItem, setRomItem] = useState<RomFolderItem | null>(null)

  const {
    data: folderData,
    error: folderError,
    loading: folderLoading,
    refresh: refreshFolder,
  } = useApi(() => api.romFolder(selected?.name ?? '', subpath), [selected?.name, subpath], {
    enabled: Boolean(selected),
  })

  const source = activeSource(config)

  /* Tipos de sistema presentes en la biblioteca (para el filtro). */
  const types = useMemo(() => {
    const set = new Set<string>()
    for (const system of systems ?? []) {
      set.add(systemType(system))
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'es'))
  }, [systems])

  /* Filtrado y orden de los sistemas. */
  const filtered = useMemo(() => {
    const list = systems ?? []
    const needle = query.trim().toLowerCase()

    const result = list.filter((system) => {
      if (needle) {
        const haystack =
          `${system.name} ${system.fullname} ${system.manufacturer} ${system.platform} ${systemType(system)}`.toLowerCase()
        if (!haystack.includes(needle)) return false
      }
      if (typeFilter !== 'all' && systemType(system) !== typeFilter) return false
      switch (statusFilter) {
        case 'with-roms':
          return system.rom_count > 0
        case 'with-media':
          return system.image_count > 0
        case 'without-media':
          return system.rom_count > 0 && system.image_count === 0
        case 'empty':
          return system.rom_count === 0
        case 'gamelist':
          return system.has_gamelist
        default:
          return true
      }
    })

    result.sort((a, b) => {
      switch (sort) {
        case 'roms-desc':
          return b.rom_count - a.rom_count || a.name.localeCompare(b.name)
        case 'roms-asc':
          return a.rom_count - b.rom_count || a.name.localeCompare(b.name)
        case 'media-desc':
          return b.media_count - a.media_count || a.name.localeCompare(b.name)
        case 'coverage':
          return (
            b.media_count / Math.max(b.rom_count, 1) - a.media_count / Math.max(a.rom_count, 1) ||
            a.name.localeCompare(b.name)
          )
        default:
          return a.name.localeCompare(b.name)
      }
    })

    return result
  }, [systems, query, typeFilter, statusFilter, sort])

  /* Métricas globales de la biblioteca. */
  const totals = useMemo(() => {
    const list = systems ?? []
    const roms = list.reduce((acc, system) => acc + system.rom_count, 0)
    const media = list.reduce((acc, system) => acc + (system.image_count || 0), 0)
    return {
      systems: list.length,
      roms,
      media,
      pending: Math.max(0, roms - media),
    }
  }, [systems])

  /** Al guardar y validar: se refresca todo y se vuelve a la lista principal. */
  const handleSaved = () => {
    refresh()
    refreshConfig()
    refreshFolder()
    setRomItem(null)
    setSelected(null)
    setSubpath('')
  }

  /** Abre el modal de scraping para uno o varios sistemas. */
  const openScrape = (systems: string[]) => {
    triggerHaptic('light')
    setScrapeSystems(systems)
    setScrapeOpen(true)
  }

  const openSystem = (system: RomSystemSummary) => {
    triggerHaptic('light')
    setSelected(system)
    setSubpath('')
  }

  /* ── Vista de la biblioteca de sistemas ──────────────────────────── */
  const listView = (
    <>
      <Topbar
        title="Scraper"
        subtitle={`${totals.systems} sistemas · ${totals.roms.toLocaleString('es-ES')} ROMs`}
        onMenu={openMenu}
        actions={
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => openScrape([])}
            >
              <Settings className="size-4" />
              Configurar
            </Button>
            <IconButton
              label="Recargar sistemas"
              onClick={() => {
                triggerHaptic('light')
                refresh()
              }}
            >
              <RefreshCw className={cn('size-4', loading && 'animate-spin')} />
            </IconButton>
          </>
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

        {config && !anySourceReady(config) && (
          <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">
              Ninguna fuente de scraping tiene credenciales. Pulsa «Configurar» para añadirlas.
            </span>
            <Button size="sm" variant="outline" onClick={() => openScrape([])}>
              <Settings className="size-4" />
              Configurar
            </Button>
          </div>
        )}

        {/* Resumen */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard label="Sistemas" value={totals.systems} icon={Gamepad2} />
          <MetricCard label="ROMs" value={totals.roms.toLocaleString('es-ES')} icon={Sparkles} />
          <MetricCard
            label="Con media"
            value={totals.media.toLocaleString('es-ES')}
            icon={ImageIcon}
            accent="good"
          />
          <MetricCard
            label="Sin media"
            value={totals.pending.toLocaleString('es-ES')}
            icon={Download}
            hint="pendientes de scrapear"
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
                placeholder="Buscar sistema, fabricante o plataforma…"
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
              {filtered.length} de {totals.systems} sistemas
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

            {types.length > 1 && (
              <PillBar>
                <Pill active={typeFilter === 'all'} onClick={() => setTypeFilter('all')}>
                  Todo tipo
                </Pill>
                {types.map((type) => (
                  <Pill key={type} active={typeFilter === type} onClick={() => setTypeFilter(type)}>
                    {type}
                  </Pill>
                ))}
              </PillBar>
            )}

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
        {loading && !systems ? (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="card h-72 animate-pulse bg-muted/40" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              icon={<Search className="size-5" />}
              title="Ningún sistema coincide"
              description="Prueba con otro texto o cambia los filtros para ver más sistemas de la biblioteca."
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery('')
                    setTypeFilter('all')
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
                key={system.name}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.25,
                  ease: EASE,
                  delay: Math.min(index * 0.015, 0.05),
                }}
              >
                <ScraperSystemCard
                  system={system}
                  onOpen={() => openSystem(system)}
                  onScrape={() => openScrape([system.name])}
                />
              </motion.div>
            ))}
          </div>
        )}
      </PageContainer>
    </>
  )

  /* ── Vista de los ROMs de un sistema ─────────────────────────────── */
  const folder = folderData?.folder ?? null
  const mediaCount = folder
    ? folder.items.filter((item) => item.is_rom && item.has_image).length
    : 0
  const pendingCount = folder
    ? folder.items.filter((item) => item.is_rom && !item.has_image).length
    : 0

  const systemView = selected ? (
    <>
      <Topbar
        title={selected.fullname || selected.name}
        subtitle={`${selected.name} · ${selected.rom_count.toLocaleString('es-ES')} ROMs · ${mediaCount} con media · ${pendingCount} sin media`}
        onMenu={openMenu}
        actions={
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => openScrape([selected.name])}
            >
              <Download className="size-4" />
              Escapear sistema
            </Button>
            <IconButton
              label="Recargar ROMs"
              onClick={() => {
                triggerHaptic('light')
                refreshFolder()
              }}
            >
              <RefreshCw className={cn('size-4', folderLoading && 'animate-spin')} />
            </IconButton>
          </>
        }
      />

      <PageContainer>
        <button
          type="button"
          onClick={() => {
            triggerHaptic('light')
            setSelected(null)
            setSubpath('')
          }}
          className={cn(
            'mb-4 inline-flex cursor-pointer items-center gap-1.5 rounded-xl px-2 py-1.5 text-xs font-semibold',
            'text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground',
            'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
          )}
        >
          <ArrowLeft className="size-3.5" />
          Volver a la lista
        </button>

        {folderError && (
          <div className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">{folderError}</span>
            <Button size="sm" variant="outline" onClick={refreshFolder}>
              Reintentar
            </Button>
          </div>
        )}

        <RomFolderView
          folder={folder}
          system={selected.name}
          subpath={subpath}
          loading={folderLoading}
          onOpenRom={(rom) => {
            triggerHaptic('light')
            setRomItem(rom)
          }}
          onOpenFolder={(path) => {
            triggerHaptic('light')
            setSubpath(path)
          }}
          onGoRoot={() => setSubpath('')}
        />
      </PageContainer>
    </>
  ) : null

  return (
    <>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={selected ? `sistema-${selected.name}-${subpath}` : 'biblioteca'}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.28, ease: EASE }}
        >
          {selected ? systemView : listView}
        </motion.div>
      </AnimatePresence>

      {/* Modal de scraping de sistema completo */}
      <ScrapeSystemModal
        open={scrapeOpen}
        onClose={() => setScrapeOpen(false)}
        systems={scrapeSystems}
        onSaved={handleSaved}
      />

      {/* Modal de un ROM concreto */}
      <ScrapeRomModal
        open={Boolean(romItem)}
        onClose={() => setRomItem(null)}
        system={selected?.name ?? ''}
        subpath={subpath}
        rom={romItem}
        source={source}
        onSaved={handleSaved}
      />
    </>
  )
}
