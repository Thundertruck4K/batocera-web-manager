import { motion } from 'motion/react'
import { ChevronRight, Folder, ImageOff, Image as ImageIcon, RefreshCw } from 'lucide-react'
import type { RomFolder, RomFolderItem } from '@/lib/types'
import { cn } from '@/lib/utils'

interface RomFolderViewProps {
  folder: RomFolder | null
  system: string
  subpath: string
  loading: boolean
  /** Abre el modal de scrape para un ROM. */
  onOpenRom: (rom: RomFolderItem) => void
  /** Entra en una subcarpeta. */
  onOpenFolder: (path: string) => void
  /** Vuelve a la raíz del sistema. */
  onGoRoot: () => void
}

/** URL de la carátula que dejó el scraper para este ROM. */
function romImageUrl(system: string, rom: RomFolderItem, subpath: string): string {
  const base = `/api/rom-image/${encodeURIComponent(system)}/${encodeURIComponent(rom.filename)}`
  return subpath ? `${base}?subpath=${encodeURIComponent(subpath)}` : base
}

/** Una fila de ROM con su carátula. */
function RomRow({
  rom,
  system,
  subpath,
  onOpenRom,
  index,
  animate = true,
}: {
  rom: RomFolderItem
  system: string
  subpath: string
  onOpenRom: (rom: RomFolderItem) => void
  index: number
  /** En listados enormes se evita animar hundreds de filas a la vez. */
  animate?: boolean
}) {
  return (
    <motion.button
      type="button"
      onClick={() => onOpenRom(rom)}
      initial={animate ? { opacity: 0, y: 6 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.22,
        ease: [0.16, 1, 0.3, 1],
        delay: animate ? Math.min(index * 0.01, 0.05) : 0,
      }}
      className={cn(
        'group flex w-full cursor-pointer items-center gap-3 rounded-2xl border border-border bg-card p-2 text-left',
        'transition-colors duration-150 hover:bg-muted',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
      )}
    >
      <span className="relative flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-muted">
        {rom.has_image ? (
          <img
            src={romImageUrl(system, rom, subpath)}
            alt=""
            loading="lazy"
            className="size-full object-cover"
          />
        ) : (
          <ImageOff className="size-4 text-muted-foreground/50" aria-hidden />
        )}
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-semibold tracking-[-0.011em] text-foreground">
          {rom.name}
        </span>
        <span className="mt-0.5 flex items-center gap-2 text-[11px] font-medium text-muted-foreground">
          <span className="uppercase">{rom.ext.replace('.', '')}</span>
          {rom.is_game_folder && (
            <span className="inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <Folder className="size-3" aria-hidden />
              carpeta
            </span>
          )}
          <span className="tabular-nums">{rom.size_human}</span>
          {rom.year && (
            <>
              <span className="h-3 w-px bg-border" />
              <span className="tabular-nums">{rom.year}</span>
            </>
          )}
        </span>
      </span>

      <ChevronRight
        className="size-4 shrink-0 text-muted-foreground/50 transition-transform duration-150 group-hover:translate-x-0.5"
        aria-hidden
      />
    </motion.button>
  )
}

/**
 * Contenido de una carpeta de ROMs: las carátulas que ya están descargadas
 * y las que todavía no, en dos bloques separados.
 */
export function RomFolderView({
  folder,
  system,
  subpath,
  loading,
  onOpenRom,
  onOpenFolder,
  onGoRoot,
}: RomFolderViewProps) {
  if (loading && !folder) {
    return (
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 8 }).map((_, index) => (
          <div key={index} className="h-[68px] animate-pulse rounded-2xl bg-muted/40" />
        ))}
      </div>
    )
  }

  if (!folder) return null

  // Un juego puede ser una carpeta (ScummVM, DOSBox, MUGEN...): entonces es un
  // ROM (se escrapea por el nombre de la carpeta), no una carpeta que se abre.
  // El backend ya deja fuera lo que no es un juego (el `_info.txt` de cada
  // sistema, el `gamelist.xml`, los guardados de estado…), así que aquí sólo
  // hay juegos y carpetas.
  const folders = folder.items.filter((item) => item.is_dir && !item.is_game_folder)
  const roms = folder.items.filter((item) => item.is_rom && (!item.is_dir || item.is_game_folder))
  const withMedia = roms.filter((rom) => rom.has_image)
  const withoutMedia = roms.filter((rom) => !rom.has_image)
  /** En sistemas con cientos de ROMs se saltan las animaciones de entrada. */
  const animateRows = folder.items.length <= 48

  const childPath = (name: string) => (subpath ? `${subpath}/${name}` : name)

  return (
    <div className="space-y-6">
      {/* Migas de pan */}
      <nav className="flex flex-wrap items-center gap-1 text-xs font-medium text-muted-foreground">
        <button
          type="button"
          onClick={onGoRoot}
          className="cursor-pointer rounded-lg px-1.5 py-0.5 transition-colors duration-150 hover:bg-muted hover:text-foreground"
        >
          {system}
        </button>
        {folder.breadcrumb.slice(1).map((part, index) => (
          <span key={`${part}-${index}`} className="flex items-center gap-1">
            <ChevronRight className="size-3" aria-hidden />
            <span className="text-foreground">{part}</span>
          </span>
        ))}
      </nav>

      {/* Carpetas */}
      {folders.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Carpetas
          </h3>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {folders.map((dir) => (
              <button
                key={dir.filename}
                type="button"
                onClick={() => onOpenFolder(childPath(dir.filename))}
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-2xl border border-border bg-card p-3 text-left',
                  'transition-colors duration-150 hover:bg-muted',
                  'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
                )}
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted">
                  <Folder className="size-4 text-brand" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-foreground">{dir.name}</span>
                  <span className="text-[11px] font-medium text-muted-foreground">
                    {dir.child_count ?? 0} ficheros
                  </span>
                </span>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground/50" aria-hidden />
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Media presente */}
      <section>
        <div className="mb-2 flex items-center gap-2">
          <ImageIcon className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden />
          <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Media presente
          </h3>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold tabular-nums text-muted-foreground">
            {withMedia.length}
          </span>
        </div>
        {withMedia.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-border px-4 py-6 text-center text-xs font-medium text-muted-foreground">
            Ningún ROM de esta carpeta tiene todavía su imagen.
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {withMedia.map((rom, index) => (
              <RomRow
                key={rom.filename}
                rom={rom}
                system={system}
                subpath={subpath}
                onOpenRom={onOpenRom}
                index={index}
                animate={animateRows}
              />
            ))}
          </div>
        )}
      </section>

      {/* Media ausente */}
      <section>
        <div className="mb-2 flex items-center gap-2">
          <ImageOff className="size-3.5 text-muted-foreground" aria-hidden />
          <h3 className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            Media ausente
          </h3>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-semibold tabular-nums text-muted-foreground">
            {withoutMedia.length}
          </span>
        </div>
        {withoutMedia.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-border px-4 py-6 text-center text-xs font-medium text-muted-foreground">
            Todos los ROMs de esta carpeta tienen su imagen. ¡Bien hecho!
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {withoutMedia.map((rom, index) => (
              <RomRow
                key={rom.filename}
                rom={rom}
                system={system}
                subpath={subpath}
                onOpenRom={onOpenRom}
                index={index}
                animate={animateRows}
              />
            ))}
          </div>
        )}
      </section>

      {folder.is_empty && (
        <p className="flex items-center justify-center gap-2 rounded-2xl border border-dashed border-border px-4 py-8 text-xs font-medium text-muted-foreground">
          <RefreshCw className="size-4" aria-hidden />
          Esta carpeta está vacía.
        </p>
      )}
    </div>
  )
}
