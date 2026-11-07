import {
  CircleAlert,
  FileArchive,
  FileCode2,
  FileCog,
  HardDrive,
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
import type { ToolsRomFile } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Conversiones que el backend sabe hacer, con su etiqueta. */
const CONVERSIONES: { target: string; label: string; hint: string }[] = [
  { target: 'iso', label: 'ISO', hint: 'imagen de 2048 bytes por sector' },
  { target: 'bin-cue', label: 'BIN + CUE', hint: 'imagen original de 2352 bytes' },
  { target: 'pbp', label: 'PBP', hint: 'formato de PlayStation' },
]

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

export function ToolsFormatsPage() {
  const { openMenu } = useShell()
  const { showNotify } = useNotify()

  const systems = useApi(() => api.romSystems(), [])
  const [system, setSystem] = useState('')
  const [selected, setSelected] = useState<ToolsRomFile | null>(null)
  const [busy, setBusy] = useState(false)

  const files = useApi(() => api.toolsRoms(system), [system], { enabled: !!system })

  /** Los sistemas que tienen ROMs y ademas tienen DAT o formato que ver. */
  const conRom = useMemo(
    () => (systems.data ?? []).filter((item) => (item.rom_count ?? 0) > 0),
    [systems.data],
  )

  const parches = useMemo(
    () => (files.data?.files ?? []).filter((file) => file.name.toLowerCase().endsWith('.ips')),
    [files.data],
  )

  const run = async (label: string, action: () => Promise<{ ok: boolean; error?: string }>) => {
    setBusy(true)
    try {
      const result = await action()
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok ? label : 'No se pudo completar',
        message: result.ok ? 'Hecho.' : result.error ?? 'Error desconocido.',
      })
      if (result.ok) {
        setSelected(null)
        files.refresh()
      }
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo completar',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

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
            onChange={(event) => setSystem(event.target.value)}
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
                ? `${files.data?.files.length ?? 0} ficheros con formato reconocido`
                : 'Elige un sistema para ver sus ficheros'
            }
            icon={<FileCog className="size-4" />}
          >
            {!system ? (
              <EmptyState
                title="Ningun sistema elegido"
                description="Arriba puedes elegir de que sistema quieres mirar las ROMs."
              />
            ) : !files.data?.files.length ? (
              <EmptyState
                title="No hay ficheros"
                description={`La carpeta de ${system} esta vacia.`}
              />
            ) : (
              <ul className="divide-y divide-border">
                {files.data.files.map((file) => (
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
                        <span className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                          <span className="rounded-md border border-border px-1.5 py-0.5 font-medium">
                            {file.label}
                          </span>
                          <span>{humanSize(file.size)}</span>
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </PanelCard>
        </div>
      </PageContainer>

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.name ?? ''}
        description={selected ? `Formato detectado: ${selected.label}` : undefined}
        footer={
          <Button variant="ghost" onClick={() => setSelected(null)}>
            Cerrar
          </Button>
        }
      >
        {selected && system && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {CONVERSIONES.filter((conversion) =>
                selected.actions.some((action) => action.toLowerCase().includes(conversion.target)),
              ).map((conversion) => (
                <Button
                  key={conversion.target}
                  variant="primary"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    run(`Convertido a ${conversion.label}`, () =>
                      api.toolsConvert({ system, file: selected.name, target: conversion.target }),
                    )
                  }
                >
                  <Wand2 className="size-4" />
                  Convertir a {conversion.label}
                </Button>
              ))}

              {selected.actions.some((action) => action.toLowerCase().includes('comprimir')) && (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    run('Fichero comprimido', () =>
                      api.toolsCompress({ system, file: selected.name }),
                    )
                  }
                >
                  <FileArchive className="size-4" />
                  Comprimir en ZIP
                </Button>
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
                      onClick={() =>
                        run('Parche aplicado', () =>
                          api.toolsPatch({ system, file: selected.name, patch: patch.name }),
                        )
                      }
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
    </>
  )
}
