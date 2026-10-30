import {
  BatteryCharging,
  BatteryFull,
  BatteryLow,
  Cpu,
  Fan,
  Gauge,
  MonitorCog,
  Network,
} from 'lucide-react'
import { PanelCard, StatRow } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import type { BatteryInfo, EsStatus, FanEntry, NetworkIface } from '@/lib/types'
import { cn } from '@/lib/utils'

/* ── EmulationStation ──────────────────────────────────────────────────── */

export function EsPanel({
  status,
  onRestart,
  busy,
}: {
  status: EsStatus | null
  onRestart?: () => void
  busy?: boolean
}) {
  const running = status?.running ?? false
  const pending = status?.restart_pending ?? false

  return (
    <PanelCard
      title="EmulationStation"
      subtitle={running ? 'En ejecución' : 'Detenido'}
      icon={<MonitorCog className="size-4" />}
      actions={
        onRestart && (
          <Button size="sm" variant="secondary" onClick={onRestart} disabled={busy}>
            {pending ? 'Reiniciando…' : 'Reiniciar'}
          </Button>
        )
      }
    >
      <div className="flex items-center gap-3 rounded-2xl border border-border bg-muted/40 px-3 py-3">
        <span
          className={cn(
            'size-2.5 shrink-0 rounded-full',
            running ? 'bg-emerald-500' : 'bg-muted-foreground/40',
          )}
        />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            {running ? 'Activo' : 'Apagado'}
          </p>
          <p className="truncate text-[11px] text-muted-foreground">
            {running
              ? `PID ${status?.pid ?? '—'} · puerto ${status?.port ?? '—'}`
              : 'No se encuentra el proceso'}
          </p>
        </div>
      </div>

      {pending && (
        <p className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] font-medium text-amber-600 dark:text-amber-400">
          Hay cambios pendientes: reinicia EmulationStation para aplicarlos.
        </p>
      )}
    </PanelCard>
  )
}

/* ── Red ───────────────────────────────────────────────────────────────── */

export function NetworkPanel({ interfaces }: { interfaces: NetworkIface[] }) {
  return (
    <PanelCard
      title="Red"
      subtitle={interfaces.length > 0 ? `${interfaces.length} interfaz(es)` : 'Sin interfaces'}
      icon={<Network className="size-4" />}
    >
      {interfaces.length === 0 ? (
        <p className="text-xs text-muted-foreground">No se han detectado interfaces de red.</p>
      ) : (
        <div className="divide-y divide-border">
          {interfaces.map((nic) => (
            <div key={nic.iface} className="py-2 first:pt-0 last:pb-0">
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium text-foreground">{nic.iface}</span>
                <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                  ↓ {nic.rx} · ↑ {nic.tx}
                </span>
              </div>
              {nic.ip && (
                <p className="truncate font-mono text-[11px] text-muted-foreground">{nic.ip}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </PanelCard>
  )
}

/* ── Ventiladores ──────────────────────────────────────────────────────── */

export function FansPanel({ fans }: { fans: FanEntry[] }) {
  return (
    <PanelCard
      title="Ventiladores"
      subtitle={fans.length > 0 ? `${fans.length} sensor(es)` : 'Sin sensores'}
      icon={<Fan className="size-4" />}
    >
      {fans.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Esta máquina no expone sensores de ventilador por hwmon.
        </p>
      ) : (
        <div className="space-y-2">
          {fans.map((fan) => (
            <div
              key={`${fan.name}-${fan.index}`}
              className="flex items-center justify-between gap-3 rounded-xl border border-border px-3 py-2"
            >
              <span className="min-w-0 truncate text-sm font-medium text-foreground">
                {fan.label || fan.name}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span
                  className={cn(
                    'size-2 rounded-full',
                    fan.status === 'ok'
                      ? 'bg-emerald-500'
                      : fan.status === 'fault'
                        ? 'bg-destructive'
                        : 'bg-muted-foreground/40',
                  )}
                />
                <span className="text-sm font-semibold tabular-nums text-foreground">
                  {fan.rpm.toLocaleString('es-ES')}
                  <span className="ml-0.5 text-[10px] font-normal text-muted-foreground">RPM</span>
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </PanelCard>
  )
}

/* ── Batería ───────────────────────────────────────────────────────────── */

export function BatteryPanel({ battery }: { battery: BatteryInfo | null }) {
  if (!battery?.available) return null

  const capacity = battery.capacity ?? 0
  const Icon = battery.charging ? BatteryCharging : capacity <= 20 ? BatteryLow : BatteryFull
  const tone =
    capacity <= 20 && !battery.charging ? 'text-destructive' : 'text-emerald-500'

  return (
    <PanelCard title="Batería" icon={<Icon className={cn('size-4', tone)} />}>
      <StatRow label="Capacidad" value={`${Math.round(capacity)}%`} />
      <StatRow label="Estado" value={battery.status ?? '—'} />
      {battery.minutes != null && (
        <StatRow
          label="Autonomía"
          value={`${Math.floor(battery.minutes / 60)} h ${battery.minutes % 60} min`}
        />
      )}
    </PanelCard>
  )
}

/* ── GPU ───────────────────────────────────────────────────────────────── */

export function GpuPanel({
  gpu,
}: {
  gpu: { available: boolean; name: string; temp: number | null; util: number | null; power: string | null } | null
}) {
  if (!gpu?.available) {
    return (
      <PanelCard title="GPU" subtitle="No detectada" icon={<Gauge className="size-4" />}>
        <p className="text-xs text-muted-foreground">
          Esta máquina no expone ninguna GPU por DRM ni por nvidia-smi.
        </p>
      </PanelCard>
    )
  }

  return (
    <PanelCard title="GPU" subtitle={gpu.name} icon={<Cpu className="size-4" />}>
      <StatRow label="Uso" value={gpu.util != null ? `${gpu.util}%` : '—'} />
      <StatRow label="Temperatura" value={gpu.temp != null ? `${gpu.temp} °C` : '—'} />
      {gpu.power && <StatRow label="Consumo" value={gpu.power} />}
    </PanelCard>
  )
}
