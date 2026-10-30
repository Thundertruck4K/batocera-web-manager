import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'

interface UseApiOptions {
  /** Intervalo de refresco en ms. 0 desactiva el polling. */
  pollMs?: number
  /** Permite no lanzar la petición hasta que la dependencia esté lista. */
  enabled?: boolean
}

interface UseApiResult<T> {
  data: T | null
  error: string | null
  loading: boolean
  /** Fuerza una recarga manual. */
  refresh: () => void
  /** Marca la carga como terminada (al refrescar en segundo plano). */
  setData: (updater: T | ((prev: T | null) => T | null)) => void
}

/**
 * Carga asíncrona sencilla con polling opcional. SeRecarga en segundo plano
 * (sin parpadeo) cuando ya hay datos.
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[], options: UseApiOptions = {}): UseApiResult<T> {
  const { pollMs = 0, enabled = true } = options

  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [nonce, setNonce] = useState(0)

  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const hasData = useRef(false)

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }
    let cancelled = false

    const run = async () => {
      if (!hasData.current) setLoading(true)
      try {
        const result = await fetcherRef.current()
        if (cancelled) return
        hasData.current = true
        setData(result)
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Error inesperado')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void run()

    let timer: number | undefined
    if (pollMs > 0) {
      timer = window.setInterval(run, pollMs)
    }
    return () => {
      cancelled = true
      if (timer) window.clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, pollMs, enabled, nonce])

  const refresh = useCallback(() => setNonce((n) => n + 1), [])

  const update = useCallback((updater: T | ((prev: T | null) => T | null)) => {
    setData((prev) =>
      typeof updater === 'function' ? (updater as (p: T | null) => T | null)(prev) : updater,
    )
  }, [])

  return { data, error, loading, refresh, setData: update }
}
