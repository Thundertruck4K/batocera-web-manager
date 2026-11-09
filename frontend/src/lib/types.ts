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

export interface BiosFirstCheck {
  ok: boolean
  /** Queda por hacer la comprobacion de BIOS del primer arranque. */
  pendiente: boolean
  /** De donde se bajan las BIOS que falten. */
  fuente: string
  /** Cuando se hizo la comprobacion (si ya se hizo). */
  fecha?: number | null
  /** Lo que dio la ultima comprobacion. */
  resumen?: Record<string, number>
}

export interface BiosJob {
  ok: boolean
  id: string
  estado: 'trabajando' | 'listo' | 'error'
  hechos: number
  total: number
  /** Lo que esta haciendo ahora. */
  actual: string
  porcentaje: number
  mensaje: string
  error?: string
  resultado?: BiosDescargaResultado
}

export interface BiosDescarga {
  /** La ruta que espera Batocera. */
  file: string
  /** De donde se ha bajado (dentro de la fuente). */
  origen?: string
  md5?: string
  size?: number
  /** Estado tras la descarga: `ok` o `sin_verificar`. */
  estado?: string | null
}

export interface BiosDescargaResultado {
  ok: boolean
  fuente: string
  /** Cuantas BIOS faltaban. */
  total: number
  descargadas: BiosDescarga[]
  /** Bajadas pero que no se han podido verificar. */
  sin_verificar: BiosDescarga[]
  /** Las que no estan en la fuente. */
  no_encontradas: string[]
  fallidas: { file: string; error?: string }[]
  resumen: {
    /** Cuantas BIOS espera el catalogo de tus sistemas. */
    esperadas: number
    faltantes: number
    descargadas: number
    no_encontradas: number
    fallidas: number
  }
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

/** Cómo se ha emparejado el DAT de un sistema con el sistema del manager. */
export type ToolsDatResolucion = 'mapa' | 'nombre' | 'ninguno'

/** Un sistema visto por el manager y el DAT que le toca (o no). */
export interface ToolsDatSystem {
  system: string
  /** Fuente del DAT (p.ej. `libretro-no-intro`). `null` si no hay DAT. */
  source: string | null
  /** Nombre legible de la fuente. `null` si no hay DAT. */
  source_name: string | null
  /** Nombre del DAT. `null` si no hay DAT. */
  dat: string | null
  /** Confianza del emparejamiento por nombre (de 0 a 1). */
  confianza: number
  /** `mapa`: exacto. `nombre`: por nombre. `ninguno`: sin DAT. */
  resuelto: ToolsDatResolucion
  /** Si el DAT está descargado en la consola. */
  instalado: boolean
  /** Juegos que lista el DAT. */
  juegos?: number | null
  /** Tamaño del DAT en bytes. */
  tamano?: number | null
  /** Fecha de instalación (epoch). */
  fecha?: number | null
}

/** Un DAT descargado en la consola. */
export interface ToolsDatFile {
  system: string
  file: string
  size: number
  /** Fuente de la que salió el DAT. */
  source?: string | null
  /** Nombre del DAT. */
  dat?: string | null
  /** Juegos que lista el DAT. */
  games?: number | null
}

/** Estado de los DAT: los que hay instalados y el DAT que le toca a cada sistema. */
export interface ToolsDatsStatus {
  ok: boolean
  /** Carpeta donde se guardan los DAT. */
  dir?: string
  dats: ToolsDatFile[]
  /** Un estado por sistema. Los que no tienen DAT vienen con `resuelto: 'ninguno'`. */
  sistemas: ToolsDatSystem[]
  error?: string
}

/** Una conversión que admite un fichero. */
export interface ToolsFormatAction {
  /** Destino que se manda al backend (`chd`, `zip`, `bin-cue`…). */
  id: string
  /** Texto del botón. */
  label: string
  /** Explicación corta de la conversión (puede ir vacía). */
  nota?: string
  /**
   * Si el sistema admite el formato de destino. Con `false` la conversión no
   * se ofrece: sería trabajo que luego no sirve.
   */
  admite?: boolean
  /** Si la utilidad que hace falta está en la consola ahora mismo. */
  disponible?: boolean
  /** Nombre de la utilidad que falta, si es que falta. */
  falta?: string
  /** Por qué no se puede: «falta la utilidad dolphin-tool». */
  motivo?: string
  /** Identificador de la utilidad que hace la conversión (`chdman`…). */
  herramienta?: string
}

/** Un sistema con los formatos que admite. */
export interface ToolsFormatSystem {
  /** Slug del sistema (`snes`, `psp`…). */
  sistema: string
  /** Extensiones que admite el sistema, sin el punto. */
  formatos: string[]
  /** El formato que se suele usar en ese sistema. */
  preferido?: string | null
  /** Lo que hay que saber de ese sistema (nota de la wiki). */
  nota?: string
  /** Compresiones que admite el sistema (`zip`, `7z`…). */
  compresiones?: string[]
}

/** Una utilidad externa para convertir entre formatos. */
export interface ToolsFormatTool {
  /** Identificador de la utilidad (`chdman`…). */
  id: string
  /** Nombre legible. */
  nombre: string
  /** Binario que se busca en la consola. */
  binario?: string | null
  /** Dónde está el proyecto. */
  url?: string | null
  /** Licencia del programa. */
  licencia?: string | null
  /** Para qué sirve. */
  para?: string
  /** Cómo se instala en la consola. */
  instalar?: string
  /** Si está en la consola ahora mismo. */
  disponible?: boolean
}

/** La respuesta de `/api/tools/formats/sistemas`. */
export interface ToolsFormatSystems {
  ok: boolean
  /** Todos los sistemas que se pueden elegir, con sus formatos. */
  sistemas: ToolsFormatSystem[]
  /** El catálogo de utilidades de conversión. */
  herramientas: ToolsFormatTool[]
  error?: string
}

/** Un fichero de un sistema con su formato detectado. */
export interface ToolsRomFile {
  name: string
  size: number
  /** Identificador técnico del formato (`gc-iso`, `n64-z64`…). */
  kind: string
  /** Nombre legible del formato. */
  label: string
  /** Consola a la que pertenece, si el backend lo sabe. */
  plataforma?: string | null
  /** Conversiones que admite este fichero. Vacío = no se puede convertir. */
  acciones: ToolsFormatAction[]
}

/** Resultado de una conversión, una compresión o un parche. */
export interface ToolsActionResult {
  ok: boolean
  /** Ruta del fichero nuevo. */
  out?: string
  /** Tamaño del resultado en bytes. */
  size?: number
  /** Explicación del backend. */
  nota?: string
  /** Variante antigua del mensaje que devuelve el backend. */
  note?: string
  error?: string
}

/** Un fichero convertido dentro de un lote. */
export interface ToolsBatchItem {
  file: string
  out: string
  ok: boolean
  error: string | null
}

/** Resumen de una conversión en lote. */
export interface ToolsBatchResult {
  ok: boolean
  /** Resultado de cada fichero del lote. */
  hechos: ToolsBatchItem[]
  resumen: {
    total: number
    hechos: number
    fallos: number
  }
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
  /** La carpeta del sistema en la que vive el juego, si es que vive en una. */
  carpeta?: string
  /** Los dos lados del cruce de hashes (el del fichero y el del DAT). */
  hashes?: {
    /** Lo que lleva el propio fichero (un disco de Wii lleva su MD5). */
    archivo?: { game_code?: string; md5?: string; title?: string; region?: string }
    /** Lo que lleva la entrada del DAT. */
    dat?: { crc?: string; md5?: string; sha1?: string }
  }
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

/** Lo que se ha tocado del `gamelist.xml` al renombrar. */
export interface ToolsRenameGamelist {
  /** Fichas del gamelist actualizadas. */
  cambios: number
  /** Ficheros de media (imágenes, vídeos) renombrados. */
  media: number
  error?: string | null
}

/**
 * El estado de un trabajo largo (el plan de renombrado o su aplicacion).
 *
 * El backend arranca el trabajo en un hilo aparte y devuelve su id; el
 * cliente va preguntando por el estado hasta que acaba, asi que se ve que
 * la aplicacion sigue trabajando en vez de quedarse en silencio.
 */
export interface ToolsJob {
  ok: boolean
  id: string
  tipo: string
  /** `trabajando` mientras dura, `listo` al terminar, `error` si falla. */
  estado: 'trabajando' | 'listo' | 'error'
  /** Cuantos ficheros lleva revisados. */
  hechos: number
  /** Cuantos ficheros hay en total. */
  total: number
  /** El fichero que esta mirando ahora mismo. */
  actual: string
  /** De 0 a 100. */
  porcentaje: number
  /** Lo que esta haciendo ("identificando los ficheros"...). */
  mensaje: string
  error?: string
  /** El resultado, si el trabajo ha terminado bien. */
  resultado?: ToolsRenamePlan | ToolsRenameResult
}

/** Resultado de aplicar o deshacer un renombrado. */
export interface ToolsRenameResult {
  ok: boolean
  renamed?: number
  restored?: string[]
  skipped?: { file: string; reason: string }[]
  errores?: { file: string; error: string }[]
  /** Lo que se ha actualizado del `gamelist.xml`. */
  gamelist?: ToolsRenameGamelist
  error?: string
}

/* ── Biblioteca de ROMs ───────────────────────────────────────────────── */

/** Un juego de la biblioteca (un fichero suelto o una carpeta-juego). */
export interface LibraryArchivo {
  sistema: string
  ruta: string
  nombre: string
  bytes: number
  /** True si el juego es una carpeta (Wii, ScummVM, DOSBox...). */
  carpeta: boolean
}

/** Un grupo de juegos repetidos. */
export interface LibraryDuplicado {
  /** El md5, si el hash completo lo ha confirmado. */
  md5: string | null
  /**
   * Si el grupo está confirmado con el hash completo. Si no lo está, es un
   * candidato: la huella rápida coincide pero no se ha leído el fichero
   * entero (es una ISO de 4 GB, y confirmarlas todas serían horas).
   */
  confirmado: boolean
  /** El tamaño de una copia. */
  bytes: number
  mb: number
  /** Cuántas copias hay. */
  copias: number
  /** Lo que se libera dejando una sola copia. */
  ahorro: number
  ahorro_mb: number
  ficheros: LibraryArchivo[]
  nombres: string[]
  sistemas: string[]
}

/** El mismo juego repetido en varios sistemas (los arcades, sobre todo). */
export interface LibraryRepetido {
  nombre: string
  sistemas: string[]
  bytes: number
  ahorro_mb: number
  ficheros: LibraryArchivo[]
}

/** Una lista de la auditoría, recortada (con el total de lo que había). */
export interface LibraryLista<T> {
  total: number
  lista: T[]
}

/** La radiografía completa de la biblioteca. */
export interface LibraryAudit {
  resumen: {
    sistemas: number
    juegos: number
    bytes: number
    gb: number
  }
  duplicados: LibraryDuplicado[]
  repetidos_entre_sistemas: LibraryRepetido[]
  /** Fichas del `gamelist.xml` cuyo fichero ya no existe. */
  fichas_sin_fichero: LibraryLista<{ sistema: string; ruta: string }>
  /** Juegos de 0 bytes. */
  ficheros_vacios: LibraryLista<LibraryArchivo>
  /** Ficheros que no son juegos (notas, listas, saves sueltos). */
  sobras: LibraryLista<LibraryArchivo>
  /** Imágenes y vídeos cuyo juego ya no está. */
  media_huerfana: LibraryLista<{ sistema: string; fichero: string; bytes: number }>
  partidas: { con_partidas: number; sin_partidas: number }
  /** El espacio por sistema. */
  espacio: { sistema: string; juegos: number; bytes: number; gb: number }[]
  /** Los juegos más grandes. */
  mayores: LibraryArchivo[]
}

/** El resumen rápido de la biblioteca (sin hashear nada). */
export interface LibrarySummary {
  ok: boolean
  sistemas: {
    nombre: string
    juegos: number
    bytes: number
    size_human: string
    con_gamelist: boolean
  }[]
  juegos: number
  bytes: number
  gb: number
}

/** Una tanda que se puede deshacer. */
export interface LibraryBatch {
  when?: number
  tipo: string
  count: number
  gamelist: string | null
  files: string[]
}

/** Un sistema que tiene DAT instalado. */
export interface LibraryDatSistema {
  sistema: string
  /** Cuántos juegos trae el DAT de ese sistema. */
  juegos_dat: number
  dat: string | null
  fuente: string | null
  version: string | null
}

/** Una versión del juego que tienes (emparejada con el DAT). */
export interface LibraryVariante {
  /** El nombre que le da el DAT. */
  nombre: string
  /** El fichero (o carpeta) de la biblioteca. */
  fichero: string
  /** Cómo se ha emparejado: nombre, hash, gamecode, serial o titulo. */
  metodo: string
  confianza: number
}

/** Una versión del DAT que no tienes. */
export interface LibraryFaltante {
  nombre: string
  /** `disco`, `region`, `revision`, `idioma` o `version`. */
  motivo: string
  /** Lo que concreta el motivo (el número de disco, la región...). */
  detalle: string
  /** Si esta versión puntúa más alto que la que tienes. */
  mejor: boolean
  puntuacion: number
  /** Cuántos volcados distintos hay con ese nombre en el DAT. */
  copias?: number
}

/** Un juego del que tienes alguna versión y faltan otras. */
export interface LibraryGrupoFaltante {
  /** El nombre del juego, sin las etiquetas. */
  titulo: string
  variantes: LibraryVariante[]
  faltan: LibraryFaltante[]
  /** Los números de disco que no tienes. */
  discos_faltantes: number[]
}

/** El resultado de comparar un sistema con su DAT. */
export interface LibraryFaltantes {
  ok: boolean
  sistema: string
  /** Cuántos juegos tiene el DAT. */
  juegos_dat: number
  /** Cuántos juegos hay en la biblioteca del sistema. */
  juegos_biblioteca: number
  /** Cuántos se han emparejado con una entrada del DAT. */
  encontrados: number
  /** Cuántos no salen en el DAT (mods, traducciones, homebrew). */
  sin_dat: number
  /**
   * Cuántos coinciden por el título pero no del todo: puede que ya los
   * tengas y el nombre no cuadre, así que no se afirma que falten.
   */
  quizas?: number
  /** Los juegos con coincencia dudosa, para poder verlos. */
  quizas_lista?: { fichero: string; candidato: string; puntuacion: number }[]
  /** Cuántos juegos tienen más versiones de las que tienes. */
  grupos: number
  /** Cuántas versiones te faltan. */
  faltantes: number
  /** Cuántas de esas son una versión mejor que la que tienes. */
  mejores: number
  /** Cuántos juegos tienen un disco sin conseguir. */
  discos: number
  /**
   * Cuántos de esos juegos tienen además alguna versión que puntúa más que
   * la que tienes. Es lo que cuenta el filtro «Mejores versiones».
   */
  grupos_mejores?: number
  detalle: LibraryGrupoFaltante[]
  detalle_recortado: boolean
  sin_dat_lista: { fichero: string; tamano: number }[]
  /** Si se ha hasheado algo (si no, el emparejamiento es por nombre o título). */
  hasheado: boolean
  error?: string
}

/** El estado del trabajo de auditoría (va en segundo plano). */
export interface LibraryJob {
  ok: boolean
  id: string
  tipo: string
  estado: 'trabajando' | 'listo' | 'error'
  hechos: number
  total: number
  actual: string
  porcentaje: number
  mensaje: string
  error?: string
  /** El resultado depende del trabajo: la auditoría o la comparación con el DAT. */
  resultado?: unknown
}
