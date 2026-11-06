import type {
  AppInfo,
  BatoceraSystems,
  CustomSystem,
  CustomSystemDetail,
  RandomGame,
  RaGamesPayload,
  RomFolder,
  RomSystemSummary,
  ScraperConfig,
  ScraperDownloadResult,
  ScraperJob,
  ScraperSearchResult,
  ScraperSource,
  ScrapeOptions,
  ServiceStatus,
  Settings,
  SystemInfo,
  SystemPayload,
  SystemWriteResult,
  ThemesPayload,
  UiTheme,
} from './types'
import { normalizeDashboard, normalizeEsStatus, normalizeGameStats } from './normalize'

/**
 * Error de API. El backend responde 200 con `{ok:false, error|errors}` en
 * muchos casos, así que `unwrap` convierte esas respuestas en excepciones
 * con el mensaje real.
 */
export class ApiError extends Error {
  readonly status: number
  readonly errors: string[]

  constructor(message: string, status = 0, errors: string[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errors = errors
  }
}

type OkEnvelope = { ok: boolean; error?: string; errors?: string[] }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: {
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError('No se pudo contactar con el servidor.')
  }

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    const payload = data as OkEnvelope | null
    const message = payload?.error || `Error ${res.status}`
    throw new ApiError(message, res.status, payload?.errors ?? [])
  }
  return data as T
}

/** Desenvuelve `{ok:true|false, error|errors}` y lanza si la operación falló. */
export function unwrap<T extends OkEnvelope>(payload: T): T {
  if (payload && payload.ok === false) {
    const errors = payload.errors?.length ? payload.errors : []
    throw new ApiError(payload.error || errors[0] || 'Operación fallida', 200, errors)
  }
  return payload
}

/* ── Peticiones del scraper ─────────────────────────────────────────────── */

/** Búsqueda de un ROM en la fuente de scraping. */
export interface ScraperSearchPayload {
  filename: string
  system: string
  subpath?: string
  source: ScraperSource
  /**
   * Fuentes a probar, en orden de prioridad. El backend devuelve el primer
   * resultado que encuentre y dice en cuál lo encontró.
   */
  sources?: ScraperSource[]
}

/** Descarga de imagen y metadatos de un ROM. */
export interface ScraperDownloadPayload {
  system: string
  filename: string
  subpath?: string
  source: ScraperSource
  game: Record<string, unknown>
  save_meta?: boolean
  img_types?: string[]
}

/** Scraping de uno o varios sistemas completos. */
export interface ScrapeSystemPayload extends ScrapeOptions {
  systems: string[]
  /** Si la fuente principal no encuentra un juego, probar con las demás. */
  fallback_sources?: boolean
}

/** Actualización manual de los metadatos de un ROM. */
export interface RomMetaPayload {
  system: string
  filename: string
  subpath?: string
  name?: string
  desc?: string
  year?: string
  publisher?: string
  genre?: string
  rating?: string
}

/** Línea de configuración del scraper (`clave` → `valor`). */
export interface ScraperConfigLine {
  key: string
  val: string
}

/** Resumen del scrape de un sistema (respuesta de `/api/scraper/scrape-system`). */
export interface ScrapeSystemResult {
  ok: number
  fail: number
  skip: number
  errors: string[]
  total: number
  quota?: Record<string, unknown>
  meta_saved?: number
}

const get = <T>(path: string) => request<T>(path)
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
const del = <T>(path: string) => request<T>(path, { method: 'DELETE' })

/** Escapa un valor para usarlo como segmento de URL. */
const enc = encodeURIComponent

export const api = {
  /* Panel y estado general */
  info: () => get<AppInfo>('/api/info'),
  dashboard: () => request<unknown>('/api/dashboard').then(normalizeDashboard),
  esStatus: () => request<unknown>('/api/es/status').then(normalizeEsStatus),
  esRestart: () => post<{ ok: boolean; [k: string]: unknown }>('/api/es/restart'),
  themes: () => get<ThemesPayload>('/api/themes'),

  /* Ajustes */
  getSettings: () => get<Settings>('/api/settings'),
  saveSettings: (payload: Partial<Settings> & { ra_api_key?: string }) =>
    post<{ ok: boolean }>('/api/settings', payload),
  saveTheme: (ui_theme: UiTheme) => post<{ ok: boolean }>('/api/settings', { ui_theme }),

  /* Servicio (arranque automático) */
  serviceStatus: () => get<ServiceStatus>('/api/service/status'),
  serviceInstall: (cmd?: string) => post<{ ok: boolean; cmd?: string; file?: string }>('/api/service/install', { cmd }),
  serviceRemove: () => post<{ ok: boolean; removed: boolean }>('/api/service/remove'),
  serviceRestart: (cmd?: string) => post<{ ok: boolean; cmd?: string }>('/api/service/restart', { cmd }),

  /* Entorno */
  systemInfo: () => get<SystemInfo>('/api/system-info'),

  /* Sistemas personalizados */
  systems: () => get<CustomSystem[]>('/api/systems'),
  systemDetail: (name: string) =>
    get<{ ok: boolean; system: CustomSystemDetail }>(`/api/system/${enc(name)}/detail`),
  systemXml: (name: string) => get<{ ok: boolean; xml: string }>(`/api/system/${enc(name)}/xml`),
  batoceraSystems: () => get<{ ok: boolean; count: number; systems: BatoceraSystems }>('/api/batocera-systems'),
  previewSystem: (payload: SystemPayload) => post<{ ok: boolean; xml: string }>('/api/preview', payload),
  createSystem: (payload: SystemPayload) => post<SystemWriteResult>('/api/create', payload),
  updateSystem: (payload: SystemPayload) => post<SystemWriteResult>('/api/update', payload),
  deleteSystem: (name: string) =>
    del<{ ok: boolean; file_deleted?: boolean; removed_systems?: number; error?: string }>(
      `/api/system/${enc(name)}`,
    ),

  /* ROMs y estadísticas */
  romSystems: () => get<RomSystemSummary[]>('/api/rom-systems'),
  gameStats: () => request<unknown>('/api/game-stats').then(normalizeGameStats),
  randomGame: () => get<{ ok: boolean; game: RandomGame | null }>('/api/random-game'),

  /* Logros (RetroAchievements) */
  raGames: (force = false) =>
    get<RaGamesPayload>(`/api/retroachievements/games${force ? '?force=1' : ''}`),

  /* Scraper */
  scraperConfig: () => get<ScraperConfig>('/api/scraper/config'),
  scraperSearch: (payload: ScraperSearchPayload) =>
    post<ScraperSearchResult>('/api/scraper/search', payload).then(unwrap),
  scraperDownload: (payload: ScraperDownloadPayload) =>
    post<ScraperDownloadResult>('/api/scraper/download', payload).then(unwrap),
  scrapeSystem: (payload: ScrapeSystemPayload) =>
    post<{ ok: boolean; results?: ScrapeSystemResult; error?: string }>(
      '/api/scraper/scrape-system',
      payload,
    ).then(unwrap),
  scrapeBatch: (payload: ScrapeSystemPayload) =>
    post<{ ok: boolean; job_id?: string; error?: string }>('/api/scraper/batch', payload).then(unwrap),
  scrapeJobs: () => get<{ ok: boolean; jobs: ScraperJob[] }>('/api/scraper/batch'),
  scrapeJob: (id: string) =>
    get<{ ok: boolean; job?: ScraperJob; error?: string }>(`/api/scraper/batch/${enc(id)}`).then(unwrap),
  scrapeJobCancel: (id: string) => del<{ ok: boolean }>(`/api/scraper/batch/${enc(id)}`),
  saveScraperConfig: (lines: ScraperConfigLine[]) =>
    post<{ ok: boolean; error?: string }>('/api/scraper/save-config', { lines }).then(unwrap),

  /* ROMs */
  romFolder: (system: string, subpath = '') =>
    get<{ ok: boolean; folder?: RomFolder; error?: string }>(
      `/api/rom-folder/${enc(system)}${subpath ? `?path=${enc(subpath)}` : ''}`,
    ).then(unwrap),
  updateRomMeta: (payload: RomMetaPayload) =>
    post<{ ok: boolean; error?: string }>('/api/rom/update-meta', payload).then(unwrap),
}
