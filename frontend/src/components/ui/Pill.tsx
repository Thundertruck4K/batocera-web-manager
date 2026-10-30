import { cn } from '@/lib/utils'

/** Barra de píldoras para filtros (skill §3). */
export function PillBar({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn('pill-bar overflow-x-auto no-scrollbar', className)}>{children}</div>
}

export function Pill({
  active = false,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      data-active={active}
      className={cn('pill cursor-pointer whitespace-nowrap focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50', className)}
      {...props}
    />
  )
}
