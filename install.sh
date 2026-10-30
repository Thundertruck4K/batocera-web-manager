#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Batocera System Manager — Instalador
#  v1.3 — Sin dependencias externas (Python stdlib)
#
#  Uso (por SSH, dentro de la propia Batocera):
#     ssh root@batocera
#     git clone https://github.com/Thundertruck4K/batocera-web-manager.git \
#         /userdata/system/batocera_web
#     cd /userdata/system/batocera_web && bash install.sh
#
#  Variables (instalaciones desatendidas y pruebas):
#     BM_BASE_DIR   base de Batocera        (def. /userdata/system)
#     BM_CUSTOM_SH  ruta de custom.sh       (def. $BM_BASE_DIR/custom.sh)
#     BM_PYTHON     intérprete de Python    (def. python3)
#     BM_PORT       puerto del servidor     (def. 5000)
#     BM_AUTOSTART  s / n: responde ya, sin preguntar
#     NO_COLOR      desactiva el color
# ═══════════════════════════════════════════════════════════════
set -e

BASE_DIR="${BM_BASE_DIR:-/userdata/system}"
INSTALL_DIR="$BASE_DIR/batocera_web"
SERVICE_SCRIPT="${BM_CUSTOM_SH:-$BASE_DIR/custom.sh}"
PYTHON="${BM_PYTHON:-python3}"
PORT="${BM_PORT:-5000}"
MARKER="# [batocera-manager]"
TAG_END="# [/batocera-manager]"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

# ── 2 · Pillow (opcional) ───────────────────────────────────────
if "$PYTHON" -c "from PIL import Image" >/dev/null 2>&1; then
  kv "Pillow (logos)" "✔ disponible"
else
  kv "Pillow (logos)" "◌ no instalado · opcional"
fi

# ── 3 · Ficheros ────────────────────────────────────────────────
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

# ── 4 · Arranque automático ─────────────────────────────────────
CMD="$PYTHON $INSTALL_DIR/app.py --port $PORT"
ANSWER=''
if [ -n "${BM_AUTOSTART:-}" ]; then
  ANSWER="$BM_AUTOSTART"
elif [ -t 0 ]; then
  printf '\n  %s¿Añadir el manager al inicio de Batocera?%s\n' "$CY" "$C0"
  tip "Así se levanta solo cada vez que enciendas la consola."
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
  if [ -f "$SERVICE_SCRIPT" ] && grep -qF "$MARKER" "$SERVICE_SCRIPT" 2>/dev/null; then
    kv "Arranque automático" "✔ ya estaba configurado"
  else
    printf '\n%s\n%s &\n%s\n' "$MARKER" "$CMD" "$TAG_END" >> "$SERVICE_SCRIPT"
    kv "Arranque automático" "✔ añadido a $SERVICE_SCRIPT"
  fi
  if command -v pgrep >/dev/null 2>&1 && pgrep -f "python3.*app.py" >/dev/null 2>&1; then
    ok "Ya estaba corriendo en el puerto $PORT"
  else
    nohup $CMD >/dev/null 2>&1 &
    ok "Arrancado ahora mismo en el puerto $PORT"
  fi
else
  warn "Arranque automático NO configurado"
  tip "Arranca el manager a mano cuando lo necesites:"
  printf '     %s%s%s\n' "$CU" "$CMD" "$C0"
  tip "Al entrar en la web te avisaré en Configuración y podrás activarlo con un clic."
fi

foot "Listo. Abre ${CU}http://BATOCERA:$PORT${C0}${CP}"
exit 0
