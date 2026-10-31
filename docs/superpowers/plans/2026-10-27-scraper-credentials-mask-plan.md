# Enmascarar las credenciales del scraper — Plan de implementación

> **Para agentes que ejecutan este plan:** SUB-SKILL REQUERIDA: usa `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de casillas (`- [ ]`) para seguimiento.

**Objetivo:** Que la contraseña de ScreenScraper, su credencial de desarrollador y las API keys de TheGamesDB e IGDB no se sirvan en claro por la API, sin romper el guardado ni el scraping.

**Arquitectura:** `get_scraper_config()` sigue leyendo `batocera.conf` y devolviendo las credenciales reales (habla con las APIs externas); el enmascarado se aplica **en el borde HTTP**, en `public_scraper_config()`. La escritura es *write-only*: una máscara nunca se guarda, se conserva lo que ya había. `resolve_scraper_creds()` ignora las máscaras que llegan del cliente, para que la máscara no acabe en ScreenScraper.

**Stack técnico:** Python 3 stdlib, CSS/JS inline. Cero dependencias. `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-27-scraper-credentials-mask-design.md`

## Restricciones globales

- Cero dependencias de terceros en el servidor. Solo stdlib de Python 3.
- `get_scraper_config()` **no** cambia de comportamiento: sigue devolviendo las credenciales reales (la usan `_scraper_search`, `_scraper_download`, `_scraper_system` y `_scraper_batch_create`).
- `GET /api/scraper/batch` y `/api/scraper/batch/<id>` **no** se tocan: ya construyen la respuesta con lista blanca.
- Los campos no secretos (`ss_region`, `ss_lang`, `ss_image_type`, `scraper_source`) no cambian de comportamiento.
- Comentarios y textos de UI en español.
- Cada tarea termina con un commit.

## Review Focus

Cinco modos de fallo que la spec implica y que ninguna tarea puede dejar sin cubrir:

1. **La máscara acaba en la API de ScreenScraper.** Si el navegador manda la máscara y el backend la.mergea sobre la credencial real, el scraping falla con 401. → Test: `resolve_scraper_creds` con una máscara del cliente devuelve la credencial del servidor.
2. **Guardar sin tocar los campos pisa las credenciales.** El frontend siempre manda todos los campos; si la máscara se guardara, `batocera.conf` quedaría con `••••••••` y el scraping dejaría de funcionar. → Test: `save_scraper_config` con una máscara conserva el valor guardado.
3. **Vaciar un campo borra de más.** Si "vacío" significara "borra" sin más, un cliente que no manda la bandera `clear` (o un campo que el usuario nunca tuvo) vaciaría credenciales ajenas. → Test: vacío sin `clear` no toca nada; con `clear: true` borra solo esa clave.
4. **Algún endpoint sigue filtrando.** Hay tres puntos que devuelven la config. → Test: en las respuestas de `GET /api/scraper/config` y `POST /api/scraper/search` no aparece ninguna credencial real.
5. **El frontend rompe el guardado.** Si el formulario se rellena con la máscara y al guardar se manda como credencial, el usuario pierde sus claves. → Test: el JS de guardado manda la máscara tal cual (el backend la ignora) y marca `clear` solo cuando el usuario vació un campo que tenía máscara.

---

### Task 1: Helpers de enmascarado genérico y de la config del scraper

**Ficheros:**
- Modificar: `app.py` (helpers junto a `mask_ra_api_key`)
- Crear: `tests/test_scraper_secrets.py`

**Interfaces:**
- Produce: `mask_secret_value(value) -> str` — genérico; `mask_ra_api_key(key)` delega en él.
- Produce: `SCRAPER_SECRET_FIELDS`, `SCRAPER_SECRET_CONF_KEYS`, `public_scraper_config(cfg) -> dict`.

- [ ] **Paso 1: Escribe el test que falla**

Crea `tests/test_scraper_secrets.py`:

```python
"""Tests del enmascarado de las credenciales del scraper.

Las credenciales del scraper viven en batocera.conf y las lee get_scraper_config()
para hablar con ScreenScraper / TheGamesDB / IGDB. Lo que no debe pasar es que
salgan en claro por la API.
"""
from __future__ import annotations


def test_public_scraper_config_masks_every_credential(appmod):
    cfg = {
        "ss_user": "mi_usuario", "ss_password": "mi_password",
        "ss_devid": "mid", "ss_devpassword": "midevpass",
        "tgdb_apikey": "TGDBKEY", "igdb_client_id": "igdbid",
        "igdb_client_secret": "igdbsecret",
        "ss_region": "wor", "ss_lang": "es",
    }
    pub = appmod.public_scraper_config(cfg)
    flat = repr(pub)
    for secret in ("mi_usuario", "mi_password", "mid", "midevpass",
                   "TGDBKEY", "igdbid", "igdbsecret"):
        assert secret not in flat, f"se filtra {secret}"


def test_public_scraper_config_keeps_non_secret_fields(appmod):
    pub = appmod.public_scraper_config({"ss_region": "eu", "ss_lang": "es",
                                        "ss_image_type": "mixrbv2"})
    assert pub["ss_region"] == "eu"
    assert pub["ss_lang"] == "es"
    assert pub["ss_image_type"] == "mixrbv2"


def test_public_scraper_config_reports_configured_state(appmod):
    pub = appmod.public_scraper_config({"ss_password": "algo", "tgdb_apikey": ""})
    assert pub["ss_password_set"] is True
    assert pub["tgdb_apikey_set"] is False


def test_public_scraper_config_does_not_mutate_input(appmod):
    src = {"ss_password": "secreto"}
    appmod.public_scraper_config(src)
    assert src["ss_password"] == "secreto"


def test_mask_secret_value_hides_short_values_entirely(appmod):
    assert appmod.mask_secret_value("abc") == "•" * 8
    assert appmod.mask_secret_value("") == ""


def test_mask_secret_value_keeps_extremes_of_long_values(appmod):
    out = appmod.mask_secret_value("abcd1234efgh5678")
    assert out.startswith("abcd")
    assert out.endswith("5678")


def test_ra_mask_still_works_through_the_generic_helper(appmod):
    assert appmod.mask_ra_api_key("abcd1234efgh5678") == appmod.mask_secret_value("abcd1234efgh5678")
```

- [ ] **Paso 2: Ejecuta el test para verificar que falla**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: FAIL con `AttributeError: module 'app' has no attribute 'public_scraper_config'`.

- [ ] **Paso 3: Implementa los helpers en `app.py`**

Sustituye el bloque actual de `mask_ra_api_key` por:

```python
# Caracter con el que se dibuja la mascara.
RA_MASK_CHAR = "•"
# Longitud minima a partir de la cual se muestran los extremos del valor.
RA_MASK_MIN_LEN = 12


def mask_secret_value(value):
    """Enmascara un valor sensible dejando reconocer sus extremos.

    Los valores cortos (menos de RA_MASK_MIN_LEN) se ocultan enteras: con un
    umbral de 8, una clave de 9 caracteres se mostraba en 8 de sus 9
    posiciones, es decir, practicamente entera.
    """
    v = str(value or "").strip()
    if not v:
        return ""
    if len(v) < RA_MASK_MIN_LEN:
        return RA_MASK_CHAR * 8
    return v[:4] + RA_MASK_CHAR * 8 + v[-4:]


def mask_ra_api_key(key):
    """Enmascara una Web API Key dejando reconocer sus extremos."""
    return mask_secret_value(key)


def looks_like_ra_mask(value):
    """True si el valor parece una mascara y no una credencial nueva.

    Una mascara nunca es una credencial valida, asi que si llega una se
    conserva la guardada. Comparar con la mascara de la credencial actual no
    basta: si la credencial cambio en otro dispositivo, la mascara que tiene
    aqui seria distinta y se guardaria como si fuera la nueva.
    """
    return RA_MASK_CHAR in str(value or "")
```

Y añade, junto a `get_scraper_config()`:

```python
# Campos de get_scraper_config() que son credenciales: nunca se sirven en claro.
SCRAPER_SECRET_FIELDS = (
    "ss_user", "ss_password", "ss_devid", "ss_devpassword",
    "tgdb_apikey", "igdb_client_id", "igdb_client_secret",
)

# Clave de batocera.conf -> campo de la config del scraper.
SCRAPER_SECRET_CONF_KEYS = {
    "global.scrapper.user":        "ss_user",
    "global.scrapper.password":    "ss_password",
    "global.scrapper.devid":       "ss_devid",
    "global.scrapper.devpassword": "ss_devpassword",
    "global.tgdb.apikey":          "tgdb_apikey",
    "global.igdb.clientid":        "igdb_client_id",
    "global.igdb.clientsecret":    "igdb_client_secret",
}


def public_scraper_config(cfg):
    """Copia de la config del scraper sin credenciales en claro."""
    pub = dict(cfg or {})
    for name in SCRAPER_SECRET_FIELDS:
        val = str(pub.get(name) or "")
        pub[name] = mask_secret_value(val)
        pub[name + "_set"] = bool(val.strip())
    return pub
```

- [ ] **Paso 4: Ejecuta el test para verificar que pasa**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: PASS (7 tests). La suite completa debe seguir en verde (el cambio de
`mask_ra_api_key` no altera su comportamiento).

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_scraper_secrets.py
git commit -m "feat(security): helpers para enmascarar las credenciales del scraper"
```

---

### Task 2: `resolve_scraper_creds` ignora las máscaras del cliente

**Ficheros:**
- Modificar: `app.py` (`resolve_scraper_creds`)
- Modificar: `tests/test_scraper_secrets.py`

**Interfaces:**
- Consume: `looks_like_ra_mask(value)` (Task 1).

- [ ] **Paso 1: Escribe el test que falla**

Añade a `tests/test_scraper_secrets.py`:

```python
def test_resolve_ignores_a_mask_sent_by_the_client(appmod, tmp_path):
    """La mascara del navegador no puede pisar la credencial real."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=real_user\n"
                    "global.scrapper.password=real_password\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    mask = appmod.mask_secret_value("real_password")
    creds = appmod.resolve_scraper_creds(settings, {
        "ss_user": mask, "ss_password": mask,
    })
    assert creds["ss_user"] == "real_user"
    assert creds["ss_password"] == "real_password"


def test_resolve_still_uses_a_real_value_sent_by_the_client(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=real_user\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    creds = appmod.resolve_scraper_creds(settings, {"ss_user": "otro_usuario"})
    assert creds["ss_user"] == "otro_usuario"
```

- [ ] **Paso 2: Ejecuta los tests para verificar que falla**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: FAIL en `test_resolve_ignores_a_mask_sent_by_the_client`.

- [ ] **Paso 3: Implementa el cambio**

En `resolve_scraper_creds()`, sustituye:

```python
    cfg = get_scraper_config(settings)
    for k in ("ss_user", "ss_password", "ss_devid", "ss_devpassword",
              "ss_region", "ss_lang", "ss_image_type",
              "tgdb_apikey", "igdb_client_id", "igdb_client_secret"):
        val = (client_data or {}).get(k)
        if val:
            cfg[k] = val
    return cfg
```

por:

```python
    cfg = get_scraper_config(settings)
    for k in ("ss_user", "ss_password", "ss_devid", "ss_devpassword",
              "ss_region", "ss_lang", "ss_image_type",
              "tgdb_apikey", "igdb_client_id", "igdb_client_secret"):
        val = (client_data or {}).get(k)
        # Una mascara no es una credencial: si llega una, manda la del servidor.
        if val and not looks_like_ra_mask(val):
            cfg[k] = val
    return cfg
```

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py tests/test_scraper_api.py -v`
Esperado: PASS.

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_scraper_secrets.py
git commit -m "fix(security): la mascara del cliente no pisa la credencial real del scraper"
```

---

### Task 3: `save_scraper_config` write-only

**Ficheros:**
- Modificar: `app.py` (`save_scraper_config`)
- Modificar: `tests/test_scraper_secrets.py`

**Interfaces:**
- Consume: `looks_like_ra_mask(value)` (Task 1), `SCRAPER_SECRET_CONF_KEYS` (Task 1).
- Produce: `save_scraper_config(conf_path, lines)` acepta `{key, val, clear}`.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/test_scraper_secrets.py`:

```python
def test_save_keeps_the_stored_credential_when_a_mask_arrives(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n", encoding="utf-8")
    mask = appmod.mask_secret_value("real_password")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": mask},
    ])
    assert ok, err
    assert "global.scrapper.password=real_password" in conf.read_text(encoding="utf-8")


def test_save_writes_a_new_credential(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=old\n", encoding="utf-8")
    ok, err = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": "nueva_password"},
    ])
    assert ok, err
    assert "global.scrapper.password=nueva_password" in conf.read_text(encoding="utf-8")


def test_save_empty_without_clear_does_not_touch_the_credential(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": ""},
    ])
    assert ok
    assert "global.scrapper.password=real_password" in conf.read_text(encoding="utf-8")


def test_save_with_clear_erases_only_that_credential(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=real_password\n"
                    "global.tgdb.apikey=TGDBKEY\n", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.password", "val": "", "clear": True},
    ])
    assert ok
    text = conf.read_text(encoding="utf-8")
    assert "global.scrapper.password=" in text
    assert "real_password" not in text
    assert "global.tgdb.apikey=TGDBKEY" in text


def test_save_still_writes_non_secret_fields(appmod, tmp_path):
    conf = tmp_path / "batocera.conf"
    conf.write_text("", encoding="utf-8")
    ok, _ = appmod.save_scraper_config(conf, [
        {"key": "global.scrapper.region", "val": "eu"},
    ])
    assert ok
    assert "global.scrapper.region=eu" in conf.read_text(encoding="utf-8")
```

- [ ] **Paso 2: Ejecuta los tests para verificar que fallan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: FAIL en `test_save_keeps_the_stored_credential_when_a_mask_arrives`.

- [ ] **Paso 3: Implementa la regla write-only**

En `save_scraper_config()`, sustituye el bloque del bucle:

```python
        for item in lines or []:
            key = (item or {}).get("key", "")
            val = (item or {}).get("val", "")
            if not key or key not in SCRAPER_CONF_KEYS:
                continue
```

por:

```python
        for item in lines or []:
            item = item or {}
            key = item.get("key", "")
            val = str(item.get("val", "") or "")
            if not key or key not in SCRAPER_CONF_KEYS:
                continue
            if key in SCRAPER_SECRET_CONF_KEYS:
                # Una mascara no es una credencial nueva: se conserva la guardada.
                if looks_like_ra_mask(val):
                    continue
                # Vacio sin intencion explicita: no se toca nada.
                if not val and not item.get("clear"):
                    continue
```

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py tests/test_scraper_api.py -v`
Esperado: PASS (los tests existentes de `save_scraper_config` siguen en verde: escriben
valores reales).

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_scraper_secrets.py
git commit -m "fix(security): las credenciales del scraper se guardan como write-only"
```

---

### Task 4: Los endpoints sirven la config enmascarada

**Ficheros:**
- Modificar: `app.py` (`GET /api/scraper/config`, `POST /api/scraper/search`)
- Modificar: `tests/test_scraper_secrets.py`

**Interfaces:**
- Consume: `public_scraper_config(cfg)` (Task 1).

- [ ] **Paso 1: Escribe el test que falla**

Añade a `tests/test_scraper_secrets.py`:

```python
def test_scraper_config_endpoint_does_not_leak_credentials(appmod, tmp_path):
    """GET /api/scraper/config no puede devolver credenciales en claro."""
    import json
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.user=mi_usuario\n"
                    "global.scrapper.password=mi_password\n"
                    "global.tgdb.apikey=TGDBKEY\n"
                    "global.igdb.clientsecret=igdbsecret\n", encoding="utf-8")
    settings = {"batocera_conf": str(conf)}
    body = json.dumps(appmod.public_scraper_config(
        appmod.get_scraper_config(settings)))
    assert "mi_usuario" not in body
    assert "mi_password" not in body
    assert "TGDBKEY" not in body
    assert "igdbsecret" not in body


def test_get_scraper_config_still_returns_the_real_values(appmod, tmp_path):
    """La lectura interna sigue dando las credenciales reales: se usan para
    hablar con ScreenScraper."""
    conf = tmp_path / "batocera.conf"
    conf.write_text("global.scrapper.password=mi_password\n", encoding="utf-8")
    cfg = appmod.get_scraper_config({"batocera_conf": str(conf)})
    assert cfg["ss_password"] == "mi_password"
```

- [ ] **Paso 2: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: PASS (el test del endpoint pasa con `public_scraper_config` aplicado a
mano). La parte que falla es la del handler: anade un test que compruebe el codigo
del handler con una expresion regular, como el que se usa en
`tests/test_scraper_system_ui.py`:

```python
def test_scraper_config_handler_uses_the_public_config():
    from pathlib import Path
    src = (Path(appmod.__file__).parent / "app.py").read_text(encoding="utf-8")
    assert "public_scraper_config(get_scraper_config(s))" in src
```

- [ ] **Paso 3: Implementa el cambio en los handlers**

En `do_GET`, sustituye:

```python
        elif path == "/api/scraper/config":
            self.send_json(get_scraper_config(s))
```

por:

```python
        elif path == "/api/scraper/config":
            self.send_json(public_scraper_config(get_scraper_config(s)))
```

Y en `_scraper_search`, sustituye las tres ocurrencias de `"cfg":cfg` por
`"cfg":public_scraper_config(cfg)`.

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: PASS.

- [ ] **Paso 5: Commit**

```bash
git add app.py tests/test_scraper_secrets.py
git commit -m "fix(security): /api/scraper/config y /api/scraper/search ya no filtran credenciales"
```

---

### Task 5: Frontend — máscara, hint y `clear` explícito

**Ficheros:**
- Modificar: `templates/index.html`
- Modificar: `tests/test_scraper_secrets.py`

**Interfaces:**
- Consume: la respuesta de `GET /api/scraper/config` ya enmascarada (Task 4).

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/test_scraper_secrets.py`:

```python
def _html():
    from pathlib import Path
    return (Path(appmod.__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")


def test_frontend_reports_configured_credentials():
    html = _html()
    assert "_set" in html, "el hint debe indicar que credenciales hay configuradas"


def test_frontend_sends_explicit_clear_flag():
    html = _html()
    assert "clear" in html, "el guardado debe marcar explicitamente el borrado"
```

- [ ] **Paso 2: Ejecuta los tests para verificar que falla**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: FAIL en `test_frontend_reports_configured_credentials`.

- [ ] **Paso 3: Implementa el frontend**

En `loadScraperConfig()`, sustituye el renderizado de los campos por:

```javascript
  const cont = document.getElementById('sc-cfg-fields');
  cont.innerHTML = [
    { key:'ss_user',           label:'ScreenScraper — Usuario',       type:'text'     },
    { key:'ss_password',       label:'ScreenScraper — Contraseña',    type:'password' },
    { key:'ss_devid',          label:'ScreenScraper — Dev ID (opcional)', type:'text', ph:'solo desarrolladores' },
    { key:'ss_devpassword',    label:'ScreenScraper — Dev Password (opcional)', type:'password' },
    { key:'ss_region',         label:'ScreenScraper — Región',        type:'text',     ph:'wor' },
    { key:'ss_lang',           label:'ScreenScraper — Idioma',        type:'text',     ph:'es'  },
    { key:'ss_image_type',     label:'ScreenScraper — Tipo imagen',   type:'text',     ph:'mixrbv1' },
    { key:'tgdb_apikey',       label:'TheGamesDB — API Key',          type:'text',     ph:'tu_api_key' },
    { key:'igdb_client_id',    label:'IGDB — Client ID (Twitch)',     type:'text',     ph:'tu_client_id' },
    { key:'igdb_client_secret',label:'IGDB — Client Secret (Twitch)', type:'password', ph:'tu_client_secret' },
  ].map(f => `
    <div class="field" style="margin-bottom:12px">
      <label>${f.label}</label>
      <input type="${f.type}" id="sccfg-${f.key}"
        value="${escHtml(cfg[f.key]||'')}" placeholder="${f.ph||''}">
      ${cfg[f.key+'_set'] ? '<span class="hint">Configurada (enmascarada)</span>' : ''}
    </div>`).join('');
```

Y sustituye el guardado por:

```javascript
async function scraperSaveConfig() {
  const fields = ['ss_user','ss_password','ss_devid','ss_devpassword','ss_region','ss_lang','ss_image_type','tgdb_apikey','igdb_client_id','igdb_client_secret'];
  const secretFields = ['ss_user','ss_password','ss_devid','ss_devpassword','tgdb_apikey','igdb_client_id','igdb_client_secret'];
  const keyMap = {
    ss_user:'global.scrapper.user', ss_password:'global.scrapper.password',
    ss_devid:'global.scrapper.devid', ss_devpassword:'global.scrapper.devpassword',
    ss_region:'global.scrapper.region', ss_lang:'global.scrapper.lang',
    ss_image_type:'global.scrapper.imageSource',
    tgdb_apikey:'global.tgdb.apikey',
    igdb_client_id:'global.igdb.clientid', igdb_client_secret:'global.igdb.clientsecret',
  };
  const lines  = [];
  fields.forEach(k => {
    const el = document.getElementById('sccfg-' + k);
    if (!el) return;
    const val = el.value.trim();
    const bkey = keyMap[k] || k;
    if (secretFields.includes(k)) {
      // Las credenciales se mandan siempre: la mascara la ignora el backend y
      // un vaciado lleva `clear` para que se borre de verdad.
      if (!val && !cfg[k]) return;
      lines.push({key: bkey, val: val, clear: !val});
    } else if (val) {
      lines.push({key: bkey, val: val});
    }
  });
  ...
}
```

**Atención**: `cfg` debe estar disponible en `scraperSaveConfig()`. Si es una variable
local de `loadScraperConfig()`, declárala en el ámbito del módulo (`let _scraperCfg = {}`)
y asígnala ahí.

- [ ] **Paso 4: Ejecuta los tests para verificar que pasan**

Ejecuta: `python -m pytest tests/test_scraper_secrets.py -v`
Esperado: PASS.

- [ ] **Paso 5: Commit**

```bash
git add templates/index.html tests/test_scraper_secrets.py
git commit -m "feat(ui): las credenciales del scraper se muestran enmascaradas"
```

---

### Task 6: Verificación end-to-end y documentación

**Ficheros:**
- Modificar: `README.md`, `CHANGELOG.md`, `MEMORY.md`

**Interfaces:**
- Consume: el comportamiento final de las Tasks 1-5.

- [ ] **Paso 1: Verificación end-to-end**

Levanta el servidor real con un `batocera.conf` temporal que tenga credenciales y
comprueba por HTTP que:

- `GET /api/scraper/config` no contiene ninguna credencial real, y sí los flags
  `<campo>_set`.
- `GET /api/scraper/config` devuelve la máscara.
- `POST /api/scraper/save-config` con la máscara conserva el valor en `batocera.conf`.
- `POST /api/scraper/save-config` con `clear: true` lo borra.
- `POST /api/scraper/search` no devuelve credenciales en el campo `cfg`.

- [ ] **Paso 2: Actualiza el README**

En la sección "🔒 Seguridad", añade que las credenciales del scraper tampoco se sirven
en claro, y que `/api/scraper/config` las devuelve enmascaradas.

- [ ] **Paso 3: Actualiza el CHANGELOG**

En `## [Unreleased]`, bajo `### Seguridad`:

```markdown
- Las credenciales del scraper (ScreenScraper, TheGamesDB e IGDB) ya no se sirven en
  claro por la API: `/api/scraper/config` y `/api/scraper/search` las devuelven
  enmascaradas con un indicador de si están configuradas. Al guardar se comportan
  como solo-escritura (si no tocas el campo, la credencial no se pierde; si lo
  vacías, se borra).
```

- [ ] **Paso 4: Actualiza el MEMORY.md**

En "Issues conocidos", la entrada 7b (credenciales del scraper expuestas en claro)
pasa a **RESUELTO**. En "Áreas prioritarias", quita la línea de "Enmascarar las
credenciales del scraper".

- [ ] **Paso 5: Ejecuta la suite completa**

Ejecuta: `python -m pytest`
Esperado: toda la suite en verde.

- [ ] **Paso 6: Commit**

```bash
git add README.md CHANGELOG.md MEMORY.md
git commit -m "docs: las credenciales del scraper ya no se sirven en claro"
```
