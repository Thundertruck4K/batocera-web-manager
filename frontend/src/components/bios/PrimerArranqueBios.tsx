import { motion } from 'motion/react'
import { CircleAlert, CircleCheck, Download, PackageSearch, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Progress } from '@/components/ui/Progress'
import { useTrabajoBios } from '@/hooks/useTrabajoBios'
import { api } from '@/lib/api'
import type { BiosDescargaResultado } from '@/lib/types'
import { cn } from '@/lib/utils'

/**
 * La comprobación de BIOS del primer arranque.
 *
 * Al abrir el manager por primera vez (después de instalar, `install.sh`
 * borra el marcador) se comprueba qué BIOS pide Batocera, se bajan de la
 * fuente las que falten y se informa de lo que se encontró y lo que no.
 *
 * Después, el botón de la sección de BIOS vuelve a hacerlo cuando se quiera.
 */
export function PrimerArranqueBios() {
  const [abierto, setAbierto] = useState(false)
  const [comprobado, setComprobado] = useState(false)
  const { trabajo, resultado, corriendo, error, arrancar } = useTrabajoBios()

  // Al cargar: ¿queda por hacer la comprobación?
  useEffect(() => {
    let cancelado = false
    const mirar = async () => {
      try {
        const estado = await api.biosFirstCheck()
        if (cancelado) return
        setComprobado(true)
        if (estado?.pendiente) {
          setAbierto(true)
          void arrancar()
        }
      } catch {
        /* El backend puede no estar listo: no se molesta al usuario. */
        setComprobado(true)
      }
    }
    void mirar()
    return () => {
      cancelado = true
    }
  }, [arrancar])

  if (!comprobado || !abierto) return null

  return (
    <Modal
      open={abierto}
      onClose={() => setAbierto(false)}
      title="Comprobando las BIOS"
      description="Se revisa qué BIOS pide Batocera y se bajan las que falten de la fuente."
      footer={
        <Button variant="secondary" onClick={() => setAbierto(false)}>
          Cerrar
        </Button>
      }
    >
      {corriendo && <Cuerpo trabajo={trabajo} />}
      {!corriendo && error && (
        <Aviso icon={CircleAlert} tone="bad" titulo="No se pudo comprobar">
          {error}
        </Aviso>
      )}
      {!corriendo && !error && resultado && (
        <Resumen resultado={resultado} onRepetir={arrancar} />
      )}
    </Modal>
  )
}

/** La barra de progreso mientras el trabajo dura. */
function Cuerpo({ trabajo }: { trabajo: { porcentaje: number; actual: string; mensaje: string; hechos: number; total: number } | null }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded-2xl border border-border bg-muted/40 px-4 py-3">
        <motion.span
          className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-brand/15 text-brand"
          animate={{ rotate: 360 }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
        >
          <RefreshCw className="size-4" />
        </motion.span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-foreground">
            {trabajo?.mensaje || 'comprobando las BIOS'}
          </p>
          <p className="truncate text-[11px] text-muted-foreground">
            {trabajo?.actual || 'preparando…'}
          </p>
        </div>
      </div>

      <Progress
        value={trabajo?.porcentaje ?? 0}
        label={`${trabajo?.hechos ?? 0} de ${trabajo?.total ?? 0}`}
      />

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        Puedes seguir usando la aplicación mientras tanto: no hace falta cerrar la ventana.
      </p>
    </div>
  )
}

/** Lo que dio la comprobación. */
function Resumen({
  resultado,
  onRepetir,
}: {
  resultado: BiosDescargaResultado
  onRepetir: () => void
}) {
  const r = resultado.resumen
  const bajadas = resultado.descargadas.length
  const sinEncontrar = resultado.no_encontradas.length
  const fallo = resultado.fallidas.length + resultado.sin_verificar.length

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2.5">
        <Cifra valor={r.esperadas} etiqueta="BIOS revisadas" />
        <Cifra valor={r.descargadas} etiqueta="descargadas" tono="good" />
        <Cifra valor={sinEncontrar} etiqueta="no están en la fuente" tono={sinEncontrar ? 'warn' : 'plain'} />
        <Cifra valor={fallo} etiqueta="con problemas" tono={fallo ? 'bad' : 'plain'} />
      </div>

      {bajadas > 0 && (
        <Aviso icon={Download} tone="good" titulo={`${bajadas} BIOS descargadas`}>
          Se han dejado donde Batocera las espera.
        </Aviso>
      )}

      {sinEncontrar > 0 && (
        <Aviso icon={PackageSearch} tone="warn" titulo={`${sinEncontrar} no están en la fuente`}>
          <ul className="mt-1 space-y-0.5">
            {resultado.no_encontradas.slice(0, 8).map((fichero) => (
              <li key={fichero} className="truncate font-mono text-[10px]">
                {fichero}
              </li>
            ))}
          </ul>
          {sinEncontrar > 8 && (
            <p className="mt-1 text-[11px]">y {sinEncontrar - 8} más…</p>
          )}
        </Aviso>
      )}

      {fallo > 0 && (
        <Aviso icon={CircleAlert} tone="bad" titulo={`${fallo} con problemas`}>
          Se pueden volver a intentar desde la sección de BIOS.
        </Aviso>
      )}

      {sinEncontrar === 0 && fallo === 0 && (
        <Aviso icon={CircleCheck} tone="good" titulo="Todo en su sitio">
          No falta ninguna BIOS de tus sistemas.
        </Aviso>
      )}

      <Button variant="secondary" onClick={onRepetir} className="w-full">
        <RefreshCw className="size-4" />
        Escanear el sistema
      </Button>
    </div>
  )
}

/** Un numero grande con su etiqueta. */
function Cifra({
  valor,
  etiqueta,
  tono = 'plain',
}: {
  valor: number
  etiqueta: string
  tono?: 'plain' | 'good' | 'warn' | 'bad'
}) {
  const color =
    tono === 'good'
      ? 'text-brand'
      : tono === 'warn'
        ? 'text-amber-600 dark:text-amber-400'
        : tono === 'bad'
          ? 'text-destructive'
          : 'text-foreground'
  return (
    <div className="rounded-2xl border border-border bg-muted/30 px-3 py-2.5">
      <p className={cn('text-xl font-semibold tabular-nums tracking-[-0.02em]', color)}>
        {valor}
      </p>
      <p className="text-[11px] leading-tight text-muted-foreground">{etiqueta}</p>
    </div>
  )
}

/** Un aviso con icono. */
function Aviso({
  icon: Icon,
  tone,
  titulo,
  children,
}: {
  icon: typeof CircleCheck
  tone: 'good' | 'warn' | 'bad'
  titulo: string
  children?: React.ReactNode
}) {
  const tono =
    tone === 'good'
      ? 'border-brand/40 bg-brand/10 text-brand'
      : tone === 'warn'
        ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400'
        : 'border-destructive/40 bg-destructive/10 text-destructive'
  return (
    <div className={cn('rounded-2xl border px-4 py-3', tono)}>
      <p className="flex items-center gap-2 text-xs font-semibold">
        <Icon className="size-4 shrink-0" />
        {titulo}
      </p>
      {children && (
        <div className="mt-1 pl-6 text-[11px] leading-relaxed opacity-90">{children}</div>
      )}
    </div>
  )
}
