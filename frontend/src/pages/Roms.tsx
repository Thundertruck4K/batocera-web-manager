import {
  CircleAlert,
  Copy,
  FileWarning,
  HardDrive,
  Images,
  ListChecks,
  RefreshCw,
  Trash2,
  Undo2,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { PageContainer, useShell } from '@/components/layout/AppShell'
import { SectionTabs, type SectionTab } from '@/components/layout/SectionTabs'
import { Topbar } from '@/components/layout/Topbar'
import { Button, IconButton } from '@/components/ui/Button'
import { PanelCard } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Progress } from '@/components/ui/Progress'
import { useApi } from '@/hooks/useApi'
import { useNotify } from '@/hooks/useNotify'
import { api } from '@/lib/api'
import type { LibraryAudit, LibraryDuplicado, LibraryJob } from '@/lib/types'
import { cn } from '@/lib/utils'

/** La clave con la que se identifica un fichero en la interfaz. */
const clave = (sistema: string, ruta: string) => `${sistema}/${ruta}`

/** Los megabytes, en texto corto. */
function mb(bytes: number): string {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${bytes} B`
}

interface RomsPageProps {
  tab: SectionTab
  onTab: (tab: SectionTab) => void
}

/**
 * La pestaña de ROMs: la biblioteca vista como conjunto.
 *
 * Antes, la sección «ROMs y BIOS» solo tenía BIOS: no había ninguna forma
 * de ver lo que ocupa la biblioteca, buscar duplicados ni enterarse de las
 * fichas rotas. Aquí está todo eso, y siempre como **trabajo en segundo
 * plano**: en una biblioteca de 1,8 TB la radiografía tarda, así que se ve
 * el progreso en vez de una página en silencio.
 *
 * Nada se borra: lo que sobra se mueve a una cuarentena y se puede deshacer.
 */
export function RomsPage({ tab, onTab }: RomsPageProps) {
  const { openMenu } = useShell()
  const { showNotify } = useNotify()
  const resumen = useApi(() => api.librarySummary(), [])

  const [auditoria, setAuditoria] = useState<LibraryAudit | null>(null)
  const [trabajo, setTrabajo] = useState<LibraryJob | null>(null)
  const [busy, setBusy] = useState(false)
  /** Los ficheros que el usuario ha marcado para mover a la cuarentena. */
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set())
  /** Para no tocar el estado si el usuario se ha ido de la pagina. */
  const montado = useRef(true)
  useEffect(() => () => { montado.current = false }, [])

  /* ── La auditoría ─────────────────────────────────────────────────── */

  /**
   * Espera a que termine el trabajo, preguntando cada poco por su estado.
   * El backend lo calcula en un hilo aparte: asi se ve el progreso.
   */
  const esperarJob = async (id: string): Promise<LibraryAudit | null> => {
    for (;;) {
      await new Promise((resolve) => setTimeout(resolve, 400))
      const estado = await api.libraryJob(id)
      if (!montado.current) return null
      setTrabajo(estado)
      if (estado.estado === 'listo') return (estado.resultado as LibraryAudit) ?? null
      if (estado.estado === 'error') {
        throw new Error(estado.error || 'La auditoría ha fallado')
      }
    }
  }

  const auditar = async () => {
    setBusy(true)
    setTrabajo(null)
    setSeleccion(new Set())
    try {
      const { job } = await api.libraryAuditStart()
      const resultado = await esperarJob(job)
      if (!resultado) return
      setAuditoria(resultado)
      showNotify({
        variant: 'success',
        title: 'Biblioteca auditada',
        message: `${resultado.resumen.juegos} juegos revisados.`,
      })
    } catch (error) {
      showNotify({
        variant: 'error',
        title: 'No se pudo auditar la biblioteca',
        message: error instanceof Error ? error.message : 'Error inesperado.',
      })
    } finally {
      if (montado.current) {
        setBusy(false)
        setTrabajo(null)
      }
    }
  }

  /* ── Las acciones ─────────────────────────────────────────────────── */

  const marcar = (id: string) => {
    setSeleccion((antes) => {
      const nuevo = new Set(antes)
      if (nuevo.has(id)) nuevo.delete(id)
      else nuevo.add(id)
      return nuevo
    })
  }

  const moverSeleccion = async () => {
    const ficheros = [...seleccion]
    if (!ficheros.length) return
    setBusy(true)
    try {
      const result = await api.libraryQuarantine(ficheros)
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok
          ? `${result.movidos.length} ficheros a la cuarentena`
          : 'Some files could not be moved',
        message: result.ok
          ? 'Se pueden recuperar con «Deshacer».'
          : (result.errores?.[0]?.error ?? 'Error desconocido.'),
      })
      setSeleccion(new Set())
      await auditar()
    } finally {
      setBusy(false)
    }
  }

  const limpiarGamelist = async (sistema: string) => {
    setBusy(true)
    try {
      const result = await api.libraryGamelistClean(sistema)
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok
          ? `${result.quitadas} fichas quitadas del gamelist`
          : 'No se pudo limpiar el gamelist',
        message: result.ok
          ? `Se puede deshacer con «Deshacer».`
          : (result.error ?? 'Error desconocido.'),
      })
      if (result.ok) await auditar()
    } finally {
      setBusy(false)
    }
  }

  const deshacer = async () => {
    setBusy(true)
    try {
      const result = await api.libraryUndo()
      showNotify({
        variant: result.ok ? 'success' : 'error',
        title: result.ok ? 'Tanda deshecha' : 'No se pudo deshacer',
        message: result.ok
          ? `${result.restaurados.length} ficheros han vuelto a su sitio.`
          : (result.error ?? 'Error desconocido.'),
      })
      await auditar()
    } finally {
      setBusy(false)
    }
  }

  /* ── Los datos ────────────────────────────────────────────────────── */

  const datos = resumen.data
  const trabajando = trabajo?.estado === 'trabajando'
  const duplicados = auditoria?.duplicados ?? []
  const sinConfirmar = duplicados.filter((d) => !d.confirmado).length
  const ahorroTotal = duplicados.reduce((suma, d) => suma + d.ahorro, 0)
  const fichasPorSistema = useMemo(() => {
    const mapa = new Map<string, number>()
    for (const ficha of auditoria?.fichas_sin_fichero.lista ?? []) {
      mapa.set(ficha.sistema, (mapa.get(ficha.sistema) ?? 0) + 1)
    }
    return [...mapa.entries()].sort((a, b) => b[1] - a[1])
  }, [auditoria])

  const haySeleccion = seleccion.size > 0

  return (
    <>
      <Topbar
        title="ROMs y BIOS"
        subtitle={
          datos
            ? `${datos.juegos.toLocaleString('es-ES')} juegos · ${datos.gb.toLocaleString('es-ES')} GB en ${datos.sistemas.length} sistemas`
            : 'La biblioteca de la consola'
        }
        onMenu={openMenu}
        actions={
          <IconButton label="Volver a auditar la biblioteca" onClick={auditar} disabled={busy}>
            <RefreshCw className={cn('size-4', trabajando && 'animate-spin')} />
          </IconButton>
        }
      />

      <PageContainer>
        <SectionTabs value={tab} onChange={onTab} />

        {resumen.error && (
          <div className="mb-4 flex items-center gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <CircleAlert className="size-4 shrink-0" />
            <span className="min-w-0 flex-1">{resumen.error}</span>
            <Button size="sm" variant="outline" onClick={resumen.refresh}>
              Reintentar
            </Button>
          </div>
        )}

        {/* Resumen */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <MetricCard label="Sistemas" value={datos?.sistemas.length ?? 0} icon={HardDrive} />
          <MetricCard
            label="Juegos"
            value={(datos?.juegos ?? 0).toLocaleString('es-ES')}
            icon={ListChecks}
          />
          <MetricCard
            label="Espacio"
            value={`${(datos?.gb ?? 0).toLocaleString('es-ES')} GB`}
            icon={Copy}
            hint="lo que ocupa la biblioteca"
          />
          <MetricCard
            label="Duplicados"
            value={duplicados.length}
            icon={Copy}
            accent={duplicados.length ? 'bad' : 'good'}
            hint={duplicados.length ? `puedes liberar ${mb(ahorroTotal)}` : 'nada repetido'}
          />
        </div>

        {/* La auditoría */}
        <div className="mt-4">
          <PanelCard
            title="Auditoría de la biblioteca"
            subtitle={
              auditoria
                ? `${auditoria.resumen.juegos.toLocaleString('es-ES')} juegos en ${auditoria.resumen.sistemas} sistemas`
                : 'Busca duplicados, fichas rotas, ficheros vacíos y media sin juego'
            }
            icon={<ListChecks className="size-4" />}
            actions={
              <>
                {haySeleccion && (
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={busy}
                    onClick={moverSeleccion}
                  >
                    <Trash2 className="size-4" />
                    Mover {seleccion.size} a la cuarentena
                  </Button>
                )}
                <Button
                  size="sm"
                  variant={auditoria ? 'outline' : 'primary'}
                  disabled={busy}
                  onClick={auditar}
                >
                  <RefreshCw className={cn('size-4', trabajando && 'animate-spin')} />
                  Auditar
                </Button>
              </>
            }
          >
            {trabajando && trabajo ? (
              <div className="rounded-2xl border border-border bg-muted/40 px-4 py-4">
                <Progress
                  value={trabajo.porcentaje}
                  label={
                    trabajo.total
                      ? `${trabajo.mensaje || 'Trabajando'} · ${trabajo.hechos} de ${trabajo.total}`
                      : (trabajo.mensaje || 'Trabajando')
                  }
                />
                {trabajo.actual && (
                  <p className="mt-2 truncate text-[11px] text-muted-foreground">
                    Ahora: {trabajo.actual}
                  </p>
                )}
                <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground/80">
                  En bibliotecas grandes esto tarda: el trabajo sigue en el servidor, asi que
                  no hace falta cerrar la ventana. Puedes esperar aqui hasta que termine.
                </p>
              </div>
            ) : !auditoria ? (
              <EmptyState
                icon={<ListChecks className="size-5" />}
                title="Todavia no hay auditoria"
                description="La radiografia recorre la biblioteca entera: en 1,8 TB tarda menos de un minuto, y no se toca nada."
                action={
                  <Button variant="primary" onClick={auditar} disabled={busy}>
                    <RefreshCw className="size-4" />
                    Auditar la biblioteca
                  </Button>
                }
              />
            ) : (
              <div className="space-y-4">
                {/* Duplicados */}
                <DuplicadosPanel
                  duplicados={duplicados}
                  sinConfirmar={sinConfirmar}
                  seleccion={seleccion}
                  marcar={marcar}
                />

                {/* Fichas rotas */}
                <PanelCard
                  title="Fichas sin fichero"
                  subtitle={
                    auditoria.fichas_sin_fichero.total
                      ? `${auditoria.fichas_sin_fichero.total} entradas del gamelist.xml apuntan a un juego que no existe`
                      : 'Todas las fichas del gamelist.xml tienen su fichero'
                  }
                  icon={<FileWarning className="size-4" />}
                >
                  {fichasPorSistema.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      El gamelist.xml esta al dia: no hay entradas rotas.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {fichasPorSistema.map(([sistema, cantidad]) => (
                        <li key={sistema} className="flex items-center gap-3 py-2.5">
                          <span className="min-w-0 flex-1 truncate text-sm font-medium">
                            {sistema}
                          </span>
                          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                            {cantidad} fichas
                          </span>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() => limpiarGamelist(sistema)}
                          >
                            Limpiar
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </PanelCard>

                {/* Ficheros vacíos, sobras y media huérfana */}
                <SencillosPanel
                  titulo="Ficheros vacios"
                  texto="Juegos de 0 bytes: no arrancan, pero ocupan su sitio en la biblioteca."
                  vacios={auditoria.ficheros_vacios}
                  seleccion={seleccion}
                  marcar={marcar}
                />
                <SencillosPanel
                  titulo="Ficheros que no son juegos"
                  texto="Notas, listas y demas: no los usa ningun emulador."
                  vacios={auditoria.sobras}
                  seleccion={seleccion}
                  marcar={marcar}
                />
                <PanelCard
                  title="Media sin juego"
                  subtitle={
                    auditoria.media_huerfana.total
                      ? `${auditoria.media_huerfana.total} imagenes o videos cuyo juego ya no esta`
                      : 'Todas las imagenes tienen su juego'
                  }
                  icon={<Images className="size-4" />}
                >
                  {auditoria.media_huerfana.lista.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      Toda la media corresponde a un juego de la biblioteca.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border">
                      {auditoria.media_huerfana.lista.slice(0, 200).map((item) => {
                        const id = clave(item.sistema, item.fichero)
                        return (
                          <li key={id} className="flex items-center gap-3 py-2">
                            <input
                              type="checkbox"
                              checked={seleccion.has(id)}
                              onChange={() => marcar(id)}
                              className="size-4 shrink-0 cursor-pointer accent-primary"
                              aria-label={`Marcar ${item.fichero}`}
                            />
                            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                              {item.sistema}/{item.fichero}
                            </span>
                            <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                              {mb(item.bytes)}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </PanelCard>

                {/* Repetidos entre sistemas */}
                {auditoria.repetidos_entre_sistemas.length > 0 && (
                  <PanelCard
                    title="El mismo juego en varios sistemas"
                    subtitle="Los arcades guardan las mismas ROMs en carpetas distintas (naomi, atomiswave...)"
                    icon={<Copy className="size-4" />}
                  >
                    <ul className="divide-y divide-border">
                      {auditoria.repetidos_entre_sistemas.slice(0, 100).map((item) => (
                        <li key={item.nombre} className="py-2.5">
                          <p className="truncate text-sm font-medium">{item.nombre}</p>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {item.sistemas.join(' · ')} · {mb(item.bytes)} en total
                          </p>
                        </li>
                      ))}
                    </ul>
                  </PanelCard>
                )}

                {/* Deshacer */}
                <div className="flex justify-end">
                  <Button variant="outline" size="sm" disabled={busy} onClick={deshacer}>
                    <Undo2 className="size-4" />
                    Deshacer la ultima tanda
                  </Button>
                </div>
              </div>
            )}
          </PanelCard>
        </div>

        {/* El espacio por sistema */}
        {auditoria && auditoria.espacio.length > 0 && (
          <div className="mt-4">
            <PanelCard
              title="El espacio por sistema"
              subtitle="Donde se lleva la memoria de la tarjeta"
              icon={<HardDrive className="size-4" />}
            >
              <ul className="space-y-2">
                {auditoria.espacio.slice(0, 20).map((item) => {
                  const maximo = auditoria.espacio[0]?.bytes || 1
                  const porcentaje = Math.round((item.bytes / maximo) * 100)
                  return (
                    <li key={item.sistema} className="flex items-center gap-3">
                      <span className="w-32 shrink-0 truncate text-xs font-medium">
                        {item.sistema}
                      </span>
                      <span className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-muted">
                        <span
                          className="block h-full rounded-full bg-primary"
                          style={{ width: `${porcentaje}%` }}
                        />
                      </span>
                      <span className="w-20 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground">
                        {item.gb.toLocaleString('es-ES')} GB
                      </span>
                    </li>
                  )
                })}
              </ul>
            </PanelCard>
          </div>
        )}
      </PageContainer>
    </>
  )
}

/* ── Los grupos de duplicados ─────────────────────────────────────────── */

function DuplicadosPanel({
  duplicados,
  sinConfirmar,
  seleccion,
  marcar,
}: {
  duplicados: LibraryDuplicado[]
  sinConfirmar: number
  seleccion: Set<string>
  marcar: (id: string) => void
}) {
  return (
    <PanelCard
      title="Juegos duplicados"
      subtitle={
        duplicados.length
          ? `${duplicados.length} grupos · ${sinConfirmar ? `${sinConfirmar} sin confirmar` : 'todos confirmados con el hash completo'}`
          : 'Ningun juego esta repetido'
      }
      icon={<Copy className="size-4" />}
    >
      {duplicados.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No hay juegos repetidos: la huella rapida no ha encontrado ninguno.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {duplicados.map((grupo, indice) => (
            <li key={`${grupo.md5 ?? 'cand'}-${indice}`} className="py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">
                  {grupo.nombres[0]}
                  {grupo.nombres.length > 1 && (
                    <span className="text-muted-foreground">
                      {' '}
                      y {grupo.nombres.length - 1} mas
                    </span>
                  )}
                </span>
                <span className="rounded-md border border-border px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {grupo.copias} copias · {mb(grupo.bytes)} cada una
                </span>
                {grupo.confirmado ? (
                  <span className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
                    hash confirmado
                  </span>
                ) : (
                  <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
                    candidato (sin confirmar)
                  </span>
                )}
                <span className="ml-auto text-[11px] font-medium tabular-nums text-muted-foreground">
                  liberas {mb(grupo.ahorro)}
                </span>
              </div>
              <ul className="mt-2 space-y-1">
                {grupo.ficheros.map((fichero) => {
                  const id = clave(fichero.sistema, fichero.ruta)
                  return (
                    <li key={id} className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={seleccion.has(id)}
                        onChange={() => marcar(id)}
                        className="size-4 shrink-0 cursor-pointer accent-primary"
                        aria-label={`Marcar ${fichero.nombre}`}
                      />
                      <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                        {fichero.sistema}/{fichero.nombre}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </PanelCard>
  )
}

/* ── Las listas sencillas ──────────────────────────────────────────────── */

function SencillosPanel({
  titulo,
  texto,
  vacios,
  seleccion,
  marcar,
}: {
  titulo: string
  texto: string
  vacios: { total: number; lista: { sistema: string; ruta: string; nombre: string; bytes: number }[] }
  seleccion: Set<string>
  marcar: (id: string) => void
}) {
  return (
    <PanelCard
      title={titulo}
      subtitle={vacios.total ? `${vacios.total} · ${texto}` : texto}
      icon={<FileWarning className="size-4" />}
    >
      {vacios.lista.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nada por aqui: todo en orden.</p>
      ) : (
        <ul className="divide-y divide-border">
          {vacios.lista.slice(0, 200).map((item) => {
            const id = clave(item.sistema, item.ruta)
            return (
              <li key={id} className="flex items-center gap-3 py-2">
                <input
                  type="checkbox"
                  checked={seleccion.has(id)}
                  onChange={() => marcar(id)}
                  className="size-4 shrink-0 cursor-pointer accent-primary"
                  aria-label={`Marcar ${item.nombre}`}
                />
                <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                  {item.sistema}/{item.nombre}
                </span>
                <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                  {mb(item.bytes)}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </PanelCard>
  )
}
