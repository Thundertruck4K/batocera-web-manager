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
  /** Juegos con imagen (los que tienen `<image>` en su gamelist.xml). */
  image_count: number
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
  /** El bloque de arranque está escrito en custom.sh. */
  registered: boolean
  /** Alias de `registered` (mismo valor, nombre corto). */
  installed: boolean
  /** El manager corre pero no hay bloque: se arrancó a mano. */
  manual_mode: boolean
  /** Comando de arranque guardado en custom.sh. */
  cmd?: string | null
  /** Bloque completo tal y como está escrito en custom.sh. */
  block?: string
  /** Fichero donde vive el bloque. */
  path?: string
}

export interface ProcessStatus {
  running: boolean
  /** PIDs encontrados (puede haber más de uno: envoltorio y servidor). */
  pids?: string[]
  /** PID principal del manager. */
  pid?: number | null
  /** Puerto en el que está escuchando. */
  port?: number | null
  /** Línea de comandos real del proceso. */
  cmd?: string | null
}

export interface ServiceStatus {
  autostart: AutostartStatus
  process: ProcessStatus
  custom_sh: string
  exists: boolean
  cmd_current: string
}

/* ── Información del sistema ─────────────────────────────────────────────── */

export interface SystemInfo {
  /** Versión del manager (la de app.py). */
  version: string
  /** Versión del intérprete de Python de la consola. */
  python_version: string
  /** Qué interfaz se está sirviendo. */
  frontend: 'react' | 'clasica'
  /** Carpeta del frontend en la consola. */
  frontend_dir: string
  /** Carpeta del bundle compilado. */
  dist_dir: string
  /** Ruta de app.py. */
  app_path: string
  /** Ruta del script de arranque automático. */
  custom_sh: string
  /** Versión de Node si está instalado; null si no. */
  node_version: string | null
  /** Puerto configurado. */
  port: number
  /** Si Pillow está disponible (logos de relleno). */
  has_pil: boolean
}

/* ── Información general ──────────────────────────────────────────────── */

export interface AppInfo {
  active_theme: string
  themes: string[]
  /** Sistemas personalizados que gestiona el manager. */
  systems_count: number
  /** Sistemas con al menos un juego en el disco. */
  rom_systems_count: number
  /** Juegos reales que hay en el disco (no sólo los catalogados). */
  disk_games_count: number
  /** Sistemas con juegos en el disco. */
  disk_systems_count: number
  ext_presets: Record<string, string>
  platform_ids: string[]
  hardware_types: string[]
  has_pil: boolean
}

export interface ThemesPayload {
  active: string
  list: string[]
}

/* ── Logros (RetroAchievements) ────────────────────────────────────────── */

export interface RaProfile {
  user: string
  avatar: string
  points: number
  true_points: number
  softcore_points: number
  member_since: string
  motto: string
  rich_presence: string
  last_game_id: number | null
}

export interface RaAwards {
  total: number
  mastery: number
  completion: number
  beaten_hardcore: number
  beaten_softcore: number
  events: number
}

export interface RaGame {
  game_id: number
  title: string
  console: string
  /** Icono de RetroAchievements (respaldo si no hay ROM local). */
  icon: string
  /** Logros conseguidos por el usuario. */
  num_awarded: number
  /** De esos, los conseguidos en modo hardcore. */
  num_awarded_hardcore: number
  /** Logros que tiene el juego. */
  max_possible: number
  hardcore: boolean
  percent: number
  /** `mastered`, `completed`, `beaten-hardcore`, `beaten-softcore`… */
  award_kind: string
  award_date: string
  recent_date: string
  /** Sistema local donde está el ROM (vacío si no hubo coincidencia). */
  system: string
  system_name: string
  filename: string
  subpath: string
  has_art: boolean
  /** Si el juego se ha emparejado con un ROM de la biblioteca. */
  local: boolean
}

export interface RaGamesPayload {
  ok: boolean
  /** Hay usuario y Web API Key configurados. */
  configured: boolean
  /** La integración está activada. */
  enabled: boolean
  updated: number | null
  /** Los datos vienen de la cache (no se ha llamado a la API). */
  cached: boolean
  /** No se ha refrescado por respetar el intervalo mínimo de peticiones. */
  throttled: boolean
  /** Segundos desde la última descarga real a la API. */
  age: number | null
  profile: RaProfile | null
  awards: RaAwards | null
  games: RaGame[]
  /** Juegos emparejados con un ROM local. */
  matched: number
  /** Juegos con progreso en RetroAchievements. */
  total: number
}

/* ── BIOS ──────────────────────────────────────────────────────────── */

/**
 * Estado de un fichero de BIOS esperado.
 *
 * `ok`            está en su ruta (el hash no decide: Batocera no es rígido).
 * `sin_verificar` está en su ruta, pero el catálogo no publica hash ni
 *                 ficheros dentro, así que no hay nada más que comprobar.
 * `miembro_falta` al ZIP le falta un fichero que el catálogo exige dentro.
 * `reparable_zip` el contenido está dentro de otro ZIP de la consola.
 * `reparable_ruta` el mismo contenido está en otra carpeta.
 * `ausente`       no está en ninguna parte.
 * `omitida`       el usuario la marcó como no necesaria.
 * `ilegible`      está pero no se puede abrir (ZIP roto).
 */
export type BiosEstado =
  | 'ok'
  | 'sin_verificar'
  | 'miembro_falta'
  | 'reparable_zip'
  | 'reparable_ruta'
  | 'ausente'
  | 'omitida'
  | 'ilegible'

/** Un fichero que el catálogo de Batocera exige dentro de un ZIP. */
export interface BiosMember {
  name: string
  md5: string | null
}

export interface BiosFile {
  /** Ruta relativa dentro de `/userdata/bios`. */
  file: string
  estado: BiosEstado
  /** Hashes aceptados para el fichero (variantes regionales). */
  md5s: string[]
  /** Ficheros que el catálogo exige dentro del ZIP. */
  members: BiosMember[]
  size: number | null
  /** Hash del fichero que hay ahora mismo en el disco. */
  md5: string | null
  motivo?: string | null
  /** Dónde está el contenido que falta (otra ruta u otro ZIP). */
  fuente?: string | null
  /** Miembros que faltan dentro del ZIP. */
  faltan: string[]
  skip_key: string
  /** Enlace para buscar ese fichero en Google. */
  busqueda?: string | null
}

export interface BiosSystem {
  /** Nombre legible del sistema («Coleco Adam»). */
  name: string
  files: BiosFile[]
  /** Enlace para buscar las BIOS de este sistema en Google. */
  busqueda?: string | null
}

export interface BiosCatalog {
  ok: boolean
  /** De dónde se ha sacado el catálogo (script oficial, readme o embebido). */
  source: string
  systems: Record<string, BiosSystem>
  summary: Record<string, number>
  /** Ficheros en el disco que el catálogo no pide. */
  extras: number
  /** Ficheros que hay en el disco. */
  scanned: number
  error?: string
}

export interface BiosRepairResult {
  ok: boolean
  estado?: string
  dest?: string
  md5?: string | null
  motivo?: string | null
  /** Dónde se guardó el fichero que se ha sustituido. */
  quarantine?: string | null
  faltan?: string[]
  error?: string
}

/* ── Scraper ─────────────────────────────────────────────────────────── */

/** Fuentes de scraping admitidas por el backend. */
export type ScraperSource = 'screenscraper' | 'thegamesdb' | 'igdb'

/**
 * Configuración pública del scraper.
 *
 * Las credenciales llegan **enmascaradas** y sólo se indica si hay alguna
 * guardada (`*_set`): el frontend nunca ve la clave real en claro.
 */
export interface ScraperConfig {
  ss_region: string
  ss_lang: string
  ss_image_type: string
  scraper_source: string
  ss_user: string
  ss_password: string
  ss_devid: string
  ss_devpassword: string
  tgdb_apikey: string
  igdb_client_id: string
  igdb_client_secret: string
  ss_user_set: boolean
  ss_password_set: boolean
  ss_devid_set: boolean
  ss_devpassword_set: boolean
  tgdb_apikey_set: boolean
  igdb_client_id_set: boolean
  igdb_client_secret_set: boolean
}

/** Una entrada del listado de una carpeta de ROMs. */
export interface RomFolderItem {
  name: string
  filename: string
  ext: string
  size: number
  size_human: string
  is_rom: boolean
  is_dir: boolean
  /** El juego es una carpeta (ScummVM, DOSBox, MUGEN...): se busca por su nombre. */
  is_game_folder?: boolean
  child_count?: number
  has_subdirs?: boolean
  desc: string
  rating: string
  genre: string
  publisher: string
  year: string
  has_image: boolean
  has_video: boolean
}

/** Contenido de una carpeta de ROMs (raíz del sistema o subcarpeta). */
export interface RomFolder {
  system: string
  subpath: string
  breadcrumb: string[]
  items: RomFolderItem[]
  item_count: number
  media_count: number
  total_size: number
  size_human: string
  has_gamelist: boolean
  is_empty: boolean
}

/** Metadatos normalizados de un juego (los que se guardan en gamelist.xml). */
export interface ScraperMeta {
  name: string
  desc: string
  genre: string
  year: string
  publisher: string
  rating: string
}

/** Resultado de buscar un ROM en la fuente de scraping. */
export interface ScraperSearchResult {
  ok: boolean
  game: Record<string, unknown> | null
  meta: ScraperMeta | null
  img_types: string[]
  source: ScraperSource
  /** URL de la carátula para la vista previa (vía proxy del backend). */
  image_url?: string | null
  /** Fuentes que se han ido probando, en orden. */
  tried?: ScraperSource[]
  quota?: Record<string, unknown>
  error?: string
}

/** Resultado de descargar imagen y metadatos de un ROM. */
export interface ScraperDownloadResult {
  ok: boolean
  results: {
    images: { type: string; path: string }[]
    meta: boolean
    errors: string[]
    es_reload?: boolean
  }
  error?: string
}

/** Trabajo de scraping por lotes (uno o varios sistemas). */
export interface ScraperJob {
  id: string
  systems: string[]
  source: string
  status: 'pending' | 'running' | 'completed' | 'cancelled' | 'failed'
  progress: number
  current_system: string
  current_rom: string
  progress_raw: [number, number]
  partial: { ok?: number; fail?: number; skip?: number }
  systems_done: number
  aggregated: {
    ok: number
    fail: number
    skip: number
    total: number
    errors: string[]
    meta_saved: number
  }
  created_at: number
  error?: string | null
  es_reload?: boolean
}

/** Opciones del scrape de un sistema completo. */
export interface ScrapeOptions {
  source: ScraperSource
  only_missing: boolean
  ss_image_type: string
  ss_region: string
  ss_lang: string
}


/* ── Herramientas de ROMs (DAT, formatos y renombrado) ─────────────── */

/** Un sistema de Batocera que tiene un DAT asignado. */
export interface ToolsDatSystem {
  system: string
  source: string
  source_name: string
  dat: string
  instalado: boolean
  juegos?: number | null
  tamano?: number | null
  fecha?: number | null
}

/** Estado de los DAT descargados. */
export interface ToolsDatsStatus {
  ok: boolean
  dir?: string
  dats: {
    system: string
    file: string
    size: number
    dat?: string | null
    games?: number | null
    generated?: number
  }[]
  sistemas: ToolsDatSystem[]
  error?: string
}

/** Un fichero de un sistema con su formato detectado. */
export interface ToolsRomFile {
  name: string
  size: number
  kind: string
  label: string
  actions: string[]
}

/** Lo que se sabe del formato de un fichero. */
export interface ToolsFormatInfo {
  ok: boolean
  path?: string
  file?: string
  kind: string
  label: string
  size: number
  details: Record<string, unknown>
  actions: string[]
  error?: string
}

/** Resultado de unaConversion, compresion o parche. */
export interface ToolsActionResult {
  ok: boolean
  out?: string
  bin?: string
  cue?: string
  size?: number
  before?: number
  note?: string
  error?: string
}

/** Una linea del plan de renombrado. */
export interface ToolsRenameItem {
  path: string
  file: string
  current: string
  proposed: string
  action: string
  reason: string
  confidence: number
  method: string
  title?: string | null
  dat_name?: string | null
  companions: string[]
  warnings: string[]
}

/** El plan completo de renombrado de un sistema. */
export interface ToolsRenamePlan {
  ok: boolean
  system: string
  con_dat: boolean
  dat?: string | null
  items: ToolsRenameItem[]
  stats: {
    total: number
    renombrar: number
    revisar: number
    igual: number
    sin_dat: number
    identificados: number
  }
}

/** Resultado de aplicar o deshacer un renombrado. */
export interface ToolsRenameResult {
  ok: boolean
  renamed?: number
  restored?: string[]
  skipped?: { file: string; reason: string }[]
  errores?: { file: string; error: string }[]
  error?: string
}
