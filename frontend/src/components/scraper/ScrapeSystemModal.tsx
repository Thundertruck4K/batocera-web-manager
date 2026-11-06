import { motion } from 'motion/react'
import {
  CircleAlert,
  CircleCheck,
  Download,
  Loader2,
  Pencil,
  RefreshCw,
  Save,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Field, Input, Select, Toggle } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { useNotify } from '@/hooks/useNotify'
import { useToast } from '@/hooks/useToast'
import { api, type ScraperConfigLine } from '@/lib/api'
import {
  SCRAPER_SOURCES,
  sourceMissing,
  sourceReady,
} from '@/lib/scraperSources'
import type { ScraperConfig, ScraperJob, ScraperSource } from '@/lib/types'
import { cn } from '@/lib/utils'

const IMAGE_TYPES = [
  { value: 'mixrbv1', label: 'Mix v1 (recomendado)' },
  { value: 'mixrbv2', label: 'Mix v2' },
  { value: 'box-2D', label: 'Caja 2D' },
  { value: 'ss', label: 'Screenshot' },
  { value: 'wheel', label: 'Rueda / logo' },
  { value: 'fanart', label: 'Fanart' },
  { value: 'screenshot', label: 'Captura' },
]

const REGIONS = [
  { value: 'wor', label: 'Mundial' },
  { value: 'eu', label: 'Europa' },
  { value: 'us', label: 'USA' },
  { value: 'jp', label: 'Japón' },
]

const LANGS = [
  { value: 'es', label: 'Español' },
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'it', label: 'Italiano' },
  { value: 'pt', label: 'Português' },
  { value: 'nl', label: 'Nederlands' },
  { value: 'sv', label: 'Svenska' },
  { value: 'pl', label: 'Polski' },
  { value: 'ru', label: 'Русский' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'zh', label: '中文' },
]

/** Credenciales que se pueden editar. La clave real nunca se muestra. */
const CRED_FIELDS: {
  key: string
  conf: string
  label: string
  type: 'text' | 'password'
  source: ScraperSource
  hint: string
}[] = [
  {
    key: 'ss_user',
    conf: 'global.scrapper.user',
    label: 'Usuario de ScreenScraper',
    type: 'text',
    source: 'screenscraper',
    hint: 'El mismo usuario que usas en screenscraper.fr',
  },
  {
    key: 'ss_password',
    conf: 'global.scrapper.password',
    label: 'Contraseña de ScreenScraper',
    type: 'password',
    source: 'screenscraper',
    hint: 'No se muestra nunca: sólo se guarda en la consola',
  },
  {
    key: 'ss_devid',
    conf: 'global.scrapper.devid',
    label: 'Developer ID',
    type: 'text',
    source: 'screenscraper',
    hint: 'Opcional: sólo para desarrolladores de ScreenScraper',
  },
  {
    key: 'ss_devpassword',
    conf: 'global.scrapper.devpassword',
    label: 'Developer password',
    type: 'password',
    source: 'screenscraper',
    hint: 'Opcional: sólo para desarrolladores de ScreenScraper',
  },
  {
    key: 'tgdb_apikey',
    conf: 'global.tgdb.apikey',
    label: 'API Key de TheGamesDB',
    type: 'password',
    source: 'thegamesdb',
    hint: 'Se obtiene en thegamesdb.net',
  },
  {
    key: 'igdb_client_id',
    conf: 'global.igdb.clientid',
    label: 'Client ID de IGDB (Twitch)',
    type: 'text',
    source: 'igdb',
    hint: 'Credenciales de la aplicación de Twitch',
  },
  {
    key: 'igdb_client_secret',
    conf: 'global.igdb.clientsecret',
    label: 'Client Secret de IGDB (Twitch)',
    type: 'password',
    source: 'igdb',
    hint: 'Credenciales de la aplicación de Twitch',
  },
]

/** ¿La fuente elegida tiene credenciales guardadas? */

interface ScrapeSystemModalProps {
  open: boolean
  onClose: () => void
  /** Sistemas a escrapear (normalmente uno). */
  systems: string[]
  /** Se llama cuando el usuario guarda y valida la configuración. */
  onSaved: () => void
}

/**
 * Modal flotante para escrapear uno o varios sistemas completos.
 *
 * El pie tiene las tres acciones: **Actualizar** (releer y verificar la
 * configuración del servidor), **Editar** (abrir las credenciales) y
 * **Guardar** (validar, persistir y cerrar).
 */
export function ScrapeSystemModal({ open, onClose, systems, onSaved }: ScrapeSystemModalProps) {
  const { showToast } = useToast()
  const { showNotify } = useNotify()

  const [config, setConfig] = useState<ScraperConfig | null>(null)
  const [source, setSource] = useState<ScraperSource>('screenscraper')
  const [onlyMissing, setOnlyMissing] = useState(true)
  const [fallback, setFallback] = useState(true)
  const [imageType, setImageType] = useState('mixrbv1')
  const [region, setRegion] = useState('wor')
  const [lang, setLang] = useState('es')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<Record<string, string>>({})
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<ScraperJob | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(false)

  /** Carga la configuración pública del servidor y la refleja en el formulario. */
  const loadConfig = useCallback(
    async (silent = false) => {
      if (!silent) setLoadingConfig(true)
      try {
        const cfg = await api.scraperConfig()
        setConfig(cfg)
        // La fuente guardada en la consola manda: es la que se usa por defecto.
        setSource(cfg.scraper_source === 'thegamesdb' || cfg.scraper_source === 'igdb' ? cfg.scraper_source : 'screenscraper')
        setImageType(cfg.ss_image_type || 'mixrbv1')
        setRegion(cfg.ss_region || 'wor')
        setLang(cfg.ss_lang || 'es')
        setError(null)
        return cfg
      } catch (err) {
        setError(err instanceof Error ? err.message : 'No se pudo leer la configuración')
        return null
      } finally {
        if (!silent) setLoadingConfig(false)
      }
    },
    [],
  )

  /* Al abrir: leer la configuración del servidor. */
  useEffect(() => {
    if (!open) return
    void loadConfig()
    setEditing(false)
    setForm({})
    setError(null)
  }, [open, loadConfig])

  /* Mientras haya un trabajo en marcha, seguir su progreso. */
  useEffect(() => {
    if (!jobId) return
    let alive = true
    const tick = async () => {
      try {
        const res = await api.scrapeJob(jobId)
        if (!alive || !res.job) return
        setJob(res.job)
      } catch {
        /* La consola puede tardar un instante: se reintenta al siguiente tick. */
      }
    }
    const timer = window.setInterval(tick, 1500)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [jobId])

  /* Al terminar el trabajo: avisar con el resumen (o con el log de errores). */
  const notificado = useRef(false)
  useEffect(() => {
    if (!job || job.status === 'pending' || job.status === 'running') {
      notificado.current = false
      return
    }
    if (notificado.current) return
    notificado.current = true

    const errores = job.aggregated?.errors ?? []
    const ok = (job.aggregated?.ok ?? 0) + (job.partial?.ok ?? 0)
    const fail = (job.aggregated?.fail ?? 0) + (job.partial?.fail ?? 0)
    onSaved()

    if (job.status === 'failed') {
      showNotify({
        variant: 'error',
        title: 'El scraping falló',
        message: job.error || `El trabajo ${job.id} terminó con errores.`,
        detail: errores.length ? errores.join('\n') : (job.error ?? undefined),
      })
    } else if (errores.length) {
      showNotify({
        variant: 'error',
        title: 'Scraping terminado con errores',
        message: `${ok} juego(s) guardados y ${fail} con fallos.`,
        detail: errores.join('\n'),
      })
    } else {
      showNotify({
        variant: 'success',
        title: 'Scraping terminado',
        message: `${ok} juego(s) scraped y guardado(s) en ${systems.length} sistema(s).`,
      })
    }
  }, [job, onSaved, showNotify, systems.length])

  const ready = sourceReady(config, source)

  const credStatus = useMemo(() => {
    if (!config) return []
    return CRED_FIELDS.filter((field) => field.source === source).map((field) => ({
      ...field,
      set: Boolean((config as unknown as Record<string, boolean>)[`${field.key}_set`]),
    }))
  }, [config, source])

  /** Lanza el trabajo de scraping por lotes. */
  const startScrape = async () => {
    setStarting(true)
    setError(null)
    try {
      const res = await api.scrapeBatch({
        systems,
        source,
        only_missing: onlyMissing,
        fallback_sources: fallback,
        ss_image_type: imageType,
        ss_region: region,
        ss_lang: lang,
      })
      if (res.job_id) {
        setJobId(res.job_id)
        setJob(null)
        showToast(`Scraping de ${systems.length} sistema(s) en marcha`, 'success')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo iniciar el scraping')
    } finally {
      setStarting(false)
    }
  }

  /** Botón «Actualizar»: relee la configuración y verifica las credenciales. */
  const handleRefresh = async () => {
    const cfg = await loadConfig(true)
    if (!cfg) {
      showToast('No se pudo verificar la configuración', 'error')
      return
    }
    const ok = sourceReady(cfg, source)
    showToast(
      ok ? 'Configuración verificada' : `Faltan credenciales: ${sourceMissing(cfg, source)}`,
      ok ? 'success' : 'error',
    )
  }

  /** Botón «Guardar»: valida, persiste y cierra el modal. */
  const handleSave = async () => {
    if (!ready) {
      setError(`Faltan credenciales para ${SCRAPER_SOURCES.find((s) => s.id === source)?.label}. Pulsa «Editar» para añadirlas.`)
      return
    }
    setError(null)
    const lines: ScraperConfigLine[] = [
      { key: 'global.scraper.source', val: source },
      { key: 'global.scrapper.region', val: region },
      { key: 'global.scrapper.lang', val: lang },
      { key: 'global.scrapper.imageSource', val: imageType },
    ]
    if (editing) {
      for (const field of CRED_FIELDS) {
        const value = (form[field.key] || '').trim()
        if (value) lines.push({ key: field.conf, val: value })
      }
    }
    try {
      await api.saveScraperConfig(lines)
      showToast('Configuración guardada y validada', 'success')
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la configuración')
    }
  }

  const running = job?.status === 'pending' || job?.status === 'running'
  const aggregated = job?.aggregated
  const partial = job?.partial ?? {}

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        systems.length === 1
          ? `Escrapear ${systems[0]}`
          : systems.length > 1
            ? `Escrapear ${systems.length} sistemas`
            : 'Configurar el scraper'
      }
      description={
        systems.length
          ? 'Elige la fuente de datos y las opciones. Las credenciales se guardan en la consola y nunca se muestran.'
          : 'Elige la fuente de datos y guarda tus credenciales. Se guardan en la consola y nunca se muestran.'
      }
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={loadingConfig}>
            <RefreshCw className={cn('size-4', loadingConfig && 'animate-spin')} />
            Actualizar
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setEditing((v) => !v)
              setError(null)
            }}
          >
            <Pencil className="size-4" />
            {editing ? 'Terminar edición' : 'Editar'}
          </Button>
          <Button variant="primary" size="sm" onClick={handleSave}>
            <Save className="size-4" />
            Guardar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive">
            <CircleAlert className="mt-px size-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Fuente de datos */}
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Fuente de datos
          </h3>
          <div className="flex flex-wrap gap-2">
            {SCRAPER_SOURCES.map((option, index) => {
              const configured = sourceReady(config, option.id)
              const active = source === option.id
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => {
                    setSource(option.id)
                    setError(null)
                  }}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition-colors duration-150',
                    'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                    active
                      ? 'border-brand bg-brand/10 text-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  <span className="tabular-nums text-[10px] font-bold text-muted-foreground">{index + 1}</span>
                  {option.label}
                  {configured ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                      <ShieldCheck className="size-3" />
                      Listo
                    </span>
                  ) : (
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                      Sin credenciales
                    </span>
                  )}
                </button>
              )
            })}
          </div>
          {!ready && (
            <p className="mt-2 text-xs font-medium text-destructive">
              {sourceMissing(config, source)}. Pulsa «Editar» para escribirlas.
            </p>
          )}
          <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
            La fuente elegida es la prioridad. Con el respaldo activado, si no encuentra un juego se
            prueban las siguientes: {SCRAPER_SOURCES.map((s) => s.label).join(' → ')}.
          </p>
        </section>

        {/* Opciones */}
        <section className="grid gap-3 sm:grid-cols-3">
          <Field label="Tipo de imagen" htmlFor="scrape-imgtype">
            <Select id="scrape-imgtype" value={imageType} onChange={(e) => setImageType(e.target.value)}>
              {IMAGE_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Región" htmlFor="scrape-region">
            <Select id="scrape-region" value={region} onChange={(e) => setRegion(e.target.value)}>
              {REGIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Idioma" htmlFor="scrape-lang">
            <Select id="scrape-lang" value={lang} onChange={(e) => setLang(e.target.value)}>
              {LANGS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
        </section>

        <Toggle
          checked={onlyMissing}
          onChange={setOnlyMissing}
          label="Sólo los ROMs que faltan"
          description="No toca los juegos que ya tienen imagen; es lo habitual para no gastar cuota."
        />

        <Toggle
          checked={fallback}
          onChange={setFallback}
          label="Usar las demás fuentes como respaldo"
          description="Si la fuente principal no encuentra un juego, se prueban las siguientes por orden."
        />

        {/* Credenciales */}
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Credenciales de {SCRAPER_SOURCES.find((s) => s.id === source)?.label}
          </h3>
          {editing ? (
            <div className="space-y-3">
              {CRED_FIELDS.filter((field) => field.source === source).map((field) => (
                <Field key={field.key} label={field.label} hint={field.hint} htmlFor={`cred-${field.key}`}>
                  <Input
                    id={`cred-${field.key}`}
                    type={field.type}
                    autoComplete="off"
                    placeholder={credStatus.find((c) => c.key === field.key)?.set ? 'Ya configurada (déjalo vacío para no cambiarla)' : ''}
                    value={form[field.key] || ''}
                    onChange={(e) => setForm((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  />
                </Field>
              ))}
            </div>
          ) : (
            <ul className="space-y-1.5">
              {credStatus.map((field) => (
                <li key={field.key} className="flex items-center justify-between gap-3 text-xs">
                  <span className="truncate font-medium text-foreground">{field.label}</span>
                  <span
                    className={cn(
                      'inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold',
                      field.set
                        ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                        : 'bg-muted text-muted-foreground',
                    )}
                  >
                    {field.set ? <CircleCheck className="size-3" /> : <X className="size-3" />}
                    {field.set ? 'Configurada' : 'Sin configurar'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Progreso del trabajo */}
        {job && (
          <section className="rounded-2xl border border-border bg-muted/40 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-semibold text-foreground">
                {running ? 'Scraping en curso…' : `Trabajo ${job.status}`}
              </span>
              <span className="text-xs font-semibold tabular-nums text-muted-foreground">{job.progress} %</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-brand"
                initial={{ width: 0 }}
                animate={{ width: `${job.progress}%` }}
                transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <p className="mt-2 truncate text-[11px] font-medium text-muted-foreground">
              {job.current_system ? `${job.current_system} → ${job.current_rom || '…'}` : 'Preparando…'}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-medium text-muted-foreground">
              <span className="tabular-nums">
                {(aggregated?.ok ?? 0) + (partial.ok ?? 0)} OK
              </span>
              <span className="tabular-nums">
                {(aggregated?.fail ?? 0) + (partial.fail ?? 0)} fallos
              </span>
              <span className="tabular-nums">{job.systems_done}/{job.systems.length} sistemas</span>
              {job.progress_raw?.[1] ? (
                <span className="tabular-nums">
                  ROM {job.progress_raw[0]}/{job.progress_raw[1]}
                </span>
              ) : null}
            </div>
            {aggregated?.errors?.length ? (
              <details className="mt-2">
                <summary className="cursor-pointer text-[11px] font-semibold text-destructive">
                  {aggregated.errors.length} errores
                </summary>
                <ul className="mt-1 max-h-32 space-y-0.5 overflow-y-auto text-[11px] text-muted-foreground">
                  {aggregated.errors.slice(0, 40).map((message, index) => (
                    <li key={index} className="truncate">
                      {message}
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </section>
        )}

        {/* Acción principal (sólo cuando hay un sistema que escrapear) */}
        {systems.length > 0 && (
          <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              El scraping se ejecuta en segundo plano: puedes seguir usando el manager.
            </p>
            <Button
              variant="secondary"
              size="sm"
              onClick={startScrape}
              disabled={starting || !ready || running}
            >
              {starting ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
              {running ? 'Scraping en curso…' : 'Escrapear sistema'}
            </Button>
          </div>
        )}
      </div>
    </Modal>
  )
}
