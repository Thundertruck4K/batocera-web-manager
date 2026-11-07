import {
  CircleAlert,
  Database,
  FileSignature,
  History,
  RefreshCw,
  Undo2,
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
import type { ToolsRenameItem } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Como se explica cada tipo de coincidencia. */
const METODOS: Record<string, string> = {
  hash: 'hash exacto del DAT',
  nombre: 'nombre idéntico al del DAT',
  serial: 'serial del disco',
  titulo: 'título parecido',
}

function etiquetaAccion(item: ToolsRenameItem): { texto: string; clase: string } {
  switch (item.action) {
    case 'renombrar':
      return { texto: 'Renombrar', clase: 'text-emerald-600 dark:text-emerald-400' }
    case 'revisar':
      return { texto: 'Revisar', clase: 'text-amber-600 dark:text-amber-400' }
    case 'igual':
      return { texto: 'Ya está bien', clase: 'text-muted-foreground' }
    default:
      return { texto: 'Sin DAT', clase: 'text-muted-foreground' }
  }
}

export function ToolsRenamePage() {
  const { openMenu } = useShell()
  const { showNotify } = useNotify()

  const systems = useApi(() => api.romSystems(), [])
  const dats = useApi(() => api.toolsDats(), [])
  const [system, setSystem] = useState('')
  const [plan, setPlan] = useState<Awaited<ReturnType<typeof api.toolsRenamePlan>> | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmar, setConfirmar] = useState(false)

  const conRom = useMemo(
    () => (systems.data ?? []).filter((item) => (item.rom_count ?? 0) > 0),
    [systems.data],
  )

  const datDelSistema = useMemo(
    () => (dats.data?.sistemas ?? []).find((item) => item.system === system) ?? null,
    [dats.data, system],
  )

  /**
   * Si el backend no ha resuelto un DAT para este sistema no hay plan que
   * calcular: se avisa y se bloquea el botón.
   */
  const sinDat =
    !!system && !!dats.data && (!datDelSistema || datDelSistema.resuelto === 'ninguno')

  const calcular = async () => {
    if (!system) return
    setBusy(true)
    try {
      const result = await api.toolsRenamePlan(system)
      setPlan(result)
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo calcular el plan',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

  const instalarDat = async () => {
    if (!system) return
    setBusy(true)
    try {
      const result = await api.toolsInstallDats([system])
      const item = result.results[0]
      showNotify({
        variant: item?.ok ? 'success' : 'error',
        title: item?.ok ? 'DAT descargado' : 'No se pudo descargar el DAT',
        message: item?.ok
          ? `${item.system}: listo para renombrar.`
          : item?.error ?? 'Error desconocido.',
      })
      dats.refresh()
    } finally {
      setBusy(false)
    }
  }

  const aplicar = async (includeReview: boolean) => {
    if (!system) return
    setBusy(true)
    try {
      const result = await api.toolsRenameApply({ system, include_review: includeReview })
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok ? `${result.renamed ?? 0} ficheros renombrados` : 'Renombrado con problemas',
        message: result.ok
          ? 'Se puede deshacer desde el botón de deshacer.'
          : (result.errores?.[0]?.error ?? 'Error desconocido.'),
      })
      setConfirmar(false)
      setPlan(null)
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo renombrar',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      setBusy(false)
    }
  }

  const deshacer = async () => {
    setBusy(true)
    try {
      const result = await api.toolsRenameUndo()
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok ? 'Renombrado deshecho' : 'No se pudo deshacer',
        message: result.ok ? 'Los nombres anteriores han vuelto.' : result.error ?? '',
      })
      setPlan(null)
    } finally {
      setBusy(false)
    }
  }

  const cambios = plan?.items.filter((item) => item.action === 'renombrar') ?? []
  const revisables = plan?.items.filter((item) => item.action === 'revisar') ?? []

  return (
    <>
      <Topbar
        title="Renombrado"
        subtitle="Poner las ROMs con el nombre que les da el DAT"
        onMenu={openMenu}
        actions={
          <IconButton label="Volver a calcular el plan" onClick={calcular} disabled={!system || sinDat}>
            <RefreshCw className={cn('size-4', busy && 'animate-spin')} />
          </IconButton>
        }
      />

      <PageContainer>
        {(systems.error || dats.error) && (
          <div className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">{systems.error ?? dats.error}</span>
            <Button size="sm" variant="outline" onClick={() => { systems.refresh(); dats.refresh() }}>
              Reintentar
            </Button>
          </div>
        )}

        <PanelCard
          title="Elige un sistema"
          subtitle="El DAT es la lista de juegos con sus nombres y sus hashes"
          icon={<Database className="size-4" />}
        >
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={system}
              onChange={(event) => {
                setSystem(event.target.value)
                setPlan(null)
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

            {system && dats.data ? (
              sinDat ? (
                <span className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-700 dark:text-amber-400">
                  Este sistema no tiene DAT disponible
                </span>
              ) : datDelSistema?.instalado ? (
                <span
                  title={datDelSistema?.dat ?? undefined}
                  className="rounded-xl border border-border bg-muted/60 px-3 py-2 text-xs font-medium text-muted-foreground"
                >
                  {datDelSistema?.resuelto === 'nombre'
                    ? `DAT por nombre · ${datDelSistema?.dat} (confianza ${Math.round((datDelSistema?.confianza ?? 0) * 100)} %)`
                    : `DAT listo · ${(datDelSistema?.juegos ?? 0).toLocaleString('es-ES')} juegos`}
                </span>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!system || busy}
                  onClick={instalarDat}
                >
                  <Database className="size-4" />
                  Descargar el DAT
                </Button>
              )
            ) : null}
          </div>
        </PanelCard>

        <div className="mt-4">
          <PanelCard
            title="Plan de renombrado"
            subtitle={
              plan
                ? `${plan.stats.total} ficheros · ${plan.stats.renombrar} para renombrar · ${plan.stats.revisar} para revisar`
                : sinDat
                  ? 'Este sistema no tiene DAT disponible: no se puede calcular el plan'
                  : 'Primero elige el sistema y calcula el plan: no se toca nada hasta que lo apliques'
            }
            icon={<FileSignature className="size-4" />}
            actions={
              <>
                {plan && (
                  <Button size="sm" variant="ghost" onClick={deshacer} disabled={busy}>
                    <Undo2 className="size-4" />
                    Deshacer
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="primary"
                  onClick={calcular}
                  disabled={!system || busy || sinDat}
                >
                  <History className="size-4" />
                  Calcular el plan
                </Button>
              </>
            }
          >
            {sinDat ? (
              <EmptyState
                icon={<FileSignature className="size-5" />}
                title="Este sistema no tiene DAT disponible"
                description="El manager no ha encontrado ningún DAT para este sistema, así que no hay plan de renombrado que calcular."
              />
            ) : !plan ? (
              <EmptyState
                icon={<FileSignature className="size-5" />}
                title="Todavía no hay plan"
                description="El plan se calcula en memoria: son los nombres que tendría cada ROM según su DAT."
              />
            ) : plan.items.length === 0 ? (
              <EmptyState
                title="No hay ficheros que renombrar"
                description={`La carpeta de ${plan.system} está vacía.`}
              />
            ) : (
              <ul className="divide-y divide-border">
                {plan.items.map((item) => {
                  const etiqueta = etiquetaAccion(item)
                  return (
                    <li key={item.path} className="py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={cn('text-[11px] font-semibold uppercase tracking-wide', etiqueta.clase)}>
                          {etiqueta.texto}
                        </span>
                        {item.method && (
                          <span className="rounded-md border border-border px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                            {METODOS[item.method] ?? item.method}
                            {item.confidence > 0 && ` · ${Math.round(item.confidence * 100)}%`}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 truncate text-sm text-muted-foreground">{item.current}</p>
                      {item.action === 'renombrar' && (
                        <p className="mt-0.5 truncate text-sm font-medium text-foreground">
                          {item.proposed}
                        </p>
                      )}
                      {item.reason && (
                        <p className="mt-0.5 text-[11px] text-muted-foreground/80">{item.reason}</p>
                      )}
                      {item.companions.length > 0 && (
                        <p className="mt-0.5 text-[11px] text-muted-foreground/80">
                          Se renombran tambien: {item.companions.join(', ')}
                        </p>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}

            {plan && plan.stats.sin_dat > 0 && (
              <p className="mt-3 flex items-start gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs leading-relaxed text-amber-700 dark:text-amber-400">
                <CircleAlert className="size-4 shrink-0" />
                <span>
                  {plan.stats.sin_dat} ficheros se quedan sin renombrar: no aparecen en el DAT.
                </span>
              </p>
            )}
          </PanelCard>
        </div>
      </PageContainer>

      <Modal
        open={confirmar}
        onClose={() => setConfirmar(false)}
        title="Aplicar el renombrado"
        description="Se renombran los ficheros y sus acompañantes (CUE, M3U…). Nada se borra."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmar(false)}>
              Cancelar
            </Button>
            {revisables.length > 0 && (
              <Button variant="outline" disabled={busy} onClick={() => aplicar(true)}>
                Renombrar {cambios.length + revisables.length}
              </Button>
            )}
            <Button variant="primary" disabled={busy || cambios.length === 0} onClick={() => aplicar(false)}>
              Renombrar {cambios.length}
            </Button>
          </>
        }
      >
        <ul className="max-h-64 space-y-2 overflow-y-auto text-xs">
          {cambios.map((item) => (
            <li key={item.path} className="rounded-xl border border-border bg-muted/40 px-3 py-2">
              <p className="truncate text-muted-foreground">{item.current}</p>
              <p className="truncate font-medium text-foreground">{item.proposed}</p>
            </li>
          ))}
        </ul>
      </Modal>
    </>
  )
}
