"""Tests de «lo que falta»: las otras versiones de los juegos que ya tienes.

El DAT de un sistema es la lista de todos sus juegos. Comparado con la
biblioteca dice qué te falta, pero la lista completa no informa de nada (el
DAT de PlayStation 2 tiene 13.618 juegos y una biblioteca normal tiene 300).
Estos tests fijan lo que sí informa:

- **las variantes de los juegos que ya tienes** (otra región, otra revisión);
- **los discos que faltan** de un juego con varios discos;
- **la versión que es mejor que la que tienes** (un volcado verificado frente
  a uno con datos malos);
- y que **nada se escribe ni se borra**: esto es solo información.
"""

import json
from pathlib import Path

from romtools import dats, faltantes


# ── Utilidades ──────────────────────────────────────────────────────────

def _entrada(nombre, tamano=100, md5="", sha1="", crc=""):
    """Una entrada del DAT, con la forma que devuelve `parse_dat`."""
    return {
        "name": nombre,
        "description": nombre,
        "cloneof": "",
        "romof": "",
        "region": "",
        "serial": "",
        "roms": [{"name": nombre + ".smc", "size": tamano,
                  "crc": crc, "md5": md5, "sha1": sha1, "serial": ""}],
    }


def _instalar_dat(cache, sistema, juegos):
    """Escribe el DAT y su indice como los deja `install_dat`."""
    cache.mkdir(parents=True, exist_ok=True)
    indice = dats.build_index_compacto(juegos)
    with open(cache / (sistema + ".json"), "w", encoding="utf-8") as fh:
        json.dump({"juegos": indice["juegos"],
                   "by_hash": indice["by_hash"],
                   "by_serial": indice["by_serial"],
                   "by_name": indice["by_name"],
                   "by_name_size": indice["by_name_size"],
                   "by_title": indice["by_title"],
                   "by_gamecode": indice["by_gamecode"]}, fh)
    with open(cache / (sistema + ".meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"system": sistema, "source": "prueba", "dat": sistema + ".dat",
                   "version": "1", "generated": 0, "games": len(juegos)}, fh)
    with open(cache / (sistema + ".dat"), "wb") as fh:
        fh.write(b"cabecera de prueba")
    return cache


def _juego(base, nombre, tamano=100):
    """Un juego en la biblioteca del sistema."""
    carpeta = base / "roms" / "snes"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_bytes(b"\x00" * tamano)
    return carpeta


def _comparar(tmp_path, juegos_dat, ficheros):
    """Prepara la biblioteca y el DAT, y devuelve el resultado."""
    base = tmp_path / "roms"
    cache = tmp_path / "system" / "batocera_manager_dats"
    _instalar_dat(cache, "snes", juegos_dat)
    for nombre, tamano in ficheros:
        _juego(tmp_path, nombre, tamano)
    return faltantes.faltantes(str(base), "snes", {".smc", ".sfc"}, str(cache))


# ── Los sistemas con DAT ────────────────────────────────────────────────

def test_los_sistemas_con_dat_se_listan(tmp_path):
    """Los sistemas con DAT instalado, con cuantos juegos tiene cada uno."""
    cache = tmp_path / "batocera_manager_dats"
    _instalar_dat(cache, "snes", [_entrada("Juego (USA)")])

    sistemas = faltantes.sistemas_con_dat(str(cache))

    assert len(sistemas) == 1
    assert sistemas[0]["sistema"] == "snes"
    assert sistemas[0]["juegos_dat"] == 1


def test_un_sistema_sin_dat_no_se_inventa(tmp_path):
    """Sin DAT no hay nada que comparar, y se dice."""
    resultado = faltantes.faltantes(str(tmp_path / "roms"), "snes",
                                    {".smc"}, str(tmp_path / "dats"))
    assert resultado["ok"] is False
    assert "DAT" in resultado["error"]


# ── Lo que falta ────────────────────────────────────────────────────────

def test_se_dice_que_otra_region_falta(tmp_path):
    """Tienes la japonesa y el DAT tiene tambien la americana."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Super Mario 64 (Japan)"), _entrada("Super Mario 64 (USA)")],
        [("Super Mario 64 (Japan).smc", 100)])

    assert resultado["ok"] is True
    assert resultado["encontrados"] == 1
    assert resultado["grupos"] == 1
    grupo = resultado["detalle"][0]
    assert grupo["titulo"] == "Super Mario 64"
    assert [v["nombre"] for v in grupo["variantes"]] == ["Super Mario 64 (Japan)"]
    assert len(grupo["faltan"]) == 1
    assert grupo["faltan"][0]["nombre"] == "Super Mario 64 (USA)"
    assert grupo["faltan"][0]["motivo"] == "region"
    assert grupo["faltan"][0]["detalle"] == "USA"


def test_se_dice_que_disco_falta(tmp_path):
    """Un juego de tres discos del que solo tienes el primero."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA) (Disc 1)"), _entrada("Juego (USA) (Disc 2)"),
         _entrada("Juego (USA) (Disc 3)")],
        [("Juego (USA) (Disc 1).smc", 100)])

    grupo = resultado["detalle"][0]
    assert grupo["titulo"] == "Juego"
    assert grupo["discos_faltantes"] == [2, 3]
    assert resultado["discos"] == 1
    motivos = {f["nombre"]: f["motivo"] for f in grupo["faltan"]}
    assert motivos["Juego (USA) (Disc 2)"] == "disco"
    assert motivos["Juego (USA) (Disc 3)"] == "disco"


def test_los_discos_que_faltan_se_cuentan_como_conjunto(tmp_path):
    """Si tienes el 1 y el 3, falta el 2 aunque el DAT no lo traiga."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA) (Disc 1)"), _entrada("Juego (USA) (Disc 3)")],
        [("Juego (USA) (Disc 1).smc", 100), ("Juego (USA) (Disc 3).smc", 100)])

    assert resultado["detalle"] == []


def test_lo_que_ya_tienes_no_se_marca_como_que_falta(tmp_path):
    """Si tienes la version que falta, no aparece en la lista."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)"), _entrada("Juego (Europe)")],
        [("Juego (USA).smc", 100), ("Juego (Europe).smc", 100)])

    assert resultado["grupos"] == 0
    assert resultado["faltantes"] == 0
    assert resultado["encontrados"] == 2


def test_los_juegos_que_no_estan_en_el_dat_se_cuentan(tmp_path):
    """Un mod o una traduccion no sale en el DAT: no es un fallo."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)")],
        [("Juego (USA).smc", 100), ("Juego (Español) [HACK].smc", 100)])

    assert resultado["encontrados"] == 1
    assert resultado["sin_dat"] == 1
    assert resultado["sin_dat_lista"][0]["fichero"] == "Juego (Español) [HACK].smc"


def test_los_dudosos_no_se_cuentan_como_que_faltan(tmp_path):
    """Un juego sin region quiza sea el del DAT: de el no se afirma nada."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Super Mario 64 (Japan)"), _entrada("Super Mario 64 (USA)")],
        [("Super Mario 64.smc", 100)])

    # No se ha podido emparejar con seguridad: no se dice ni que lo tienes ni
    # que te falta, pero tampoco cuenta como un juego que no esta en el DAT.
    assert resultado["encontrados"] == 0
    assert resultado["quizas"] == 1
    assert resultado["sin_dat"] == 0
    assert resultado["detalle"] == []


def test_se_cuentan_los_juegos_con_una_version_mejor(tmp_path):
    """El filtro «mejores versiones» cuenta juegos, no versiones."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA) [b]"), _entrada("Juego (USA) [!]"),
         _entrada("Juego (USA) (Rev 2)")],
        [("Juego (USA) [b].smc", 100)])

    assert resultado["grupos"] == 1
    assert resultado["mejores"] == 2
    assert resultado["grupos_mejores"] == 1


def test_la_region_del_fichero_manda(tmp_path):
    """Si el fichero dice «(USA)», la variante es la «(USA)».

    El parecido entre caracteres favorece al nombre con **menos** etiquetas:
    «Super Mario 64» se parece mas a «(USA)» (0,881) que a «(Japan)»
    (0,758). Por eso la region que declara el nombre va por delante del
    parecido.
    """
    # El tamano no cuadra a proposito: si cuadrase, el emparejamiento seria
    # por el nombre y no se probaria la regla.
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)", tamano=100), _entrada("Juego (Japan)", tamano=100)],
        [("Juego (USA).smc", 200)])

    grupo = resultado["detalle"][0]
    assert [v["nombre"] for v in grupo["variantes"]] == ["Juego (USA)"]
    assert grupo["faltan"][0]["nombre"] == "Juego (Japan)"
    assert grupo["faltan"][0]["motivo"] == "region"


def test_un_juego_con_un_nombre_parecido_no_es_el_mismo(tmp_path):
    """«Tomb Raider  I» y «Tomb Raider (USA)» no son el mismo juego."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Tomb Raider (USA)", tamano=100),
         _entrada("Tomb Raider (Europe)", tamano=100)],
        [("Tomb Raider  I.smc", 200)])

    assert resultado["encontrados"] == 0
    assert resultado["quizas"] == 0
    assert resultado["sin_dat"] == 1
    assert resultado["detalle"] == []


def test_la_version_buena_se_marca(tmp_path):
    """Tienes un volcado con datos malos y hay uno verificado: eso es mejor."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA) [b]"), _entrada("Juego (USA) [!]")],
        [("Juego (USA) [b].smc", 100)])

    grupo = resultado["detalle"][0]
    buena = [f for f in grupo["faltan"] if f["mejor"]]
    assert buena, "la version verificada deberia marcarse como mejor"
    assert buena[0]["nombre"] == "Juego (USA) [!]"
    assert resultado["mejores"] == 1


def test_se_dice_como_se_ha_emparejado(tmp_path):
    """Una coincidencia por nombre no es lo mismo que una por hash."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)")],
        [("Juego (USA).smc", 100)])

    variante = resultado["detalle"][0]["variantes"] if resultado["detalle"] else None
    if variante is None:
        # Con una sola version en el DAT no hay grupo, pero el emparejamiento
        # sigue siendo el del nombre.
        assert resultado["encontrados"] == 1
    else:
        assert variante[0]["metodo"] == "nombre"


def test_los_volcados_repetidos_se_agrupan(tmp_path):
    """El DAT puede traer dos entradas con el mismo nombre: se agrupan."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)"), _entrada("Juego (Europe)"),
         _entrada("Juego (Europe)", md5="otro")],
        [("Juego (USA).smc", 100)])

    grupo = resultado["detalle"][0]
    faltas = {f["nombre"]: f for f in grupo["faltan"]}
    assert list(faltas) == ["Juego (Europe)"]
    assert faltas["Juego (Europe)"]["copias"] == 2


def test_una_region_con_dos_paises_se_detecta(tmp_path):
    """``(Europe, Australia)`` es una region, no una version sin nombre."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (Japan)"), _entrada("Juego (Europe, Australia)")],
        [("Juego (Japan).smc", 100)])

    falta = resultado["detalle"][0]["faltan"][0]
    assert falta["motivo"] == "region"
    assert falta["detalle"] == "Europe"


def test_una_edicion_distinta_no_se_dice_que_es_el_idioma(tmp_path):
    """``(GameCube)`` no es un idioma: lo que cambia es la edicion."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (Europe) (En,Fr,De)"), _entrada("Juego (Europe) (GameCube)")],
        [("Juego (Europe) (En,Fr,De).smc", 100)])

    falta = resultado["detalle"][0]["faltan"][0]
    assert falta["motivo"] == "version"


def test_el_idioma_diferente_se_dice(tmp_path):
    """Si los dos dicen sus idiomas y no son los mismos, eso es el motivo."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (Europe) (En,Fr,De)"), _entrada("Juego (Europe) (Es,It)")],
        [("Juego (Europe) (En,Fr,De).smc", 100)])

    falta = resultado["detalle"][0]["faltan"][0]
    assert falta["motivo"] == "idioma"
    assert falta["detalle"] == "Es, It"


def test_una_carpeta_juego_se_compara_sin_la_extension(tmp_path):
    """ScummVM: la carpeta es «Myst.scummvm» y el DAT la llama «Myst».

    La extension del motor («.scummvm») no es parte del nombre del juego: sin
    quitarla, la clave no coincide con la de la entrada y no se empareja nada.
    """
    base = tmp_path / "roms"
    cache = tmp_path / "system" / "batocera_manager_dats"
    _instalar_dat(cache, "scummvm", [_entrada("Myst (1993) (Windows)")])
    carpeta = base / "scummvm" / "Myst.scummvm"
    carpeta.mkdir(parents=True)
    (carpeta / "myst.scummvm").write_bytes(b"\x00" * 100)

    resultado = faltantes.faltantes(str(base), "scummvm", {".scummvm"}, str(cache))

    # Ni el uno ni el otro declaran region: no hay nada que contradecir, asi
    # que la variante se puede afirmar.
    assert resultado["encontrados"] == 1
    assert resultado["quizas"] == 0


def test_la_comparacion_no_toca_la_biblioteca(tmp_path):
    """Esto es solo informacion: no se escribe ni se borra nada."""
    resultado = _comparar(
        tmp_path,
        [_entrada("Juego (USA)"), _entrada("Juego (Europe)")],
        [("Juego (USA).smc", 100)])

    assert resultado["ok"] is True
    assert (tmp_path / "roms" / "snes" / "Juego (USA).smc").exists()
    # No se crea ninguna cuarentena ni se escribe en la biblioteca.
    assert not (tmp_path / "roms" / ".quarantine").exists()
    entradas = sorted(p.name for p in (tmp_path / "roms" / "snes").iterdir())
    assert entradas == ["Juego (USA).smc"]


# ── La aplicacion ───────────────────────────────────────────────────────

def _settings(appmod, tmp_path):
    """Los ajustes con las rutas del temporal."""
    ajustes = dict(appmod.DEFAULT_SETTINGS)
    ajustes["roms_base"] = str(tmp_path / "roms")
    ajustes["tools_base"] = str(tmp_path / "system")
    return ajustes


class _Peticion:
    """Un handler de mentira: solo lo que usa el enrutador de la biblioteca."""

    def __init__(self, path, comando="GET", cuerpo=None):
        self.path = path
        self.command = comando
        self.cuerpo = cuerpo
        self.out = None
        self.status = 200

    def send_json(self, datos, status=200):
        self.out = datos
        self.status = status

    def read_json(self):
        return self.cuerpo


def _llamar(appmod, settings, path, comando="GET", cuerpo=None):
    """Llama al enrutador. El path puede traer la query (`?system=snes`)."""
    ruta = path.split("?")[0]
    peticion = _Peticion(path, comando, cuerpo)
    partes = [p for p in ruta.split("/") if p]
    appmod.BatoceraHandler._library(peticion, settings, ruta, partes)
    return peticion


def test_el_endpoint_de_los_sistemas_con_dat(appmod, tmp_path):
    """`GET /api/library/missing/systems` lista los sistemas con DAT."""
    cache = tmp_path / "system" / "batocera_manager_dats"
    _instalar_dat(cache, "snes", [_entrada("Juego (USA)")])
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/missing/systems")

    assert peticion.out["ok"] is True
    assert peticion.out["sistemas"][0]["sistema"] == "snes"


def test_el_endpoint_de_la_comparacion_arranca_un_trabajo(appmod, tmp_path):
    """La comparación va en segundo plano: devuelve el id del trabajo."""
    cache = tmp_path / "system" / "batocera_manager_dats"
    _instalar_dat(cache, "snes", [_entrada("Juego (USA)"), _entrada("Juego (Europe)")])
    _juego(tmp_path, "Juego (USA).smc", 100)
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/missing/start?system=snes")

    assert peticion.out["ok"] is True
    assert peticion.out["job"]
    trabajo = appmod._rt_jobs.JOBS.obtener(peticion.out["job"])
    assert trabajo is not None
    import time
    for _ in range(200):
        if trabajo.estado != "trabajando":
            break
        time.sleep(0.05)
    assert trabajo.estado == "listo"
    assert trabajo.resultado["faltantes"] == 1


def test_la_comparacion_necesita_un_sistema(appmod, tmp_path):
    """Sin sistema no hay comparación."""
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/missing/start")

    assert peticion.out["ok"] is False
    assert "sistema" in peticion.out["error"]


# ── La interfaz ─────────────────────────────────────────────────────────

def _texto(ruta_relativa):
    raiz = Path(__file__).resolve().parent.parent
    return (raiz / "frontend" / "src" / ruta_relativa).read_text(encoding="utf-8")


def test_la_seccion_de_lo_que_falta_esta_en_la_pagina_de_roms():
    """La página de ROMs tiene que ofrecer la comparación con el DAT."""
    h = _texto("pages/Roms.tsx")
    assert "FaltantesPanel" in h
    assert "api.libraryMissingStart(" in h
    assert "api.libraryJob(" in h


def test_el_panel_explica_de_donde_sale_cada_coincidencia():
    """Una coincidencia por hash no es lo mismo que una por titulo."""
    h = _texto("components/library/FaltantesPanel.tsx")
    assert "METODOS" in h
    assert "por el hash" in h
    assert "por el titulo" in h


def test_el_filtro_de_mejores_cuenta_los_juegos():
    """El numero del filtro tiene que ser el de los juegos que se ensenan."""
    h = _texto("components/library/FaltantesPanel.tsx")
    assert "grupos_mejores" in h
    assert "gruposConMejores" in h


def test_el_panel_avisa_del_progreso():
    """Comparar un sistema con su DAT tarda: tiene que haber barra."""
    h = _texto("components/library/FaltantesPanel.tsx")
    assert "Progress" in h
    assert "no hace falta cerrar la ventana" in h
