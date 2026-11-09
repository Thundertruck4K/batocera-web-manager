import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import type { BiosDescargaResultado, BiosJob } from '@/lib/types'

/** Cada cuánto se pregunta por el estado del trabajo (ms). */
const SONDEO = 900

interface UseTrabajoBios {
  /** El trabajo en curso (o el último). */
  trabajo: BiosJob | null
  /** El resultado, cuando ha terminado. */
  resultado: BiosDescargaResultado | null
  /** Va corriendo ahora mismo. */
  corriendo: boolean
  /** Error al arrancar o durante el trabajo. */
  error: string | null
  /** Arranca la comprobación (escaneo + descarga de lo que falte). */
  arrancar: () => Promise<void>
  /** Olvida el resultado (para empezar de cero). */
  reiniciar: () => void
}

/**
 * La comprobación de BIOS: escanea la consola y baja de la fuente lo que
 * falte.
 *
 * Va en segundo plano con su barra de progreso: baja ficheros de internet y
 * puede tardar, así que la interfaz tiene que enseñar que sigue viva (si no,
 * el usuario cierra la ventana creyendo que la aplicación se ha colgado).
 */
export function useTrabajoBios(): UseTrabajoBios {
  const [trabajo, setTrabajo] = useState<BiosJob | null>(null)
  const [resultado, setResultado] = useState<BiosDescargaResultado | null>(null)
  const [corriendo, setCorriendo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => {
    if (timer.current) window.clearTimeout(timer.current)
  }, [])

  const arrancar = useCallback(async () => {
    setCorriendo(true)
    setError(null)
    setResultado(null)
    try {
      const arranque = await api.biosDownloadStart()
      if (!arranque?.job) throw new Error('no se pudo arrancar la comprobación')
      setTrabajo({
        ok: true,
        id: arranque.job,
        estado: 'trabajando',
        hechos: 0,
        total: 0,
        actual: '',
        porcentaje: 0,
        mensaje: 'comprobando las BIOS',
      })

      const preguntar = async () => {
        try {
          const estado = await api.biosJob(arranque.job)
          setTrabajo(estado)
          if (estado.estado === 'listo') {
            setResultado((estado.resultado as BiosDescargaResultado) ?? null)
            setCorriendo(false)
            return
          }
          if (estado.estado === 'error') {
            setError(estado.error || 'la comprobación falló')
            setCorriendo(false)
            return
          }
          timer.current = window.setTimeout(preguntar, SONDEO)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error inesperado')
          setCorriendo(false)
        }
      }
      void preguntar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error inesperado')
      setCorriendo(false)
    }
  }, [])

  const reiniciar = useCallback(() => {
    setTrabajo(null)
    setResultado(null)
    setError(null)
    setCorriendo(false)
  }, [])

  return { trabajo, resultado, corriendo, error, arrancar, reiniciar }
}
