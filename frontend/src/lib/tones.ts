/**
 * Los acentos de color del panel.
 *
 * La escala monocroma del skill §1 se queda para lo que debe verse gris
 * (rejillas, ejes, texto). Para lo que manda —el valor de cada tarjeta— hay
 * una paleta de seis tonos sobrios: ámbar, cian, rosa, violeta, azul y
 * esmeralda. Cada tarjeta del panel toma uno, así que la pantalla se lee por
 * colores sin perder el diseño ni la calma.
 */
export type Tone = 'amber' | 'cyan' | 'rose' | 'violet' | 'sky' | 'emerald'

/** El color del acento, para pintar gráficos y bordes. */
export const TONE_COLOR: Record<Tone, string> = {
  amber: 'var(--color-tone-1)',
  cyan: 'var(--color-tone-2)',
  rose: 'var(--color-tone-3)',
  violet: 'var(--color-tone-4)',
  sky: 'var(--color-tone-5)',
  emerald: 'var(--color-tone-6)',
}

/** La versión tenue del acento (halo de fondo, rellenos). */
export const TONE_SOFT: Record<Tone, string> = {
  amber: 'var(--tone-1-soft)',
  cyan: 'var(--tone-2-soft)',
  rose: 'var(--tone-3-soft)',
  violet: 'var(--tone-4-soft)',
  sky: 'var(--tone-5-soft)',
  emerald: 'var(--tone-6-soft)',
}
