import { AnimatePresence, motion, type HTMLMotionProps } from 'motion/react'

/**
 * Intercambia dos iconos con un cross-fade + escala. El estado vive fuera:
 * el consumidor decide qué icono mostrar (skill §4).
 */
export function IconSwap({ children }: { children: React.ReactNode }) {
  return <AnimatePresence mode="popLayout" initial={false}>{children}</AnimatePresence>
}

export function IconSwapItem({ children, className, ...props }: HTMLMotionProps<'span'>) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.25, filter: 'blur(4px)' }}
      animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, scale: 0.25, filter: 'blur(4px)' }}
      transition={{ type: 'spring', duration: 0.25, bounce: 0 }}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
      className={className}
      {...props}
    >
      {children}
    </motion.span>
  )
}
