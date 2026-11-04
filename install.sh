#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Batocera System Manager — Instalador
#  v1.6 — Interfaz React + Tailwind (bundle precompilado) · Python stdlib
#
#  Uso (por SSH, dentro de la propia Batocera):
#     ssh root@batocera
#     git clone https://github.com/Thundertruck4K/batocera-web-manager.git \
#         /userdata/system/batocera_web
#     cd /userdata/system/batocera_web && bash install.sh
#
#  Batocera es Buildroot: no trae gestor de paquetes, así que **ni git
#  ni node vienen de serie**. El instalador los valida al principio:
#  - si están, sigue con la instalación sin preguntar nada;
#  - si faltan, avisa de que es necesario instalarlos y los instala.
#
#  Node es opcional de verdad: el frontend se despliega ya compilado,
#  así que sólo hace falta para recompilar el bundle en la consola.
#  Git sirve para actualizar el manager con «git pull».
#
#  Variables (instalaciones desatendidas y pruebas):
#     BM_BASE_DIR      base de Batocera         (def. /userdata/system)
#     BM_CUSTOM_SH     ruta de custom.sh        (def. $BM_BASE_DIR/custom.sh)
#     BM_PYTHON        intérprete de Python     (def. python3)
#     BM_PORT          puerto del servidor      (def. 5000)
#     BM_AUTOSTART     s / n: responde ya, sin preguntar
#     BM_GIT           auto / install / skip    (def. auto)
#     BM_NODE          auto / install / skip    (def. auto)
#     BM_GIT_DIR       dónde se instala Git     (def. $BM_BASE_DIR/mamba)
#     BM_GIT_BIN_DIR   dónde se enlazan los binarios (def. /usr/bin)
#     BM_NODE_DIR      dónde se instala Node    (def. $BM_BASE_DIR/node)
#     BM_NODE_BIN_DIR  dónde se enlazan los binarios (def. /usr/bin)
#     BM_NODE_VERSION  versión concreta de Node (def. la última LTS)
#     BM_NODE_URL      espejo de nodejs.org     (def. https://nodejs.org/dist)
#     BM_MICROMAMBA_URL    espejo de micromamba (def. https://micro.mamba.pm/api/micromamba)
#     BM_MICROMAMBA_VERSION versión de micromamba (def. 2.10.0)
#     BM_MICROMAMBA_SHA256  sha256 esperado     (def. el de conda-forge)
#     BM_CONDA_CHANNEL canal de conda           (def. conda-forge)
#     NO_COLOR         desactiva el color
# ═══════════════════════════════════════════════════════════════
set -e

BASE_DIR="${BM_BASE_DIR:-/userdata/system}"
INSTALL_DIR="$BASE_DIR/batocera_web"
SERVICE_SCRIPT="${BM_CUSTOM_SH:-$BASE_DIR/custom.sh}"
PYTHON="${BM_PYTHON:-python3}"
PORT="${BM_PORT:-5000}"
MARKER="# [batocera-manager]"
TAG_END="# [/batocera-manager]"
NODE_MARKER="# [batocera-node]"
NODE_TAG_END="# [/batocera-node]"
GIT_MARKER="# [batocera-git]"
GIT_TAG_END="# [/batocera-git]"
# Patrón con el que se localizan los procesos del manager. El punto va
# escapado para que `app.py` no se lea como un comodín.
KILL_PATTERN='python3.*app\.py'
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Git (vía micromamba + conda-forge: Batocera no tiene gestor de paquetes)
GIT_MODE="${BM_GIT:-auto}"
GIT_DIR="${BM_GIT_DIR:-$BASE_DIR/mamba}"
GIT_BIN_DIR="${BM_GIT_BIN_DIR:-/usr/bin}"
GIT_ENV="$GIT_DIR/envs/git"
MICROMAMBA_URL="${BM_MICROMAMBA_URL:-https://micro.mamba.pm/api/micromamba}"
MICROMAMBA_VERSION="${BM_MICROMAMBA_VERSION:-2.10.0}"
CONDA_CHANNEL="${BM_CONDA_CHANNEL:-conda-forge}"
# sha256 de micromamba $MICROMAMBA_VERSION (paquetes de conda-forge, inmutables)
MICROMAMBA_SHA256_LINUX_64="9a97976244929bbae28fb1fae504e74a3e7e6d1932870e3a03321f01b7fbd07b"
MICROMAMBA_SHA256_LINUX_AARCH64="890bc4906e6ab17f1b393f0da21547f75e000078e573a156316ec925b92a4a4c"
MICROMAMBA_SHA256_LINUX_PPC64LE="6a143602e15bbf10b2345d7a8e322af6ffc7c057bec23d0a73382bd93176c2c9"

# Node
NODE_MODE="${BM_NODE:-auto}"
NODE_VERSION="${BM_NODE_VERSION:-}"
NODE_DIR="${BM_NODE_DIR:-$BASE_DIR/node}"
NODE_BIN_DIR="${BM_NODE_BIN_DIR:-/usr/bin}"
NODE_URL="${BM_NODE_URL:-https://nodejs.org/dist}"

# ── Pintura: se apaga sola si la salida no es un terminal ───────
IS_TTY=0
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  IS_TTY=1
  C0=$'\033[0m';  CD=$'\033[2m'   ; CU=$'\033[38;5;51m'; CP=$'\033[38;5;141m'
  CG=$'\033[38;5;84m'; CY=$'\033[38;5;221m'; CR=$'\033[38;5;203m'
else
  C0=''; CD=''; CU=''; CP=''; CG=''; CY=''; CR=''
fi

rule() {   # rule [ancho]
  local n="${1:-56}" s='' i=0
  while [ "$i" -lt "$n" ]; do s="${s}─"; i=$(( i + 1 )); done
  printf '%s' "$s"
}

hdr()  { printf '\n%s  ╭─%s%s\n' "$CP" "$(rule 56)" "$C0"; }
sub()  { printf '%s  │%s  %s\n' "$CP" "$C0" "$1"; }
foot() { printf '%s  ╰─%s %s\n\n' "$CP" "$C0" "$1"; }
ok()   { printf '  %s✔%s %s\n' "$CG" "$C0" "$1"; }
warn() { printf '  %s◌%s %s\n' "$CY" "$C0" "$1"; }
bad()  { printf '  %s✖%s %s\n' "$CR" "$C0" "$1"; }
kv()   { printf '  %s◆%s %-22s %s\n' "$CU" "$C0" "$1" "$2"; }
tip()  { printf '     %s\n' "$1"; }

bar() {    # bar <pct> [ancho]
  local pct="$1" w="${2:-26}" i=0 fill out=''
  fill=$(( pct * w / 100 ))
  while [ "$i" -lt "$w" ]; do
    if [ "$i" -lt "$fill" ]; then out="$out${CU}█"; else out="$out${CD}░"; fi
    i=$(( i + 1 ))
  done
  printf '%s%s' "$out" "$C0"
}

# ── Barra de progreso real de la copia (un tick por fichero) ────
COPIED=0
TOTAL=0
copy_tick() {
  local pct
  pct=$(( COPIED * 100 / TOTAL ))
  if [ "$IS_TTY" = 1 ]; then
    printf '\r     %s  %3d%%  %d/%d   ' "$(bar "$pct")" "$pct" "$COPIED" "$TOTAL"
  fi
}

# ═══════════════════════════════════════════════════════════════
#  Utilidades
# ═══════════════════════════════════════════════════════════════

fetch() {   # fetch <url> <destino>
  local url="$1" dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dest"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$url" -O "$dest"
  else
    return 1
  fi
}

has_block() {   # has_block <marcador> <fin>
  [ -f "$SERVICE_SCRIPT" ] \
    && grep -qF "$1" "$SERVICE_SCRIPT" \
    && grep -qF "$2" "$SERVICE_SCRIPT"
}

# Escribe (o reescribe) un bloque delimitado en custom.sh.
#
# Es idempotente y reescribible a propósito: si el puerto o la ruta cambian,
# el bloque antiguo se quedaría con los datos viejos y la consola arrancaría
# el manager con la configuración anterior.
write_block() {   # write_block <marcador> <fin> <fichero con el bloque>
  local begin="$1" end="$2" blockfile="$3" tmp="$SERVICE_SCRIPT.bwm.$$"
  if has_block "$begin" "$end"; then
    awk -v b="$begin" -v e="$end" -v bf="$blockfile" '
      $0 == b { while ((getline line < bf) > 0) print line; skipping = 1; next }
      skipping && $0 == e { skipping = 0; next }
      !skipping { print }
    ' "$SERVICE_SCRIPT" > "$tmp"
  else
    if [ -f "$SERVICE_SCRIPT" ]; then
      cat "$SERVICE_SCRIPT" > "$tmp"
      printf '\n' >> "$tmp"
    else
      printf '#!/bin/bash\n' > "$tmp"
    fi
    cat "$blockfile" >> "$tmp"
  fi
  mv "$tmp" "$SERVICE_SCRIPT"
  chmod 755 "$SERVICE_SCRIPT" 2>/dev/null || true
}

detect_node_arch() {   # x64 | arm64 | armv7l | armv6l
  case "$(uname -m)" in
    x86_64|amd64)        echo "x64" ;;
    aarch64|arm64)       echo "arm64" ;;
    armv7l|armv7)        echo "armv7l" ;;
    armv6l|armv6)        echo "armv6l" ;;
    *)                   echo "" ;;
  esac
}

detect_conda_platform() {   # linux-64 | linux-aarch64 | linux-ppc64le
  case "$(uname -m)" in
    x86_64|amd64)   echo "linux-64" ;;
    aarch64|arm64)  echo "linux-aarch64" ;;
    ppc64le)        echo "linux-ppc64le" ;;
    *)              echo "" ;;
  esac
}

micromamba_sha256_for() {   # micromamba_sha256_for <plataforma>
  case "$1" in
    linux-64)      echo "$MICROMAMBA_SHA256_LINUX_64" ;;
    linux-aarch64) echo "$MICROMAMBA_SHA256_LINUX_AARCH64" ;;
    linux-ppc64le) echo "$MICROMAMBA_SHA256_LINUX_PPC64LE" ;;
    *)             echo "" ;;
  esac
}

# ═══════════════════════════════════════════════════════════════
#  Git — vía micromamba + conda-forge
#
#  Batocera no tiene gestor de paquetes ni compilador, así que Git se
#  instala con micromamba (un único binario estático) contra el canal
#  conda-forge. micromamba comprueba el sha256 de cada paquete que
#  descarga; el propio micromamba se verifica con el hash fijado aquí.
# ═══════════════════════════════════════════════════════════════

link_git_binary() {
  if [ -w "$GIT_BIN_DIR" ] 2>/dev/null; then
    if ln -sf "$GIT_ENV/bin/git" "$GIT_BIN_DIR/git" 2>/dev/null; then
      ok "Enlazado en $GIT_BIN_DIR/git"
      return 0
    fi
  fi
  warn "No se pudo enlazar en $GIT_BIN_DIR (¿sin permisos?)"
  tip "Añade $GIT_ENV/bin al PATH para usar git."
  return 1
}

# El bloque # [batocera-git] se ejecuta en cada arranque: /usr es un
# overlay que se pierde al reiniciar, así que el enlace hay que
# recrearlo.
write_git_block() {
  local tmp="$SERVICE_SCRIPT.gitblock.$$"
  {
    printf '%s\n' "$GIT_MARKER"
    printf '%s\n' '# Git (opcional) - enlace para actualizar el manager con git pull'
    printf '%s\n' "GIT_HOME=\"$GIT_DIR\""
    printf '%s\n' 'if [ -x "$GIT_HOME/envs/git/bin/git" ]; then'
    printf '%s\n' "  [ -w \"$GIT_BIN_DIR\" ] && ln -sf \"\$GIT_HOME/envs/git/bin/git\" \"$GIT_BIN_DIR/git\" || true"
    printf '%s\n' 'fi'
    printf '%s\n' "$GIT_TAG_END"
  } > "$tmp"
  write_block "$GIT_MARKER" "$GIT_TAG_END" "$tmp"
  rm -f "$tmp"
}

install_git() {
  local platform url tmp mm expected actual

  platform="$(detect_conda_platform)"
  if [ -z "$platform" ]; then
    bad "No hay Git para la arquitectura $(uname -m)."
    tip "Actualiza el manager con el tarball de la release."
    return 1
  fi
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    bad "Necesito curl o wget para descargar Git."
    return 1
  fi

  expected="${BM_MICROMAMBA_SHA256:-$(micromamba_sha256_for "$platform")}"
  if [ -z "$expected" ]; then
    bad "No conozco el sha256 de micromamba para $platform."
    tip "Indícalo con BM_MICROMAMBA_SHA256=<hash> para continuar."
    return 1
  fi

  tmp="$(mktemp -d 2>/dev/null || printf '%s' "/tmp/bwm-mm-$$")"
  mkdir -p "$tmp"
  url="$MICROMAMBA_URL/$platform/$MICROMAMBA_VERSION"

  printf '     %sDescargando micromamba %s…%s\n' "$CD" "$MICROMAMBA_VERSION" "$C0"
  if ! fetch "$url" "$tmp/mm.tar.bz2"; then
    bad "No se pudo descargar $url"
    rm -rf "$tmp"
    return 1
  fi
  actual="$(sha256sum "$tmp/mm.tar.bz2" 2>/dev/null | awk '{ print $1 }')"
  if [ "$actual" != "$expected" ]; then
    bad "sha256 incorrecto: esperaba $expected y obtuve $actual"
    rm -rf "$tmp"
    return 1
  fi
  ok "sha256 verificado"

  if ! tar -xjf "$tmp/mm.tar.bz2" -C "$tmp" bin/micromamba 2>/dev/null \
     && ! tar -xzf "$tmp/mm.tar.bz2" -C "$tmp" bin/micromamba 2>/dev/null; then
    bad "No se pudo descomprimir micromamba"
    rm -rf "$tmp"
    return 1
  fi
  chmod +x "$tmp/bin/micromamba" 2>/dev/null || true
  mm="$tmp/bin/micromamba"

  printf '     %sInstalando Git desde %s…%s\n' "$CD" "$CONDA_CHANNEL" "$C0"
  if ! MAMBA_ROOT_PREFIX="$GIT_DIR/root" "$mm" create -y -p "$GIT_ENV" \
        -c "$CONDA_CHANNEL" git >"$tmp/mm.log" 2>&1; then
    bad "No se pudo instalar Git"
    if [ -f "$tmp/mm.log" ]; then
      tail -n 10 "$tmp/mm.log" 2>/dev/null | while IFS= read -r l; do printf '     %s\n' "$l"; done
    fi
    rm -rf "$tmp"
    return 1
  fi
  # La caché de paquetes ocupa cientos de MB: se va al terminar.
  MAMBA_ROOT_PREFIX="$GIT_DIR/root" "$mm" clean --all --yes >/dev/null 2>&1 || true
  rm -rf "$tmp"

  if [ ! -x "$GIT_ENV/bin/git" ]; then
    bad "Git no quedó instalado en $GIT_ENV"
    return 1
  fi
  link_git_binary || true
  write_git_block
  ok "Git $("$GIT_ENV/bin/git" --version 2>/dev/null | awk '{ print $3 }') instalado"
}

# ═══════════════════════════════════════════════════════════════
#  Node.js (opcional)
# ═══════════════════════════════════════════════════════════════

latest_lts() {   # latest_lts <index.json>  →  vX.Y.Z
  "$PYTHON" - "$1" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)
for entry in data:
    if entry.get("lts"):
        print(entry["version"])
        break
PY
}

link_node_binaries() {
  local b target linked=0
  for b in node npm npx corepack; do
    target="$NODE_DIR/current/bin/$b"
    [ -e "$target" ] || continue
    if [ -w "$NODE_BIN_DIR" ] 2>/dev/null; then
      ln -sf "$target" "$NODE_BIN_DIR/$b" 2>/dev/null && linked=1
    fi
  done
  if [ "$linked" = 1 ]; then
    ok "Binarios enlazados en $NODE_BIN_DIR"
  else
    warn "No se pudo enlazar en $NODE_BIN_DIR (¿sin permisos?)"
    tip "Añade $NODE_DIR/current/bin al PATH para usarlos."
  fi
}

# El bloque # [batocera-node] se ejecuta en cada arranque: /usr es un
# overlay que se pierde al reiniciar, así que los enlaces hay que
# recrearlos. El PATH y las rutas de npm también se dejan persistentes.
write_node_block() {
  local tmp="$SERVICE_SCRIPT.nodeblock.$$"
  {
    printf '%s\n' "$NODE_MARKER"
    printf '%s\n' '# Node.js (opcional) - enlaces y entorno para recompilar el frontend'
    printf '%s\n' "NODE_HOME=\"$NODE_DIR\""
    printf '%s\n' 'if [ -x "$NODE_HOME/current/bin/node" ]; then'
    printf '%s\n' "  [ -w \"$NODE_BIN_DIR\" ] && ln -sf \"\$NODE_HOME/current/bin/node\" \"$NODE_BIN_DIR/node\" || true"
    printf '%s\n' "  [ -w \"$NODE_BIN_DIR\" ] && ln -sf \"\$NODE_HOME/current/bin/npm\" \"$NODE_BIN_DIR/npm\" || true"
    printf '%s\n' "  [ -w \"$NODE_BIN_DIR\" ] && ln -sf \"\$NODE_HOME/current/bin/npx\" \"$NODE_BIN_DIR/npx\" || true"
    printf '%s\n' "  [ -w \"$NODE_BIN_DIR\" ] && ln -sf \"\$NODE_HOME/current/bin/corepack\" \"$NODE_BIN_DIR/corepack\" || true"
    printf '%s\n' '  export PATH="$NODE_HOME/current/bin:$PATH"'
    printf '%s\n' '  export npm_config_prefix="$NODE_HOME/npm-global"'
    printf '%s\n' '  export npm_config_cache="$NODE_HOME/npm-cache"'
    printf '%s\n' 'fi'
    printf '%s\n' "$NODE_TAG_END"
  } > "$tmp"
  write_block "$NODE_MARKER" "$NODE_TAG_END" "$tmp"
  rm -f "$tmp"
}

install_node() {
  local arch dist tarball url tmp expected actual dir

  arch="$(detect_node_arch)"
  if [ -z "$arch" ]; then
    bad "Arquitectura no soportada por Node: $(uname -m)"
    return 1
  fi
  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    bad "Necesito curl o wget para descargar Node"
    return 1
  fi

  tmp="$(mktemp -d 2>/dev/null || printf '%s' "/tmp/bwm-node-$$")"
  mkdir -p "$tmp"

  if [ -z "$NODE_VERSION" ]; then
    printf '     %sBuscando la última LTS…%s\n' "$CD" "$C0"
    if ! fetch "$NODE_URL/index.json" "$tmp/index.json"; then
      bad "No se pudo consultar $NODE_URL/index.json"
      rm -rf "$tmp"
      return 1
    fi
    NODE_VERSION="$(latest_lts "$tmp/index.json")"
    if [ -z "$NODE_VERSION" ]; then
      bad "No se pudo determinar la última LTS de Node"
      rm -rf "$tmp"
      return 1
    fi
  fi

  dist="$NODE_URL/$NODE_VERSION"
  tarball="node-$NODE_VERSION-linux-$arch.tar.gz"
  url="$dist/$tarball"

  # El sha256 se comprueba contra el SHASUMS256.txt oficial: si no cuadra,
  # el tarball no se toca.
  if ! fetch "$dist/SHASUMS256.txt" "$tmp/SHASUMS256.txt"; then
    bad "No se pudo descargar $dist/SHASUMS256.txt"
    rm -rf "$tmp"
    return 1
  fi
  expected="$(awk -v f="$tarball" '{ gsub(/^\*/, "", $2); if ($2 == f) { print $1; exit } }' "$tmp/SHASUMS256.txt")"
  if [ -z "$expected" ]; then
    bad "El sha256 de $tarball no aparece en SHASUMS256.txt"
    rm -rf "$tmp"
    return 1
  fi

  if ! fetch "$url" "$tmp/$tarball"; then
    bad "No se pudo descargar $url"
    rm -rf "$tmp"
    return 1
  fi

  actual="$(sha256sum "$tmp/$tarball" 2>/dev/null | awk '{ print $1 }')"
  if [ "$actual" != "$expected" ]; then
    bad "sha256 incorrecto: esperaba $expected y obtuve $actual"
    rm -rf "$tmp"
    return 1
  fi
  ok "sha256 verificado"

  mkdir -p "$NODE_DIR"
  if ! tar -xzf "$tmp/$tarball" -C "$NODE_DIR"; then
    bad "No se pudo descomprimir $tarball"
    rm -rf "$tmp"
    return 1
  fi
  dir="node-$NODE_VERSION-linux-$arch"
  if [ ! -d "$NODE_DIR/$dir" ]; then
    bad "El tarball no contiene $dir"
    rm -rf "$tmp"
    return 1
  fi
  ln -sfn "$NODE_DIR/$dir" "$NODE_DIR/current"
  mkdir -p "$NODE_DIR/npm-global" "$NODE_DIR/npm-cache"
  rm -rf "$tmp"

  ok "Node $NODE_VERSION instalado en $NODE_DIR/current"
  link_node_binaries
  write_node_block
  ok "Bloque $NODE_MARKER escrito en $SERVICE_SCRIPT"
}

# ═══════════════════════════════════════════════════════════════
#  Validación de utilidades
#
#  Si git y node están, se sigue sin preguntar nada. Si faltan, se
#  avisa de que es necesario instalarlos y se instalan.
# ═══════════════════════════════════════════════════════════════

# Dónde está el git: el del PATH o, si no, el que instaló este mismo
# script. El enlace de /usr/bin se pierde al reiniciar (/usr es un
# overlay), así que el prefijo es la fuente de verdad.
git_bin() {
  local b
  b="$(command -v git 2>/dev/null || true)"
  if [ -z "$b" ] && [ -x "$GIT_ENV/bin/git" ]; then
    b="$GIT_ENV/bin/git"
  fi
  printf '%s' "$b"
}

ensure_git() {
  local bin ver
  bin="$(git_bin)"
  if [ -n "$bin" ] && [ "$GIT_MODE" != "install" ]; then
    ver="$("$bin" --version 2>/dev/null | head -n 1)"
    kv "Git" "✔ ${ver:-instalado} · $bin"
    # Si el git es el nuestro, se deja el bloque escrito: recrea el
    # enlace en cada arranque (/usr es un overlay).
    if [ -x "$GIT_ENV/bin/git" ]; then
      write_git_block
    fi
    return 0
  fi
  if [ -z "$bin" ]; then
    warn "No se encontró git en el sistema: es necesario instalarlo para continuar."
    tip "Git actualiza el manager con «git pull» (si no, descarga el tarball de la release)."
  fi
  if [ "$GIT_MODE" = "skip" ]; then
    warn "Omitida la instalación de git (BM_GIT=skip)"
    return 1
  fi
  if install_git; then
    bin="$(git_bin)"
    if [ -n "$bin" ]; then
      ver="$("$bin" --version 2>/dev/null | head -n 1)"
      kv "Git" "✔ ${ver:-instalado} · $bin"
      return 0
    fi
  fi
  warn "Git no está disponible: el manager funciona igual, pero para actualizarlo"
  tip "tendrás que descargar el tarball de la release."
  return 1
}

# Lo mismo con node: el del PATH o el que instaló el script.
node_bin() {
  local b
  b="$(command -v node 2>/dev/null || true)"
  if [ -z "$b" ] && [ -x "$NODE_DIR/current/bin/node" ]; then
    b="$NODE_DIR/current/bin/node"
  fi
  printf '%s' "$b"
}

ensure_node() {
  local bin ver
  bin="$(node_bin)"
  if [ -n "$bin" ] && [ "$NODE_MODE" != "install" ]; then
    ver="$("$bin" -v 2>/dev/null || true)"
    kv "Node.js" "✔ ${ver:-instalado} · $bin"
    # Si el node es el nuestro, se deja el bloque escrito: recrea los
    # enlaces en cada arranque (/usr es un overlay).
    if [ -x "$NODE_DIR/current/bin/node" ]; then
      write_node_block
    fi
    return 0
  fi
  if [ -z "$bin" ]; then
    warn "No se encontró node en el sistema: es necesario instalarlo para continuar."
    tip "Node sólo hace falta para recompilar el frontend en la consola."
  fi
  if [ "$NODE_MODE" = "skip" ]; then
    warn "Omitida la instalación de node (BM_NODE=skip)"
    return 1
  fi
  if install_node; then
    bin="$(node_bin)"
    if [ -n "$bin" ]; then
      ver="$("$bin" -v 2>/dev/null || true)"
      kv "Node.js" "✔ ${ver:-instalado} · $bin"
      return 0
    fi
  fi
  warn "Node no está disponible: el manager funciona igual (el frontend va compilado),"
  tip "pero no podrás recompilarlo aquí."
  return 1
}

hdr
sub "Batocera System Manager · instalador"
sub "destino: $INSTALL_DIR"
printf '%s  ╰─%s%s\n\n' "$CP" "$(rule 56)" "$C0"

# ── 1 · Python ──────────────────────────────────────────────────
if "$PYTHON" --version >/dev/null 2>&1; then
  PY_VER="$("$PYTHON" --version 2>&1)"
  kv "Python 3" "✔ $PY_VER"
else
  bad "No encuentro '$PYTHON' en el sistema."
  tip "Instálalo o indica la ruta: BM_PYTHON=/ruta/python3 bash install.sh"
  exit 1
fi

# ── 2 · Puerto ───────────────────────────────────────────────────
case "$PORT" in
  ''|*[!0-9]*)
    bad "El puerto '$PORT' no es un número."
    tip "Indica uno válido: BM_PORT=5000 bash install.sh"
    exit 1
    ;;
esac
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  bad "El puerto $PORT está fuera de rango (1-65535)."
  exit 1
fi
if command -v ss >/dev/null 2>&1 && ss -tln 2>/dev/null | grep -q ":$PORT "; then
  warn "El puerto $PORT ya está ocupado por otro servicio"
  tip "Si es el propio manager, se reiniciará al final del instalador."
fi

# ── 3 · Pillow (opcional) ───────────────────────────────────────
if "$PYTHON" -c "from PIL import Image" >/dev/null 2>&1; then
  kv "Pillow (logos)" "✔ disponible"
else
  kv "Pillow (logos)" "◌ no instalado · opcional"
fi

# ── 4 · Utilidades: git y node ───────────────────────────────────
# Si están, se sigue sin preguntar nada. Si faltan, se avisa y se
# instalan (son necesarias para actualizar y recompilar el manager).
GIT_OK=0
NODE_OK=0
ensure_git  || GIT_OK=1
ensure_node || NODE_OK=1
if [ "$GIT_OK" = 0 ] && [ "$NODE_OK" = 0 ]; then
  kv "Utilidades" "✔ git y node listos"
else
  MISSING=""
  [ "$GIT_OK" != 0 ]  && MISSING="git"
  [ "$NODE_OK" != 0 ] && MISSING="${MISSING:+$MISSING, }node"
  kv "Utilidades" "◌ sin $MISSING (el manager funciona igual)"
fi

# ── 5 · Ficheros ────────────────────────────────────────────────
# ¿El proyecto ya vive en su carpeta definitiva? (flujo git clone).
# Se compara la ruta y también el fichero por inodo, para no depender de
# cómo monte el sistema /tmp, /userdata o los symlinks.
IN_PLACE=0
if [ "$SCRIPT_DIR" = "$INSTALL_DIR" ]; then
  IN_PLACE=1
elif [ -f "$SCRIPT_DIR/app.py" ] && [ -f "$INSTALL_DIR/app.py" ] \
     && [ "$SCRIPT_DIR/app.py" -ef "$INSTALL_DIR/app.py" ]; then
  IN_PLACE=1
fi

if [ "$IN_PLACE" = 1 ]; then
  kv "Ficheros" "✔ ya están en su sitio (git clone)"
else
  mkdir -p "$INSTALL_DIR/templates"
  for f in app.py batocera_systems.json; do
    if [ -f "$SCRIPT_DIR/$f" ]; then TOTAL=$(( TOTAL + 1 )); fi
  done
  if [ -d "$SCRIPT_DIR/templates" ]; then
    n=$(find "$SCRIPT_DIR/templates" -type f 2>/dev/null | wc -l | tr -d ' ')
    TOTAL=$(( TOTAL + n ))
  fi
  # Bundle del frontend React: se despliega ya compilado (el dispositivo no tiene Node).
  if [ -d "$SCRIPT_DIR/frontend/dist" ]; then
    n=$(find "$SCRIPT_DIR/frontend/dist" -type f 2>/dev/null | wc -l | tr -d ' ')
    TOTAL=$(( TOTAL + n ))
  fi
  if [ "$TOTAL" -gt 0 ]; then
    printf '  %s◆%s Copiando ficheros\n' "$CU" "$C0"
    for f in app.py batocera_systems.json; do
      if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
        COPIED=$(( COPIED + 1 )); copy_tick
      fi
    done
    if [ -d "$SCRIPT_DIR/templates" ]; then
      while IFS= read -r f; do
        rel="${f#"$SCRIPT_DIR"/}"
        mkdir -p "$INSTALL_DIR/$(dirname "$rel")"
        cp "$f" "$INSTALL_DIR/$rel"
        COPIED=$(( COPIED + 1 )); copy_tick
      done < <(find "$SCRIPT_DIR/templates" -type f)
    fi
    if [ -d "$SCRIPT_DIR/frontend/dist" ]; then
      while IFS= read -r f; do
        rel="${f#"$SCRIPT_DIR"/}"
        mkdir -p "$INSTALL_DIR/$(dirname "$rel")"
        cp "$f" "$INSTALL_DIR/$rel"
        COPIED=$(( COPIED + 1 )); copy_tick
      done < <(find "$SCRIPT_DIR/frontend/dist" -type f)
    fi
    if [ "$IS_TTY" = 1 ]; then printf '\r\033[K'; fi
    ok "Ficheros copiados a $INSTALL_DIR"
  else
    warn "No encuentro app.py junto a este instalador"
  fi
fi

# ── 6 · Arranque automático ─────────────────────────────────────
# La ruta se entrecomilla sólo si lo necesita, igual que hace shlex.quote
# en el backend: así el bloque escrito aquí y el que escribe la web se
# parecen.
APP_PATH="$INSTALL_DIR/app.py"
case "$APP_PATH" in
  *[!A-Za-z0-9_./-]*) APP_PATH_Q="\"$APP_PATH\"" ;;
  *)                   APP_PATH_Q="$APP_PATH" ;;
esac
CMD="$PYTHON $APP_PATH_Q --port $PORT"

ANSWER=''
if [ -n "${BM_AUTOSTART:-}" ]; then
  ANSWER="$BM_AUTOSTART"
elif [ -t 0 ]; then
  printf '\n  %s¿Añadir el manager al inicio de Batocera?%s\n' "$CY" "$C0"
  tip "Así se levanta solo cada vez que enciendes la consola."
  printf '  %s[S]í / [n]o:%s ' "$CY" "$C0"
  read -r ANSWER || ANSWER=''
else
  warn "Sin terminal interactiva: no toco el arranque automático"
fi

AUTO=0
# limpiar espacios y retornos de carro (SSH, piped input, BM_AUTOSTART)
ANSWER="${ANSWER//[$'\r\n\t ']/}"
case "$ANSWER" in
  s|S|si|sí|Si|Sí|y|Y|yes|YES) AUTO=1 ;;
  *) AUTO=0 ;;
esac

if [ "$AUTO" = 1 ]; then
  # El bloque se reescribe siempre: si ya existía con otro puerto u otra
  # ruta, se queda con los datos viejos y la consola arrancaría el
  # manager como estaba antes.
  BLOCK_FILE="$(mktemp 2>/dev/null || printf '%s' "/tmp/bwm-block-$$")"
  {
    printf '%s\n' "$MARKER"
    printf '%s\n' '# Batocera System Manager Web - arranque automatico'
    printf '%s\n' "pkill -f \"$KILL_PATTERN\" 2>/dev/null || true"
    printf '%s\n' "$CMD &"
    printf '%s\n' "$TAG_END"
  } > "$BLOCK_FILE"
  write_block "$MARKER" "$TAG_END" "$BLOCK_FILE"
  rm -f "$BLOCK_FILE"
  kv "Arranque automático" "✔ bloque en $SERVICE_SCRIPT"

  # Si ya había una instancia corriendo se para: si no, seguiría
  # sirviendo el código de antes de la actualización.
  if command -v pkill >/dev/null 2>&1; then
    if pgrep -f "$KILL_PATTERN" >/dev/null 2>&1; then
      pkill -f "$KILL_PATTERN" 2>/dev/null || true
      sleep 1
      ok "Instancia anterior detenida"
    fi
  fi
  nohup $CMD >/dev/null 2>&1 &
  ok "Arrancado ahora mismo en el puerto $PORT"
else
  warn "Arranque automático NO configurado"
  tip "Arranca el manager a mano cuando lo necesites:"
  printf '     %s%s%s\n' "$CU" "$CMD" "$C0"
  tip "Al entrar en la web te avisaré en Configuración y podrás activarlo con un clic."
fi

foot "Listo. Abre ${CU}http://BATOCERA:$PORT${C0}${CP}"
exit 0
