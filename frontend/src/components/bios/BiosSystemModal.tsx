import { Copy, SkipForward, Upload, Wrench } from 'lucide-react'
import { useRef, useState } from 'react'
import { Button, IconButton } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { useNotify } from '@/hooks/useNotify'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import { BIOS_ESTADOS, esReparable } from '@/lib/biosStates'
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

/**
 * Detalle de las BIOS de un sistema: cada fichero con su estado, el hash que
 * pide Batocera y las acciones para arreglarlo.
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

  const reparables = files.filter((file) => esReparable(file.estado))
  const correctas = files.filter((file) => file.estado === 'ok' || file.estado === 'sin_verificar')
  const problemas = files.filter(
    (file) => !esReparable(file.estado) && file.estado !== 'ok' && file.estado !== 'sin_verificar' && file.estado !== 'omitida',
  )

  /** Repara un fichero: lo deja en su sitio y verifica el resultado. */
  const repair = async (file: BiosFile) => {
    setBusy(file.file)
    triggerHaptic('light')
    try {
      const result = await api.biosRepair({ system: slug, file: file.file })
      showNotify({
        variant: 'success',
        title: `${file.file} colocada`,
        message:
          result.estado === 'ok'
            ? 'Verificada contra el catálogo de Batocera.'
            : 'Colocada en su sitio.',
      })
      onRepaired()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: `No se pudo reparar ${file.file}`,
        message: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setBusy(null)
    }
  }

  /** Repara todo lo reparable del sistema. */
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
        ? 'Las que fallaron se pueden subir a mano.'
        : 'Todo verificado contra el catálogo de Batocera.',
    })
    onRepaired()
  }

  /** Sube a mano el fichero que el usuario elige. */
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
                  {esReparable(file.estado) && (
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
            </li>
          )
        })}
      </ul>
    </Modal>
  )
}
