import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-xl bg-muted', className)} />
}

/** Bloque de carga con la forma de una tarjeta del panel. */
export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="card space-y-3 p-5">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-24 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-3 w-full" />
      ))}
    </div>
  )
}
