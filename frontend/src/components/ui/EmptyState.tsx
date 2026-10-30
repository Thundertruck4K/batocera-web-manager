import { cn } from '@/lib/utils'

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-3xl border border-dashed border-border px-6 py-14 text-center',
        className,
      )}
    >
      {icon && (
        <span className="mb-3 flex size-11 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
          {icon}
        </span>
      )}
      <h3 className="text-sm font-semibold tracking-[-0.015em] text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
