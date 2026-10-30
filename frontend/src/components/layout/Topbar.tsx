import { motion } from 'motion/react'
import { Menu, Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { IconSwap, IconSwapItem } from '@/components/ui/IconSwap'
import { cn } from '@/lib/utils'

interface TopbarProps {
  title: string
  subtitle?: string
  onMenu?: () => void
  actions?: React.ReactNode
}

export function Topbar({ title, subtitle, onMenu, actions }: TopbarProps) {
  const { resolved, toggle } = useTheme()

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1800px] items-center gap-3 px-4 py-3 sm:px-6 lg:px-10">
        {onMenu && (
          <button
            type="button"
            onClick={onMenu}
            aria-label="Abrir menú"
            className="-ml-1 cursor-pointer rounded-xl border border-border bg-card p-2 text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 lg:hidden"
          >
            <Menu className="size-4" />
          </button>
        )}

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold tracking-[-0.019em] text-foreground sm:text-xl">
            {title}
          </h1>
          {subtitle && (
            <p className="truncate text-xs font-medium text-muted-foreground sm:text-[13px]">
              {subtitle}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {actions}
          <motion.button
            type="button"
            onClick={toggle}
            aria-label={resolved === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
            title={resolved === 'dark' ? 'Tema claro' : 'Tema oscuro'}
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            className={cn(
              'flex size-9 cursor-pointer items-center justify-center rounded-xl border border-border bg-card text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground',
              'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
            )}
          >
            <IconSwap>
              <IconSwapItem key={resolved}>
                {resolved === 'dark' ? (
                  <Sun className="size-4" />
                ) : (
                  <Moon className="size-4" />
                )}
              </IconSwapItem>
            </IconSwap>
          </motion.button>
        </div>
      </div>
    </header>
  )
}
