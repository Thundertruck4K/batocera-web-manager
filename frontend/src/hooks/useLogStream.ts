import { useEffect, useRef, useState } from 'react'
import type { LogEntry } from '@/components/overtrue/log-stream'

/** Máximo de eventos que se guardan en el cliente (el backend también corta a 500). */
const MAX_ENTRIES = 500

export interface LogStreamState {
  entries: LogEntry[]
  /** `true` mientras el stream SSE está abierto. */
  connected: boolean
}

/**
 * Escucha el stream de eventos del backend por SSE.
 *
 * Al conectar, el backend manda el historial pendiente y después los eventos
 * nuevos. Si la conexión se cae, `EventSource` reintenta solo: los ids ya
 * vistos se descartan para no duplicar líneas.
 */
export function useLogStream(): LogStreamState {
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const lastId = useRef(0)

  useEffect(() => {
    const source = new EventSource('/api/logs/stream?since=0')

    source.onopen = () => setConnected(true)

    source.onmessage = (event) => {
      let entry: LogEntry
      try {
        entry = JSON.parse(event.data) as LogEntry
      } catch {
        return // línea corrupta: se ignora en vez de romper el stream
      }
      const id = Number(entry.id)
      if (Number.isFinite(id)) {
        if (id <= lastId.current) return // ya estaba en pantalla
        lastId.current = id
      }
      setEntries((current) => {
        const next = current.concat(entry)
        return next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next
      })
    }

    source.onerror = () => setConnected(false)

    return () => source.close()
  }, [])

  return { entries, connected }
}
