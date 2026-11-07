import { useState } from 'react'
import { type SectionTab } from '@/components/layout/SectionTabs'
import { BiosPage } from '@/pages/Bios'
import { RomsPage } from '@/pages/Roms'

/**
 * La sección «ROMs y BIOS»: dos pestañas en la misma pagina.
 *
 * Antes era solo BIOS (la ruta `/roms` montaba la pagina de BIOS y ya).
 * Ahora la de ROMs administer la biblioteca: duplicados, fichas rotas,
 * ficheros vacios y media sin juego, con cuarentena y vuelta atras.
 */
export function RomsBiosPage() {
  const [tab, setTab] = useState<SectionTab>('roms')
  return tab === 'bios' ? (
    <BiosPage tab={tab} onTab={setTab} />
  ) : (
    <RomsPage tab={tab} onTab={setTab} />
  )
}
