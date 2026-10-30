import { motion } from 'motion/react'
import { Cpu, Gamepad2, HardDrive, RefreshCw, Trophy } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { AreaTrend } from '@/components/charts/AreaTrend'
import { ChartCard } from '@/components/charts/ChartCard'
import { DonutChart } from '@/components/charts/DonutChart'
import { GaugeArc } from '@/components/charts/GaugeArc'
import { RoundedBarChart } from '@/components/charts/RoundedBarChart'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { RandomGameCard } from '@/components/dashboard/RandomGameCard'
import {
  BatteryPanel,
  EsPanel,
  FansPanel,
  GpuPanel,
  NetworkPanel,
} from '@/components/dashboard/StatusPanels'
import { TopGamesPanel } from '@/components/dashboard/TopGamesPanel'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { IconButton } from '@/components/ui/Button'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { PanelCard, StatRow } from '@/components/ui/Card'
import { PillBar, Pill } from '@/components/ui/Pill'
import { useApi } from '@/hooks/useApi'
import { useToast } from '@/hooks/useToast'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api, unwrap } from '@/lib/api'
import type { RandomGame } from '@/lib/types'
import { humanDuration } from '@/lib/utils'

const EASE = [0.16, 1, 0.3, 1] as const

const REFRESH_OPTIONS = [
  { label: 'Automático', value: 10000 },
  { label: 'Cada 30 s', value: 30000 },
  { label: 'Manual', value: 0 },
]

export function Dashboard() {
  const { openMenu } = useShell()
  const { showToast } = useToast()
  const [pollMs, setPollMs] = useState(10000)
  const [randomGame, setRandomGame] = useState<RandomGame | null>(null)
  const [rolling, setRolling] = useState(false)
  const [restarting, setRestarting] = useState(false)

  const dash = useApi(() => api.dashboard(), [], { pollMs })
  const stats = useApi(() => api.gameStats(), [], { pollMs: 60000 })
  const info = useApi(() => api.info(), [], { pollMs: 60000 })

  const data = dash.data
  const primaryDisk = useMemo(() => {
    if (!data?.disk?.length) return null
    return [...data.disk].sort((a, b) => b.size_gb - a.size_gb)[0]
  }, [data?.disk])

  const rollRandom = useCallback(async () => {
    setRolling(true)
    try {
      const res = unwrap(await api.randomGame())
      setRandomGame(res.game)
      if (!res.game) showToast('No hay ROMs en la biblioteca todavía.')
    } catch {
      showToast('No se pudo elegir un juego al azar.', 'error')
    } finally {
      setRolling(false)
    }
  }, [showToast])

  const restartEs = useCallback(async () => {
    setRestarting(true)
    triggerHaptic('medium')
    try {
      const res = await api.esRestart()
      if (res.ok) {
        showToast('EmulationStation se está reiniciando.', 'success')
        dash.refresh()
      } else {
        showToast('No se pudo reiniciar EmulationStation.', 'error')
      }
    } catch {
      showToast('No se pudo reiniciar EmulationStation.', 'error')
    } finally {
      setRestarting(false)
    }
  }, [dash, showToast])

  const topProcesses = useMemo(
    () =>
      (data?.processes ?? []).slice(0, 6).map((p) => ({
        label: p.cmd || p.pid,
        value: Number.parseFloat(p.cpu) || 0,
      })),
    [data?.processes],
  )

  const activity = useMemo(
    () =>
      (stats.data?.activity ?? []).slice(-14).map((a) => ({
        label: a.date.slice(5),
        value: a.count,
      })),
    [stats.data?.activity],
  )

  const title = 'Panel de control'
  const subtitle = data
    ? `Batocera ${data.batocera_version} · encendido desde hace ${data.uptime}`
    : 'Cargando el estado de la máquina…'

  return (
    <>
      <Topbar
        title={title}
        subtitle={subtitle}
        onMenu={openMenu}
        actions={
          <>
            <PillBar className="hidden md:flex">
              {REFRESH_OPTIONS.map((opt) => (
                <Pill
                  key={opt.value}
                  active={pollMs === opt.value}
                  onClick={() => {
                    triggerHaptic('light')
                    setPollMs(opt.value)
                  }}
                >
                  {opt.label}
                </Pill>
              ))}
            </PillBar>
            <IconButton label="Refrescar ahora" onClick={() => dash.refresh()}>
              <RefreshCw className={cnRefresh(dash.loading)} />
            </IconButton>
          </>
        }
      />

      <PageContainer>
        {dash.error && (
          <div className="mb-4 rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive">
            {dash.error}
          </div>
        )}

        {dash.loading && !data ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : data ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: EASE }}
            className="space-y-4"
          >
            {/* Métricas principales */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <ChartCard
                label="CPU"
                tag="Carga"
                value={`${data.cpu.cores} núcleos`}
                footer={
                  <>
                    <span>{data.cpu.model || 'Modelo desconocido'}</span>
                    <span className="font-medium text-foreground">{data.cpu.usage}%</span>
                  </>
                }
              >
                <GaugeArc value={data.cpu.usage} caption="en uso" />
              </ChartCard>

              <ChartCard
                label="Memoria RAM"
                tag="Usada"
                value={`${data.memory.used_mb.toLocaleString('es-ES')} MB`}
                footer={
                  <>
                    <span>de {data.memory.total_mb.toLocaleString('es-ES')} MB</span>
                    <span className="font-medium text-foreground">{data.memory.used_pct}%</span>
                  </>
                }
              >
                <GaugeArc value={data.memory.used_pct} caption="ocupada" />
              </ChartCard>

              <ChartCard
                label="Temperatura"
                tag={data.cpu.temp_src || 'CPU'}
                value={data.cpu.temp != null ? `${data.cpu.temp} °C` : 'Sin sensor'}
                footer={
                  <>
                    <span>Fuente: {data.cpu.temp_src}</span>
                    <span className="font-medium text-foreground">
                      {data.cpu.temp != null && data.cpu.temp > 80 ? 'Alta' : 'Normal'}
                    </span>
                  </>
                }
              >
                <GaugeArc
                  value={data.cpu.temp != null ? Math.min((data.cpu.temp / 100) * 100, 100) : 0}
                  suffix="°C"
                  caption="de 100 °C"
                />
              </ChartCard>

              <ChartCard
                label="Disco principal"
                tag={primaryDisk ? primaryDisk.mount : '—'}
                value={primaryDisk ? `${primaryDisk.used_gb} GB usados` : 'Sin datos'}
                footer={
                  <>
                    <span>{primaryDisk ? `${primaryDisk.free_gb} GB libres` : ''}</span>
                    <span className="font-medium text-foreground">
                      {primaryDisk ? `${primaryDisk.pct}%` : ''}
                    </span>
                  </>
                }
              >
                <DonutChart
                  data={
                    primaryDisk
                      ? [
                          { name: 'Usado', value: primaryDisk.pct },
                          { name: 'Libre', value: Math.max(0, 100 - primaryDisk.pct) },
                        ]
                      : []
                  }
                  centerLabel="ocupado"
                  formatValue={(v) => `${v.toFixed(0)}%`}
                />
              </ChartCard>
            </div>

            {/* Resumen rápido */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <MetricCard
                label="Sistemas"
                value={info.data?.systems_count ?? 0}
                icon={Gamepad2}
                hint={`${info.data?.rom_systems_count ?? 0} con ROMs`}
              />
              <MetricCard
                label="Procesos"
                value={data.processes.length}
                icon={Cpu}
                hint={`${topProcesses[0]?.label ?? 'sin datos'} en cabeza`}
              />
              <MetricCard
                label="Particiones"
                value={data.disk.length}
                icon={HardDrive}
                hint={data.disk_updated ? `Actualizado ${data.disk_updated}` : 'Sin fecha'}
              />
              <MetricCard
                label="Juegos"
                value={stats.data?.totals.games ?? 0}
                icon={Trophy}
                hint={
                  stats.data?.has_playtime
                    ? humanDuration(stats.data.totals.playtime_s)
                    : 'Sin horas registradas'
                }
              />
            </div>

            {/* Gráficos */}
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <ChartCard
                label="Procesos principales"
                tag="CPU %"
                value={`${data.processes.length}`}
                footer={<span>Los 6 procesos con más carga</span>}
              >
                <RoundedBarChart
                  data={topProcesses}
                  formatValue={(v) => `${v.toFixed(1)}%`}
                />
              </ChartCard>

              <ChartCard
                label="Actividad de juego"
                tag="Últimos 14 días"
                value={stats.data ? `${stats.data.totals.playcount}` : '—'}
                footer={<span>Partidas registradas por día</span>}
              >
                <AreaTrend data={activity} formatValue={(v) => `${v} partidas`} />
              </ChartCard>
            </div>

            {/* Estado */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <EsPanel status={data.es} onRestart={restartEs} busy={restarting} />
              <NetworkPanel interfaces={data.network} />
              <FansPanel fans={data.fans} />
              <GpuPanel gpu={data.gpu} />
              <BatteryPanel battery={data.battery} />

              <PanelCard
                title="Almacenamiento"
                subtitle={`${data.disk.length} partición(es)`}
                icon={<HardDrive className="size-4" />}
              >
                {data.disk.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No se han detectado particiones.</p>
                ) : (
                  <div className="divide-y divide-border">
                    {data.disk.map((part) => (
                      <div key={part.mount} className="py-1.5 first:pt-0 last:pb-0">
                        <StatRow
                          label={part.mount}
                          value={`${part.used_gb} / ${part.size_gb} GB`}
                          hint={`${part.pct}%`}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </PanelCard>
            </div>

            {/* Juego y library */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <RandomGameCard
                game={randomGame}
                loading={rolling}
                onRoll={rollRandom}
              />
              <TopGamesPanel stats={stats.data} />
            </div>
          </motion.div>
        ) : null}
      </PageContainer>
    </>
  )
}

function cnRefresh(loading: boolean) {
  return `size-3.5 ${loading ? 'animate-spin' : ''}`
}
