import {
  CircleAlert,
  FileCog,
  FileCode2,
  HardDrive,
  Layers,
  RefreshCw,
  Wand2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { Button, IconButton } from '@/components/ui/Button'
import { PanelCard } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { useApi } from '@/hooks/useApi'
import { useNotify } from '@/hooks/useNotify'
import { api } from '@/lib/api'
import type { ToolsBatchResult, ToolsFormatAction, ToolsRomFile } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Tamaño legible de un fichero. */
function humanSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`
}

/** El backend no ha sabido qué formato tiene este fichero. */
function sinReconocer(file: ToolsRomFile): boolean {
  return !file.label || file.kind === 'desconocido'
}

/** Un destino de conversión y cuántos ficheros del sistema lo admiten. */
interface Destino {
  id: string
  label: string
  nota?: string
  count: number
}

/** Un formato detectado y cuántos ficheros del sistema lo tienen. */
interface Formato {
  kind: string
  label: string
  count: number
}

export function ToolsFormatsPage() {
  const { openMenu } = useShell()
  const { showNotify } = useNotify()

  const systems = useApi(() => api.romSystems(), [])
  const [system, setSystem] = useState('')
  const [selected, setSelected] = useState<ToolsRomFile | null>(null)
  const [busy, setBusy] = useState(false)

  /* Conversión en lote. */
  const [destino, setDestino] = useState('')
  const [origen, setOrigen] = useState('')
  const [confirmarLote, setConfirmarLote] = useState(false)
  const [lote, setLote] = useState<ToolsBatchResult | null>(null)

  const files = useApi(() => api.toolsRoms(system), [system], { enabled: !!system })

  /** Los sistemas que tienen ROMs y ademas tienen formato que ver. */
  const conRom = useMemo(
    () => (systems.data ?? []).filter((item) => (item.rom_count ?? 0) > 0),
    [systems.data],
  )

  const lista = files.data?.files ?? []

  /** Los parches IPS de la carpeta (no son ROMs, pero se aplican igual). */
  const parches = useMemo(
    () => (files.data?.files ?? []).filter((file) => file.name.toLowerCase().endsWith('.ips')),
    [files.data],
  )

  /** Cuántos ficheros tienen un formato reconocido. */
  const reconocidos = useMemo(
    () => (files.data?.files ?? []).filter((file) => !sinReconocer(file)).length,
    [files.data],
  )

  /** Destinos de conversión que ofrece el backend para este sistema. */
  const destinos = useMemo<Destino[]>(() => {
    const mapa = new Map<string, Destino>()
    for (const file of files.data?.files ?? []) {
      for (const accion of file.acciones ?? []) {
        const actual = mapa.get(accion.id)
        if (actual) actual.count += 1
        else
          mapa.set(accion.id, {
            id: accion.id,
            label: accion.label,
            nota: accion.nota,
            count: 1,
          })
      }
    }
    return Array.from(mapa.values()).sort(
      (a, b) => b.count - a.count || a.label.localeCompare(b.label, 'es'),
    )
  }, [files.data])

  /** Formatos detectados en el sistema (para filtrar el lote). */
  const formatos = useMemo<Formato[]>(() => {
    const mapa = new Map<string, Formato>()
    for (const file of files.data?.files ?? []) {
      const actual = mapa.get(file.kind)
      if (actual) actual.count += 1
      else
        mapa.set(file.kind, {
          kind: file.kind,
          label: sinReconocer(file) ? 'Formato no reconocido' : file.label,
          count: 1,
        })
    }
    return Array.from(mapa.values()).sort((a, b) => b.count - a.count)
  }, [files.data])

  /** El destino elegido (si ya no existe, el primero disponible). */
  const destinoActual = destinos.find((item) => item.id === destino) ?? destinos[0] ?? null

  /** Ficheros que entran en el lote con el destino y el filtro elegidos. */
  const candidatos = useMemo(() => {
    if (!destinoActual) return []
    return (files.data?.files ?? []).filter(
      (file) =>
        (file.acciones ?? []).some((accion) => accion.id === destinoActual.id) &&
        (!origen || file.kind === origen),
    )
  }, [files.data, destinoActual, origen])

  /** Convierte un fichero suelto al destino que pide el backend. */
  const convertir = async (accion: ToolsFormatAction) => {
    if (!selected || !system) return
    setBusy(true)
    try {
      const result = await api.toolsConvert({ system, file: selected.name, target: accion.id })
      showNotify({
        variant: 'success',
        title: `Convertido a ${accion.label}`,
        message: result.out
          ? `${result.out}${result.size ? ` · ${humanSize(result.size)}` : ''}`
          : 'Hecho.',
      })
      setSelected(null)
      files.refresh()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo convertir',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

  /** Aplica un parche IPS a un fichero. */
  const parchear = async (patch: ToolsRomFile) => {
    if (!selected || !system) return
    setBusy(true)
    try {
      const result = await api.toolsPatch({ system, file: selected.name, patch: patch.name })
      showNotify({
        variant: 'success',
        title: 'Parche aplicado',
        message: result.out ?? 'Hecho.',
      })
      setSelected(null)
      files.refresh()
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo aplicar el parche',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

  /** Convierte en lote todos los ficheros que admitan el destino. */
  const convertirLote = async () => {
    if (!system || !destinoActual) return
    setBusy(true)
    try {
      const result = await api.toolsConvertBatch({
        system,
        target: destinoActual.id,
        ...(origen ? { kind: origen } : {}),
      })
      const resumen = result.resumen
      const convertidos = resumen?.hechos ?? 0
      const fallidos = resumen?.fallos ?? 0
      const total = resumen?.total ?? (result.hechos?.length ?? 0)
      setLote(result)
      setConfirmarLote(false)
      files.refresh()
      showNotify({
        variant: fallidos > 0 ? 'error' : 'success',
        title: 'Conversión en lote terminada',
        message: `${convertidos} convertidos · ${fallidos} fallidos de ${total}.`,
      })
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo convertir en lote',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

  const fallos = (lote?.hechos ?? []).filter((item) => !item.ok)

  return (
    <>
      <Topbar
        title="Formatos"
        subtitle="Convertir, parchear y comprimir las ROMs de la consola"
        onMenu={openMenu}
        actions={
          <IconButton label="Volver a listar" onClick={() => files.refresh()}>
            <RefreshCw className={cn('size-4', files.loading && 'animate-spin')} />
          </IconButton>
        }
      />

      <PageContainer>
        {systems.error && (
          <div className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">{systems.error}</span>
            <Button size="sm" variant="outline" onClick={systems.refresh}>
              Reintentar
            </Button>
          </div>
        )}

        <PanelCard
          title="Elige un sistema"
          subtitle="Los formatos se detectan leyendo la cabecera de cada imagen"
          icon={<HardDrive className="size-4" />}
        >
          <select
            value={system}
            onChange={(event) => {
              setSystem(event.target.value)
              setDestino('')
              setOrigen('')
              setLote(null)
            }}
            className="h-10 w-full max-w-sm cursor-pointer rounded-xl border border-border bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <option value="">— elige un sistema —</option>
            {conRom.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name} · {item.rom_count} ficheros
              </option>
            ))}
          </select>
        </PanelCard>

        <div className="mt-4">
          <PanelCard
            title={system ? `Ficheros de ${system}` : 'Ficheros'}
            subtitle={
              system
                ? `${lista.length} ficheros · ${reconocidos} con formato reconocido`
                : 'Elige un sistema para ver sus ficheros'
            }
            icon={<FileCog className="size-4" />}
          >
            {!system ? (
              <EmptyState
                title="Ningún sistema elegido"
                description="Arriba puedes elegir de qué sistema quieres mirar las ROMs."
              />
            ) : files.loading && !files.data ? (
              <EmptyState title="Leyendo los ficheros…" description="Un momento." />
            ) : !lista.length ? (
              <EmptyState
                title="No hay ficheros"
                description={`La carpeta de ${system} está vacía.`}
              />
            ) : (
              <ul className="divide-y divide-border">
                {lista.map((file) => {
                  const conversiones = (file.acciones ?? []).map((accion) => accion.label)
                  return (
                    <li key={file.name}>
                      <button
                        type="button"
                        onClick={() => setSelected(file)}
                        className="flex w-full cursor-pointer items-center gap-3 py-2.5 text-left transition-colors duration-150 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                      >
                        <FileCode2 className="size-4 shrink-0 text-muted-foreground" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-foreground">
                            {file.name}
                          </span>
                          <span className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                            <span
                              className={cn(
                                'rounded-md border px-1.5 py-0.5 font-medium',
                                sinReconocer(file)
                                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                                  : 'border-border',
                              )}
                            >
                              {sinReconocer(file) ? 'Formato no reconocido' : file.label}
                            </span>
                            <span>{humanSize(file.size)}</span>
                            {conversiones.length > 0 && (
                              <span className="truncate">· {conversiones.join(' · ')}</span>
                            )}
                          </span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </PanelCard>
        </div>

        <div className="mt-4">
          <PanelCard
            title="Convertir en lote"
            subtitle="Convierte de una vez todos los ficheros del sistema que admitan el mismo destino"
            icon={<Layers className="size-4" />}
          >
            {!system ? (
              <EmptyState
                title="Ningún sistema elegido"
                description="Elige un sistema arriba para convertir sus ROMs de una sola vez."
              />
            ) : files.loading && !files.data ? (
              <EmptyState title="Leyendo los ficheros…" description="Un momento." />
            ) : !destinos.length ? (
              <EmptyState
                title="Nada que convertir"
                description="Ningún fichero de este sistema admite una conversión."
              />
            ) : (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  <select
                    value={destinoActual?.id ?? ''}
                    onChange={(event) => setDestino(event.target.value)}
                    aria-label="Destino de la conversión"
                    className="h-10 w-full max-w-xs cursor-pointer rounded-xl border border-border bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    {destinos.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label} · {item.count} ficheros
                      </option>
                    ))}
                  </select>

                  <select
                    value={origen}
                    onChange={(event) => setOrigen(event.target.value)}
                    aria-label="Formato de origen"
                    className="h-10 w-full max-w-xs cursor-pointer rounded-xl border border-border bg-card px-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    <option value="">Todos los formatos</option>
                    {formatos.map((item) => (
                      <option key={item.kind} value={item.kind}>
                        {item.label} · {item.count} ficheros
                      </option>
                    ))}
                  </select>
                </div>

                <p className="text-xs text-muted-foreground">
                  Se convertirán {candidatos.length} ficheros a {destinoActual?.label}
                  {origen ? ' (un solo formato de origen)' : ''}. El original no se borra.
                </p>

                <Button
                  variant="primary"
                  size="sm"
                  disabled={busy || !candidatos.length}
                  onClick={() => setConfirmarLote(true)}
                >
                  <Wand2 className="size-4" />
                  Convertir todo
                </Button>

                {lote && (
                  <div className="rounded-xl border border-border bg-muted/40 px-3 py-2.5">
                    <p className="text-sm font-medium text-foreground">
                      {lote.resumen?.hechos ?? 0} convertidos · {lote.resumen?.fallos ?? 0} fallidos
                      · {lote.resumen?.total ?? 0} intentados
                    </p>
                    {fallos.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {fallos.map((item, index) => (
                          <li
                            key={`${item.file}-${index}`}
                            className="text-[11px] leading-relaxed text-destructive"
                          >
                            {item.file}: {item.error ?? 'Error desconocido.'}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            )}
          </PanelCard>
        </div>
      </PageContainer>

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.name ?? ''}
        description={
          selected
            ? `Formato detectado: ${sinReconocer(selected) ? 'no reconocido' : selected.label}`
            : undefined
        }
        footer={
          <Button variant="ghost" onClick={() => setSelected(null)}>
            Cerrar
          </Button>
        }
      >
        {selected && system && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <span className="rounded-md border border-border px-1.5 py-0.5 font-medium text-foreground">
                {sinReconocer(selected) ? 'Formato no reconocido' : selected.label}
              </span>
              <span>{humanSize(selected.size)}</span>
              {selected.plataforma && <span>{selected.plataforma}</span>}
            </div>

            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Conversiones disponibles
              </p>
              {(selected.acciones ?? []).length === 0 ? (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Este fichero no se puede convertir: el formato detectado ({selected.kind}) no
                  admite ninguna conversión.
                </p>
              ) : (
                <div className="space-y-2">
                  {(selected.acciones ?? []).map((accion) => (
                    <div
                      key={accion.id}
                      className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-muted/40 px-3 py-2"
                    >
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={busy}
                        onClick={() => convertir(accion)}
                      >
                        <Wand2 className="size-4" />
                        Convertir a {accion.label}
                      </Button>
                      {accion.nota && (
                        <span className="text-[11px] text-muted-foreground">{accion.nota}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {parches.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Parches IPS en la carpeta
                </p>
                <div className="flex flex-wrap gap-2">
                  {parches.map((patch) => (
                    <Button
                      key={patch.name}
                      variant="outline"
                      size="sm"
                      disabled={busy}
                      onClick={() => parchear(patch)}
                    >
                      <FileCog className="size-4" />
                      {patch.name}
                    </Button>
                  ))}
                </div>
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Al aplicar un parche se guarda una copia del original (.bak) para poder deshacerlo.
                </p>
              </div>
            )}

            <p className="text-[11px] text-muted-foreground">
              Convertir no borra el original: el resultado se deja al lado con otro nombre.
            </p>
          </div>
        )}
      </Modal>

      <Modal
        open={confirmarLote}
        onClose={() => setConfirmarLote(false)}
        title={`Convertir todo a ${destinoActual?.label ?? ''}`}
        description={`Se escribirán ${candidatos.length} ficheros nuevos en la SD. El original no se borra.`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmarLote(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              disabled={busy || !candidatos.length}
              onClick={convertirLote}
            >
              {busy ? 'Convirtiendo…' : `Sí, convertir ${candidatos.length}`}
            </Button>
          </>
        }
      >
        <ul className="max-h-64 space-y-1 overflow-y-auto text-xs text-muted-foreground">
          {candidatos.slice(0, 50).map((file) => (
            <li key={file.name} className="truncate">
              {file.name}
            </li>
          ))}
        </ul>
        {candidatos.length > 50 && (
          <p className="mt-2 text-[11px] text-muted-foreground">
            … y {candidatos.length - 50} ficheros más.
          </p>
        )}
      </Modal>
    </>
  )
}
