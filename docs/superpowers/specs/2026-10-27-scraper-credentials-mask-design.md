# Diseño: Enmascarar las credenciales del scraper

**Fecha:** 2026-10-27
**Autor:** sesión de trabajo (asistida)
**Estado:** aprobado por el usuario ("continúa entonces") — cierra el punto I3 de la
revisión del cambio anterior (enmascarado de la Web API Key de RetroAchievements)

---

## 1. Contexto

El manager no tiene autenticación: toda la API es legible desde la LAN. El cambio
anterior cerró la fuga de la **Web API Key de RetroAchievements** en `/api/settings`,
pero la revisión detectó que las **credenciales del scraper** siguen saliendo en
claro, y son estrictamente peores: es la contraseña de tu cuenta de ScreenScraper, su
contraseña de desarrollador y tres API keys.

Dónde se filtran hoy (verificado sobre `app.py`):

| Punto | Qué devuelve |
|---|---|
| `GET /api/scraper/config` (`app.py:4912`) | `get_scraper_config(s)` completo, con `ss_user`, `ss_password`, `ss_devid`, `ss_devpassword`, `tgdb_apikey`, `igdb_client_id`, `igdb_client_secret` |
| `POST /api/scraper/search` (`app.py:5365`, `5376`, `5401`) | `"cfg": cfg` — el mismo dict con todas las credenciales |

Las credenciales viven en `batocera.conf` (`global.scrapper.*`, `global.tgdb.apikey`,
`global.igdb.*`), no en el JSON de ajustes. El backend las lee con
`get_scraper_config()` y las combina con lo que envía el navegador con
`resolve_scraper_creds()`.

**No** se filtran por `GET /api/scraper/batch` ni por `/api/scraper/batch/<id>`: ambos
construyen la respuesta con una lista blanca de campos que no incluye `creds`. Eso se
ha verificado y no se toca.

## 2. Objetivo

Que ninguna credencial del scraper salga en claro por la API, sin romper el flujo de
configuración ni el scraping.

## 3. Requisitos

- Los siete campos de credenciales se sirven enmascarados, con un indicador de si
  están configurados.
- Guardar la configuración sin tocar los campos conserva las credenciales guardadas.
- Vaciar un campo borra esa credencial (y solo esa).
- El scraping sigue funcionando: la credencial real es la que sale hacia
  ScreenScraper / TheGamesDB / IGDB, nunca la máscara.

## 4. No-objetivos

- **No** se cifra nada en reposo ni se cambia el formato de `batocera.conf`.
- **No** se toca la lógica de scraping, ni los endpoints de descarga, ni el worker de
  lotes.
- **No** se cambia el comportamiento de los campos que no son credenciales
  (`ss_region`, `ss_lang`, `ss_image_type`, `scraper_source`): se siguen mostrando y
  escribiendo en claro.
- **No** se implementa autenticación (sigue siendo el pendiente de fondo).

## 5. Restricciones

- Cero dependencias; backend stdlib.
- `get_scraper_config()` es una función **interna**: se usa para hablar con
  ScreenScraper, así que debe seguir devolviendo las credenciales reales. Lo que se
  enmascara es la **respuesta HTTP**, no la lectura.
- `resolve_scraper_creds(settings, client_data)` combina servidor + cliente. Si el
  cliente manda una máscara, esta **no** puede ganar: si no, la máscara acabaría
  enviada a ScreenScraper.
- El frontend rellena hoy los formularios con la credencial real (`fillIfEmpty`), y
  el guardado manda los valores de los campos tal cual.

## 6. Enfoques considerados

### 6.1 Dónde aplicar el enmascarado

| Enfoque | Trade-off |
|---|---|
| **A. Enmascarar en el borde de la API** ✅ elegido | `get_scraper_config()` intacta (habla con ScreenScraper con las reales); solo se enmascara lo que sale por HTTP. Un solo sitio donde revisar las fugas. |
| B. Enmascarar en la lectura de `batocera.conf` | La función que lee el conf devolvería máscaras, y habría que desenmascarar en cada uso saliente. Se spreads el riesgo de enviar una máscara a la API externa. |
| C. Mover las credenciales al JSON de ajustes | Reescribe el modelo de datos y how Batocera espera encontrarlas. No aporta nada frente a A. |

### 6.2 Cómo distinguir "el usuario no tocó el campo" de "el usuario lo borró"

Hoy el frontend **no manda** los campos vacíos, así que vacío = "no tocar". Con
enmascarado, el campo vacío puede significar dos cosas: "no había nada" o "el usuario
ha borrado la credencial". Se resuelve con intención explícita:

- El frontend manda siempre una línea por campo de credencial, con `clear: true`
  cuando el usuario vació un campo que tenía máscara.
- El backend: máscara → conserva; `clear: true` → borra; valor nuevo → escribe;
  vacío sin `clear` → conserva (no toca nada, por si acaso).

Así, un cliente viejo que no manda `clear` **no borra** credenciales por accidente.

## 7. Diseño

### 7.1 Backend (`app.py`)

**Constantes y helpers**

```python
# Campos de get_scraper_config() que son credenciales.
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
```

`mask_secret_value(value)` pasa a ser el helper genérico de enmascarado, y
`mask_ra_api_key()` delega en él (misma regla: los primeros y últimos 4 caracteres si
la clave tiene 12+ caracteres; si es más corta, se oculta entera).

`public_scraper_config(cfg)` devuelve una **copia** con los siete campos enmascarados
y un `<campo>_set` booleano por cada uno.

**Lectura**

- `GET /api/scraper/config` → `public_scraper_config(get_scraper_config(s))`.
- `POST /api/scraper/search` → `"cfg": public_scraper_config(cfg)`.

**Escritura**

- `save_scraper_config(conf_path, lines)`: si la clave es secreta y el valor parece
  una máscara, la línea se salta (se conserva lo guardado); si viene vacío sin
  `clear`, también se salta; si viene `clear: true`, se escribe vacío.

**Combinación servidor + cliente**

- `resolve_scraper_creds()`: un valor del cliente que parezca máscara se ignora, de
  modo que manda el del servidor. Sin esto, la máscara acabaría en ScreenScraper.

### 7.2 Frontend (`templates/index.html`)

- `loadScraperConfig()` rellena los campos con la **máscara** en lugar de la
  credencial, y añade un hint con las credenciales que están configuradas.
- `scraperSaveConfig()` manda una línea por campo de credencial:
  - el valor del campo tal cual (que será la máscara si no se ha tocado),
  - `clear: true` si el usuario vació un campo que tenía máscara.
- El pre-relleno de las pestañas "individual" / "sistema" / "lote" sigue igual, pero
  ahora rellena con la máscara. Es seguro: el backend la ignora y usa la credencial
  real del servidor.

### 7.3 Cómo se ve

```
ScreenScraper — Contraseña    [••••••••]   Configurada
TheGamesDB — API Key          [••••••••]   Configurada
ScreenScraper — Región        [wor]       (sin cambios)
```

## 8. Verificación

- Tests nuevos en `tests/test_scraper_secrets.py`.
- Se amplía `tests/test_scraper_api.py` con la regla write-only de `save_scraper_config`.
- Suite completa en verde.
- End-to-end contra el servidor HTTP real: `GET /api/scraper/config` no debe contener
  ninguna credencial, y `POST /api/scraper/search` tampoco.

## 9. Decisiones tomadas por el implementador

1. **Se enmascaran los siete campos**, incluidos `ss_user` y `igdb_client_id`, que no
   son secretos de por sí: son la otra mitad de la credencial y sin ellos la
   contraseña no sirve.
2. **Los campos no secretos no cambian** de comportamiento: se siguen viendo y
   escribiendo en claro.
3. **El valor por defecto de `ss_devid`/`ss_devpassword`** (los credenciales oficiales
   de Batocera, `SS_DEV_FALLBACK`) también se enmascara: son credenciales aunque no
   sean las del usuario.
4. **`clear` explícito** en lugar de interpretar el vacío: evita que un cliente que
   no manda la bandera borre credenciales por accidente.
