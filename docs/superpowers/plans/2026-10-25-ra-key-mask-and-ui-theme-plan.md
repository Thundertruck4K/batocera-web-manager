# Enmascarar la Web API Key de RA + modo claro/oscuro — Plan de implementación

> **Para agentes que ejecutan este plan:** SUB-SKILL REQUERIDA: usa `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de casillas (`- [ ]`) para seguimiento.

**Objetivo:** Que la Web API Key de RetroAchievements nunca se sirva en claro por la API, y que el manager tenga un tema claro con contraste WCAG AA, sin parpadeo al cargar.

**Arquitectura:** Backend stdlib puro (`app.py`): dos helpers de módulo (`mask_ra_api_key`, `public_settings`) y semántica *write-only* de la key en `POST /api/settings`; `render_index()` inyecta `data-theme` en `<html>` para que el tema se pinte sin parpadeo. Frontend de un solo fichero (`templates/index.html`): un bloque CSS `:root[data-theme="light"]` con variables semánticas "glass" que sustituyen a los `rgba(255,255,255,…)` que asumían fondo oscuro, y un script inline en `<head>` que resuelve `auto` antes del primer pintado.

**Stack técnico:** Python 3 stdlib (`http.server`, `json`, `pathlib`), CSS variables, JS inline. Cero dependencias. Tests con `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-25-ra-key-mask-and-ui-theme-design.md`

## Restricciones globales

- Cero dependencias de terceros en el servidor. Solo stdlib de Python 3.
- Todo el CSS/JS va inline en `templates/index.html`; no se añaden ficheros de assets.
- La paleta oscura de `:root` **no se toca**: el tema actual debe quedar idéntico.
- Comentarios y textos de UI en español (convención del repo).
- Los identificadores de UI existentes no se renombran (los tests los extraen por regex).
- El servidor renderiza con sustitución de cadenas `{{variable}}` (`render_index()`).
- Cada tarea termina con un commit.

## Review Focus

Cinco modos de fallo que la spec implica y que ninguna tarea puede dejar sin cubrir:

1. **La máscara se guarda como si fuera la key nueva.** Si el usuario pulsa "Guardar" sin tocar el campo, la key real se pierde y RA deja de funcionar en silencio. → Test: `POST /api/settings` con el valor de `mask_ra_api_key(stored)` conserva la key guardada.
2. **Vaciar el campo no borra la key.** Con semántica write-only, un vacío se lee como "no cambiar"; el usuario se queda sin poder quitar una key caducada. → Test: `POST /api/settings` con `""` deja `ra_api_key == ""`.
3. **Fuga por otro campo.** Si mañana se añade otra credencial (p. ej. `tgdb_apikey`), un enmascarado manual de `ra_api_key` no la protegería. → Test: `public_settings` no deja ningún valor de credencial en claro.
4. **Contraste insuficiente en la paleta clara.** `--text3` es el texto más flojo de la interfaz y el que se lee sobre `--panel`. → Test: ratio ≥ 4.5 para `--text`/`--text2`/`--text3` sobre `--bg`/`--panel`/`--bg3` en claro.
5. **Parpadeo y tema no persistido.** Si `data-theme` no se inyecta desde el servidor, la primera pintura sale siempre oscura aunque el usuario haya elegido claro, y el cambio se pierde al recargar. → Test: `render_index()` produce `data-theme="light"` con `ui_theme="light"`, y el POST persiste el valor.

---

### Task 1: Helpers de enmascarado en el backend

**Ficheros:**
- Modificar: `app.py` (nuevos helpers a nivel de módulo, junto a los demás del área de ajustes)
- Crear: `tests/test_ra_key_mask.py`

**Interfaces:**
- Produce: `mask_ra_api_key(key: str) -> str` — devuelve la máscara legible; `""` si la key está vacía.
- Produce: `public_settings(settings: dict) -> dict` — copia de los ajustes con `ra_api_key` enmascarado y `ra_api_key_set: bool` añadido.

- [ ] **Paso 1: Escribe el test que falla**

Crea `tests/test_ra_key_mask.py`:

```python
"""Tests del enmascarado de la Web API Key de RetroAchievements."""
from __future__ import annotations


def test_mask_empty_key_returns_empty(appmod):
    assert appmod.mask_ra_api_key("") == ""
    assert appmod.mask_ra_api_key(None) == ""


def test_mask_short_key_is_fully_hidden(appmod):
    out = appmod.mask_ra_api_key("abc")
    assert "abc" not in out
    assert out == "•" * 8


def test_mask_long_key_keeps_first_and_last_four(appmod):
    out = appmod.mask_ra_api_key("abcd1234efgh5678")
    assert out.startswith("abcd")
    assert out.endswith("5678")
    assert "1234efgh" not in out


def test_public_settings_masks_key_and_adds_flag(appmod):
    pub = appmod.public_settings({"ra_user": "tester", "ra_api_key": "abcd1234efgh5678"})
    assert pub["ra_user"] == "tester"
    assert pub["ra_api_key_set"] is True
    assert "abcd1234efgh5678" not in pub["ra_api_key"]


def test_public_settings_reports_missing_key(appmod):
    pub = appmod.public_settings({"ra_api_key": ""})
    assert pub["ra_api_key_set"] is False
    assert pub["ra_api_key"] == ""


def test_public_settings_does_not_mutate_input(appmod):
    src = {"ra_api_key": "abcd1234efgh5678"}
    appmod.public_settings(src)
    assert src["ra_api_key"] == "abcd1234efgh5678"


def test_public_settings_hides_every_secret(appmod):
    pub = appmod.public_settings({
        "ra_api_key": "abcd1234efgh5678",
        "tgdb_apikey": "TGDB-SECRET-KEY",
    })
    flat = repr(pub)
    assert "abcd1234efgh5678" not in flat
    assert "TGDB-SECRET-KEY" not in flat
```

- [ ] **Paso 2: Ejecuta el test para verificar que falla**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: FAIL con `AttributeError: module 'app' has no attribute 'mask_ra_api_key'`.

- [ ] **Paso 3: Implementa los helpers en `app.py`**

Añade a nivel de módulo (junto a `load_settings` / `save_settings_to_file`):

```python
# ─── Enmascarado de credenciales ───────────────────────────────────
# La Web API Key de RetroAchievements nunca debe servirse en claro:
# /api/settings es accesible sin autenticación desde la LAN.

def mask_ra_api_key(key):
    """Enmascara una Web API Key dejando reconocer sus extremos."""
    k = (key or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return "•" * 8
    return k[:4] + "•" * 8 + k[-4:]


def public_settings(settings):
    """Copia de los ajustes sin credenciales en claro.

    Solo se exponen las claves conocidas: el fichero de ajustes se edita a
    mano, así que no debe poder inyectar campos extra en la respuesta.
    """
    pub = {k: v for k, v in (settings or {}).items() if k in DEFAULT_SETTINGS}
    key = str(pub.get("ra_api_key") or "")
    pub["ra_api_key_set"] = bool(key.strip())
    pub["ra_api_key"] = mask_ra_api_key(key)
    return pub
```

- [ ] **Paso 4: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: PASS (7 tests).

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_ra_key_mask.py
git commit -m "feat(security): helpers para enmascarar la Web API Key de RetroAchievements"
```

---

### Task 2: `/api/settings` enmascarado y escritura write-only

**Ficheros:**
- Modificar: `app.py` (handler `GET /api/settings` y handler `POST /api/settings`)
- Modificar: `tests/test_ra_key_mask.py`

**Interfaces:**
- Consume: `mask_ra_api_key(key) -> str` y `public_settings(settings) -> dict` (Tarea 1).
- Produce: `GET /api/settings` devuelve `public_settings(s)`; `POST /api/settings` aplica la tabla write-only.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/test_ra_key_mask.py`:

```python
def _post_settings(appmod, monkeypatch, payload, stored):
    """Simula el handler POST /api/settings con una key ya guardada."""
    saved = {}

    def fake_save(data):
        saved.update(data)

    monkeypatch.setattr(appmod, "load_settings", lambda: dict(stored))
    monkeypatch.setattr(appmod, "save_settings_to_file", fake_save)
    appmod.apply_settings_update(payload, dict(stored))
    return saved
```

El helper de arriba presupone una función nueva `apply_settings_update(payload, current) -> dict`
a nivel de módulo, que encapsula la lógica write-only y es testeable sin servidor. Si al
implementarla prefieres la firma `apply_settings_update(payload: dict, current: dict) -> dict`,
ajusta la llamada del test en consecuencia.

Los casos a cubrir:

```python
def test_post_keeps_stored_key_when_mask_is_submitted(appmod, monkeypatch):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    payload = {"ra_api_key": appmod.mask_ra_api_key(stored["ra_api_key"])}
    out = appmod.apply_settings_update(payload, dict(stored))
    assert out["ra_api_key"] == "abcd1234efgh5678"


def test_post_keeps_stored_key_when_key_absent(appmod, monkeypatch):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_user": "otro"}, dict(stored))
    assert out["ra_api_key"] == "abcd1234efgh5678"


def test_post_replaces_key_with_new_value(appmod, monkeypatch):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_api_key": "nueva1234clave5678"}, dict(stored))
    assert out["ra_api_key"] == "nueva1234clave5678"


def test_post_empty_key_clears_stored_key(appmod, monkeypatch):
    stored = {"ra_api_key": "abcd1234efgh5678"}
    out = appmod.apply_settings_update({"ra_api_key": ""}, dict(stored))
    assert out["ra_api_key"] == ""


def test_post_ignores_unknown_keys(appmod, monkeypatch):
    out = appmod.apply_settings_update({"no_existe": "x"}, {"ra_api_key": "abcd1234efgh5678"})
    assert "no_existe" not in out


def test_post_normalises_ui_theme(appmod, monkeypatch):
    assert appmod.apply_settings_update({"ui_theme": "light"}, {})["ui_theme"] == "light"
    assert appmod.apply_settings_update({"ui_theme": "auto"}, {})["ui_theme"] == "auto"
    assert appmod.apply_settings_update({"ui_theme": "futurol"}, {})["ui_theme"] == "dark"
    assert appmod.apply_settings_update({"ui_theme": ""}, {})["ui_theme"] == "dark"
```

- [ ] **Paso 2: Ejecuta los tests para verificar que fallan**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: FAIL con `AttributeError: module 'app' has no attribute 'apply_settings_update'`.

- [ ] **Paso 3: Implementa `apply_settings_update` y conecta los handlers**

Añade a nivel de módulo en `app.py`:

```python
VALID_UI_THEMES = ("dark", "light", "auto")


def normalize_ui_theme(value):
    """Normaliza el tema de interfaz a un valor conocido."""
    t = str(value or "").strip().lower()
    return t if t in VALID_UI_THEMES else "dark"


def apply_settings_update(payload, current):
    """Aplica un POST /api/settings sobre los ajustes actuales.

    La Web API Key es write-only: si no viene se conserva, si viene la máscara
    se conserva, si viene vacía se borra y cualquier otro valor la sustituye.
    """
    current = dict(current or {})
    incoming = {k: v for k, v in (payload or {}).items() if k in DEFAULT_SETTINGS}
    if "ra_api_key" in incoming:
        sent = str(incoming["ra_api_key"] or "").strip()
        stored = str(current.get("ra_api_key") or "").strip()
        if not sent:
            current["ra_api_key"] = ""
        elif sent != mask_ra_api_key(stored):
            current["ra_api_key"] = sent
    for k, v in incoming.items():
        if k == "ra_api_key":
            continue
        current[k] = normalize_ui_theme(v) if k == "ui_theme" else v
    return current
```

En `do_GET`, cambia la rama de ajustes:

```python
        elif path == "/api/settings":
            self.send_json(public_settings(s))
```

En `do_POST`, cambia la rama de ajustes:

```python
        elif path == "/api/settings":
            data = self.read_json()
            current = load_settings()
            updated = apply_settings_update(data, current)
            save_settings_to_file(updated)
            if any(k.startswith("ra_") for k in data):
                _ra_cache.update({"ts": 0, "data": None, "user": ""})
            self.send_json({"ok": True})
```

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: PASS (13 tests).

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_ra_key_mask.py
git commit -m "fix(security): /api/settings enmascara la key de RA y la trata como write-only"
```

---

### Task 3: Frontend — mostrar la máscara y avisar de cómo se borra

**Ficheros:**
- Modificar: `templates/index.html` (campo de la key + `loadRASettings()` + hint)
- Modificar: `tests/test_ra_key_mask.py`

**Interfaces:**
- Consume: `GET /api/settings` ya enmascarado (Tarea 2).
- Produce: hint con id `ra-key-hint` junto al campo de la key.

- [ ] **Paso 1: Escribe el test que falla**

Añade a `tests/test_ra_key_mask.py`:

```python
def test_ra_field_has_hint_element():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="ra-key-hint"' in html


def test_load_ra_settings_shows_masked_hint():
    from pathlib import Path
    html = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text(encoding="utf-8")
    assert "ra_api_key_set" in html, "el hint debe indicar si hay key configurada"
    assert "mask" in html.lower() or "enmascarad" in html.lower()
```

- [ ] **Paso 2: Ejecuta el test para verificar que falla**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: FAIL en `test_ra_field_has_hint_element`.

- [ ] **Paso 3: Implementa el hint y actualiza `loadRASettings()`**

En el bloque de la key (dentro de la card de RetroAchievements), sustituye el bloque:

```html
          <div class="field" style="margin-bottom:14px">
            <label>Web API Key</label>
            <div style="display:flex;gap:8px">
              <input id="set-ra-api-key" type="password" placeholder="••••••••" autocomplete="off" style="flex:1">
              <button class="btn btn-ghost btn-sm" type="button" onclick="toggleRAKey()">👁</button>
            </div>
          </div>
```

por:

```html
          <div class="field" style="margin-bottom:14px">
            <label>Web API Key</label>
            <div style="display:flex;gap:8px">
              <input id="set-ra-api-key" type="password" placeholder="••••••••" autocomplete="off" style="flex:1">
              <button class="btn btn-ghost btn-sm" type="button" onclick="toggleRAKey()">👁</button>
            </div>
            <span class="hint" id="ra-key-hint"></span>
          </div>
```

Y sustituye `loadRASettings()` por:

```javascript
async function loadRASettings() {
  const data = await fetchJson('/api/settings');
  if (!data) return;
  const u = document.getElementById('set-ra-user');
  const k = document.getElementById('set-ra-api-key');
  const e = document.getElementById('set-ra-enabled');
  const hint = document.getElementById('ra-key-hint');
  if (u) u.value = data.ra_user || '';
  // La key llega enmascarada: nunca se expone en claro por la API.
  if (k) k.value = data.ra_api_key || '';
  if (e) e.checked = !!data.ra_enabled;
  if (hint) {
    hint.textContent = data.ra_api_key_set
      ? 'Key guardada (enmascarada). Escribe una nueva para cambiarla, o vacía el campo para borrarla.'
      : 'Sin key guardada. Pega tu Web API Key de retroachievements.org/settings.';
  }
}
```

- [ ] **Paso 4: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_ra_key_mask.py -v`
Esperado: PASS (15 tests).

- [ ] **Paso 5: Commit**

```bash
git add templates/index.html tests/test_ra_key_mask.py
git commit -m "feat(ui): la Web API Key de RA se muestra enmascarada con hint explicativo"
```

---

### Task 4: Paleta clara y variables "glass" en el CSS

**Ficheros:**
- Modificar: `templates/index.html` (bloque `<style>`)
- Crear: `tests/test_ui_theme.py`

**Interfaces:**
- Produce: bloque `:root[data-theme="light"]` con la paleta clara; variables `--glass`, `--glass2`, `--glass-soft`, `--glass2-soft`, `--hover-bg`, `--active-bg`, `--active-fg`, `--chip-hover-bg`, `--chip-hover-fg`, `--badge-bg`, `--badge-fg`, `--spinner-track`, `--spinner-top`, `--grid-line` definidas en ambos bloques.

- [ ] **Paso 1: Escribe el test que falla**

Crea `tests/test_ui_theme.py`:

```python
"""Tests del tema claro/oscuro de la interfaz del manager."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"

GLASS_VARS = [
    "glass", "glass2", "glass-soft", "glass2-soft", "hover-bg", "active-bg",
    "active-fg", "chip-hover-bg", "chip-hover-fg", "badge-bg", "badge-fg",
    "spinner-track", "spinner-top", "grid-line",
]


def _css() -> str:
    return HTML.read_text(encoding="utf-8")


def _block(selector: str) -> str:
    css = _css()
    m = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css)
    assert m, f"no se encontró el bloque {selector}"
    return m.group(1)


def _var(block: str, name: str) -> str:
    m = re.search(rf"--{re.escape(name)}\s*:\s*([^;]+);", block)
    assert m, f"variable --{name} no encontrada en el bloque"
    return m.group(1).strip()


def test_light_block_exists():
    _block(':root[data-theme="light"]')


def test_dark_block_still_exists():
    _block(":root")


def test_glass_vars_defined_in_both_themes():
    dark = _block(":root")
    light = _block(':root[data-theme="light"]')
    for name in GLASS_VARS:
        _var(dark, name)
        _var(light, name)


def test_no_raw_white_overlays_left_outside_theme_blocks():
    """Los rgba(255,255,255,…) de superficies deben pasar por variables."""
    css = _css()
    style = css[css.index("<style>"):css.index("</style>")]
    offenders = []
    for line in style.split("\n"):
        if "rgba(255,255,255" not in line:
            continue
        if any(v in line for v in ("--glass", "--hover-bg", "--active-bg",
                                   "--chip-hover-bg", "--badge-bg",
                                   "--spinner-track", "--grid-line")):
            continue
        # Los efectos del landing viven sobre fondo siempre oscuro.
        if ".fx__" in line:
            continue
        offenders.append(line.strip())
    assert not offenders, "usa variables de tema en vez de rgba(255,255,255,…):\n" + "\n".join(offenders)
```

- [ ] **Paso 2: Ejecuta el test para verificar que falla**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: FAIL en `test_light_block_exists`.

- [ ] **Paso 3: Añade las variables "glass" al bloque oscuro**

Dentro del `:root` existente, después de `--navr:13px;`, añade:

```css
  /* ── Superficies "glass" (dependen del tema) ── */
  --glass:rgba(255,255,255,.06);
  --glass2:rgba(255,255,255,.02);
  --glass-soft:rgba(255,255,255,.04);
  --glass2-soft:rgba(255,255,255,.015);
  --hover-bg:rgba(255,255,255,.055);
  --active-bg:rgba(255,255,255,.085);
  --active-fg:#fff;
  --chip-hover-bg:rgba(255,255,255,.13);
  --chip-hover-fg:#fff;
  --badge-bg:rgba(255,255,255,.2);
  --badge-fg:#fff;
  --spinner-track:rgba(255,255,255,.2);
  --spinner-top:#fff;
  --grid-line:rgba(255,255,255,.12);
```

Y sustituye las occurrences fijas por las variables:

| Original | Nuevo |
|---|---|
| `linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,.015))` (×2) | `linear-gradient(180deg,var(--glass-soft),var(--glass2-soft))` |
| `linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02))` (×6) | `linear-gradient(180deg,var(--glass),var(--glass2))` |
| `.nav-item:hover{background:rgba(255,255,255,.055)` | `.nav-item:hover{background:var(--hover-bg)` |
| `.nav-item.active{background:rgba(255,255,255,.085);color:#fff` | `.nav-item.active{background:var(--active-bg);color:var(--active-fg)` |
| `.nav-item.active .nav-badge{background:rgba(255,255,255,.2);color:#fff}` | `.nav-item.active .nav-badge{background:var(--badge-bg);color:var(--badge-fg)}` |
| `.chip{...background:rgba(255,255,255,.055)` | `.chip{...background:var(--hover-bg)` |
| `.chip-btn:hover{background:rgba(255,255,255,.13);color:#fff}` | `.chip-btn:hover{background:var(--chip-hover-bg);color:var(--chip-hover-fg)}` |
| spinner `border:2px solid rgba(255,255,255,.2)` | `border:2px solid var(--spinner-track)` |
| spinner `border-top-color:#fff` | `border-top-color:var(--spinner-top)` |
| `repeating-linear-gradient(0deg,transparent 0 3px,rgba(255,255,255,…` | `repeating-linear-gradient(0deg,transparent 0 3px,var(--grid-line),…` |

**No tocar** los `rgba(255,255,255,…)` de `.fx__bubble` y `.fx__spark` (fondo del landing
siempre oscuro) ni el `color:#fff` de `.dash-random-ph span` (gradiente propio oscuro).

- [ ] **Paso 4: Añade el bloque de la paleta clara**

Inmediatamente después del bloque `:root{...}`, añade:

```css
/* ── Paleta clara (tema "light" de la web del manager) ── */
:root[data-theme="light"]{
  --bg:#F4F6FB;
  --bg2:#FFFFFF;
  --bg3:#EDF1F8;
  --panel:#FFFFFF;
  --text:#141824;
  --text2:#454E63;
  --text3:#5B6478;
  --accent:#3B5BDB;
  --border:#D8DEEA;
  --green:#14804A;
  --yellow:#8A5D00;
  --red:#C92A2A;
  --purple:#5F3DC4;
  --bg4:#E3E9F4;
  --border2:#C2CBDA;
  --accent2:#3B5BDB;
  --aurora:#0CA5B0;
  --green2:#0E6B3C;
  --red2:#A61E1E;
  --orange:#B25E12;
  --purple2:#7048E3;
  --shadow:0 22px 60px -26px rgba(20,24,36,.35),inset 0 1px 0 rgba(255,255,255,.9);
  /* Superficies "glass" sobre fondo claro */
  --glass:rgba(20,24,36,.035);
  --glass2:rgba(20,24,36,.012);
  --glass-soft:rgba(20,24,36,.025);
  --glass2-soft:rgba(20,24,36,.008);
  --hover-bg:rgba(20,24,36,.045);
  --active-bg:rgba(20,24,36,.07);
  --active-fg:#141824;
  --chip-hover-bg:rgba(20,24,36,.08);
  --chip-hover-fg:#141824;
  --badge-bg:rgba(20,24,36,.14);
  --badge-fg:#141824;
  --spinner-track:rgba(20,24,36,.15);
  --spinner-top:#3B5BDB;
  --grid-line:rgba(20,24,36,.10);
}
```

- [ ] **Paso 5: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: PASS (4 tests).

- [ ] **Paso 6: Commit**

```bash
git add templates/index.html tests/test_ui_theme.py
git commit -m "feat(ui): paleta clara con variables glass dependientes del tema"
```

---

### Task 5: Persistencia del tema e inyección en el HTML

**Ficheros:**
- Modificar: `app.py` (`DEFAULT_SETTINGS`, `render_index()`)
- Modificar: `templates/index.html` (atributos de `<html>`)
- Modificar: `tests/test_ui_theme.py`

**Interfaces:**
- Consume: `normalize_ui_theme(value) -> str` (Tarea 2).
- Produce: `DEFAULT_SETTINGS["ui_theme"] == "dark"`; `render_index()` sustituye `{{ui_theme}}`.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/test_ui_theme.py`:

```python
def test_default_settings_has_ui_theme(appmod):
    assert appmod.DEFAULT_SETTINGS.get("ui_theme") == "dark"


def test_render_index_injects_theme(appmod, monkeypatch, tmp_path):
    tpl = tmp_path / "index.html"
    tpl.write_text('<html lang="es" data-theme="{{ui_theme}}"></html>', encoding="utf-8")
    monkeypatch.setattr(appmod, "Path", lambda p: tpl if str(p).endswith("index.html") else Path(p))
    monkeypatch.setattr(appmod, "load_settings", lambda: {"ui_theme": "light"})
    out = appmod.render_index()
    assert 'data-theme="light"' in out


def test_render_index_falls_back_to_dark(appmod, monkeypatch, tmp_path):
    tpl = tmp_path / "index.html"
    tpl.write_text('<html lang="es" data-theme="{{ui_theme}}"></html>', encoding="utf-8")
    monkeypatch.setattr(appmod, "Path", lambda p: tpl if str(p).endswith("index.html") else Path(p))
    monkeypatch.setattr(appmod, "load_settings", lambda: {"ui_theme": "no-existe"})
    out = appmod.render_index()
    assert 'data-theme="dark"' in out
```

Si `render_index()` no es alcanzable con ese monkeypatch (porque usa otras variables del
template), reescribe el test para extraer solo la lógica de sustitución: extrae el bloque
de `render_index()` con regex y comprueba que contiene `{{ui_theme}}` y que llama a
`normalize_ui_theme`. El criterio es: el HTML servido debe llevar el tema guardado.

- [ ] **Paso 2: Ejecuta los tests para verificar que fallan**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: FAIL (`ui_theme` ausente de `DEFAULT_SETTINGS`).

- [ ] **Paso 3: Implementa la persistencia**

En `app.py`, dentro de `DEFAULT_SETTINGS`, añade:

```python
    # Tema de la interfaz del manager: "dark" | "light" | "auto"
    "ui_theme":      "dark",
```

En `render_index()`, junto a los demás `html.replace(...)`:

```python
        html = html.replace("{{ui_theme}}", normalize_ui_theme(s.get("ui_theme")))
```

En `templates/index.html`, cambia la etiqueta raíz:

```html
<html lang="es" data-theme="{{ui_theme}}" data-theme-mode="{{ui_theme}}">
```

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: PASS (7 tests).

- [ ] **Paso 5: Commit**

```bash
git add app.py templates/index.html tests/test_ui_theme.py
git commit -m "feat(ui): el tema de interfaz se persiste en los ajustes y se inyecta en el HTML"
```

---

### Task 6: Script inline, conmutador del sidebar y selector en Ajustes

**Ficheros:**
- Modificar: `templates/index.html`
- Modificar: `tests/test_ui_theme.py`

**Interfaces:**
- Consume: `POST /api/settings` con `ui_theme` (Tarea 5).
- Produce: `toggleTheme()`, `onUiThemeChange(mode)`, `saveUiTheme(mode)`, botón `#theme-toggle`, selector `#set-ui-theme`.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/test_ui_theme.py`:

```python
def test_html_declares_theme_attribute_and_inline_script():
    css = _css()
    assert 'data-theme="{{ui_theme}}"' in css
    assert "prefers-color-scheme: light" in css


def test_theme_functions_exist():
    css = _css()
    for fn in ("function toggleTheme(", "function onUiThemeChange(",
               "function saveUiTheme(", "function _applyTheme("):
        assert fn in css, f"falta {fn}"


def test_sidebar_has_theme_toggle():
    css = _css()
    m = re.search(r'<aside class="sidebar">([\s\S]*?)</aside>', css)
    assert m
    assert 'id="theme-toggle"' in m.group(1)


def test_settings_has_theme_selector():
    css = _css()
    assert 'id="set-ui-theme"' in css
    for value in ("dark", "light", "auto"):
        assert f'<option value="{value}"' in css
```

- [ ] **Paso 2: Ejecuta los tests para verificar que fallan**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: FAIL en `test_theme_functions_exist`.

- [ ] **Paso 3: Añade el script inline en `<head>`**

Justo después de la línea `<title>Batocera System Manager</title>`, añade:

```html
<script>
// Aplica el tema ANTES del primer pintado para que no haya parpadeo.
// "auto" se resuelve aquí con la preferencia del sistema operativo.
(function(){
  var el = document.documentElement;
  var mode = el.dataset.themeMode || 'dark';
  if (mode === 'auto') {
    var mq = window.matchMedia('(prefers-color-scheme: light)');
    var apply = function(){ el.dataset.theme = mq.matches ? 'light' : 'dark'; };
    apply();
    if (mq.addEventListener) mq.addEventListener('change', apply);
    else if (mq.addListener) mq.addListener(apply);
  }
})();
</script>
```

- [ ] **Paso 4: Añade el conmutador al sidebar**

En el bloque `.sidebar-logo`, después de `<div class="sidebar-badge">Batocera v43+</div>`,
añade:

```html
      <button id="theme-toggle" class="btn btn-ghost btn-sm" type="button"
              onclick="toggleTheme()" title="Cambiar de tema" style="margin-top:10px;width:100%">☀️</button>
```

- [ ] **Paso 5: Añade el selector en Configuración**

En el panel de Configuración, antes de la card de "Rutas de Batocera", añade:

```html
        <!-- ── Tema de la interfaz ── -->
        <div class="card">
          <div class="card-title"><span class="icon">🎨</span>Tema de la interfaz</div>
          <div class="field" style="margin-bottom:14px">
            <label>Modo de color</label>
            <select id="set-ui-theme" onchange="onUiThemeChange(this.value)">
              <option value="dark">Oscuro</option>
              <option value="light">Claro</option>
              <option value="auto">Seguir al sistema</option>
            </select>
            <span class="hint">Se guarda en el manager, así que se aplica igual desde el móvil o el PC.</span>
          </div>
        </div>
```

- [ ] **Paso 6: Añade el JS del tema**

Añade un bloque junto al resto de JS de ajustes:

```javascript
// ─── Tema claro/oscuro ────────────────────────────────────────────
const THEME_VALUES = ['dark', 'light', 'auto'];
let _themeMode = 'dark';

function _applyTheme(mode){
  _themeMode = THEME_VALUES.indexOf(mode) >= 0 ? mode : 'dark';
  const el = document.documentElement;
  el.dataset.themeMode = _themeMode;
  if (_themeMode === 'auto') {
    _resolveAutoTheme();
  } else {
    el.dataset.theme = _themeMode;
  }
  _syncThemeUI();
}

function _resolveAutoTheme(){
  const el = document.documentElement;
  const mq = window.matchMedia('(prefers-color-scheme: light)');
  const apply = function(){ el.dataset.theme = mq.matches ? 'light' : 'dark'; };
  apply();
  if (mq.addEventListener) mq.addEventListener('change', apply);
  else if (mq.addListener) mq.addListener(apply);
}

function _syncThemeUI(){
  const el = document.documentElement;
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    const isLight = el.dataset.theme === 'light';
    btn.textContent = isLight ? '🌙' : '☀️';
    btn.title = isLight ? 'Cambiar a tema oscuro' : 'Cambiar a tema claro';
  }
  const sel = document.getElementById('set-ui-theme');
  if (sel && sel.value !== _themeMode) sel.value = _themeMode;
}

function _initTheme(){
  const el = document.documentElement;
  _themeMode = el.dataset.themeMode || 'dark';
  if (_themeMode === 'auto' && el.dataset.theme !== 'light' && el.dataset.theme !== 'dark') {
    _resolveAutoTheme();
  }
  _syncThemeUI();
}

async function toggleTheme(){
  const next = (document.documentElement.dataset.theme === 'light') ? 'dark' : 'light';
  _applyTheme(next);
  await saveUiTheme(next);
}

async function onUiThemeChange(mode){
  _applyTheme(mode);
  await saveUiTheme(mode);
}

async function saveUiTheme(mode){
  const res = await fetchJson('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ui_theme: mode }),
  });
  if (!res || !res.ok) toast('No se pudo guardar el tema', 'err');
}
```

Llama a `_initTheme()` al arrancar la página (junto al resto de inicializaciones).

- [ ] **Paso 7: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_ui_theme.py -v`
Esperado: PASS (11 tests).

- [ ] **Paso 8: Commit**

```bash
git add templates/index.html tests/test_ui_theme.py
git commit -m "feat(ui): conmutador de tema claro/oscuro y selector en Ajustes"
```

---

### Task 7: Contraste WCAG AA de la paleta clara

**Ficheros:**
- Modificar: `tests/test_theme_contrast.py`

**Interfaces:**
- Consume: los bloques `:root` y `:root[data-theme="light"]` (Tarea 4).

- [ ] **Paso 1: Escribe el test que falla**

En `tests/test_theme_contrast.py`, añade un extractor por bloque y los tests:

```python
def _block(selector: str) -> str:
    css = HTML.read_text(encoding="utf-8")
    m = re.search(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css)
    assert m, f"bloque {selector} no encontrado"
    return m.group(1)


def _block_var(block: str, name: str) -> str:
    m = re.search(rf"--{re.escape(name)}\s*:\s*(#[0-9a-fA-F]{{6}})", block)
    assert m, f"variable --{name} no encontrada en el bloque"
    return m.group(1)


@pytest.mark.parametrize("fg", ["text", "text2", "text3"])
@pytest.mark.parametrize("bg", ["bg", "panel", "bg3"])
def test_light_palette_contrast_meets_wcag_aa(fg: str, bg: str):
    block = _block(':root[data-theme="light"]')
    ratio = _contrast(_block_var(block, fg), _block_var(block, bg))
    assert ratio >= 4.5, f"claro: --{fg} sobre --{bg}: ratio {ratio:.2f} < 4.5"


def test_accent_is_readable_on_light_backgrounds():
    block = _block(':root[data-theme="light"]')
    accent = _block_var(block, "accent")
    for bg in ("bg", "panel", "bg3"):
        ratio = _contrast(accent, _block_var(block, bg))
        assert ratio >= 4.5, f"claro: --accent sobre --{bg}: ratio {ratio:.2f} < 4.5"
```

- [ ] **Paso 2: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_theme_contrast.py -v`
Esperado: PASS (10 tests). Si alguno falla, ajusta los valores de la paleta clara en
`templates/index.html` hasta cumplir 4.5:1.

- [ ] **Paso 3: Ejecuta la suite completa**

Ejecuta: `python -m pytest`
Esperado: toda la suite en verde (336 + los tests nuevos).

- [ ] **Paso 4: Commit**

```bash
git add tests/test_theme_contrast.py
git commit -m "test(ui): contraste WCAG AA de la paleta clara del manager"
```

---

### Task 8: Documentación

**Ficheros:**
- Modificar: `README.md` (API y Roadmap)
- Modificar: `CHANGELOG.md`
- Modificar: `MEMORY.md`

**Interfaces:**
- Consume: el comportamiento final de las Tareas 1-7.

- [ ] **Paso 1: Actualiza el README**

- En la tabla de endpoints, `GET /api/settings` sigue igual, pero añade una nota bajo
  "Seguridad": la Web API Key de RetroAchievements no se sirve en claro; `/api/settings`
  devuelve una máscara y un indicador `ra_api_key_set`.
- En el Roadmap, marca "Autenticación opcional" y "Copia de seguridad y restauración de
  `es_systems_*.cfg`" como pendientes, y **sustituye** "Modo claro/oscuro y temas para la
  propia web" por "Modo claro/oscuro (hecho: tema claro en Ajustes)".
- Añade una línea en "Características" sobre el tema claro/oscuro.

- [ ] **Paso 2: Actualiza el CHANGELOG**

En la sección `## [Unreleased]`, añade:

```markdown
### Added
- Tema claro/oscuro para la web del manager (Ajustes → Tema de la interfaz, con
  opción de seguir al sistema). Se guarda en el servidor, así que se aplica desde
  cualquier dispositivo y no hay parpadeo al cargar.

### Security
- La Web API Key de RetroAchievements ya no se sirve en claro por `/api/settings`:
  se devuelve enmascarada junto con un indicador de si está configurada, y al
  guardar se comporta como write-only (si no tocas el campo, no se pierde).
```

- [ ] **Paso 3: Actualiza el MEMORY.md**

- En "Issues conocidos", el punto 8 (Web API Key en `/api/settings`) pasa a estar
  **resuelto**: reescríbelo indicando que ahora se enmascara y que queda pendiente
  únicamente la autenticación de la API.
- En "Áreas prioritarias", sustituye "Ocultar la Web API Key de RetroAchievements en
  `/api/settings` — pendiente" por "Autenticación de la API (la key ya se enmascara) —
  pendiente".

- [ ] **Paso 4: Ejecuta la suite completa una última vez**

Ejecuta: `python -m pytest`
Esperado: toda la suite en verde.

- [ ] **Paso 5: Commit**

```bash
git add README.md CHANGELOG.md MEMORY.md
git commit -m "docs: tema claro/oscuro y enmascarado de la Web API Key de RetroAchievements"
```
