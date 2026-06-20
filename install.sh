#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Batocera System Manager — Script de instalación
#  Ejecutar como root en Batocera v43+
#  v1.2 — Sin dependencias externas (stdlib Python puro)
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

# 2. Pillow es opcional (para generar placeholders de logos)
echo "→ Pillow opcional — para placeholders de logos..."
if python3 -c "from PIL import Image" 2>/dev/null; then
    echo "  ✔ Pillow ya disponible"
else
    echo "  ℹ  Pillow no instalado (solo afecta generación de logos placeholder)"
    echo "     Para instalarlo: python3 -m pip install pillow --break-system-packages"
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
MARKER="# [batocera-manager]"
CMD="python3 $INSTALL_DIR/app.py --port 5000"

if [ -f "$SERVICE_SCRIPT" ]; then
    if grep -q "$MARKER" "$SERVICE_SCRIPT" 2>/dev/null; then
        echo "  ℹ  Autostart ya configurado en custom.sh"
    else
        cat >> "$SERVICE_SCRIPT" << EOF

$MARKER
$CMD &
# [/batocera-manager]
EOF
        echo "  ✔ Entrada agregada a custom.sh"
    fi
else
    cat > "$SERVICE_SCRIPT" << 'EOF'
#!/bin/bash
# [batocera-manager]
python3 /userdata/system/batocera_web/app.py --port 5000 &
# [/batocera-manager]
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
