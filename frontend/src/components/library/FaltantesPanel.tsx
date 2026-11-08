import { PackageSearch, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Select } from '@/components/ui/Field'
import { Button } from '@/components/ui/Button'
import { PanelCard } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Pill, PillBar } from '@/components/ui/Pill'
import { Progress } from '@/components/ui/Progress'
import type { LibraryDatSistema, LibraryFaltante, LibraryFaltantes, LibraryJob } from '@/lib/types'

/**
 * Cómo se emparejó el juego con el DAT. No es lo mismo una coincidencia por
 * hash que una por título, así que se dice de dónde salió cada una.
 */
const METODOS: Record<string, string> = {
  nombre: 'por el nombre',
  hash: 'por el hash',
  gamecode: 'por el codigo del disco',
  serial: 'por el serial',
  titulo: 'por el titulo (conviene revisarlo)',
}

/** Por qué falta esa versión. */
function motivo(faltante: LibraryFaltante): string {
  switch (faltante.motivo) {
    case 'disco':
      return `te falta el disco ${faltante.detalle}`
    case 'region':
      return `otra región (${faltante.detalle})`
    case 'revision':
      return 'otra revisión'
    case 'idioma':
      return `otro idioma (${faltante.detalle})`
    default:
      return 'otra versión'
  }
}

type Filtro = 'todo' | 'discos' | 'mejores'

interface FaltantesPanelProps {
  sistemas: LibraryDatSistema[]
  sistema: string
  onSistema: (sistema: string) => void
  resultado: LibraryFaltantes | null
  trabajo: LibraryJob | null
  onComparar: () => void
  busy: boolean
}

/**
 * La sección «Lo que falta»: las otras versiones de los juegos que ya tienes.
 *
 * El DAT de un sistema es la lista de todos sus juegos, así que comparado con
 * la biblioteca dice qué te falta. Pero la lista completa no informa de nada
 * (el DAT de PlayStation 2 tiene 13.618 juegos y una biblioteca normal tiene
 * 300), así que aquí se enseña **lo que falta de los juegos que ya tienes**:
 * la otra región, el otro disco, la versión mejor.
 *
 * La comparación es por sistema y va en segundo plano: cargar los 17 índices
 * a la vez son 55 MB de JSON y en la consola eso es memoria que no está.
 */
export function FaltantesPanel({
  sistemas,
  sistema,
  onSistema,
  resultado,
  trabajo,
  onComparar,
  busy,
}: FaltantesPanelProps) {
  const [filtro, setFiltro] = useState<Filtro>('todo')

  const grupos = useMemo(() => {
    const lista = resultado?.detalle ?? []
    if (filtro === 'discos') return lista.filter((g) => g.discos_faltantes.length > 0)
    if (filtro === 'mejores') {
      return lista.filter((g) => g.faltan.some((f) => f.mejor))
    }
    return lista
  }, [resultado, filtro])

  /**
   * Cuántos juegos tienen alguna versión mejor. Lo cuenta el backend, pero
   * si el resultado viene recortado se usa el de la lista, para que el número
   * del filtro sea el número de cosas que se enseñan.
   */
  const gruposConMejores = useMemo(
    () => (resultado?.detalle ?? []).filter((g) => g.faltan.some((f) => f.mejor)).length,
    [resultado],
  )

  const trabajando = trabajo?.estado === 'trabajando'

  return (
    <PanelCard
      title="Lo que falta"
      subtitle="Las otras versiones de los juegos que ya tienes"
      icon={<PackageSearch className="size-4" />}
      actions={
        <>
          <Select
            value={sistema}
            onChange={(event) => onSistema(event.target.value)}
            className="h-9 w-52 text-xs"
            aria-label="Sistema con DAT"
          >
            {sistemas.length === 0 && <option value="">sin DAT instalado</option>}
            {sistemas.map((s) => (
              <option key={s.sistema} value={s.sistema}>
                {s.sistema} · {s.juegos_dat.toLocaleString('es-ES')} juegos
              </option>
            ))}
          </Select>
          <Button size="sm" variant="primary" disabled={busy || !sistema} onClick={onComparar}>
            <Search className="size-4" />
            Comparar con el DAT
          </Button>
        </>
      }
    >
      {sistemas.length === 0 ? (
        <EmptyState
          icon={<PackageSearch className="size-5" />}
          title="No hay DAT instalado"
          description="Los DAT son metadatos (la lista de juegos con sus hashes, sin una sola ROM) y se descargan desde la sección de herramientas."
        />
      ) : trabajando && trabajo ? (
        <div className="rounded-2xl border border-border bg-muted/40 px-4 py-4">
          <Progress
            value={trabajo.porcentaje}
            label={
              trabajo.total
                ? `${trabajo.mensaje || 'Comparando'} · ${trabajo.hechos} de ${trabajo.total}`
                : (trabajo.mensaje || 'Comparando')
            }
          />
          {trabajo.actual && (
            <p className="mt-2 truncate text-[11px] text-muted-foreground">
              Ahora: {trabajo.actual}
            </p>
          )}
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground/80">
            Se compara el sistema entero con su DAT: puede tardar un rato. El trabajo sigue en el
            servidor, asi que no hace falta cerrar la ventana.
          </p>
        </div>
      ) : !resultado ? (
        <EmptyState
          icon={<PackageSearch className="size-5" />}
          title="Todavia no hay comparacion"
          description="Elige un sistema y pulsa «Comparar con el DAT»: se busca que otras versiones hay de los juegos que ya tienes. No se toca nada."
        />
      ) : resultado.detalle.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          {resultado.sin_dat > 0 ? (
            <>
              Los {resultado.encontrados} juegos de este sistema estan en su DAT y no hay mas
              versiones de ellos. Hay {resultado.sin_dat} juegos que no salen en el DAT (mods,
              traducciones o homebrew).
            </>
          ) : (
            'No hay nada que comparar: este sistema no tiene juegos en la biblioteca.'
          )}
        </p>
      ) : (
        <div className="space-y-4">
          {/* El resumen */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Resumen valor={resultado.grupos} texto="juegos con más versiones" />
            <Resumen valor={resultado.faltantes} texto="versiones que no tienes" />
            <Resumen valor={resultado.mejores} texto="versiones que son mejores" />
            <Resumen valor={resultado.discos} texto="juegos a los que falta un disco" />
          </div>

          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Comparado <span className="font-medium text-foreground">{resultado.sistema}</span> ·{' '}
            {resultado.encontrados.toLocaleString('es-ES')} juegos emparejados con el DAT ·{' '}
            {resultado.sin_dat.toLocaleString('es-ES')} que no salen en el DAT
            {resultado.quizas
              ? ` · ${resultado.quizas.toLocaleString('es-ES')} con coincidencia dudosa (quiza ya los tienes)`
              : ''}
          </p>

          {/* Los dudosos: puede que ya los tengas y el nombre no cuadre */}
          {resultado.quizas_lista && resultado.quizas_lista.length > 0 && (
            <details className="rounded-2xl border border-border px-3 py-2">
              <summary className="cursor-pointer text-[11px] text-muted-foreground">
                {resultado.quizas?.toLocaleString('es-ES') ?? resultado.quizas_lista.length} juegos con
                coincidencia dudosa: quiza ya los tienes y el nombre no cuadra
              </summary>
              <ul className="mt-2 space-y-1">
                {resultado.quizas_lista.map((quiza) => (
                  <li key={quiza.fichero} className="text-[11px] text-muted-foreground">
                    <span className="text-foreground">{quiza.fichero}</span>
                    {' · quiza sea «'}
                    {quiza.candidato}
                    {'»'}
                  </li>
                ))}
              </ul>
            </details>
          )}

          {/* Los filtros */}
          <PillBar>
            <Pill active={filtro === 'todo'} onClick={() => setFiltro('todo')}>
              Todo ({resultado.grupos})
            </Pill>
            <Pill active={filtro === 'discos'} onClick={() => setFiltro('discos')}>
              Juegos con discos que faltan ({resultado.discos})
            </Pill>
            <Pill active={filtro === 'mejores'} onClick={() => setFiltro('mejores')}>
              Juegos con versión mejor ({resultado.grupos_mejores ?? gruposConMejores})
            </Pill>
          </PillBar>

          {/* Los juegos */}
          <ul className="space-y-2">
            {grupos.map((grupo) => (
              <li key={grupo.titulo} className="rounded-2xl border border-border p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm font-semibold">{grupo.titulo}</p>
                  {grupo.discos_faltantes.length > 0 && (
                    <span className="rounded-full bg-destructive/15 px-2 py-0.5 text-[11px] font-medium text-destructive">
                      te falta el disco {grupo.discos_faltantes.join(', ')}
                    </span>
                  )}
                </div>

                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Tienes</p>
                    <ul className="mt-1 space-y-1">
                      {grupo.variantes.map((variante) => (
                        <li key={variante.fichero} className="text-xs">
                          <span className="text-foreground">{variante.nombre}</span>
                          <span className="text-muted-foreground">
                            {' '}
                            · {METODOS[variante.metodo] ?? variante.metodo} · {variante.fichero}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Faltan</p>
                    <ul className="mt-1 space-y-1">
                      {grupo.faltan.map((faltante) => (
                        <li key={faltante.nombre} className="text-xs">
                          <span className="text-foreground">{faltante.nombre}</span>
                          {faltante.copias && faltante.copias > 1 && (
                            <span className="text-muted-foreground"> ×{faltante.copias}</span>
                          )}
                          <span className="text-muted-foreground"> · {motivo(faltante)}</span>
                          {faltante.mejor && (
                            <span className="ml-1 rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                              versión mejor
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          {resultado.detalle_recortado && (
            <p className="text-[11px] text-muted-foreground">
              Se enseñan {resultado.detalle.length} de {resultado.grupos} juegos: hay mas.
            </p>
          )}
          {!resultado.hasheado && (
            <p className="text-[11px] leading-relaxed text-muted-foreground/80">
              Los ficheros grandes no se han hasheado (hasher una ISO de 4 GB lleva un rato), asi que
              algunos juegos se han emparejado por el nombre o por el titulo. El DAT no se toca.
            </p>
          )}
        </div>
      )}
    </PanelCard>
  )
}

/** Una cifra con su texto, para el resumen. */
function Resumen({ valor, texto }: { valor: number; texto: string }) {
  return (
    <div className="rounded-2xl border border-border bg-muted/30 px-3 py-2">
      <p className="text-lg font-semibold tabular-nums">{valor.toLocaleString('es-ES')}</p>
      <p className="text-[11px] leading-tight text-muted-foreground">{texto}</p>
    </div>
  )
}
