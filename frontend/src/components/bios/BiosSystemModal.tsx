import {
  CircleAlert,
  Copy,
  Download,
  ExternalLink,
  SkipForward,
  Upload,
  Wrench,
} from 'lucide-react'
import { useRef, useState } from 'react'
import { Button, IconButton } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { useNotify } from '@/hooks/useNotify'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import { BIOS_ESTADOS, esProblema, esReparable } from '@/lib/biosStates'
import type { BiosCandidate, BiosFile } from '@/lib/types'
import { cn } from '@/lib/utils'

interface BiosSystemModalProps {
  open: boolean
  onClose: () => void
  /** Slug del sistema. */
  slug: string
  /** Nombre legible del catálogo de Batocera. */
  name: string
  /** Ficheros de BIOS que exige el catálogo para este sistema. */
  files: BiosFile[]
  /** Se llama cuando algo ha cambiado y hay que refrescar la lista. */
  onRepaired: () => void
}

/** Tamaño legible (el backend lo manda en bytes). */
function humanSize(bytes: number | null): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

/** Enlace para buscar ese fichero de BIOS por otro lado (GitHub). */
function busquedaExterna(file: string): string {
  return `https://github.com/search?q=${encodeURIComponent(file)}&type=code`
}

/**
 * Agrupa los candidatos por contenedor: de un ZIP con tres ficheros útiles
 * sale una sola fila, no tres.
 */
function agruparCandidatos(lista: BiosCandidate[]) {
  const mapa = new Map<string, { candidato: BiosCandidate; miembros: string[] }>()
  for (const c of lista) {
    const clave = `${c.item}|${c.name}`
    const previo = mapa.get(clave)
    if (previo) {
      if (c.member && !previo.miembros.includes(c.member)) previo.miembros.push(c.member)
      previo.candidato.trae = Math.max(previo.candidato.trae ?? 0, c.trae ?? 0)
      previo.candidato.completo = previo.candidato.completo || c.completo
    } else {
      mapa.set(clave, { candidato: { ...c }, miembros: c.member ? [c.member] : [] })
    }
  }
  return [...mapa.values()]
}

/**
 * Detalle de las BIOS de un sistema: cada fichero con su estado, el hash que
 * pide Batocera y las acciones para arreglarlo.
 *
 * «Reparar» va en este orden: primero se busca el contenido en la propia
 * consola (no necesita red); si no está, se busca en archive.org y se
 * enseñan las fuentes con su licencia para que el usuario elija. Si no hay
 * ninguna fuente, se dice con claridad y se ofrece subir el fichero a mano.
 */
export function BiosSystemModal({
  open,
  onClose,
  slug,
  name,
  files,
  onRepaired,
}: BiosSystemModalProps) {
  const { showNotify } = useNotify()
  const [busy, setBusy] = useState<string | null>(null)
  const [batch, setBatch] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploadTarget, setUploadTarget] = useState<string | null>(null)
  /** Candidatos de archive.org ya buscados, por fichero. */
  const [candidatos, setCandidatos] = useState<Record<string, BiosCandidate[]>>({})

  const reparables = files.filter((file) => esReparable(file.estado))
  const correctas = files.filter((file) => file.estado === 'ok' || file.estado === 'sin_verificar')
  const problemas = files.filter(
    (file) => !esReparable(file.estado) && file.estado !== 'ok' && file.estado !== 'sin_verificar' && file.estado !== 'omitida',
  )

  /** Sube un fichero a mano (la última vía, siempre disponible). */
  const pickFile = (file: string) => {
    setUploadTarget(file)
    inputRef.current?.click()
  }

  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const blob = event.target.files?.[0]
    const target = uploadTarget
    event.target.value = ''
    if (!blob || !target) return
    setBusy(target)
    try {
      await api.biosUpload({ system: slug, file: target, blob })
      showNotify({ variant: 'success', title: `${target} subida` })
      onRepaired()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: `No se pudo subir ${target}`,
        message: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setBusy(null)
    }
  }

  /**
   * Repara un fichero: primero en la consola y, si no está, en archive.org.
   *
   * La descarga de archive.org no se hace sin que el usuario la pida: se
   * enseñan las fuentes con su licencia y él elige.
   */
  const repair = async (file: BiosFile) => {
    setBusy(file.file)
    triggerHaptic('light')
    try {
      const local = await api.biosRepair({ system: slug, file: file.file, source: 'local' })
      showNotify({
        variant: 'success',
        title: `${file.file} colocada`,
        message:
          local.estado === 'ok'
            ? 'Verificada contra el catálogo de Batocera.'
            : 'Colocada en su sitio.',
      })
      onRepaired()
      return
    } catch {
      // No está en la consola: sigue buscando en archive.org.
    }
    try {
      const encontrado = await api.biosSearchSources({ system: slug, file: file.file })
      setCandidatos((prev) => ({ ...prev, [file.file]: encontrado.candidates ?? [] }))
      if (!encontrado.candidates?.length) {
        showNotify({
          variant: 'error',
          title: 'No hay ninguna fuente con ese contenido',
          message: 'Ninguna colección de archive.org lo tiene. Puedes subir el fichero a mano.',
        })
      }
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo buscar en archive.org',
        message: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setBusy(null)
    }
  }

  /** Descarga el candidato elegido y lo instala en su sitio. */
  const install = async (file: BiosFile, candidate: BiosCandidate) => {
    setBusy(file.file)
    triggerHaptic('light')
    try {
      await api.biosInstall({ system: slug, file: file.file, candidate })
      showNotify({
        variant: 'success',
        title: `${file.file} instalada`,
        message: `Descargada de ${candidate.source} y verificada contra el catálogo.`,
      })
      setCandidatos((prev) => {
        const next = { ...prev }
        delete next[file.file]
        return next
      })
      onRepaired()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: `No se pudo instalar ${file.file}`,
        message: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setBusy(null)
    }
  }

  /** Repara todo lo reparable SIN salir de la consola. */
  const repairAll = async () => {
    if (!reparables.length) return
    setBatch(true)
    triggerHaptic('medium')
    let ok = 0
    let fail = 0
    for (const file of reparables) {
      try {
        await api.biosRepair({ system: slug, file: file.file, source: 'local' })
        ok += 1
      } catch {
        fail += 1
      }
    }
    setBatch(false)
    showNotify({
      variant: fail ? 'error' : 'success',
      title: fail ? `${ok} reparadas y ${fail} con problemas` : `${ok} BIOS reparadas`,
      message: fail
        ? 'Las que fallaron se pueden subir a mano.'
        : 'Todo verificado contra el catálogo de Batocera.',
    })
    onRepaired()
  }

  const toggleSkip = async (file: BiosFile) => {
    try {
      if (file.estado === 'omitida') {
        await api.biosUnskip(file.skip_key)
      } else {
        await api.biosSkip(file.skip_key)
      }
      onRepaired()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo cambiar el estado',
        message: error instanceof Error ? error.message : undefined,
      })
    }
  }

  /** Copia el hash que pide Batocera (o el que hay en disco) al portapapeles. */
  const copyHash = async (file: BiosFile) => {
    const hash = file.md5s[0] ?? file.md5
    if (!hash) {
      showNotify({ variant: 'error', title: 'Esta BIOS no tiene hash publicado' })
      return
    }
    try {
      await navigator.clipboard.writeText(hash)
      showNotify({ variant: 'success', title: 'Hash copiado', message: hash })
    } catch {
      showNotify({ variant: 'error', title: 'No se pudo copiar el hash' })
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={name}
      description={`${slug} · ${correctas.length} correctas de ${files.length} · ${problemas.length} con problemas`}
      className="max-w-3xl"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cerrar
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!reparables.length || batch}
            onClick={repairAll}
          >
            <Wrench className="size-4" />
            {batch ? 'Reparando…' : `Reparar ${reparables.length || ''}`.trim()}
          </Button>
        </>
      }
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={upload}
        aria-label="Subir una BIOS"
      />

      <ul className="max-h-[52vh] space-y-2 overflow-y-auto pr-1">
        {files.map((file) => {
          const info = BIOS_ESTADOS[file.estado]
          const EstadoIcon = info.icon
          const working = busy === file.file
          const candidatosFile = candidatos[file.file]
          const reparable = esReparable(file.estado)
          const conProblema = esProblema(file.estado)
          return (
            <li
              key={file.file}
              className="rounded-2xl border border-border bg-muted/30 p-3 transition-colors duration-150 hover:bg-muted/50"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold',
                        info.badge,
                      )}
                    >
                      <EstadoIcon className="size-3" />
                      {info.label}
                    </span>
                    <span className="truncate font-mono text-xs font-medium text-foreground">
                      {file.file}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    {file.members.length > 0
                      ? `ZIP con ${file.members.length} ${
                          file.members.length === 1 ? 'fichero exigido' : 'ficheros exigidos'
                        } dentro`
                      : info.ayuda}
                    {file.fuente ? ` · disponible en ${file.fuente}` : ''}
                    {file.faltan.length ? ` · falta: ${file.faltan.join(', ')}` : ''}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-1.5">
                  {(reparable || conProblema) && (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={working}
                      onClick={() => repair(file)}
                    >
                      <Wrench className="size-3.5" />
                      {working ? 'Reparando…' : 'Reparar'}
                    </Button>
                  )}
                  <IconButton label={`Subir ${file.file}`} onClick={() => pickFile(file.file)}>
                    <Upload className="size-3.5" />
                  </IconButton>
                  <IconButton
                    label="Copiar el hash"
                    onClick={() => copyHash(file)}
                  >
                    <Copy className="size-3.5" />
                  </IconButton>
                  <IconButton
                    label={file.estado === 'omitida' ? 'No omitir esta BIOS' : 'Omitir esta BIOS'}
                    onClick={() => toggleSkip(file)}
                  >
                    <SkipForward className="size-3.5" />
                  </IconButton>
                </div>
              </div>

              {/* Detalle: hash, tamaño y ruta */}
              <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-muted-foreground sm:grid-cols-4">
                <span className="truncate" title={file.md5s.join(', ')}>
                  md5 esperado:{' '}
                  <span className="font-mono text-foreground">
                    {file.md5s[0] ? `${file.md5s[0].slice(0, 12)}…` : 'no publicado'}
                  </span>
                </span>
                <span className="truncate" title={file.md5 ?? ''}>
                  md5 en disco:{' '}
                  <span className="font-mono text-foreground">
                    {file.md5 ? `${file.md5.slice(0, 12)}…` : '—'}
                  </span>
                </span>
                <span>tamaño: {humanSize(file.size)}</span>
                <span className="truncate" title={`/userdata/bios/${file.file}`}>
                  destino: <span className="font-mono text-foreground">/userdata/bios/{file.file}</span>
                </span>
              </div>

              {/* Fuentes en archive.org para este fichero */}
              {candidatosFile && (
                <div className="mt-2 rounded-xl border border-border bg-background/60 p-2">
                  {candidatosFile.length ? (
                    <>
                      <p className="text-[11px] font-medium text-foreground">
                        Encontrado en archive.org. Elige de dónde descargarlo:
                      </p>
                      <ul className="mt-1 space-y-1">
                        {agruparCandidatos(candidatosFile).map(({ candidato, miembros }) => (
                          <li
                            key={`${candidato.item}|${candidato.name}`}
                            className="flex flex-wrap items-center justify-between gap-2"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-[11px] font-medium text-foreground">
                                {candidato.source}
                              </p>
                              <p className="truncate text-[10px] text-muted-foreground">
                                {candidato.name} · {humanSize(candidato.size)} ·{' '}
                                {candidato.license ?? 'sin licencia declarada'}
                              </p>
                              {miembros.length > 0 && (
                                <p className="truncate text-[10px] text-muted-foreground">
                                  {miembros.join(', ')}
                                </p>
                              )}
                              {candidato.exigido && candidato.exigido > 1 && (
                                <p
                                  className={cn(
                                    'text-[10px]',
                                    candidato.completo
                                      ? 'text-emerald-600 dark:text-emerald-400'
                                      : 'text-amber-600 dark:text-amber-400',
                                  )}
                                >
                                  {candidato.completo
                                    ? `trae los ${candidato.exigido} ficheros que exige Batocera`
                                    : `trae ${candidato.trae ?? 0} de ${candidato.exigido} ficheros: faltará el resto`}
                                </p>
                              )}
                            </div>
                            <Button
                              size="sm"
                              variant="secondary"
                              disabled={working}
                              onClick={() => install(file, candidato)}
                            >
                              <Download className="size-3.5" />
                              Descargar
                            </Button>
                          </li>
                        ))}
                      </ul>
                      <p className="mt-2 flex items-start gap-1 text-[10px] leading-relaxed text-muted-foreground">
                        <CircleAlert className="mt-0.5 size-3 shrink-0" />
                        Estas BIOS tienen copyright. La app sólo las descarga si lo pides tú, y
                        comprueba el hash que exige Batocera antes de instalar nada.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-[11px] font-medium text-foreground">
                        Ninguna colección de archive.org tiene este contenido.
                      </p>
                      <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">
                        Puedes subir el fichero a mano (botón de arriba) o buscarlo en otro
                        sitio: el hash que tiene que tener es{' '}
                        <span className="font-mono">{file.md5s[0] ?? 'el que pide el catálogo'}</span>.
                      </p>
                      <a
                        href={busquedaExterna(file.file)}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-primary underline-offset-2 hover:underline"
                      >
                        <ExternalLink className="size-3" />
                        Buscar {file.file} en GitHub
                      </a>
                    </>
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </Modal>
  )
}
