"""Tests de la biblioteca de ROMs: duplicados, auditoría y cuarentena.

La sección «ROMs y BIOS» tenía solo BIOS. Con esta tanda la biblioteca se ve
como conjunto: que hay, que está repetido, que está roto y cuanto ocupa.
Estos tests fijan ese comportamiento, y sobre todo dos reglas:

- **nada se borra**: lo que sobra va a una cuarentena y se puede deshacer;
- **nunca se hashea la biblioteca entera**: los duplicados se buscan con una
  huella rápida y solo se confirman los candidatos.
"""

import json

import pytest

from romtools import library


# ── Utilidades ──────────────────────────────────────────────────────────

def _roms(tmp_path, sistema="snes"):
    """La carpeta de un sistema dentro de la biblioteca."""
    base = tmp_path / "roms" / sistema
    base.mkdir(parents=True, exist_ok=True)
    return base


def _exts(*sistemas):
    """Las extensiones que son juego en cada sistema."""
    return {s: {".smc", ".iso", ".n64", ".v64", ".z64"} for s in sistemas}


def _juegos(base, sistema="snes", exts=None):
    """Los juegos de un sistema (con la regla de extensiones)."""
    return library.recolectar(str(base.parent), [sistema],
                               exts or _exts(sistema))["juegos"]


# ── Los duplicados ──────────────────────────────────────────────────────

def test_los_juegos_repetidos_se_encuentran(tmp_path):
    """Dos ficheros con el mismo contenido son un duplicado."""
    base = _roms(tmp_path)
    (base / "Juego (USA).smc").write_bytes(b"contenido" * 100)
    (base / "Copia (USA).smc").write_bytes(b"contenido" * 100)

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base))

    assert len(dups) == 1
    assert dups[0]["copias"] == 2
    assert dups[0]["confirmado"] is True
    assert dups[0]["ahorro"] == 900, "se puede liberar una copia"
    assert sorted(dups[0]["nombres"]) == ["Copia (USA).smc", "Juego (USA).smc"]


def test_dos_ficheros_distintos_del_mismo_tamano_no_son_duplicados(tmp_path):
    """El hash completo descarta los falsos positivos de la huella rapida."""
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 4096)
    (base / "Otro.smc").write_bytes(b"B" * 4096)

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base))

    assert dups == [], "mismo tamaño, distinto contenido: no son duplicados"


def test_un_juego_de_cero_bytes_no_cuenta_como_duplicado(tmp_path):
    """Todos los ficheros vacios serian iguales: no dicen nada."""
    base = _roms(tmp_path)
    (base / "Vacio.smc").write_bytes(b"")
    (base / "TambienVacio.smc").write_bytes(b"")

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base))

    assert dups == []


def test_el_presupuesto_deja_algunos_grupos_sin_confirmar(tmp_path):
    """Si no cabe el hash completo, el grupo sale como candidato."""
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 4096)
    (base / "Otro.smc").write_bytes(b"A" * 4096)

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base),
                              max_bytes=1)

    assert len(dups) == 1
    assert dups[0]["confirmado"] is False
    assert dups[0]["md5"] is None


def test_la_auditoria_devuelve_el_resumen_de_la_biblioteca(tmp_path):
    """La radiografia cuenta los juegos y los bytes."""
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 100)
    (base / "Otro.smc").write_bytes(b"B" * 200)

    informe = library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"))

    assert informe["resumen"]["sistemas"] == 1
    assert informe["resumen"]["juegos"] == 2
    assert informe["resumen"]["bytes"] == 300


def test_la_auditoria_no_termina_el_trabajo_antes_de_hora(tmp_path):
    """El aviso de «terminado» solo puede llegar al final.

    El trabajo en segundo plano se cierra con ese aviso: si una fase
    intermedia lo mandara, el trabajo acabaria con el resultado a medias (y
    el `job` se quedaria sin resultado, que es lo que pasaba en la consola
    real con la biblioteca de 1,8 TB).
    """
    estados = []
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 100)
    (base / "Otro.smc").write_bytes(b"A" * 100)

    library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"),
                      progreso=lambda estado: estados.append(estado))

    terminados = [i for i, estado in enumerate(estados) if estado.get("terminado")]
    assert terminados, "acaba avisando de que ha terminado"
    assert terminados == [len(estados) - 1], "solo el ultimo aviso dice «terminado»"


def test_los_duplicados_no_cortan_el_trabajo(tmp_path):
    """Buscar duplicados tampoco puede cerrar el trabajo antes de tiempo."""
    estados = []
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 100)
    (base / "Otro.smc").write_bytes(b"A" * 100)

    library.duplicados(str(tmp_path / "roms"), _juegos(base),
                       progreso=lambda estado: estados.append(estado))

    assert not [e for e in estados if e.get("terminado")]


def test_las_carpetas_se_comparan_enteras_no_por_el_motor(tmp_path):
    """En ScummVM y DOSBox el fichero mas grande es el motor, igual para todos.

    Comparando solo ese fichero, dos juegos distintos salian como duplicados.
    """
    base = _roms(tmp_path)
    for juego in ("kq3", "pq2"):
        carpeta = base / f"{juego}.scummvm"
        (carpeta / juego).mkdir(parents=True)
        # El motor: el mismo fichero, byte a byte, en los dos juegos.
        (carpeta / "scummvm").write_bytes(b"MOTOR" * 500)
        (carpeta / juego / "datos.dat").write_bytes(juego.encode() * 300)

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base))

    assert dups == [], "son juegos distintos: el motor comun no los hace iguales"


def test_dos_carpetas_identicas_son_duplicado(tmp_path):
    """Si la carpeta entera es la misma, sí es un duplicado."""
    base = _roms(tmp_path)
    for nombre in ("kq3.scummvm", "copia.scummvm"):
        carpeta = base / nombre
        (carpeta / "datos").mkdir(parents=True)
        (carpeta / "scummvm").write_bytes(b"MOTOR" * 500)
        (carpeta / "datos" / "datos.dat").write_bytes(b"MISMO" * 300)

    dups = library.duplicados(str(tmp_path / "roms"), _juegos(base))

    assert len(dups) == 1
    assert dups[0]["confirmado"] is True
    assert dups[0]["copias"] == 2


# ── Lo que esta roto ────────────────────────────────────────────────────

def test_las_fichas_sin_fichero_se_detectan(tmp_path):
    """Una entrada del gamelist que apunta a un juego que no esta."""
    base = _roms(tmp_path)
    (base / "Existe.smc").write_bytes(b"A" * 100)
    (base / "gamelist.xml").write_text(
        "<gameList><game><path>./Existe.smc</path></game>"
        "<game><path>./Fantasma.smc</path></game></gameList>",
        encoding="utf-8")

    informe = library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"))

    rotas = informe["fichas_sin_fichero"]
    assert rotas["total"] == 1
    assert rotas["lista"][0]["ruta"] == "Fantasma.smc"


def test_los_ficheros_que_no_son_juegos_son_sobras(tmp_path):
    """Un `.txt` no es un juego: es un fichero que sobra."""
    base = _roms(tmp_path)
    (base / "Juego.smc").write_bytes(b"A" * 100)
    (base / "_info.txt").write_text("notas", encoding="utf-8")

    informe = library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"))

    sobras = informe["sobras"]
    assert sobras["total"] == 1
    assert sobras["lista"][0]["nombre"] == "_info.txt"


def test_la_media_de_un_juego_que_no_esta_se_ve_como_huerfana(tmp_path):
    """La imagen de un juego borrado no corresponde a nadie."""
    base = _roms(tmp_path)
    (base / "Juego.smc").write_bytes(b"A" * 100)
    (base / "images").mkdir()
    (base / "images" / "Juego-image.png").write_bytes(b"x" * 10)
    (base / "images" / "Fantasma-image.png").write_bytes(b"x" * 10)

    informe = library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"))

    huerfanos = [m["fichero"] for m in informe["media_huerfana"]["lista"]]
    assert "images/Fantasma-image.png" in huerfanos
    assert "images/Juego-image.png" not in huerfanos, "esa si tiene su juego"


def test_un_juego_renombrado_no_deja_su_media_como_huerfana(tmp_path):
    """El nombre de la media se puede haber cortado: se busca por prefijo."""
    base = _roms(tmp_path)
    (base / "Super Mario World (USA).smc").write_bytes(b"A" * 100)
    (base / "images").mkdir()
    (base / "images" / "Super Mario World (USA)-image.png").write_bytes(b"x" * 10)

    informe = library.auditoria(str(tmp_path / "roms"), ["snes"], _exts("snes"))

    assert informe["media_huerfana"]["total"] == 0


# ── La cuarentena ───────────────────────────────────────────────────────

def test_mover_a_cuarentena_no_borra_nada_y_se_deshace(tmp_path):
    """Lo que sobra se aparta, no se borra: y se puede volver."""
    base = _roms(tmp_path)
    (base / "Sobra.txt").write_text("notas", encoding="utf-8")
    root = str(tmp_path / "system")

    salida = library.cuarentena(str(tmp_path / "roms"), ["snes/Sobra.txt"], root=root)

    assert salida["ok"] is True
    assert len(salida["movidos"]) == 1
    assert not (base / "Sobra.txt").exists()
    cuarentena = tmp_path / "roms" / library.QUARANTINE / "snes" / "Sobra.txt"
    assert cuarentena.exists()

    vuelta = library.undo_last(root)

    assert vuelta["ok"] is True
    assert (base / "Sobra.txt").exists(), "el fichero vuelve a su sitio"


def test_la_cuarentena_no_sale_de_la_biblioteca(tmp_path):
    """Un `../` en la ruta no puede tocar ficheros de fuera."""
    fuera = tmp_path / "importante.txt"
    fuera.write_text("no tocar", encoding="utf-8")
    _roms(tmp_path)

    salida = library.cuarentena(str(tmp_path / "roms"), ["snes/../importante.txt"],
                                root=str(tmp_path / "system"))

    assert salida["ok"] is False
    assert salida["movidos"] == []
    assert fuera.exists()


def test_dos_juegos_con_el_mismo_nombre_no_se_pisan_en_la_cuarentena(tmp_path):
    """La cuarentena apila los nombres repetidos con un sufijo."""
    base = _roms(tmp_path)
    (base / "Juego.smc").write_bytes(b"A")
    (base / "images").mkdir()
    root = str(tmp_path / "system")
    destino = tmp_path / "roms" / library.QUARANTINE / "snes"

    library.cuarentena(str(tmp_path / "roms"), ["snes/Juego.smc"], root=root)
    # Se vuelve a poner un juego con el mismo nombre y se aparta otra vez.
    (base / "Juego.smc").write_bytes(b"B")
    library.cuarentena(str(tmp_path / "roms"), ["snes/Juego.smc"], root=root)

    assert (destino / "Juego.smc").exists()
    assert (destino / "Juego.smc.1").exists()


def test_una_cuarentena_vacia_no_deja_rastro_en_el_journal(tmp_path):
    """Una tanda que no movió nada no se puede deshacer: no llena el historial."""
    _roms(tmp_path)
    root = str(tmp_path / "system")

    salida = library.cuarentena(str(tmp_path / "roms"), ["snes/no_existe.txt"],
                                root=root)

    assert salida["ok"] is False
    assert library.journal_batches(root) == []


# ── El gamelist ─────────────────────────────────────────────────────────

def test_limpiar_el_gamelist_quita_las_fichas_rotas_y_se_deshace(tmp_path):
    """Se quitan las entradas cuyo fichero no esta, y se pueden reponer."""
    base = _roms(tmp_path)
    (base / "Existe.smc").write_bytes(b"A" * 100)
    original = ("<gameList><game><path>./Existe.smc</path></game>"
                "<game><path>./Fantasma.smc</path></game></gameList>")
    (base / "gamelist.xml").write_text(original, encoding="utf-8")
    root = str(tmp_path / "system")

    salida = library.limpiar_gamelist(str(tmp_path / "roms"), "snes", root=root)

    assert salida["ok"] is True
    assert salida["quitadas"] == 1
    texto = (base / "gamelist.xml").read_text(encoding="utf-8")
    assert "Fantasma.smc" not in texto
    assert "Existe.smc" in texto

    library.undo_last(root)

    assert (base / "gamelist.xml").read_text(encoding="utf-8") == original


def test_limpiar_el_gamelist_de_un_sistema_que_no_existe_da_error(tmp_path):
    """Si no hay gamelist, se dice en vez de inventarse nada."""
    _roms(tmp_path)

    salida = library.limpiar_gamelist(str(tmp_path / "roms"), "snes",
                                       root=str(tmp_path / "system"))

    assert salida["ok"] is False
    assert salida["error"]


def test_el_journal_guarda_las_tandas(appmod, tmp_path):
    """Cada tanda queda en el journal: se puede deshacer y se ve el historial."""
    base = _roms(tmp_path)
    (base / "Sobra.txt").write_text("notas", encoding="utf-8")
    root = str(tmp_path / "system")

    library.cuarentena(str(tmp_path / "roms"), ["snes/Sobra.txt"], root=root)

    tandas = library.journal_batches(root)
    assert len(tandas) == 1
    assert tandas[0]["count"] == 1
    assert tandas[0]["files"] == ["Sobra.txt"]
    # El journal esta en disco y es JSON.
    contenido = json.loads((tmp_path / "system" / library.JOURNAL_NAME)
                           .read_text(encoding="utf-8"))
    assert contenido[0]["tipo"] == "cuarentena"


# ── El resumen de la aplicacion ─────────────────────────────────────────

def _settings(appmod, tmp_path):
    """Los ajustes con las rutas del temporal."""
    ajustes = dict(appmod.DEFAULT_SETTINGS)
    ajustes["roms_base"] = str(tmp_path / "roms")
    ajustes["tools_base"] = str(tmp_path / "system")
    return ajustes


def test_el_resumen_de_la_biblioteca_cuenta_sistemas_y_juegos(appmod, tmp_path):
    """El resumen es rapido: no hashea nada."""
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 100)
    (base / "Otro.smc").write_bytes(b"B" * 100)
    ajustes = _settings(appmod, tmp_path)

    sistemas = appmod.library_sistemas(ajustes)

    assert len(sistemas) == 1
    assert sistemas[0]["nombre"] == "snes"
    assert sistemas[0]["juegos"] == 2
    assert sistemas[0]["bytes"] == 200


def test_la_auditoria_de_la_aplicacion_usa_las_extensiones_del_sistema(appmod,
                                                                       tmp_path):
    """Un `.txt` no cuenta como juego: lo decide el sistema, no el modulo."""
    base = _roms(tmp_path)
    (base / "Juego.smc").write_bytes(b"A" * 100)
    (base / "notas.txt").write_text("x", encoding="utf-8")
    ajustes = _settings(appmod, tmp_path)

    informe = appmod.library_auditoria(ajustes)

    assert informe["resumen"]["juegos"] == 1
    assert informe["sobras"]["total"] == 1


# ── El enrutador ────────────────────────────────────────────────────────

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
    """Llama al enrutador de la biblioteca y devuelve lo que responde."""
    peticion = _Peticion(path, comando, cuerpo)
    partes = [p for p in path.split("/") if p]
    appmod.BatoceraHandler._library(peticion, settings, path, partes)
    return peticion


def test_el_endpoint_del_resumen(appmod, tmp_path):
    """`GET /api/library/summary` devuelve el resumen."""
    base = _roms(tmp_path)
    (base / "Uno.smc").write_bytes(b"A" * 100)
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/summary")

    assert peticion.out["ok"] is True
    assert peticion.out["juegos"] == 1
    assert peticion.out["sistemas"][0]["nombre"] == "snes"


def test_el_endpoint_de_la_auditoria_arranca_un_trabajo(appmod, tmp_path):
    """La auditoría va en segundo plano: devuelve el id del trabajo."""
    _roms(tmp_path)
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/audit/start")

    assert peticion.out["ok"] is True
    assert peticion.out["job"]
    trabajo = appmod._rt_jobs.JOBS.obtener(peticion.out["job"])
    assert trabajo is not None
    # El trabajo termina y devuelve la radiografia.
    for _ in range(100):
        if trabajo.estado != "trabajando":
            break
        import time
        time.sleep(0.05)
    assert trabajo.estado == "listo"
    assert trabajo.resultado["resumen"]["sistemas"] == 1


def test_el_endpoint_del_trabajo(appmod, tmp_path):
    """`GET /api/library/job?id=` devuelve el estado del trabajo."""
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/job?id=inventado")

    assert peticion.status == 404
    assert peticion.out["ok"] is False


def test_el_endpoint_de_la_cuarentena(appmod, tmp_path):
    """Mover ficheros a la cuarentena por la API."""
    base = _roms(tmp_path)
    (base / "Sobra.txt").write_text("notas", encoding="utf-8")
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/quarantine", "POST",
                        {"ficheros": ["snes/Sobra.txt"]})

    assert peticion.out["ok"] is True
    assert not (base / "Sobra.txt").exists()


def test_el_endpoint_de_la_cuarentena_pide_ficheros(appmod, tmp_path):
    """Sin ficheros no hay nada que hacer: se dice."""
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/quarantine", "POST", {})

    assert peticion.out["ok"] is False


def test_el_endpoint_de_limpiar_el_gamelist(appmod, tmp_path):
    """Limpiar el gamelist de un sistema, por la API."""
    base = _roms(tmp_path)
    (base / "gamelist.xml").write_text(
        "<gameList><game><path>./Fantasma.smc</path></game></gameList>",
        encoding="utf-8")
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/gamelist/clean", "POST",
                        {"sistema": "snes"})

    assert peticion.out["ok"] is True
    assert peticion.out["quitadas"] == 1


def test_el_endpoint_de_deshacer(appmod, tmp_path):
    """Deshacer devuelve los ficheros a su sitio."""
    base = _roms(tmp_path)
    (base / "Sobra.txt").write_text("notas", encoding="utf-8")
    ajustes = _settings(appmod, tmp_path)
    _llamar(appmod, ajustes, "/api/library/quarantine", "POST",
            {"ficheros": ["snes/Sobra.txt"]})

    peticion = _llamar(appmod, ajustes, "/api/library/undo", "POST", {})

    assert peticion.out["ok"] is True
    assert (base / "Sobra.txt").exists()


def test_una_ruta_desconocida_da_error(appmod, tmp_path):
    """Si la ruta no existe, se dice (y con codigo 404)."""
    ajustes = _settings(appmod, tmp_path)

    peticion = _llamar(appmod, ajustes, "/api/library/inventado")

    assert peticion.status == 404
    assert peticion.out["ok"] is False


# ── La interfaz ─────────────────────────────────────────────────────────

def _texto(ruta_relativa):
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent
    return (raiz / "frontend" / "src" / ruta_relativa).read_text(encoding="utf-8")


def test_la_pagina_de_roms_avisa_del_progreso(appmod):
    """La auditoría tarda: la pagina tiene que enseñar la barra."""
    h = _texto("pages/Roms.tsx")
    assert "Progress" in h
    assert "api.libraryJob(" in h
    assert "no hace falta cerrar la ventana" in h


def test_la_pagina_de_roms_no_borra_nada(appmod):
    """Lo que sobra va a la cuarentena, y se puede deshacer."""
    h = _texto("pages/Roms.tsx")
    assert "api.libraryQuarantine(" in h
    assert "api.libraryUndo()" in h
    assert "api.libraryGamelistClean(" in h


def test_la_seccion_roms_y_bios_tiene_dos_pestanas(appmod):
    """La ruta `/roms` ya no es solo la pagina de BIOS."""
    h = _texto("pages/RomsBios.tsx")
    assert "RomsPage" in h and "BiosPage" in h
    assert _texto("components/layout/SectionTabs.tsx").count("key: 'roms'") == 1
