import { Pill, PillBar } from '@/components/ui/Pill'
import { triggerHaptic } from '@/hooks/useWebHaptics'

/** Las dos pestañas de la sección «ROMs y BIOS». */
export type SectionTab = 'roms' | 'bios'

interface SectionTabsProps {
  value: SectionTab
  onChange: (value: SectionTab) => void
}

const TABS: { key: SectionTab; label: string }[] = [
  { key: 'roms', label: 'ROMs' },
  { key: 'bios', label: 'BIOS' },
]

/**
 * Las pestañas de la sección «ROMs y BIOS».
 *
 * La sección era solo BIOS: no había forma de administrar la biblioteca de
 * ROMs. Ahora son dos pestañas, la de las ROMs y la de las BIOS.
 */
export function SectionTabs({ value, onChange }: SectionTabsProps) {
  return (
    <PillBar className="mb-4">
      {TABS.map((tab) => (
        <Pill
          key={tab.key}
          active={value === tab.key}
          onClick={() => {
            triggerHaptic('light')
            onChange(tab.key)
          }}
        >
          {tab.label}
        </Pill>
      ))}
    </PillBar>
  )
}
