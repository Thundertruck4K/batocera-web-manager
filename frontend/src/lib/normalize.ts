import type {
  BatteryInfo,
  DashboardPayload,
  EsStatus,
  FanEntry,
  GameStats,
  MemoryInfo,
  PlayTotals,
} from './types'

/**
 * Normalizadores de respuesta.
 *
 * El backend lee `/proc` y `/sys`, que no existen fuera de Linux: ahí
 * `get_memory()` devuelve `{}` y `get_disk()` una lista vacía. Sin
 * normalizar, un campo ausente revienta el render entero con una pantalla
 * en blanco. Aquí se rellenan los huecos con valores neutros para que la
 * interfaz degrade en lugar de romperse.
 */

const num = (value: unknown, fallback = 0): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback

const nullableNum = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

const str = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : fallback

export function normalizeEsStatus(raw: unknown): EsStatus {
  const es = (raw ?? {}) as Partial<EsStatus>
  return {
    running: Boolean(es.running),
    pid: es.pid === undefined ? undefined : String(es.pid),
    port: nullableNum(es.port),
    restart_pending: Boolean(es.restart_pending),
  }
}

export function normalizeDashboard(raw: unknown): DashboardPayload {
  const d = (raw ?? {}) as Partial<DashboardPayload>
  const cpu = d.cpu ?? ({} as DashboardPayload['cpu'])
  const gpu = d.gpu ?? ({} as DashboardPayload['gpu'])
  const memory = d.memory ?? ({} as MemoryPayloadShape)
  const battery = d.battery ?? ({} as BatteryInfo)

  const memoryOut: MemoryInfo = {
    total_mb: num(memory.total_mb),
    used_mb: num(memory.used_mb),
    free_mb: num(memory.free_mb),
    used_pct: num(memory.used_pct),
    swap_total_mb: num(memory.swap_total_mb),
    swap_used_mb: num(memory.swap_used_mb),
  }

  const batteryOut: BatteryInfo = {
    available: Boolean(battery.available),
    status: battery.status === undefined ? undefined : str(battery.status),
    capacity: nullableNum(battery.capacity),
    charging: Boolean(battery.charging),
    minutes: nullableNum(battery.minutes),
  }

  return {
    batocera_version: str(d.batocera_version, 'N/A'),
    uptime: str(d.uptime, 'N/A'),
    es: normalizeEsStatus(d.es),
    cpu: {
      model: str(cpu.model, 'N/A'),
      cores: num(cpu.cores),
      usage: num(cpu.usage),
      temp: nullableNum(cpu.temp),
      temp_src: str(cpu.temp_src, 'N/A'),
    },
    gpu: {
      available: Boolean(gpu.available),
      name: str(gpu.name, 'N/A'),
      temp: nullableNum(gpu.temp),
      util: nullableNum(gpu.util),
      mem_used: nullableNum(gpu.mem_used),
      mem_total: nullableNum(gpu.mem_total),
      power: gpu.power === undefined ? null : str(gpu.power),
      gpus: Array.isArray(gpu.gpus) ? gpu.gpus : [],
    },
    memory: memoryOut,
    disk: Array.isArray(d.disk) ? d.disk : [],
    disk_updated: d.disk_updated ?? null,
    disk_io: Array.isArray(d.disk_io) ? d.disk_io : [],
    battery: batteryOut,
    network: Array.isArray(d.network) ? d.network : [],
    processes: Array.isArray(d.processes) ? d.processes : [],
    fans: normalizeFans(d.fans),
  }
}

type MemoryPayloadShape = Partial<MemoryInfo>

export function normalizeFans(raw: unknown): FanEntry[] {
  if (!Array.isArray(raw)) return []
  return raw.map((f) => {
    const fan = f as Partial<FanEntry>
    return {
      name: str(fan.name),
      index: str(fan.index),
      label: str(fan.label),
      rpm: num(fan.rpm),
      min: nullableNum(fan.min),
      fault: Boolean(fan.fault),
      alarm: Boolean(fan.alarm),
      status: fan.status === 'ok' || fan.status === 'fault' ? fan.status : 'stopped',
    }
  })
}

export function normalizeGameStats(raw: unknown): GameStats {
  const g = (raw ?? {}) as Partial<GameStats>
  const totals = (g.totals ?? {}) as Partial<PlayTotals>
  return {
    ok: g.ok !== false,
    updated: num(g.updated),
    has_playtime: Boolean(g.has_playtime),
    totals: {
      games: num(totals.games),
      playcount: num(totals.playcount),
      playtime_s: num(totals.playtime_s),
      systems: num(totals.systems),
    },
    top_games: Array.isArray(g.top_games) ? g.top_games : [],
    by_system: Array.isArray(g.by_system) ? g.by_system : [],
    activity: Array.isArray(g.activity) ? g.activity : [],
  }
}
