#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Batocera System Manager — Script de instalación
#  Ejecutar como root en Batocera v43+
# ═══════════════════════════════════════════════════════════════

set -e
INSTALL_DIR="/userdata/system/batocera_web"
SERVICE_SCRIPT="/userdata/system/custom.sh"

echo ""
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║   Batocera System Manager — Instalador   ║"
echo "  ╚═══════════════════════════════════════════╝"
echo ""

# 1. Verificar Python
echo "→ Verificando Python..."
python3 --version || { echo "✖ Python3 no encontrado"; exit 1; }

# 2. Instalar Pillow (opcional — logos placeholder)
echo "→ Instalando Pillow (opcional, para logos placeholder)..."
PIP="python3 -m pip"

if ! python3 -m pip --version &>/dev/null; then
    echo "  pip no disponible, intentando via ensurepip..."
    python3 -m ensurepip --upgrade 2>/dev/null || true
fi

if python3 -m pip --version &>/dev/null; then
    $PIP install pillow --break-system-packages -q 2>/dev/null || \
    $PIP install pillow -q || true
    echo "  ✔ Pillow disponible" 2>/dev/null || echo "  ℹ  Pillow no instalado (no crítico)"
fi

# 3. Crear directorio de instalación
echo "→ Creando directorio: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/templates"

# 4. Copiar archivos
echo "→ Copiando archivos..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/app.py" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/templates/" "$INSTALL_DIR/"
echo "  ✔ Archivos copiados a $INSTALL_DIR"

# 5. Crear/actualizar custom.sh para inicio automático
echo "→ Configurando inicio automático..."
SERVICE_MARKER="# [batocera-manager]"
SERVICE_TAG_END="# [/batocera-manager]"
SERVICE_CMD="python3 $INSTALL_DIR/app.py"

if [ -f "$SERVICE_SCRIPT" ]; then
    if grep -q "$SERVICE_MARKER" "$SERVICE_SCRIPT" 2>/dev/null; then
        echo "  ℹ  custom.sh ya tiene el bloque de autostart"
    else
        echo "" >> "$SERVICE_SCRIPT"
        echo "$SERVICE_MARKER" >> "$SERVICE_SCRIPT"
        echo "$SERVICE_CMD &" >> "$SERVICE_SCRIPT"
        echo "$SERVICE_TAG_END" >> "$SERVICE_SCRIPT"
        echo "  ✔ Bloque de autostart agregado a custom.sh"
    fi
else
    cat > "$SERVICE_SCRIPT" << EOF
#!/bin/bash
$SERVICE_MARKER
$SERVICE_CMD &
$SERVICE_TAG_END
EOF
    chmod +x "$SERVICE_SCRIPT"
    echo "  ✔ custom.sh creado"
fi

# 6. Obtener IP
IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}')

echo ""
echo "  ════════════════════════════════════════════"
echo "  ✅  Instalación completada"
echo ""
echo "  Para iniciar ahora mismo:"
echo "  python3 $INSTALL_DIR/app.py &"
echo ""
echo "  Accede desde el navegador:"
echo "  → http://localhost:5000"
[ -n "$IP" ] && echo "  → http://$IP:5000  (desde tu red local)"
echo ""
echo "  Arranca automáticamente en el próximo reinicio."
echo "  ════════════════════════════════════════════"
echo ""
