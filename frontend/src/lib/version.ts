/**
 * Versión del manager. La inyecta `app.py` en el `<meta name="bm-app-version">`
 * al servir el index.html; si el frontend se abre desde el servidor de
 * desarrollo de Vite, el marcador queda sin sustituir y se muestra "dev".
 */
export const APP_VERSION: string = (() => {
  if (typeof document === 'undefined') return 'dev'
  const raw = document.querySelector('meta[name="bm-app-version"]')?.getAttribute('content') ?? ''
  const version = raw.trim()
  return version && !version.includes('{{') ? version : 'dev'
})()
