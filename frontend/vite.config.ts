import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// El backend Python (app.py) sirve la API en el mismo puerto que indique
// BATOCERA_MANAGER_PORT (5000 por defecto). En desarrollo, Vite hace de proxy
// para que el frontend hable con /api/* sin CORS.
const BACKEND = process.env.BATOCERA_BACKEND ?? 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/media': { target: BACKEND, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    // El backend sirve el bundle como un único index.html + assets.
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        // Trozos separados: el navegador cachea las librerías entre visitas
        // y sólo descarga el código de la app cuando cambia.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          motion: ['motion'],
          charts: ['recharts'],
        },
      },
    },
  },
})
