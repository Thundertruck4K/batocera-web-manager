import { motion } from 'motion/react'
import {
  CircleAlert,
  Gamepad2,
  Medal,
  RefreshCw,
  Settings,
  Sparkles,
  Trophy,
  UserRound,
  Zap,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AchievementCard } from '@/components/achievements/AchievementCard'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { Button, IconButton } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pill, PillBar } from '@/components/ui/Pill'
import { useApi } from '@/hooks/useApi'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import type { RaGame } from '@/lib/types'

type SortKey = 'awarded' | 'percent' | 'total'

const SORTS: { key: SortKey; label: string }[] = [
  { key: 'awarded', label: 'Mis logros' },
  { key: 'percent', label: '% completado' },
  { key: 'total', label: 'Logros del juego' },
]

function sortGames(games: RaGame[], sort: SortKey): RaGame[] {
  const sorted = [...games]
  if (sort === 'awarded') {
    sorted.sort((a, b) => b.num_awarded - a.num_awarded || b.percent - a.percent)
  } else if (sort === 'percent') {
    sorted.sort((a, b) => b.percent - a.percent || b.num_awarded - a.num_awarded)
  } else {
    sorted.sort((a, b) => b.max_possible - a.max_possible || b.num_awarded - a.num_awarded)
  }
  return sorted
}

/** Formatea una fecha de la API (ISO) como día/mes/año. */
function formatDate(value: string): string {
  const day = value.slice(0, 10)
  if (!day) return ''
  const [y, m, d] = day.split('-')
  return `${d}/${m}/${y}`
}

/** Antigüedad de los datos descargados, en texto corto. */
function formatAge(seconds: number | null | undefined): string {
  const s = Math.max(0, Math.floor(seconds ?? 0))
  if (s < 60) return `${s} s`
  if (s < 3600) return `${Math.floor(s / 60)} min`
  if (s < 86400) return `${Math.floor(s / 3600)} h`
  return `${Math.floor(s / 86400)} d`
}

export function AchievementsPage() {
  const { openMenu } = useShell()
  const navigate = useNavigate()
  /* La API de RetroAchievements se llama lo justo: al entrar se usan los datos
     guardados y sólo el botón de recargar pide datos frescos. */
  const [force, setForce] = useState(false)
  const { data, error, loading, refresh } = useApi(() => api.raGames(force), [force])
  const [sort, setSort] = useState<SortKey>('awarded')

  const games = useMemo(() => sortGames(data?.games ?? [], sort), [data, sort])

  const totals = useMemo(() => {
    const list = data?.games ?? []
    return {
      awarded: list.reduce((acc, g) => acc + (g.num_awarded || 0), 0),
      possible: list.reduce((acc, g) => acc + (g.max_possible || 0), 0),
    }
  }, [data])

  const profile = data?.profile
  const awards = data?.awards

  /* Sin credenciales: avisar y llevar a Configuración. */
  if (data && !data.configured) {
    return (
      <>
        <Topbar title="Logros" subtitle="RetroAchievements" onMenu={openMenu} />
        <PageContainer>
          <EmptyState
            icon={<UserRound className="size-5" />}
            title="Configura tu cuenta de RetroAchievements"
            description="Para ver tus logros hace falta tu usuario y tu Web API Key de RetroAchievements. Se guardan en el manager y sólo se usan para leer tus datos; no se comparten con nadie más."
            action={
              <Button variant="primary" onClick={() => navigate('/configuracion')}>
                <Settings className="size-4" />
                Ir a Configuración
              </Button>
            }
          />
        </PageContainer>
      </>
    )
  }

  /* Integración desactivada. */
  if (data && !data.enabled) {
    return (
      <>
        <Topbar title="Logros" subtitle="RetroAchievements" onMenu={openMenu} />
        <PageContainer>
          <EmptyState
            icon={<CircleAlert className="size-5" />}
            title="RetroAchievements está desactivado"
            description="Hay credenciales guardadas, pero el interruptor de la integración está apagado. Actívalo en Configuración para volver a ver tus logros."
            action={
              <Button variant="primary" onClick={() => navigate('/configuracion')}>
                <Settings className="size-4" />
                Ir a Configuración
              </Button>
            }
          />
        </PageContainer>
      </>
    )
  }

  return (
    <>
      <Topbar
        title="Logros"
        subtitle={
          profile?.user
            ? `${profile.user} · ${profile.points.toLocaleString('es-ES')} puntos`
            : 'RetroAchievements'
        }
        onMenu={openMenu}
        actions={
          <IconButton
            label="Recargar logros"
            onClick={() => {
              triggerHaptic('light')
              setForce(true)
              refresh()
            }}
          >
            <RefreshCw className={loading ? 'size-4 animate-spin' : 'size-4'} />
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
          <MetricCard
            label="Puntos"
            value={(profile?.points ?? 0).toLocaleString('es-ES')}
            icon={Trophy}
            hint={profile ? `true ${(profile.true_points ?? 0).toLocaleString('es-ES')}` : undefined}
            accent="good"
          />
          <MetricCard
            label="Juegos"
            value={data?.total ?? 0}
            icon={Gamepad2}
            hint={data ? `${data.matched} con ROM local` : undefined}
          />
          <MetricCard
            label="Logros"
            value={totals.awarded}
            unit={`/ ${totals.possible}`}
            icon={Sparkles}
            accent="good"
          />
          <MetricCard
            label="Dominados"
            value={awards?.mastery ?? 0}
            unit={`/ ${awards?.total ?? 0}`}
            icon={Medal}
            hint={awards ? `${awards.beaten_hardcore} batidos en hardcore` : undefined}
          />
        </div>

        {/* Filtros */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
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

          {profile?.member_since && (
            <p className="text-[11px] font-medium text-muted-foreground">
              Miembro desde {formatDate(profile.member_since)}
            </p>
          )}
          {data?.updated && (
            <p className="text-[11px] font-medium text-muted-foreground">
              {data.cached
                ? `Datos guardados · actualizados hace ${formatAge(data.age)}`
                : 'Datos descargados de RetroAchievements'}
              {data.throttled && ' · se respeta el intervalo mínimo entre peticiones'}
            </p>
          )}
        </div>

        {/* Tarjetas */}
        {loading && !data ? (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card h-64 animate-pulse bg-muted/40" />
            ))}
          </div>
        ) : games.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              icon={<Zap className="size-5" />}
              title="Sin logros todavía"
              description="No hay juegos con progreso en RetroAchievements para esta cuenta. En cuanto desbloquees el primer logro, aparecerá aquí con su carátula."
            />
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {games.map((game, index) => (
              <motion.div
                key={game.game_id ?? game.title}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.25,
                  ease: [0.16, 1, 0.3, 1],
                  delay: Math.min(index * 0.015, 0.05),
                }}
              >
                <AchievementCard game={game} />
              </motion.div>
            ))}
          </div>
        )}
      </PageContainer>
    </>
  )
}
