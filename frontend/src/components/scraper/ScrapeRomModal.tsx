import { CircleAlert, CircleCheck, ImageOff, Loader2, Pencil, RefreshCw, Save, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Field, Input, Textarea } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { useNotify } from '@/hooks/useNotify'
import { ApiError, api } from '@/lib/api'
import {
  SCRAPER_SOURCES,
  readySources,
  sourceLabel,
  sourceMissing,
  sourceReady,
} from '@/lib/scraperSources'
import type {
  RomFolderItem,
  ScraperConfig,
  ScraperMeta,
  ScraperSearchResult,
  ScraperSource,
} from '@/lib/types'
import { cn } from '@/lib/utils'

/** Etiqueta de cada tipo de imagen que se puede descargar. */
const IMG_TYPE_LABELS: Record<string, string> = {
  mixrbv1: 'Mix v1 (caja + fondo)',
  mixrbv2: 'Mix v2',
  'box-2D': 'Caja 2D',
  ss: 'Screenshot',
  screenshot: 'Captura',
  wheel: 'Rueda / logo',
  fanart: 'Fanart',
}

/** Metadatos vacíos: la base sobre la que se edita. */
const EMPTY_META: ScraperMeta = { name: '', desc: '', genre: '', year: '', publisher: '', rating: '' }

interface ScrapeRomModalProps {
  open: boolean
  onClose: () => void
  system: string
  subpath: string
  rom: RomFolderItem | null
  /** Se llama cuando el ROM queda scraped y validado. */
  onSaved: () => void
}

/**
 * Modal flotante para buscar, descargar y editar los metadatos de un ROM.
 *
 * El flujo es por prioridad: se prueba **ScreenScraper** y, si no encuentra
 * el juego, se prueban **TheGamesDB** e **IGDB** como respaldo. Se puede
 * desactivar cualquier fuente desde el propio modal.
 *
 * **Actualizar** vuelve a buscar, **Editar** abre los metadatos y **Guardar**
 * descarga la imagen, guarda los datos y cierra el modal.
 */
export function ScrapeRomModal({ open, onClose, system, subpath, rom, onSaved }: ScrapeRomModalProps) {
  const { showNotify } = useNotify()

  const [config, setConfig] = useState<ScraperConfig | null>(null)
  const [enabled, setEnabled] = useState<ScraperSource[]>([])
  const [result, setResult] = useState<ScraperSearchResult | null>(null)
  const [meta, setMeta] = useState<ScraperMeta>(EMPTY_META)
  const [editing, setEditing] = useState(false)
  const [searching, setSearching] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imgTypes, setImgTypes] = useState<string[]>([])
  const [imageType, setImageType] = useState('mixrbv1')
  const [imgState, setImgState] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle')
  /** Nombre con el que se busca: se puede editar para afinar la búsqueda. */
  const [searchName, setSearchName] = useState('')
  /** Muestra el campo para editar el nombre de búsqueda. */
  const [nameEditor, setNameEditor] = useState(false)
  /** La búsqueda no encontró nada (no es un error: se puede afinar el nombre). */
  const [noResults, setNoResults] = useState(false)
  /** El juego ya tiene su ficha en la biblioteca: se muestran los datos locales. */
  const [local, setLocal] = useState(false)

  /** Busca el ROM en las fuentes indicadas, por orden de prioridad. */
  const runSearch = useCallback(
    async (sources: ScraperSource[], nombre: string) => {
      if (!rom) return
      if (!sources.length) {
        setError('Elige al menos una fuente de datos')
        return
      }
      if (!nombre.trim()) {
        setError('Escribe un nombre para buscar')
        return
      }
      setSearching(true)
      setError(null)
      setNoResults(false)
      setLocal(false)
      try {
        const res = await api.scraperSearch({
          filename: nombre.trim(),
          system,
          subpath,
          source: sources[0],
          sources,
        })
        setResult(res)
        const found = res.meta ?? EMPTY_META
        setMeta({
          name: found.name || rom.name,
          desc: found.desc || rom.desc || '',
          genre: found.genre || rom.genre || '',
          year: found.year || rom.year || '',
          publisher: found.publisher || rom.publisher || '',
          rating: found.rating || rom.rating || '',
        })
        // Por defecto se descarga el tipo de imagen configurado; si no está
        // disponible, el primero que ofrezca la fuente.
        const available = res.img_types ?? []
        setImgTypes(
          available.includes(imageType) ? [imageType] : available.length ? [available[0]] : [],
        )
        // Sin resultados: se ofrece editar el nombre para afinar la búsqueda.
        if (!res.game) {
          setNoResults(true)
          setNameEditor(true)
        }
      } catch (err) {
        setResult(null)
        const mensaje = err instanceof Error ? err.message : 'No se pudo buscar el juego'
        // «Sin resultados» no es un fallo: lo que hace falta es otro nombre.
        if (/sin resultado|no encontrad|no result/i.test(mensaje)) {
          setNoResults(true)
          setNameEditor(true)
        } else {
          setError(mensaje)
        }
      } finally {
        setSearching(false)
      }
    },
    [rom, system, subpath, imageType],
  )

  /* Al abrir: leer la configuración, elegir las fuentes con credenciales y
     buscar el juego. */
  useEffect(() => {
    if (!open || !rom) return
    setEditing(false)
    setError(null)
    setResult(null)
    setImgState('idle')
    setNameEditor(false)
    setNoResults(false)
    setLocal(false)
    // Si el juego es una carpeta (ScummVM, DOSBox, MUGEN...) se busca por el
    // nombre de la carpeta, sin la extension.
    const nombreBusqueda = rom.is_game_folder ? rom.name : rom.filename
    setSearchName(nombreBusqueda)
    let cancelled = false
    void (async () => {
      let cfg: ScraperConfig | null = null
      try {
        cfg = await api.scraperConfig()
      } catch {
        cfg = null
      }
      if (cancelled) return
      setConfig(cfg)
      const preferred = cfg?.ss_image_type || 'mixrbv1'
      setImageType(preferred)
      const fuentes = cfg
        ? readySources(cfg)
        : (SCRAPER_SOURCES.map((s) => s.id) as ScraperSource[])
      setEnabled(fuentes)
      if (rom.has_image) {
        // El juego ya tiene su ficha en la biblioteca: no hay nada que
        // scrapear, se muestran los datos locales. El scraping queda como
        // opción si el usuario lo pide.
        setLocal(true)
        setMeta({
          name: rom.name,
          desc: rom.desc ?? '',
          genre: rom.genre ?? '',
          year: rom.year ?? '',
          publisher: rom.publisher ?? '',
          rating: rom.rating ?? '',
        })
        return
      }
      await runSearch(fuentes, nombreBusqueda)
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, rom])

  /* Carátula: la de la fuente (vía proxy, porque ScreenScraper no la sirve
     sin referer) y, si no hay, la que ya tiene el ROM en la biblioteca. */
  const preview = useMemo(() => {
    if (result?.image_url) {
      return `/api/scraper/image?url=${encodeURIComponent(result.image_url)}`
    }
    if (rom?.has_image) {
      const base = `/api/rom-image/${encodeURIComponent(system)}/${encodeURIComponent(rom.filename)}`
      return subpath ? `${base}?subpath=${encodeURIComponent(subpath)}` : base
    }
    return null
  }, [result?.image_url, rom, system, subpath])

  /* La carátula se descarga desde el proxy: puede tardar, así que se avisa
     mientras llega. */
  useEffect(() => {
    setImgState(preview ? 'loading' : 'idle')
  }, [preview])

  /** Fuentes que se probaron sin éxito (todas menos la que acertó). */
  const fallbacks = useMemo(() => {
    if (!result?.tried?.length || !result.source) return []
    const idx = result.tried.indexOf(result.source)
    return idx > 0 ? result.tried.slice(0, idx) : []
  }, [result])

  /** Botón «Guardar»: descarga la imagen, guarda los metadatos y cierra. */
  const handleSave = async () => {
    if (!rom) return
    if (!result?.game) {
      // Modo local (el juego ya tenía ficha): sólo se guardan los metadatos
      // editados, sin volver a scrapear ni descargar imágenes.
      if (!editing) {
        setError('No hay nada que guardar: el juego ya tiene su ficha')
        return
      }
      setSaving(true)
      setError(null)
      try {
        await api.updateRomMeta({
          system,
          filename: rom.filename,
          subpath,
          name: meta.name,
          desc: meta.desc,
          genre: meta.genre,
          year: meta.year,
          publisher: meta.publisher,
          rating: meta.rating,
        })
        onSaved()
        onClose()
        showNotify({
          variant: 'success',
          title: 'Ficha actualizada',
          message: `${meta.name || rom.name} · datos guardados en el gamelist.xml`,
        })
      } catch (err) {
        const detalle =
          err instanceof ApiError ? [err.message, ...err.errors].join('\n') : String(err)
        setError(err instanceof Error ? err.message : 'No se pudo guardar la ficha')
        showNotify({
          variant: 'error',
          title: 'No se pudo guardar la ficha',
          message: err instanceof Error ? err.message : 'No se pudo guardar la ficha',
          detail: detalle,
        })
      } finally {
        setSaving(false)
      }
      return
    }
    setSaving(true)
    setError(null)
    try {
      const download = await api.scraperDownload({
        system,
        filename: rom.filename,
        subpath,
        source: result.source,
        game: result.game,
        save_meta: true,
        img_types: imgTypes.length ? imgTypes : undefined,
      })

      if (editing) {
        await api.updateRomMeta({
          system,
          filename: rom.filename,
          subpath,
          name: meta.name,
          desc: meta.desc,
          genre: meta.genre,
          year: meta.year,
          publisher: meta.publisher,
          rating: meta.rating,
        })
      }

      const failures = download.results?.errors ?? []
      const imagenes = download.results?.images ?? []
      onSaved()
      onClose()

      if (failures.length) {
        // El aviso de error se queda en pantalla hasta que se confirme.
        showNotify({
          variant: 'error',
          title: 'Guardado con errores',
          message: `Se guardaron los metadatos, pero ${failures.length} imagen(es) no se pudieron descargar.`,
          detail: failures.join('\n'),
        })
      } else {
        showNotify({
          variant: 'success',
          title: 'Juego scraped y guardado',
          message: [
            meta.name || rom.name,
            imagenes.length
              ? `${imagenes.length} imagen(es) descargada(s)`
              : 'Metadatos guardados',
          ].join(' · '),
        })
      }
    } catch (err) {
      const detalle =
        err instanceof ApiError ? [err.message, ...err.errors].join('\n') : String(err)
      setError(err instanceof Error ? err.message : 'No se pudo guardar el juego')
      showNotify({
        variant: 'error',
        title: 'No se pudo guardar el juego',
        message: err instanceof Error ? err.message : 'No se pudo guardar el juego',
        detail: detalle,
      })
    } finally {
      setSaving(false)
    }
  }

  const metaItems = [
    { key: 'name' as const, label: 'Título' },
    { key: 'year' as const, label: 'Año' },
    { key: 'publisher' as const, label: 'Editorial' },
    { key: 'genre' as const, label: 'Género' },
    { key: 'rating' as const, label: 'Nota' },
  ]

  const toggleSource = (id: ScraperSource) => {
    setEnabled((prev) => {
      if (prev.includes(id)) {
        const next = prev.filter((s) => s !== id)
        return next.length ? next : prev
      }
      // Se reinserta respetando el orden de prioridad.
      return SCRAPER_SOURCES.map((s) => s.id).filter(
        (s) => s === id || prev.includes(s),
      ) as ScraperSource[]
    })
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={rom?.name ?? 'Juego'}
      description={`${system}${subpath ? ` / ${subpath}` : ''}`}
      className="max-w-xl"
      footer={
        <>
          {result?.game ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void runSearch(enabled, searchName)}
              disabled={searching || saving}
            >
              <RefreshCw className={cn('size-4', searching && 'animate-spin')} />
              Actualizar
            </Button>
          ) : (
            <Button
              variant={local && !editing ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => void runSearch(enabled, searchName)}
              disabled={searching || saving}
            >
              {searching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
              Escapear
            </Button>
          )}
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
          {(result?.game || editing) && (
            <Button variant="primary" size="sm" onClick={handleSave} disabled={saving || searching}>
              {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
              Guardar
            </Button>
          )}
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

        {/* Fuentes, por orden de prioridad (sólo cuando hay algo que scrapear) */}
        {!local && (
          <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Fuentes (por orden de prioridad)
          </h3>
          <div className="flex flex-wrap gap-2">
            {SCRAPER_SOURCES.map((option, index) => {
              const active = enabled.includes(option.id)
              const ready = sourceReady(config, option.id)
              return (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => toggleSource(option.id)}
                  className={cn(
                    'flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-colors duration-150',
                    'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                    active
                      ? 'border-brand bg-brand/10 text-foreground'
                      : 'border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground',
                    !ready && 'opacity-70',
                  )}
                >
                  <span className="tabular-nums text-[10px] font-bold text-muted-foreground">{index + 1}</span>
                  {option.label}
                  <span
                    className={cn(
                      'rounded-full px-1.5 py-0.5 text-[10px] font-semibold',
                      !ready
                        ? 'bg-muted text-muted-foreground'
                        : active
                          ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                          : 'bg-muted text-muted-foreground',
                    )}
                  >
                    {!ready ? sourceMissing(config, option.id) : active ? 'Activa' : 'Inactiva'}
                  </span>
                </button>
              )
            })}
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            Se prueban en orden: la primera que encuentre el juego gana.
          </p>
          </section>
        )}

        {searching && (
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-muted/40 px-4 py-6 text-xs font-medium text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Buscando en {enabled.map(sourceLabel).join(' → ') || '…'}
          </div>
        )}

        {!searching && !result?.game && !error && !local && (
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-border px-4 py-8 text-center">
            <Search className="size-5 text-muted-foreground/60" />
            <p className="text-xs font-medium text-muted-foreground">
              {noResults
                ? 'Ninguna fuente encontró el juego con ese nombre. Edítalo para acotar la búsqueda.'
                : 'Sin resultados. Pulsa «Actualizar» para buscarlo de nuevo.'}
            </p>
          </div>
        )}

        {/* Nombre de búsqueda: si no aparece, se puede afinar */}
        {nameEditor && (
          <section className="rounded-2xl border border-border bg-muted/40 p-3">
            <Field
              label="Nombre para buscar"
              htmlFor="scrape-search-name"
              hint={
                rom?.is_game_folder
                  ? 'El juego está en una carpeta: se busca por el nombre de la carpeta. La carpeta no se renombra, los datos se guardan siempre en su sitio.'
                  : 'Por ejemplo «007: Agent Under Fire». El ROM no se renombra: los datos se guardan siempre en el fichero original.'
              }
            >
              <div className="flex gap-2">
                <Input
                  id="scrape-search-name"
                  value={searchName}
                  autoFocus
                  spellCheck={false}
                  onChange={(e) => setSearchName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      void runSearch(enabled, searchName)
                    }
                  }}
                  placeholder="Nombre del juego"
                />
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={searching || !searchName.trim()}
                  onClick={() => void runSearch(enabled, searchName)}
                >
                  {searching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
                  Buscar
                </Button>
              </div>
            </Field>
          </section>
        )}

        {result?.game && !nameEditor && (
          <button
            type="button"
            onClick={() => setNameEditor(true)}
            className="cursor-pointer text-[11px] font-semibold text-muted-foreground underline-offset-2 transition-colors duration-150 hover:text-foreground hover:underline"
          >
            Buscar con otro nombre
          </button>
        )}

        {local && !result?.game && (
          <div className="space-y-3">
            <div className="flex gap-3 rounded-2xl border border-border bg-muted/40 p-3">
              {/* Carátula local */}
              <div className="flex size-28 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-muted">
                {preview ? (
                  <img
                    src={preview}
                    alt=""
                    className="size-full object-cover"
                  />
                ) : (
                  <ImageOff className="size-5 text-muted-foreground/50" aria-hidden />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-2">
                  <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">
                      {meta.name || rom?.name}
                    </p>
                    <p className="mt-0.5 text-[11px] font-medium text-muted-foreground">
                      {[meta.year, meta.publisher, meta.genre].filter(Boolean).join(' · ') ||
                        'Sin metadatos'}
                    </p>
                  </div>
                </div>
                <p className="mt-1.5 text-[11px] font-semibold text-foreground">
                  Ficha de tu biblioteca
                </p>
                {meta.desc && (
                  <p className="mt-1.5 line-clamp-4 text-[11px] leading-relaxed text-muted-foreground">
                    {meta.desc}
                  </p>
                )}
              </div>
            </div>

            <p className="rounded-xl border border-border bg-muted/40 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
              {meta.desc || meta.genre || meta.publisher || meta.year ? (
                <>
                  Este juego <strong className="text-foreground">ya tiene su información y su
                  carátula</strong>: no hace falta volver a scrapearlo. Puedes <strong
                    className="text-foreground">editar</strong> los datos o, si quieres
                  actualizarlos, pulsar «Escapear» para buscarlo de nuevo en las fuentes.
                </>
              ) : (
                <>
                  Este juego <strong className="text-foreground">ya tiene su carátula</strong>,
                  aunque le faltan los datos. Puedes <strong className="text-foreground">editar
                  </strong> la ficha a mano o pulsar «Escapear» para completarla desde las
                  fuentes.
                </>
              )}
            </p>
          </div>
        )}

        {result?.game && (
          <>
            <div className="flex gap-3 rounded-2xl border border-border bg-muted/40 p-3">
              {/* Carátula */}
              <div className="flex size-28 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-muted">
                {preview ? (
                  <>
                    <img
                      key={preview}
                      src={preview}
                      alt=""
                      onLoad={() => setImgState('ok')}
                      onError={() => setImgState('error')}
                      className={cn(
                        'size-full object-cover transition-opacity duration-200',
                        imgState === 'ok' ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                    {imgState !== 'ok' &&
                      (imgState === 'error' ? (
                        <ImageOff className="size-5 text-muted-foreground/50" aria-hidden />
                      ) : (
                        <Loader2 className="size-5 animate-spin text-muted-foreground/60" aria-hidden />
                      ))}
                  </>
                ) : (
                  <ImageOff className="size-5 text-muted-foreground/50" aria-hidden />
                )}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-2">
                  <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold tracking-[-0.015em] text-foreground">
                      {meta.name || result.meta?.name || rom?.name}
                    </p>
                    <p className="mt-0.5 text-[11px] font-medium text-muted-foreground">
                      {[meta.year, meta.publisher, meta.genre].filter(Boolean).join(' · ') || 'Sin metadatos'}
                    </p>
                  </div>
                </div>
                <p className="mt-1.5 text-[11px] font-semibold text-foreground">
                  Fuente: {sourceLabel(result.source)}
                </p>
                {imgState === 'loading' && (
                  <p className="mt-0.5 text-[11px] text-muted-foreground">Cargando carátula…</p>
                )}
                {imgState === 'error' && (
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    No se pudo cargar la carátula de la fuente.
                  </p>
                )}
                {fallbacks.length > 0 && (
                  <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
                    {fallbacks.map(sourceLabel).join(' y ')} no tenían datos para este juego.
                  </p>
                )}
                {meta.desc && (
                  <p className="mt-1.5 line-clamp-3 text-[11px] leading-relaxed text-muted-foreground">
                    {meta.desc}
                  </p>
                )}
              </div>
            </div>

            {/* Opciones de imagen a descargar */}
            {result.source === 'screenscraper' && (result.img_types?.length ?? 0) > 0 && (
              <section>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                  Imágenes a descargar
                </h3>
                <div className="flex flex-wrap gap-2">
                  {(result.img_types ?? []).map((type) => {
                    const active = imgTypes.includes(type)
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() =>
                          setImgTypes((prev) =>
                            prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
                          )
                        }
                        className={cn(
                          'cursor-pointer rounded-xl border px-2.5 py-1 text-[11px] font-semibold transition-colors duration-150',
                          'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                          active
                            ? 'border-brand bg-brand/10 text-foreground'
                            : 'border-border text-muted-foreground hover:bg-muted hover:text-foreground',
                        )}
                      >
                        {IMG_TYPE_LABELS[type] ?? type}
                      </button>
                    )
                  })}
                </div>
              </section>
            )}

            {editing && (
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  {metaItems.map((item) => (
                    <Field key={item.key} label={item.label} htmlFor={`rom-${item.key}`}>
                      <Input
                        id={`rom-${item.key}`}
                        value={meta[item.key]}
                        onChange={(e) => setMeta((prev) => ({ ...prev, [item.key]: e.target.value }))}
                      />
                    </Field>
                  ))}
                </div>
                <Field label="Descripción" htmlFor="rom-desc">
                  <Textarea
                    id="rom-desc"
                    value={meta.desc}
                    onChange={(e) => setMeta((prev) => ({ ...prev, desc: e.target.value }))}
                  />
                </Field>
              </div>
            )}

            <p className="border-t border-border pt-3 text-[11px] leading-relaxed text-muted-foreground">
              Al guardar se descarga la imagen y se escriben los metadatos en el gamelist.xml.
            </p>
          </>
        )}
      </div>
    </Modal>
  )
}
