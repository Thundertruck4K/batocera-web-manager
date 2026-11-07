import {
  CircleAlert,
  Copy,
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
import type { BiosFile } from '@/lib/types'
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
  /** Enlace para buscar las BIOS de este sistema en Google. */
  busqueda?: string | null
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

/** Enlace de respaldo si el backend no lo manda. */
function busquedaGoogle(file: string): string {
  const nombre = file.split('/').pop() ?? file
  return `https://www.google.com/search?q=${encodeURIComponent(`"${nombre}"`)}`
}

/**
 * Detalle de las BIOS de un sistema: cada fichero con su estado y las
 * acciones para arreglarlo.
 *
 * El flujo es el de Batocera en la realidad: si el fichero está en su sitio,
 * no hay nada que hacer; si no está, se busca por fuera (Google) o lo sube el
 * usuario. «Reparar» mueve contenido que ya está en la propia consola, que es
 * lo único que se puede hacer sin red.
 */
export function BiosSystemModal({
  open,
  onClose,
  slug,
  name,
  files,
  busqueda,
  onRepaired,
}: BiosSystemModalProps) {
  const { showNotify } = useNotify()
  const [busy, setBusy] = useState<string | null>(null)
  const [batch, setBatch] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploadTarget, setUploadTarget] = useState<string | null>(null)

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
   * Repara un fichero con lo que ya hay en la consola (otro ZIP u otra
   * carpeta). Si no hay nada, se dice con claridad: hay que buscarlo por
   * fuera o subirlo.
   */
  const repair = async (file: BiosFile) => {
    setBusy(file.file)
    triggerHaptic('light')
    try {
      await api.biosRepair({ system: slug, file: file.file })
      showNotify({
        variant: 'success',
        title: `${file.file} colocada`,
        message: 'Colocada donde Batocera la espera.',
      })
      onRepaired()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No hay nada que reparar en la consola',
        message:
          error instanceof Error
            ? error.message
            : 'El contenido no está en la tarjeta: búscalo en Google o súbelo.',
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
        await api.biosRepair({ system: slug, file: file.file })
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
        ? 'Las que fallaron hay que buscarlas por fuera o subirlas a mano.'
        : 'Todo colocado donde Batocera lo espera.',
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

  /** Copia el hash que publica Batocera (o el que hay en disco) al portapapeles. */
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
          {/* El botón sólo aparece si hay algo que reparar: si no, es un botón
              inerte que no hace nada. */}
          {reparables.length > 0 && (
            <Button variant="primary" size="sm" disabled={batch} onClick={repairAll}>
              <Wrench className="size-4" />
              {batch ? 'Reparando…' : `Reparar ${reparables.length}`}
            </Button>
          )}
        </>
      }
    >
      {/* El input está oculto, pero no se esconde con `display: none` (con
          `hidden` no lo alcanza ni el teclado): se queda en el flujo, con
          tamaño 0, para no ensanchar el documento. */}
      <input
        ref={inputRef}
        type="file"
        className="h-px w-px border-0 p-0 opacity-0"
        onChange={upload}
        aria-label="Subir una BIOS"
      />

      <ul className="max-h-[52vh] space-y-2 overflow-y-auto pr-1">
        {files.map((file) => {
          const info = BIOS_ESTADOS[file.estado]
          const EstadoIcon = info.icon
          const working = busy === file.file
          const reparable = esReparable(file.estado)
          const conProblema = esProblema(file.estado)
          /** Sin contenido en la consola: hay que buscarlo por fuera o subirlo. */
          const buscar = conProblema
          const enlaceFichero = file.busqueda || busquedaGoogle(file.file)
          /** El enlace busca el nombre del fichero, no su ruta. */
          const nombreFichero = file.file.split('/').pop() ?? file.file
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
                  {reparable && (
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
                  md5 publicado:{' '}
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

              {/* Falta contenido: se busca por fuera o lo sube el usuario */}
              {buscar && (
                <div className="mt-2 rounded-xl border border-border bg-background/60 p-3">
                  <p className="text-[11px] font-medium text-foreground">
                    {file.file} no está en la consola
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    No hay nada que reparar por dentro: el contenido no está en la tarjeta.
                    Búscalo por tu cuenta en Google y súbelo aquí; la app lo deja en su sitio.
                    {file.members.length > 0 && ' Si es un ZIP, sube el ZIP completo.'}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <a
                      href={enlaceFichero}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-primary underline-offset-2 hover:underline"
                    >
                      <ExternalLink className="size-3" />
                      Buscar {nombreFichero} en Google
                    </a>
                    {busqueda && (
                      <a
                        href={busqueda}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="inline-flex items-center gap-1 text-[11px] font-medium text-primary underline-offset-2 hover:underline"
                      >
                        <ExternalLink className="size-3" />
                        Buscar las BIOS de {name} en Google
                      </a>
                    )}
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={working}
                      onClick={() => pickFile(file.file)}
                    >
                      <Upload className="size-3.5" />
                      Subir el archivo
                    </Button>
                  </div>
                  <p className="mt-2 flex items-start gap-1 text-[10px] leading-relaxed text-muted-foreground">
                    <CircleAlert className="mt-0.5 size-3 shrink-0" />
                    Las BIOS tienen copyright: la app no descarga nada por su cuenta. Sólo tú
                    decides qué fichero subes.
                  </p>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </Modal>
  )
}
