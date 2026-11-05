import { CircleAlert, CircleCheck, Download, Loader2, Pencil, RefreshCw, Save, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Field, Input, Textarea } from '@/components/ui/Field'
import { Modal } from '@/components/ui/Modal'
import { useToast } from '@/hooks/useToast'
import { api } from '@/lib/api'
import type { RomFolderItem, ScraperMeta, ScraperSearchResult, ScraperSource } from '@/lib/types'
import { cn } from '@/lib/utils'

const SOURCE_LABELS: Record<ScraperSource, string> = {
  screenscraper: 'ScreenScraper',
  thegamesdb: 'TheGamesDB',
  igdb: 'IGDB',
}

/** Metadatos vacíos: la base sobre la que se edita. */
const EMPTY_META: ScraperMeta = { name: '', desc: '', genre: '', year: '', publisher: '', rating: '' }

interface ScrapeRomModalProps {
  open: boolean
  onClose: () => void
  system: string
  subpath: string
  rom: RomFolderItem | null
  source: ScraperSource
  /** Se llama cuando el ROM queda scraped y validado. */
  onSaved: () => void
}

/**
 * Modal flotante para buscar, descargar y editar los metadatos de un ROM.
 *
 * **Actualizar** vuelve a buscar el juego, **Editar** abre los metadatos y
 * **Guardar** descarga la imagen, guarda los datos y cierra el modal.
 */
export function ScrapeRomModal({ open, onClose, system, subpath, rom, source, onSaved }: ScrapeRomModalProps) {
  const { showToast } = useToast()

  const [result, setResult] = useState<ScraperSearchResult | null>(null)
  const [meta, setMeta] = useState<ScraperMeta>(EMPTY_META)
  const [editing, setEditing] = useState(false)
  const [searching, setSearching] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [imageType, setImageType] = useState('mixrbv1')

  /** Busca el ROM en la fuente configurada. */
  const search = useCallback(async () => {
    if (!rom) return
    setSearching(true)
    setError(null)
    try {
      const res = await api.scraperSearch({
        filename: rom.filename,
        system,
        subpath,
        source,
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
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'No se pudo buscar el juego')
    } finally {
      setSearching(false)
    }
  }, [rom, system, subpath, source])

  /* Al abrir: buscar el juego y leer el tipo de imagen configurado. */
  useEffect(() => {
    if (!open || !rom) return
    setEditing(false)
    void search()
    void api
      .scraperConfig()
      .then((cfg) => setImageType(cfg.ss_image_type || 'mixrbv1'))
      .catch(() => undefined)
  }, [open, rom, search])

  /** Tipos de imagen que se pueden descargar para este juego. */
  const availableTypes = useMemo(() => result?.img_types ?? [], [result])

  /** Botón «Guardar»: descarga la imagen, guarda los metadatos y cierra. */
  const handleSave = async () => {
    if (!rom) return
    if (!result?.game) {
      setError('Busca primero el juego para poder guardarlo')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const types = availableTypes.includes(imageType)
        ? [imageType]
        : availableTypes.length
          ? [availableTypes[0]]
          : [imageType]

      const download = await api.scraperDownload({
        system,
        filename: rom.filename,
        subpath,
        source,
        game: result.game,
        save_meta: true,
        img_types: types,
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
      if (failures.length) {
        showToast(`Guardado con avisos: ${failures.length} imagen(es) sin descargar`, 'info')
      } else {
        showToast('Juego scraped y validado', 'success')
      }
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el juego')
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

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={rom?.name ?? 'Juego'}
      description={`${system}${subpath ? ` / ${subpath}` : ''} · ${SOURCE_LABELS[source]}`}
      className="max-w-xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={() => void search()} disabled={searching || saving}>
            <RefreshCw className={cn('size-4', searching && 'animate-spin')} />
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
          <Button variant="primary" size="sm" onClick={handleSave} disabled={saving || searching}>
            {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
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

        {searching && (
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-muted/40 px-4 py-6 text-xs font-medium text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Buscando en {SOURCE_LABELS[source]}…
          </div>
        )}

        {!searching && !result?.game && !error && (
          <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-border px-4 py-8 text-center">
            <Search className="size-5 text-muted-foreground/60" />
            <p className="text-xs font-medium text-muted-foreground">
              Sin resultados. Pulsa «Actualizar» para buscarlo de nuevo.
            </p>
          </div>
        )}

        {result?.game && (
          <>
            <div className="rounded-2xl border border-border bg-muted/40 p-3">
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
              {meta.desc && (
                <p className="mt-2 line-clamp-4 text-xs leading-relaxed text-muted-foreground">{meta.desc}</p>
              )}
              {availableTypes.length > 0 && (
                <p className="mt-2 text-[11px] font-medium text-muted-foreground">
                  Imagen: {availableTypes.includes(imageType) ? imageType : availableTypes[0]}
                </p>
              )}
            </div>

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

            <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Al guardar se descarga la imagen y se escriben los metadatos en el gamelist.xml.
              </p>
              <Button variant="secondary" size="sm" onClick={() => void search()} disabled={searching}>
                <Download className="size-4" />
                Buscar
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
