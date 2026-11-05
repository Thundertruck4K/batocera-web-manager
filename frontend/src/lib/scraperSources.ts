import type { ScraperConfig, ScraperSource } from './types'

/**
 * Fuentes de scraping, en orden de prioridad.
 *
 * ScreenScraper es la que más información da, así que va la primera; si no
 * encuentra un juego se prueban TheGamesDB e IGDB como respaldo.
 */
export const SCRAPER_SOURCES: { id: ScraperSource; label: string }[] = [
  { id: 'screenscraper', label: 'ScreenScraper' },
  { id: 'thegamesdb', label: 'TheGamesDB' },
  { id: 'igdb', label: 'IGDB' },
]

/** Etiqueta corta de una fuente. */
export function sourceLabel(source: string): string {
  return SCRAPER_SOURCES.find((s) => s.id === source)?.label ?? source
}

/** ¿La fuente tiene credenciales guardadas? */
export function sourceReady(config: ScraperConfig | null, source: ScraperSource): boolean {
  if (!config) return false
  if (source === 'thegamesdb') return config.tgdb_apikey_set
  if (source === 'igdb') return config.igdb_client_id_set && config.igdb_client_secret_set
  return config.ss_user_set && config.ss_password_set
}

/** Qué le falta a la fuente para poder usarse. */
export function sourceMissing(config: ScraperConfig | null, source: ScraperSource): string {
  if (!config) return 'Configuración desconocida'
  if (source === 'thegamesdb') return 'Falta la API Key'
  if (source === 'igdb') return 'Faltan Client ID y Secret'
  if (!config.ss_user_set || !config.ss_password_set) return 'Faltan usuario y contraseña'
  return ''
}

/** Fuentes con credenciales, en el orden de prioridad. */
export function readySources(config: ScraperConfig | null): ScraperSource[] {
  return SCRAPER_SOURCES.filter((s) => sourceReady(config, s.id)).map((s) => s.id)
}
