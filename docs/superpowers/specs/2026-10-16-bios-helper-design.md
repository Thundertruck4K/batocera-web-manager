# Diseño: Asistente de BIOS faltantes (legal-primero)

**Fecha:** 2026-10-16
**Proyecto:** 5 de 6
**Estado:** aprobado (el usuario eligió la opción **legal-primero**)

## Objetivo

Ayudar a **subsanar las BIOS faltantes** sin que la app distribuya material con
copyright. Para cada BIOS faltante:

1. **Enlace de búsqueda en GitHub** (prioridad pedida), para que el usuario
   localice el archivo por su cuenta.
2. **Descarga desde una URL que el usuario proporciona** (solo `http`/`https`),
   con verificación de MD5 contra `BIOS_DB`.

La app **no incluye, no sugiere ni aloja** fuentes de BIOS. La responsabilidad de
lo que se descarga es del usuario. Se refuerza con un aviso legal en la UI.

## Decisiones

1. **No hay fuentes empaquetadas.** Solo un enlace de búsqueda y una descarga
   manual desde la URL que el usuario pegue.
2. **Sin dependencias nuevas** (`urllib`, stdlib).
3. **Seguridad:** solo esquemas `http`/`https`; límite de tamaño
   (`MAX_BIOS_DOWNLOAD = 64 MiB`); ruta validada con `safe_path_under` (respeta
   subcarpetas tipo `neocd/neocd_f.rom`); nunca lanza.
4. **Reutiliza lo existente:** `BIOS_DB`, `_check_bios_grouped`, `/api/bios/missing`,
   la tarjeta "🧩 BIOS Faltante" y `setBiosMissingCount`.
5. **Aviso legal** visible en la tarjeta de BIOS.

## Backend (`app.py`)

- `_bios_urlopen(url, timeout=30)` → indirección testeable sobre `urllib.request`.
- `github_bios_search_url(filename)` → URL de búsqueda de código en GitHub
  (`https://github.com/search?q=<file>&type=code`).
- `download_bios_from_url(bios_dir, filename, url, expected_md5s=None, timeout=30)`
  → `{ok, error?, dest, size, md5, md5_valid}`.
- Endpoint `POST /api/bios/fetch` con `{system, file, url}`:
  recoge los md5 esperados de `_get_bios_entries(system)` y llama al descargador.

## Frontend (`templates/index.html`)

En cada ítem de BIOS faltante (`renderMissingBios`), añadir a las acciones:
- `🔎` enlace a `github_bios_search_url(b.file)` (`target="_blank"`).
- `⬇ URL` → `fetchBios(system, file)`: pide la URL con `prompt()`, hace
  `POST /api/bios/fetch`, refresca la lista y avisa del resultado (incluye aviso
  si el MD5 no coincide).
- Aviso legal al pie de la tarjeta.

## Tests (`tests/test_bios_helper.py`)

1. `github_bios_search_url` apunta a GitHub e incluye el nombre del archivo.
2. `download_bios_from_url`: rechaza esquemas no http/https; rechaza traversal;
   escribe el archivo y valida MD5; reporta `md5_valid=False` si no coincide;
   tolera errores de red; aplica el límite de tamaño; respeta subcarpetas.
3. Endpoint `/api/bios/fetch` declarado.
4. UI: `fetchBios`, el enlace a GitHub y el aviso legal.

## Fuera de alcance

- Listas de fuentes persistentes por BIOS (posible mejora futura).
- Descarga automática sin intervención del usuario.
