<div align="center">

# Batocera System Manager Web

**v1.2** — Interfaz web para gestionar sistemas personalizados en **Batocera v43+**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Dependencias](https://img.shields.io/badge/dependencias-stdlib%20(Python%20puro)-0d1117)]()

**Sin dependencias externas** — solo usa la librería estándar de Python.  
Accede desde cualquier navegador en tu red local (PC, celular, tablet).

</div>

---

## ✨ Características

- **🕹️ Gestor de sistemas** — Crear, editar y eliminar sistemas personalizados para EmulationStation con formulario completo
- **🔍 Scraper multi-fuente** — ScreenScraper.fr (devid opcional), TheGamesDB, IGDB (Twitch)
- **🖼️ Scraping estilo Batocera** — Imágenes guardadas en `images/<rom>-image|box|wheel|fanart…` como EmulationStation espera
- **🔐 Subidas seguras** — Validación de extensión por sistema (es_systems.cfg) y BIOS en subcarpetas correctas
- **📊 Dashboard** — Monitor en vivo de CPU, GPU, RAM, disco, red, temperatura, procesos
- **📁 Explorador de ROMs** — Navegar, buscar, renombrar, subir y eliminar ROMs
- **🔬 Verificación de BIOS** — Chequea integridad MD5 de tus BIOS
- **🖼️ Subida de logos** — Placeholder automático o subida manual al tema activo
- **📄 Vista previa XML** — Modo simulación (dry-run) antes de escribir
- **🚀 Gestor de autostart** — Instalar/desinstalar/reiniciar servicio en custom.sh
- **⚙️ Configuración persistente** — Rutas ajustables guardadas en JSON

---

## 📦 Instalación

### En Batocera (vía SSH)

```bash
# Conectar por SSH
ssh root@<IP-de-Batocera>
# contraseña por defecto: linux

# Subir los archivos (desde tu PC)
scp -r batocera_web/ root@<IP-Batocera>:/userdata/system/

# En Batocera: ejecutar
cd /userdata/system/batocera_web
python3 app.py
```

### Iniciar con puerto personalizado

```bash
python3 app.py --port 5001
```

### Pillow (opcional)

Para generar placeholders de logos automáticos:
```bash
python3 -m pip install pillow --break-system-packages
```

---

## 🚀 Uso

```
http://<IP-de-Batocera>:5000
```

Verás el dashboard con información del sistema. Navegación lateral con:

| Panel | Descripción |
|-------|-------------|
| 📊 Dashboard | Monitor de sistema en vivo |
| ➕ Agregar Sistema | Formulario para nuevo sistema personalizado |
| 📋 Sistemas | Lista de sistemas creados |
| 📁 ROMs | Explorador de ROMs por sistema |
| 🎨 Temas | Gestión de temas y logos |
| ⚙ Configuración | Rutas y autostart |
| 🔍 Scraper | Búsqueda y descarga de metadatos |

---

## 🔧 Configuración

Las rutas por defecto (pueden ajustarse desde el panel de configuración):

| Ruta | Propósito |
|------|-----------|
| `/userdata/roms/` | Base de ROMs |
| `/userdata/system/configs/emulationstation/` | CFG de sistemas personalizados |
| `/userdata/themes/` | Temas de usuario |
| `/userdata/system/batocera.conf` | Configuración principal |
| `/userdata/bios/` | Archivos BIOS |

Los settings se guardan en `/userdata/system/batocera_manager_settings.json`.

---

## 🧱 Estructura del proyecto

```
batocera_web/
├── app.py                  # Backend: servidor HTTP + API REST + scraper + dashboard
├── templates/
│   └── index.html          # Frontend SPA (todo el HTML/CSS/JS inline)
├── AGENTS.md               # Guía para asistentes de IA
├── install.sh              # Script de instalación (heredado)
├── LICENSE                 # Licencia MIT
└── README.md               # Este archivo
```

---

## 📡 API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/info` | Info del sistema (temas, plataformas) |
| `GET` | `/api/systems` | Lista sistemas personalizados |
| `GET` | `/api/themes` | Tema activo y lista de temas |
| `GET` | `/api/settings` | Configuración de rutas |
| `POST` | `/api/settings` | Guardar configuración |
| `GET` | `/api/rom-systems` | Lista sistemas con ROMs |
| `GET` | `/api/dashboard` | Dashboard completo |
| `GET` | `/api/fans` | Estado de ventiladores (RPM, fallos) desde hwmon |
| `GET` | `/api/news` | Noticias RSS de emulación en español (cache 30 min) |
| `POST` | `/api/create` | Crear sistema (soporta dry-run) |
| `DELETE` | `/api/system/<slug>` | Eliminar sistema |
| `POST` | `/api/scraper/search` | Buscar juego en scraper |
| `POST` | `/api/scraper/download` | Descargar metadatos e imagen |
| `POST` | `/api/scraper/scrape-system` | Scrapear sistema completo |

Respuestas en JSON. Ver `app.py` para documentación detallada de endpoints.

### Notas del scraper ScreenScraper.fr

ScreenScraper exige un **Dev ID / Dev Password** de desarrollador en todas las llamadas a su API v2 (la cuenta normal no sirve). Batocera incrusta los suyos en el binario; este gestor permite añadir los tuyos (opcionales) en `Configuración → Scraper`. Sin ellos, se recomienda usar **TheGamesDB** o **IGDB** (ambas ya funcionan).

Las imágenes se guardan siguiendo el layout de Batocera (`images/<rom>-image.png`, `-box`, `-wheel`, `-marquee`, `-fanart`, `videos/<rom>-video`, etc.) y el gamelist.xml apunta con rutas relativas `./images/...`.

---

## 🗺️ Roadmap

- [ ] Autenticación básica opcional
- [ ] Scraping batch programable
- [ ] Modo multiusuario
- [ ] Exportar/importar configuración
- [ ] Soporte para más fuentes de scraping

---

## 📝 Licencia

MIT © 2024 — Ver archivo [LICENSE](LICENSE).

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor abre un issue o PR en GitHub.

---

<div align="center">
<sub>Hecho para la comunidad de Batocera · Sin Flask · Sin complicaciones</sub>
</div>
