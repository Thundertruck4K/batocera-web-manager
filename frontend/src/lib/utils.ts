import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Formatea bytes como "1.4 GB" (mismo criterio que `human_size` del backend). */
export function humanSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let n = bytes
  let i = 0
  while (Math.abs(n) >= 1024 && i < units.length - 1) {
    n /= 1024
    i += 1
  }
  return `${n.toFixed(1)} ${units[i]}`
}

/** Convierte segundos en "3 h 24 min" (o "45 min" / "2 d 1 h"). */
export function humanDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0 min'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d} d ${h} h`
  if (h > 0) return `${h} h ${m} min`
  return `${m} min`
}

/** Acorta un nombre de fichero conservando la extensión: "Sonic The Hedgehog 2.md" → "Sonic The He…2.md" */
export function truncateMiddle(text: string, max = 42): string {
  if (text.length <= max) return text
  const dot = text.lastIndexOf('.')
  const ext = dot > 0 ? text.slice(dot) : ''
  const stem = ext ? text.slice(0, dot) : text
  const keep = Math.max(4, max - ext.length)
  const head = Math.ceil(keep * 0.6)
  const tail = keep - head
  return `${stem.slice(0, head)}…${stem.slice(stem.length - tail)}${ext}`
}
