import { motion, type HTMLMotionProps } from 'motion/react'
import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive'
export type ButtonSize = 'sm' | 'md' | 'lg'

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground hover:opacity-90 shadow-[0_2px_10px_-2px_rgba(0,0,0,0.35)]',
  secondary: 'bg-muted text-foreground hover:bg-accent',
  outline: 'border border-border bg-transparent text-foreground hover:bg-muted',
  ghost: 'bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground',
  destructive: 'bg-destructive text-destructive-foreground hover:opacity-90',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-lg',
  md: 'h-10 px-4 text-sm gap-2 rounded-xl',
  lg: 'h-11 px-5 text-sm gap-2 rounded-xl',
}

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: ButtonVariant
  size?: ButtonSize
  children?: React.ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', className, children, disabled, ...props },
  ref,
) {
  return (
    <motion.button
      ref={ref}
      type="button"
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.96 }}
      transition={{ type: 'spring', stiffness: 400, damping: 28 }}
      className={cn(
        'inline-flex cursor-pointer select-none items-center justify-center font-semibold tracking-[-0.015em] whitespace-nowrap transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        'disabled:pointer-events-none disabled:opacity-45',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {children}
    </motion.button>
  )
})

/** Botón de icono cuadrado (copiar, recargar, borrar…). */
export function IconButton({
  label,
  className,
  children,
  ...props
}: Omit<ButtonProps, 'children' | 'size'> & { label: string; children: React.ReactNode }) {
  return (
    <motion.button
      type="button"
      aria-label={label}
      title={label}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      transition={{ type: 'spring', stiffness: 400, damping: 28 }}
      className={cn(
        'inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-border bg-card text-muted-foreground transition-colors duration-200 hover:bg-muted hover:text-foreground',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        className,
      )}
      {...props}
    >
      {children}
    </motion.button>
  )
}
