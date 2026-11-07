"""Tests del contrato de la seccion Herramientas (backend).

La seccion se reescribio: las conversiones ya no son etiquetas de texto sino
identificadores, y hay un endpoint de conversion en lote. Estos tests fijan
ese contrato.
"""

import struct
import time

import pytest


def _settings(tmp_path):
    return {"roms_base": str(tmp_path / "roms"),
            "tools_base": str(tmp_path / "system")}


def _snes(tmp_path):
    """Una carpeta de snes con una ROM y dos ficheros que no son juegos."""
    base = tmp_path / "roms" / "snes"
    base.mkdir(parents=True)
    cabecera = bytearray(512)
    cabecera[0x08:0x0A] = b"\xaa\xbb"
    (base / "Juego (USA).smc").write_bytes(bytes(cabecera) + bytes(range(256)) * 4)
    (base / "_info.txt").write_text("no es un juego", encoding="utf-8")
    (base / "gamelist.xml").write_text("<gameList/>", encoding="utf-8")
    (base / "partida.srm").write_bytes(b"guardada")
    return base


def _iso(base, nombre="Juego.iso"):
    """Un ISO 9660 minimo en la carpeta del sistema."""
    ruta = base / nombre
    with open(ruta, "wb") as fh:
        for i in range(24):
            sector = bytearray(2048)
            if i == 16:
                sector[0] = 1
                sector[1:6] = b"CD001"
                sector[6] = 1
            fh.write(bytes(sector))
    return ruta


# ── Los ficheros de un sistema ───────────────────────────────────────────

def test_los_ficheros_traen_las_conversiones_estructuradas(appmod, tmp_path):
    """Cada fichero dice a que se puede convertir, con identificadores."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    ficheros = appmod.tools_rom_files(settings, "snes")

    assert len(ficheros) == 1, "solo el .smc es un juego"
    juego = ficheros[0]
    assert juego["name"] == "Juego (USA).smc"
    assert juego["kind"] == "snes-smc"
    assert juego["label"]
    ids = [accion["id"] for accion in juego["acciones"]]
    assert "sfc" in ids and "fig" in ids
    for accion in juego["acciones"]:
        assert set(accion) >= {"id", "label"}


def test_los_ficheros_que_no_son_juegos_no_se_listan(appmod, tmp_path):
    """Las notas, la gamelist y las guardadas no son juegos."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    nombres = [f["name"] for f in appmod.tools_rom_files(settings, "snes")]

    assert "_info.txt" not in nombres
    assert "gamelist.xml" not in nombres
    assert "partida.srm" not in nombres


# ── Convertir un fichero ────────────────────────────────────────────────

def test_convertir_un_fichero(appmod, tmp_path):
    """La conversion suelta devuelve donde ha quedado el fichero nuevo."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    salida = appmod.tools_convert(settings, "snes", "Juego (USA).smc", "sfc")

    assert salida["ok"] is True
    assert salida["out"].endswith(".sfc")
    assert salida["size"] > 0
    assert (tmp_path / "roms" / "snes" / "Juego (USA).sfc").exists()


def test_convertir_un_fichero_inexistente_da_error(appmod, tmp_path):
    """Si el fichero no esta, se dice."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    with pytest.raises(ValueError):
        appmod.tools_convert(settings, "snes", "NoEsta.smc", "sfc")


def test_convertir_a_un_destino_imposible_da_error(appmod, tmp_path):
    """Un destino que el formato no admite se explica, no se simula."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    with pytest.raises(ValueError):
        appmod.tools_convert(settings, "snes", "Juego (USA).smc", "chd")


# ── Convertir en lote ────────────────────────────────────────────────────

def test_convertir_en_lote(appmod, tmp_path):
    """El lote convierte lo que admite el destino y cuenta lo que hizo."""
    base = _snes(tmp_path)
    _iso(base, "Cosa.iso")
    settings = _settings(tmp_path)

    salida = appmod.tools_convert_batch(settings, "snes", "sfc")

    assert salida["ok"] is True
    assert salida["resumen"]["total"] == 1
    assert salida["resumen"]["hechos"] == 1
    assert salida["resumen"]["fallos"] == 0
    assert salida["hechos"][0]["file"] == "Juego (USA).smc"
    assert salida["hechos"][0]["ok"] is True


def test_el_lote_solo_convierte_lo_que_admite_el_destino(appmod, tmp_path):
    """Un ISO no se convierte a SMC: el lote se lo salta."""
    base = _snes(tmp_path)
    _iso(base, "Cosa.iso")
    settings = _settings(tmp_path)

    salida = appmod.tools_convert_batch(settings, "snes", "smc")

    assert salida["resumen"]["total"] == 0


def test_el_lote_puede_filtrar_por_formato(appmod, tmp_path):
    """Con filtro, solo entran los ficheros de ese formato."""
    base = _snes(tmp_path)
    _iso(base, "Cosa.iso")
    settings = _settings(tmp_path)

    salida = appmod.tools_convert_batch(settings, "snes", "zip",
                                         kind="iso-gamecube")

    assert salida["resumen"]["total"] == 0


def test_el_lote_avisa_de_los_ficheros_que_fallan(appmod, tmp_path):
    """Un fallo en un fichero no para el lote: se cuenta y se explica."""
    base = _snes(tmp_path)
    (base / "Roto.smc").write_bytes(b"")
    settings = _settings(tmp_path)

    salida = appmod.tools_convert_batch(settings, "snes", "sfc")

    assert salida["resumen"]["total"] == 2
    assert salida["resumen"]["fallos"] == 1
    fallidos = [h for h in salida["hechos"] if not h["ok"]]
    assert fallidos[0]["error"]


#: El DAT de Wii: el codigo de juego va en el serial.
_WII_DATOS = [
    {"name": "Excite Truck (USA)", "description": "Excite Truck (USA)",
     "serial": "RVL-REXE-USA", "region": "USA", "roms": []},
    {"name": "Excite Truck (Europe)", "description": "Excite Truck (Europe)",
     "serial": "RVL-REXP-EUR", "region": "Europe", "roms": []},
]


def _wbfs_wii(codigo="REXP01", titulo="Excite Truck"):
    """Un volcado de Wii con la informacion del disco."""
    head = bytearray(0x400)
    head[0:4] = b"WBFS"
    base = 0x200
    head[base:base + 6] = codigo.encode("ascii")
    head[base + 0x1C:base + 0x20] = bytes.fromhex("5d1c9ea3")
    head[base + 0x20:base + 0x20 + len(titulo)] = titulo.encode("ascii")
    head[base + 0xEC:base + 0xF0] = b"MD5#"
    head[base + 0xF0:base + 0x100] = bytes.fromhex(
        "5fd682d8ef74b90f8d538f92a75318a1")
    return bytes(head) + b"\x00" * 4096


# ── Los DAT ──────────────────────────────────────────────────────────────

def test_el_estado_de_los_dats_dice_como_se_resolvieron(appmod, tmp_path,
                                                        monkeypatch):
    """Cada sistema dice si su DAT viene del mapa o se resolvio por nombre."""
    monkeypatch.setattr(appmod, "tools_catalogo", lambda *a, **k: [])
    monkeypatch.setattr(appmod, "tools_sistemas",
                        lambda *a, **k: [{"name": "snes", "fullname": "Super Nintendo"},
                                        {"name": "inventado", "fullname": "Inventado"}])

    estado = appmod.tools_dats_status(_settings(tmp_path))

    assert estado["ok"] is True
    sistemas = {item["system"]: item for item in estado["sistemas"]}
    assert "snes" in sistemas
    assert sistemas["snes"]["resuelto"] == "mapa"
    assert sistemas["snes"]["confianza"] == 1.0
    assert sistemas["snes"]["dat"]
    # Un sistema que no existe no aparece: el frontend lo dice solo.
    assert "inventado" not in sistemas


def test_el_plan_de_wii_encuentra_los_juegos_que_viven_en_carpeta(appmod, tmp_path,
                                                                   monkeypatch):
    """En Wii cada juego es una carpeta con el volcado dentro."""
    base = tmp_path / "roms" / "wii"
    carpeta = base / "Excite Truck [REXP01]"
    carpeta.mkdir(parents=True)
    (carpeta / "REXP01.wbfs").write_bytes(_wbfs_wii())
    indice = appmod._rt_dats.build_index(_WII_DATOS)
    monkeypatch.setattr(appmod._rt_dats, "load_index", lambda *a, **k: indice)

    plan = appmod.tools_rename_plan(_settings(tmp_path), "wii")

    items = plan["items"]
    assert len(items) == 1
    assert items[0]["carpeta"] == "Excite Truck [REXP01]"
    assert items[0]["method"] == "gamecode"
    assert items[0]["proposed"] == "Excite Truck (Europe) [REXP01]"


def test_al_renombrar_se_actualiza_el_gamelist(appmod, tmp_path):
    """El endpoint de renombrado deja el gamelist.xml al día."""
    base = tmp_path / "roms" / "snes"
    base.mkdir(parents=True)
    (base / "images").mkdir()
    (base / "Juego.smc").write_bytes(b"ROM")
    (base / "images" / "Juego-image.png").write_bytes(b"PNG")
    (base / "gamelist.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gameList><game><path>./Juego.smc</path><name>Juego</name>'
        '<image>./images/Juego-image.png</image></game></gameList>\n',
        encoding="utf-8")
    settings = _settings(tmp_path)

    # Un plan con un solo renombrado, sin necesitar el DAT.
    plan = {"items": [{"file": "Juego.smc", "proposed": "Juego (USA).smc",
                       "action": "renombrar", "companions": []}]}
    monkey = getattr(appmod, "_rt_rename", None)
    assert monkey is not None

    salida = appmod._rt_rename.apply_plan(plan, str(base),
                                           root=str(tmp_path / "journal"))

    assert salida["ok"] is True
    assert (base / "Juego (USA).smc").exists()
    assert (base / "images" / "Juego (USA)-image.png").exists()
    gamelist = (base / "gamelist.xml").read_text(encoding="utf-8")
    assert "./Juego (USA).smc" in gamelist
    assert "./images/Juego (USA)-image.png" in gamelist


# ── El plan en segundo plano, con progreso ────────────────────────────────

class _HandlerFalso:
    """El enrutador de `/api/tools` sin levantar el servidor entero."""

    command = "GET"

    def __init__(self, path, cuerpo=None):
        self.path = path
        self.cuerpo = cuerpo or {}
        self.respondido = None

    def read_json(self):
        return self.cuerpo

    def send_json(self, data, code=200):
        self.respondido = (code, data)


def _espera(trabajo):
    for _ in range(300):
        if trabajo.estado != "trabajando":
            break
        time.sleep(0.01)
    return trabajo


def test_el_plan_avisa_del_progreso(appmod, tmp_path):
    """El calculo del plan va contando lo que lleva hecho."""
    _snes(tmp_path)
    settings = _settings(tmp_path)
    estados = []

    appmod.tools_rename_plan(settings, "snes", progreso=estados.append)

    assert estados, "el plan tiene que avisar del progreso"
    assert estados[-1]["porcentaje"] == 100
    assert estados[-1]["total"] == 1


def test_el_endpoint_arranca_el_plan_en_segundo_plano(appmod, tmp_path):
    """`rename/plan/start` arranca un trabajo y `rename/job` lo consulta."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    arranque = _HandlerFalso("/api/tools/rename/plan/start?system=snes")
    appmod.BatoceraHandler._tools(arranque, settings,
                                  "/api/tools/rename/plan/start", [])

    codigo, datos = arranque.respondido
    assert codigo == 200
    assert datos["ok"] is True
    trabajo = _espera(appmod._rt_jobs.JOBS.obtener(datos["job"]))
    assert trabajo.estado == "listo"

    consulta = _HandlerFalso(f"/api/tools/rename/job?id={datos['job']}")
    appmod.BatoceraHandler._tools(consulta, settings, "/api/tools/rename/job", [])

    codigo, estado = consulta.respondido
    assert codigo == 200
    assert estado["estado"] == "listo"
    assert estado["resultado"]["stats"]["total"] == 1


def test_el_endpoint_del_trabajo_que_no_existe(appmod, tmp_path):
    """Preguntar por un trabajo que no esta da error, no un fallo raro."""
    settings = _settings(tmp_path)

    consulta = _HandlerFalso("/api/tools/rename/job?id=inventado")
    appmod.BatoceraHandler._tools(consulta, settings, "/api/tools/rename/job", [])

    codigo, datos = consulta.respondido
    assert codigo == 404
    assert datos["ok"] is False


def test_el_endpoint_de_aplicar_arranca_un_trabajo(appmod, tmp_path):
    """`rename/apply/start` tambien va en segundo plano."""
    _snes(tmp_path)
    settings = _settings(tmp_path)

    arranque = _HandlerFalso("/api/tools/rename/apply/start")
    arranque.command = "POST"
    arranque.cuerpo = {"system": "snes"}
    appmod.BatoceraHandler._tools(arranque, settings,
                                  "/api/tools/rename/apply/start", [])

    codigo, datos = arranque.respondido
    assert codigo == 200
    assert datos["ok"] is True
    trabajo = _espera(appmod._rt_jobs.JOBS.obtener(datos["job"]))
    assert trabajo.estado == "listo"
    assert trabajo.as_dict()["resultado"]["ok"] is True
