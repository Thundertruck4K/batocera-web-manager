# Sidebar Redesign + Palette Refinement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refinar la paleta oscura (`:root`) en toda la app y rediseñar el sidebar (iconos SVG Lucide, item activo estilo "cristal + borde acento", separadores de sección) sin tocar `app.py` ni la API.

**Architecture:** Todo el cambio vive en `templates/index.html` (CSS embebido + markup del sidebar). No se añade JS ni dependencias. La lógica de navegación (`showPanel`) queda intacta; solo cambian el CSS del sidebar y los `<span class="icon">emoji</span>` → `<svg>` inline.

**Tech Stack:** HTML/CSS/JS vanilla, single-file SPA. Python 3 stdlib (`http.server`) para servir. `pytest` + `node --check` como verificación.

**Spec:** `docs/superpowers/specs/2026-10-16-sidebar-redesign-design.md`
**Referencia visual (iconos exactos, Variante C):** `docs/superpowers/specs/2026-10-16-sidebar-mockup.html`

## Global Constraints

- Solo stdlib de Python; sin dependencias nuevas (ni CDN ni webfonts).
- No romper rutas `/api/*` ni el contrato JSON.
- No tocar `app.py`.
- `python _jscheck.py; node --check _extracted.js` sin errores.
- `python -m pytest` verde (suite actual 95; subirá con los tests nuevos).
- `python -m py_compile app.py` sin salida.
- Mantener intacto el bloque `<!-- >>> UI-HELPERS ... <<< UI-HELPERS -->` (lo extrae `tests/test_systems_ui.py`).
- Conservar las clases `sidebar`, `nav`, `nav-item`, `nav-section-label`, `nav-badge`, `sidebar-footer`, `theme-chip` y los `onclick="showPanel('<id>',this)"` en el `<button>`.
- Tras el cambio, el sidebar **no contiene emojis**.
- Paleta: se mantienen los tonos de identidad (mismos hues); solo se refina el contraste.

## Review Focus

- `showPanel` debe seguir dejando **una sola** `.nav-item.active` (quitar en todas, poner en `btn`).
- Los `nav-badge` (`badge-count`, `badge-roms`, `badge-biosmissing`) deben seguir presentes y con sus `id`.
- Contraste de texto **fuera del sidebar** (paneles/tarjetas) no debe degradarse al refinar `:root`.
- El logo `<h1>` con SVG no debe romper la alineación del `.sidebar-logo`.
- Los emojis de la **topbar** (`panelMeta`) quedan **fuera** de alcance: no deben tocarse.

---

### Task 1: Refinar la paleta `:root` (app completa)

**Files:**
- Create: `tests/test_theme_contrast.py`
- Modify: `templates/index.html:10-40` (bloque `:root`)

**Interfaces:**
- Consumes: nada (primera tarea).
- Produces: variables `:root` refinadas; en concreto `--text3` pasa a `#868fb2`. El resto de variables conservan su nombre y hue. Las tareas siguientes asumen los NOMBRES actuales (`--accent`, `--accent2`, `--border`, `--bg3`, etc.).

- [ ] **Step 1: Escribir el test de contraste (falla hoy)**

Crea `tests/test_theme_contrast.py`. Comprueba WCAG AA (ratio ≥ 4.5) de `--text2` y `--text3` frente a `--bg` **y** `--panel`.

```python
from __future__ import annotations
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

def _root_var(name: str) -> str:
    css = HTML.read_text(encoding="utf-8")
    m = re.search(rf"--{name}\s*:\s*(#[0-9a-fA-F]{{6}})", css)
    assert m, f"variable --{name} no encontrada"
    return m.group(1)

def _luminance(hexcolor: str) -> float:
    r, g, b = (int(hexcolor[i:i+2], 16) / 255 for i in (1, 3, 5))
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def _contrast(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)

@pytest.mark.parametrize("fg", ["text2", "text3"])
@pytest.mark.parametrize("bg", ["bg", "panel"])
def test_text_contrast_meets_wcag_aa(fg: str, bg: str):
    ratio = _contrast(_root_var(fg), _root_var(bg))
    assert ratio >= 4.5, f"--{fg} sobre --{bg}: ratio {ratio:.2f} < 4.5"
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_theme_contrast.py -v`
Expected: FAIL en los casos de `--text3` (ratio ≈ 4.07 sobre `--bg` y ≈ 4.43 sobre `--panel`). `--text2` pasa.

- [ ] **Step 3: Refinar `--text3` en el bloque `:root`**

En `templates/index.html`, cambia únicamente la línea de `--text3`:

```css
  --text3:#868fb2;
```

(Valor medido: ratio ≈ 5.5 sobre `--bg` y ≈ 5.0 sobre `--panel`.) No cambies el resto de la paleta salvo que un caso siga en rojo.

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_theme_contrast.py -v`
Expected: 4 passed.

- [ ] **Step 5: No romper nada más**

Run: `python _jscheck.py; node --check _extracted.js` → sin errores.
Run: `python -m pytest` → suite completa verde.
Run: `python -m py_compile app.py` → sin salida.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html tests/test_theme_contrast.py
git commit -m "feat(ui): refinar contraste de la paleta oscura a WCAG AA"
```

---

### Task 2: Rediseño del sidebar (iconos SVG + item activo Variante C)

**Files:**
- Create: `tests/test_sidebar_ui.py`
- Modify: `templates/index.html` — sidebar markup (~570-612) y CSS del sidebar (~55-113)

**Interfaces:**
- Consumes: nombres de variables de Task 1 (`--accent`, `--accent2`, `--border`, `--bg3`, `--text2`, `--text3`).
- Produces: sidebar con 8 `<button class="nav-item" ...>` cada uno conteniendo un `<svg>`; logo con `<svg>`; sin `span.icon`; CSS `.nav-item.active` (Variante C), `.nav-item svg`, `.nav-section-label::after`.

- [ ] **Step 1: Escribir los tests de estructura del sidebar (fallan hoy)**

Crea `tests/test_sidebar_ui.py`. Extrae el bloque entre `<aside class="sidebar">` y `</aside>`.

```python
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

_SIDEBAR_RE = re.compile(r'<aside class="sidebar">([\s\S]*?)</aside>')
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002190-\U000021FF\U00002B00-\U00002BFF]"
)

def _sidebar() -> str:
    html = HTML.read_text(encoding="utf-8")
    m = _SIDEBAR_RE.search(html)
    assert m, "no se encontró <aside class=\"sidebar\">"
    return m.group(1)

def test_eight_nav_items_with_svg_icons():
    s = _sidebar()
    assert len(re.findall(r'class="nav-item', s)) == 8
    assert len(re.findall(r"<svg", s)) >= 8, "cada item debe tener un icono SVG"
    assert '<span class="icon">' not in s, "no deben quedar iconos emoji"

def test_nav_items_keep_showpanel_handlers():
    s = _sidebar()
    for pid in ["dashboard", "add", "list", "themes", "preview", "roms", "biosmissing", "settings"]:
        assert f"showPanel('{pid}',this)" in s, f"falta handler showPanel('{pid}')"

def test_sidebar_has_four_sections_and_no_emoji():
    s = _sidebar()
    for label in ["Principal", "Visual", "Contenido", "Sistema"]:
        assert label in s, f"falta la sección {label}"
    assert not _EMOJI_RE.search(s), "el sidebar no debe contener emojis"

def test_badges_kept():
    s = _sidebar()
    for bid in ["badge-count", "badge-roms", "badge-biosmissing"]:
        assert f'id="{bid}"' in s, f"falta el badge {bid}"

def test_showpanel_still_toggles_single_active():
    js = HTML.read_text(encoding="utf-8")
    m = re.search(r"function showPanel\(name, btn\)\s*\{([\s\S]*?)\n\}", js)
    assert m, "falta showPanel"
    body = m.group(1)
    assert ".nav-item" in body and "remove('active')" in body and "add('active')" in body

def test_active_item_uses_accent_gradient_and_border():
    css = HTML.read_text(encoding="utf-8")
    m = re.search(r"\.nav-item\.active\s*\{([^}]*)\}", css, re.S)
    assert m, "falta la regla .nav-item.active"
    body = m.group(1)
    assert "gradient" in body and "border" in body, "Variante C: gradiente + borde acento"
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `python -m pytest tests/test_sidebar_ui.py -v`
Expected: FAIL (hoy hay `<span class="icon">emoji</span>`, 0 `<svg>`, emojis presentes, y `.nav-item.active` es un relleno plano sin gradiente/borde).

- [ ] **Step 3: Sustituir los iconos del sidebar por SVG inline**

Copia **exactamente** el markup `<svg>...</svg>` de cada item desde la sección **Variante C** de `docs/superpowers/specs/2026-10-16-sidebar-mockup.html` y reemplaza el `<span class="icon">…</span>` correspondiente dentro de cada `<button class="nav-item">`. Mapa item → icono:

| Item | Icono |
|------|-------|
| Dashboard | `layout-dashboard` |
| Agregar Sistema | `plus-circle` |
| Sistemas Creados | `list` |
| Temas & Assets | `palette` |
| Vista Previa XML | `eye` |
| ROMs & BIOS | `gamepad-2` |
| BIOS Faltante | `puzzle` |
| Configuración | `settings` |

Atributos comunes de cada `<svg>`: `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"`. **No** cambies el `onclick` ni el `<span class="nav-badge">` de cada botón.

- [ ] **Step 4: Reemplazar el emoji del logo por SVG**

En `<h1>🕹️ Batocera Manager</h1>` sustituye el emoji por un `<svg>` inline `gamepad-2` (mismos atributos comunes, color heredado del `color:var(--accent)` del `h1`):

```html
<h1><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="11" x2="10" y2="11"/><line x1="8" y1="9" x2="8" y2="13"/><line x1="15" y1="12" x2="15.01" y2="12"/><line x1="18" y1="10" x2="18.01" y2="10"/><rect x="2" y="6" width="20" height="12" rx="6"/></svg> Batocera Manager</h1>
```

- [ ] **Step 5: Aplicar el CSS del sidebar (Variante C)**

Ajusta las reglas del sidebar en `templates/index.html`:

```css
.nav-item svg{width:17px;height:17px;flex:none;stroke-width:2;opacity:.92}
.nav-section-label{position:relative}
.nav-section-label::after{content:"";flex:1;height:1px;margin-left:8px;
  background:linear-gradient(90deg,var(--border),transparent)}
.nav-item.active{
  background:linear-gradient(135deg,rgba(110,168,254,.18),rgba(74,118,212,.06));
  color:#fff;border:1px solid rgba(110,168,254,.45);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06), 0 6px 16px -8px rgba(110,168,254,.6);
}
```

Notas:
- `.nav-section-label` debe poder alojar el `::after` (es un flex o se convierte en uno con `display:flex;align-items:center`).
- Para evitar saltos al activar, deja el borde reservado en el estado normal: `.nav-item{border:1px solid transparent}`.
- Sustituye la regla actual `.nav-item.active{background:var(--accent2);color:#fff}`.
- Mantén `transition:all var(--transition)` (0.18s) ya existente.

- [ ] **Step 6: Ejecutar y verificar que pasa**

Run: `python -m pytest tests/test_sidebar_ui.py -v`
Expected: 6 passed.

- [ ] **Step 7: No romper nada más**

Run: `python _jscheck.py; node --check _extracted.js` → sin errores.
Run: `python -m pytest` → suite completa verde (incluye `test_systems_ui.py`).

- [ ] **Step 8: Commit**

```bash
git add templates/index.html tests/test_sidebar_ui.py
git commit -m "feat(ui): rediseñar el sidebar con iconos SVG y estado activo acentuado"
```

---

### Task 3: Verificación visual end-to-end y documentación

**Files:**
- Modify: `AGENTS.md` (conteo de tests)
- Modify: `MEMORY.md` (changelog)
- Verify: `templates/index.html` servido en `:5000`

**Interfaces:**
- Consumes: sidebar rediseñado (Task 2) y paleta refinada (Task 1).
- Produces: evidencia de verificación + docs actualizados; commits de la spec/plan/mockup.

- [ ] **Step 1: Suite completa y chequeos estáticos**

Run: `python -m pytest -q` → todo verde (anota el total, p. ej. 95 + 10 = 105).
Run: `python _jscheck.py; node --check _extracted.js` → sin errores.
Run: `python -m py_compile app.py` → sin salida.

- [ ] **Step 2: Recorrido visual en el servidor dev**

Arranca `python app.py` (o el server dev ya activo en `:5000`) y comprueba en el navegador:
1. Sidebar en reposo: 8 items con iconos SVG, 4 etiquetas de sección con separador degradado.
2. Hover sobre un item: fondo `--bg3` + texto claro.
3. Clic en **Configuración**: el item activo muestra gradiente + borde acento + glow; **Dashboard pierde** `.active`; el panel cambia.
4. Paneles **Dashboard**, **ROMs & BIOS** y **Configuración**: el texto secundario/terciario se lee bien (refinamiento app-wide sin regresión).

Captura el sidebar (reposo, hover y activo) para el reporte.

- [ ] **Step 3: Actualizar `AGENTS.md`**

Cambia la línea de tests al número real obtenido (p. ej. `- **Tests**: 104 con \`pytest\` en \`tests/\` ...`).

- [ ] **Step 4: Actualizar `MEMORY.md`**

Añade una entrada de changelog: "Sidebar rediseñado con iconos SVG Lucide + estado activo Variante C; paleta `:root` refinada a WCAG AA (`--text3` → `#868fb2`). Tests nuevos: `test_theme_contrast.py`, `test_sidebar_ui.py`."

- [ ] **Step 5: Commit (docs + referencia visual + spec/plan)**

```bash
git add AGENTS.md MEMORY.md docs/superpowers/
git commit -m "docs(ui): spec, plan y referencia del rediseño del sidebar"
```

- [ ] **Step 6 (OPCIONAL, requiere confirmación del humano): Desplegar**

Solo si el humano lo pide. Usar `_deploy.py deploy` (backup → subida → verificación). El reinicio de EmulationStation es **opt-in** y no forma parte de este plan.
