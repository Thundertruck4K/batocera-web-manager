/**
 * Tipos del contrato JSON de `app.py`.
 *
 * Reflejan exactamente lo que devuelve el backend (`/api/*`). Cuando el
 * backend añada campos, el tipado se relaja con `Partial<>` sólo donde el
 * campo es opcional de verdad.
 */

/* ── Sistema / EmulationStation ───────────────────────────────────────── */

export interface EsStatus {
  running: boolean
  pid?: string
  port?: number | null
  restart_pending?: boolean
}

/* ── Métricas del panel ───────────────────────────────────────────────── */

export interface CpuInfo {
  model: string
  cores: number
  usage: number
  temp: number | null
  temp_src: string
}

export interface GpuEntry {
  name: string
  temp?: number | null
  util?: number | null
  mem_used?: number | null
  mem_total?: number | null
  power?: string | null
  is_nvidia?: boolean
}

export interface GpuInfo {
  available: boolean
  name: string
  temp: number | null
  util: number | null
  mem_used: number | null
  mem_total: number | null
  power: string | null
  gpus: GpuEntry[]
}

export interface MemoryInfo {
  total_mb: number
  used_mb: number
  free_mb: number
  used_pct: number
  swap_total_mb: number
  swap_used_mb: number
}

export interface DiskPartition {
  fs: string
  mount: string
  size_gb: number
  used_gb: number
  free_gb: number
  pct: number
}

export interface DiskIoEntry {
  device: string
  r_kbs: number
  w_kbs: number
  busy: number
}

export interface NetworkIface {
  iface: string
  ip?: string | null
  rx: string
  tx: string
  rx_raw: number
  tx_raw: number
}

export interface ProcessEntry {
  user: string
  pid: string
  cpu: string
  mem: string
  cmd: string
}

export interface FanEntry {
  name: string
  index: string
  label: string
  rpm: number
  min: number | null
  fault: boolean
  alarm: boolean
  status: 'ok' | 'stopped' | 'fault'
}

export interface BatteryInfo {
  available: boolean
  status?: string
  capacity?: number | null
  charging?: boolean
  minutes?: number | null
}

export interface DashboardPayload {
  batocera_version: string
  uptime: string
  es: EsStatus
  cpu: CpuInfo
  gpu: GpuInfo
  memory: MemoryInfo
  disk: DiskPartition[]
  disk_updated: string | null
  disk_io: DiskIoEntry[]
  battery: BatteryInfo
  network: NetworkIface[]
  processes: ProcessEntry[]
  fans: FanEntry[]
}

/* ── Sistemas personalizados ──────────────────────────────────────────── */

export interface CustomSystem {
  name: string
  fullname: string
  path: string
  theme: string
  hardware: string
  file: string
  filename: string
}

export interface CustomSystemDetail extends CustomSystem {
  manufacturer: string
  release: string
  platform: string
  description: string
  /** El backend lo llama `extension` (no `extensions`). */
  extension: string
  emulator?: string
  core?: string
  extra_cores?: string
}

/** Payload que consume `build_xml` en el backend. */
export interface SystemPayload {
  fullname: string
  name: string
  manufacturer: string
  release: string
  hardware: string
  rompath: string
  extensions: string
  platform: string
  theme: string
  description: string
  emulator: string
  core: string
  extra_cores: string
  create_roms_dir?: boolean
  batocera_conf_entry?: boolean
  dry_run?: boolean
  /** Sólo en /api/update: slug original. */
  old_name?: string
}

export interface SystemWriteResult {
  ok: boolean
  log: string[]
  xml: string
  cfg_path: string
  errors?: string[]
}

/* ── Catálogo de referencia de Batocera ────────────────────────────────── */

export interface BatoceraSystemEntry {
  /** Nombre completo del sistema. */
  n: string
  /** Emuladores disponibles. */
  l: string[]
  /** Sistemas relacionados. */
  s: string[]
}

export type BatoceraSystems = Record<string, BatoceraSystemEntry>

/* ── ROMs ──────────────────────────────────────────────────────────────── */

export interface RomSystemSummary {
  name: string
  rom_count: number
  media_count: number
  size_human: string
  is_empty: boolean
  has_gamelist: boolean
  has_bios: boolean
  bios_count: number
  has_logo: boolean
  type: string
  manufacturer: string
  platform: string
  release: string
  fullname: string
}

/* ── Estadísticas de juego ────────────────────────────────────────────── */

export interface PlayTotals {
  games: number
  playcount: number
  playtime_s: number
  systems: number
}

export interface PlayedGame {
  system: string
  name: string
  path: string
  playcount: number
  lastplayed: string
  playtime_s: number
  image: string
}

export interface PlayedSystem {
  system: string
  playcount: number
  playtime_s: number
  games: number
}

export interface GameStats {
  ok: boolean
  updated: number
  has_playtime: boolean
  totals: PlayTotals
  top_games: PlayedGame[]
  by_system: PlayedSystem[]
  activity: { date: string; count: number }[]
}

export interface RandomGame {
  system: string
  system_name: string
  name: string
  filename: string
  subpath?: string
  has_art: boolean
  meta?: {
    name?: string
    desc?: string
    genre?: string
    players?: string
    publisher?: string
    developer?: string
    year?: string
    playcount?: number
    gametime_s?: number
    lastplayed?: string
  }
}

/* ── Ajustes ───────────────────────────────────────────────────────────── */

export type UiTheme = 'dark' | 'light' | 'auto'

export interface Settings {
  es_cfg_dir: string
  roms_base: string
  themes_user: string
  themes_sys: string
  batocera_conf: string
  python_path: string
  bios_dir: string
  app_path: string
  server_port: number
  ra_user: string
  /** La clave real nunca viaja al cliente: llega enmascarada o vacía. */
  ra_api_key: string
  ra_api_key_set: boolean
  ra_enabled: boolean
  ui_theme: UiTheme
}

/* ── Servicio / arranque automático ────────────────────────────────────── */

export interface AutostartStatus {
  installed: boolean
  manual_mode: boolean
  marker_found?: boolean
}

export interface ProcessStatus {
  running: boolean
  pid?: number | null
  cmd?: string
}

export interface ServiceStatus {
  autostart: AutostartStatus
  process: ProcessStatus
  custom_sh: string
  exists: boolean
  cmd_current: string
}

/* ── Información general ──────────────────────────────────────────────── */

export interface AppInfo {
  active_theme: string
  themes: string[]
  systems_count: number
  rom_systems_count: number
  ext_presets: Record<string, string>
  platform_ids: string[]
  hardware_types: string[]
  has_pil: boolean
}

export interface ThemesPayload {
  active: string
  list: string[]
}
