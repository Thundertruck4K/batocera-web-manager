// Normaliza los finales de línea del bundle a LF.
//
// En Windows, Vite inyecta las etiquetas de <script>/<link> con CRLF, así que el
// mismo código produce artefactos distintos según la máquina que compila. El
// bundle se versiona en el repositorio y se despliega en Linux, así que se
// normaliza después de compilar: el artefacto es idéntico en todas partes.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, relative } from 'node:path'

const DIST = join(process.cwd(), 'dist')
const TEXTUAL = /\.(html|css|js|mjs|json|map|svg|txt|xml)$/i

let tocados = 0

function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full)
      continue
    }
    if (!TEXTUAL.test(entry.name)) continue

    const original = readFileSync(full, 'utf8')
    const normalizado = original.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    if (normalizado !== original) {
      writeFileSync(full, normalizado, 'utf8')
      tocados += 1
      console.log('  normalizado:', relative(process.cwd(), full))
    }
  }
}

walk(DIST)
console.log(`dist normalizado (${tocados} fichero(s))`)
