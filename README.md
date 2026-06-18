# Batocera System Manager Web — v1.0

Interfaz web moderna para gestionar sistemas personalizados en **Batocera v43+**.
Accede desde cualquier navegador en tu red local (PC, celular, tablet).

---

## Características

- **Agregar sistemas** con formulario completo: nombre, slug, rutas, extensiones, emulador, core, plataforma de scraping
- **Subir e instalar logos** directamente al directorio del tema activo
- **Vista previa del XML** antes de escribir cualquier archivo
- **Modo simulación** (dry-run) para ver qué haría sin modificar nada
- **Lista de sistemas creados** con visor de XML y borrado
- **Detección automática** del tema activo
- **Configuración de rutas** ajustable y persistente
- Acceso desde **cualquier dispositivo** en la red (no requiere display)

---

## Instalación rápida

### En Batocera (vía SSH)

```bash
# Conectar por SSH
ssh root@<IP-de-Batocera>
# contraseña por defecto: linux

# Subir los archivos (desde tu PC)
scp -r batocera_web/ root@<IP-Batocera>:/userdata/system/

# En Batocera: instalar
cd /userdata/system/batocera_web
chmod +x install.sh
bash install.sh
```

### Manual (sin script)

```bash
# 1. Instalar dependencias
pip install flask pillow --break-system-packages

# 2. Copiar archivos a un directorio persistente
cp -r batocera_web/ /userdata/system/batocera-manager/

# 3. Ejecutar
python3 /userdata/system/batocera-manager/app.py
```

---

## Uso

### Iniciar el servidor

```bash
python3 app.py
```

Verás:
```
═══════════════════════════════════════════════════════
  Batocera System Manager Web  v1.0
  Abre en tu navegador:
  → http://localhost:5000
  → http://<IP-de-Batocera>:5000  (desde otra PC)
═══════════════════════════════════════════════════════
```

### Acceder

Desde cualquier dispositivo en tu red:
```
http://<IP-de-Batocera>:5000
```

Para ver la IP de Batocera:
```bash
ip addr show | grep "inet "
# o
hostname -I
```

---

## Inicio automático con Batocera

Para que el servidor arranque solo con Batocera, agrega esto a `/userdata/system/custom.sh`:

```bash
#!/bin/bash
python3 /userdata/system/batocera-manager/app.py &
```

El `&` es importante — hace que corra en segundo plano sin bloquear el arranque.

---

## Estructura de archivos

```
batocera_web/
├── app.py              ← Servidor Flask (backend)
├── install.sh          ← Script de instalación automática
├── README.md           ← Este archivo
└── templates/
    └── index.html      ← Interfaz web completa (UI)
```

---

## Cómo funciona por dentro

### XML generado

Cada sistema se escribe en un archivo separado:
```
/userdata/system/configs/emulationstation/es_systems_<slug>.cfg
```

Ejemplo para un sistema "misonsola":
```xml
<?xml version="1.0" encoding="UTF-8"?>
<systemList>
    <system>
        <fullname>Mi Consola Personalizada</fullname>
        <name>misonsola</name>
        <manufacturer>MiFabricante</manufacturer>
        <release>2000</release>
        <hardware>console</hardware>
        <path>/userdata/roms/misonsola</path>
        <extension>.zip .7z .iso</extension>
        <command>python /usr/lib/python3.11/site-packages/configgen/emulatorlauncher.py
                 %CONTROLLERSCONFIG% -system %SYSTEM% -rom %ROM%</command>
        <platform>snes</platform>
        <theme>misonsola</theme>
        <emulators>
            <emulator name="libretro">
                <cores>
                    <core default="true">snes9x</core>
                </cores>
            </emulator>
        </emulators>
    </system>
</systemList>
```

### Logos

El logo se copia a:
```
/userdata/themes/<tema-activo>/<slug>/art/logo.png
```

---

## Notas importantes para Batocera v43

- El `python_path` por defecto es `/usr/lib/python3.11/site-packages/configgen/emulatorlauncher.py` — verifica con `find / -name emulatorlauncher.py 2>/dev/null`
- Los CFG personalizados van en `/userdata/system/configs/emulationstation/` (NO en `/usr/share/`)
- Batocera fusiona todos los `es_systems_*.cfg` al arrancar ES
- Para aplicar cambios: reinicia EmulationStation con `batocera-es-swissknife --restart`
- Los directorios bajo `/userdata/` son persistentes entre reinicios

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| Puerto 5000 ocupado | Edita `app.py`, cambia `port=5000` |
| Flask no encontrado | `pip install flask --break-system-packages` |
| Sistema no aparece en ES | Verifica el XML en "Vista Previa" y reinicia ES |
| Logo no aparece | Revisa la ruta del tema activo en "Configuración" |
| Permission denied al escribir CFG | Ejecutar con `sudo` o verificar permisos de `/userdata` |
