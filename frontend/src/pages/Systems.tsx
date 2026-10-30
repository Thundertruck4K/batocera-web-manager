import { AnimatePresence, motion } from 'motion/react'
import {
  FileCode,
  Gamepad2,
  Pencil,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { Topbar } from '@/components/layout/Topbar'
import { Button, IconButton } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Field'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { useApi } from '@/hooks/useApi'
import { useToast } from '@/hooks/useToast'
import { triggerHaptic } from '@/hooks/useWebHaptics'
import { api } from '@/lib/api'
import type { CustomSystem } from '@/lib/types'

const EASE = [0.16, 1, 0.3, 1] as const

export function Systems() {
  const { openMenu } = useShell()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const systems = useApi(() => api.systems(), [])
  const [query, setQuery] = useState('')
  const [pendingDelete, setPendingDelete] = useState<CustomSystem | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [xmlOf, setXmlOf] = useState<{ name: string; xml: string } | null>(null)

  const filtered = useMemo(() => {
    const list = systems.data ?? []
    const q = query.trim().toLowerCase()
    if (!q) return list
    return list.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.fullname.toLowerCase().includes(q) ||
        s.path.toLowerCase().includes(q),
    )
  }, [systems.data, query])

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    triggerHaptic('medium')
    try {
      await api.deleteSystem(pendingDelete.name)
      showToast(`Sistema «${pendingDelete.name}» eliminado.`, 'success')
      setPendingDelete(null)
      systems.refresh()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'No se pudo eliminar.', 'error')
    } finally {
      setDeleting(false)
    }
  }

  const showXml = async (system: CustomSystem) => {
    triggerHaptic('light')
    try {
      const res = await api.systemXml(system.name)
      if (res.ok) {
        setXmlOf({ name: system.name, xml: res.xml })
      } else {
        showToast('No se pudo leer el XML.', 'error')
      }
    } catch {
      showToast('No se pudo leer el XML.', 'error')
    }
  }

  return (
    <>
      <Topbar
        title="Sistemas"
        subtitle={`${filtered.length} sistema(s) definido(s) en EmulationStation`}
        onMenu={openMenu}
        actions={
          <Button size="sm" variant="primary" onClick={() => navigate('/sistemas/nuevo')}>
            <Plus className="size-3.5" />
            Añadir
          </Button>
        }
      />

      <PageContainer>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-xs">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nombre, slug o ruta…"
              className="pl-9"
              aria-label="Buscar sistemas"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Los sistemas se guardan como <code className="font-mono">es_systems_&lt;slug&gt;.cfg</code>
          </p>
        </div>

        {systems.loading && !systems.data ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : systems.error ? (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive">
            {systems.error}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Gamepad2 className="size-5" />}
            title={query ? 'Ningún sistema coincide' : 'Todavía no hay sistemas definidos'}
            description={
              query
                ? 'Prueba con otro texto de búsqueda.'
                : 'Crea el primer sistema a partir del catálogo de referencia de Batocera.'
            }
            action={
              !query && (
                <Button variant="primary" onClick={() => navigate('/sistemas/nuevo')}>
                  <Plus className="size-4" />
                  Añadir sistema
                </Button>
              )
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2 xl:grid-cols-3 xl:gap-x-6">
            <AnimatePresence initial={false}>
              {filtered.map((system, index) => (
                <motion.article
                  key={`${system.filename}-${system.name}`}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{
                    duration: 0.25,
                    ease: EASE,
                    delay: Math.min(index * 0.015, 0.05),
                  }}
                  className="card card-hover group flex flex-col overflow-hidden"
                >
                  <div className="flex items-start justify-between gap-3 px-5 pt-4">
                    <div className="min-w-0">
                      <h3 className="truncate text-[15px] font-semibold tracking-[-0.015em] text-foreground">
                        {system.fullname || system.name}
                      </h3>
                      <p className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
                        {system.name}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5 opacity-0 transition-opacity duration-200 group-hover:opacity-100 focus-within:opacity-100">
                      <IconButton label="Ver XML" onClick={() => showXml(system)}>
                        <FileCode className="size-3.5" />
                      </IconButton>
                      <IconButton
                        label="Editar"
                        onClick={() => navigate(`/sistemas/${encodeURIComponent(system.name)}/editar`)}
                      >
                        <Pencil className="size-3.5" />
                      </IconButton>
                      <IconButton
                        label="Eliminar"
                        onClick={() => {
                          triggerHaptic('warning')
                          setPendingDelete(system)
                        }}
                      >
                        <Trash2 className="size-3.5" />
                      </IconButton>
                    </div>
                  </div>

                  <div className="flex-1 px-5 py-3">
                    <dl className="space-y-1.5">
                      <div className="flex items-baseline justify-between gap-3">
                        <dt className="text-xs text-muted-foreground">Ruta</dt>
                        <dd className="min-w-0 truncate font-mono text-[11px] text-foreground">
                          {system.path}
                        </dd>
                      </div>
                      <div className="flex items-baseline justify-between gap-3">
                        <dt className="text-xs text-muted-foreground">Tema</dt>
                        <dd className="min-w-0 truncate text-[11px] text-foreground">
                          {system.theme || '—'}
                        </dd>
                      </div>
                      <div className="flex items-baseline justify-between gap-3">
                        <dt className="text-xs text-muted-foreground">Hardware</dt>
                        <dd className="min-w-0 truncate text-[11px] text-foreground">
                          {system.hardware || '—'}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  <footer className="flex items-center justify-between gap-2 border-t border-border px-5 py-2.5">
                    <span className="truncate font-mono text-[10px] text-muted-foreground">
                      {system.filename}
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate(`/sistemas/${encodeURIComponent(system.name)}/editar`)}
                    >
                      Editar
                    </Button>
                  </footer>
                </motion.article>
              ))}
            </AnimatePresence>
          </div>
        )}
      </PageContainer>

      <Modal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title="Eliminar sistema"
        description={
          pendingDelete
            ? `Se eliminará «${pendingDelete.fullname || pendingDelete.name}» de ${pendingDelete.filename}. Si el fichero contiene otros sistemas, sólo se quitará este.`
            : undefined
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Eliminando…' : 'Eliminar'}
            </Button>
          </>
        }
      />

      <Modal
        open={xmlOf !== null}
        onClose={() => setXmlOf(null)}
        title={xmlOf ? `${xmlOf.name}.cfg` : ''}
        description="Contenido del fichero de configuración que genera el manager."
        className="max-w-3xl"
      >
        <pre className="max-h-[60vh] overflow-auto rounded-2xl border border-border bg-stage p-4 font-mono text-[11px] leading-relaxed text-foreground">
          {xmlOf?.xml}
        </pre>
      </Modal>
    </>
  )
}
