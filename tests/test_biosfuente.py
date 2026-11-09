"""Tests de la fuente de BIOS: el indice, el emparejamiento y la descarga.

El catalogo de Batocera dice que BIOS hace falta en cada sistema, pero no las
trae. La fuente de BIOS es un indice de directorios con las BIOS en la misma
disposicion en que Batocera las espera, asi que descargarlas es copiarlas a su
sitio.

Estos tests fijan lo que importa:

- el indice se construye **dirigido** (solo las carpetas que hacen falta), que
  es lo que hace que tarde segundos y no minutos en la consola;
- el emparejamiento va por ruta exacta, luego ignorando mayusculas y por
  ultimo por nombre de fichero;
- **lo que no esta en la fuente no se inventa**: se informa;
- la descarga deja cada BIOS en su sitio y avisa del progreso.
"""

from romtools import biosfuente


# ── Utilidades ──────────────────────────────────────────────────────────

INDICE = """<html><body>
<table>
<tr><td><a href="?C=N;O=D">Name</a></td></tr>
<tr><td><a href="/update/Batocera/">Parent Directory</a></td></tr>
<tr><td><a href="Acorn/">Acorn/</a></td></tr>
<tr><td><a href="bbc.zip">bbc.zip</a></td></tr>
<tr><td><a href="7800%20BIOS%20(E).rom">7800 BIOS (E).rom</a></td></tr>
</table>
</body></html>
"""


class FuenteFalsa(biosfuente.Fuente):
    """Una fuente que no sale de casa: el indice y los ficheros van en un mapa."""

    def __init__(self, carpetas=None, ficheros=None):
        super().__init__(url="http://ejemplo.test/bios/")
        self.carpetas = carpetas or {}
        self.ficheros = ficheros or {}
        self.pedidas = []

    def listar(self, carpeta=""):
        self.pedidas.append(carpeta)
        return list(self.carpetas.get(carpeta, []))

    def _leer(self, url):
        # La URL acaba con la ruta codificada: se deshace para buscar el fichero.
        from urllib.parse import unquote
        ruta = unquote(url.replace("http://ejemplo.test/bios/", ""))
        if ruta not in self.ficheros:
            raise OSError("no existe: " + ruta)
        return self.ficheros[ruta]


# ── El indice ───────────────────────────────────────────────────────────

def test_se_parsea_el_indice_de_un_directorio():
    nombres = biosfuente.parse_indice(INDICE)
    assert "Acorn/" in nombres
    assert "bbc.zip" in nombres
    assert "7800%20BIOS%20(E).rom" in nombres
    # Ni los enlaces de orden de columnas ni la carpeta padre.
    assert not any(n.startswith("?") for n in nombres)
    assert not any(n.startswith("/") for n in nombres)


def test_solo_se_indexan_las_carpetas_que_hacen_falta():
    fuente = FuenteFalsa(carpetas={
        "": ["Acorn/", "bbc.zip"],
        "Acorn/": ["basic2.rom"],
    })
    fuente.indexar(["Acorn/basic2.rom", "bbc.zip"])
    # La raiz (para el emparejamiento por nombre) y la carpeta que hace falta.
    assert fuente.pedidas == ["", "Acorn/"]
    assert "Acorn/basic2.rom" in fuente.index
    assert "bbc.zip" in fuente.index


def test_una_carpeta_que_no_existe_no_rompe():
    fuente = FuenteFalsa(carpetas={"": ["Acorn/"]})
    fuente.indexar(["BBCMicro/os12.rom"])
    # La carpeta no existe: no hay nada ahi, pero tampoco error.
    assert fuente.index == {}


# ── El emparejamiento ───────────────────────────────────────────────────

def test_se_empareja_por_ruta_exacta():
    fuente = FuenteFalsa(carpetas={"": [], "bk/": ["DISK_327.ROM"]})
    fuente.indexar(["bk/DISK_327.ROM"])
    assert fuente.emparejar("bk/DISK_327.ROM") == "bk/DISK_327.ROM"


def test_se_empareja_ignorando_mayusculas():
    fuente = FuenteFalsa(carpetas={"": [], "bk/": ["DISK_327.ROM"]})
    fuente.indexar(["bk/disk_327.rom"])
    assert fuente.emparejar("bk/disk_327.rom") == "bk/DISK_327.ROM"


def test_se_empareja_por_nombre_de_fichero():
    """Si la BIOS esta en la raiz de la fuente, se usa esa."""
    fuente = FuenteFalsa(carpetas={"": ["basic2.rom"], "Acorn/": []})
    fuente.indexar(["Acorn/basic2.rom"])
    assert fuente.emparejar("Acorn/basic2.rom") == "basic2.rom"


def test_lo_que_no_esta_en_la_fuente_no_se_inventa():
    fuente = FuenteFalsa(carpetas={"": [], "Acorn/": ["basic2.rom"]})
    fuente.indexar(["BBCMicro/os12.rom"])
    assert fuente.emparejar("BBCMicro/os12.rom") is None


# ── Las rutas ───────────────────────────────────────────────────────────

def test_se_rechazan_las_rutas_peligrosas():
    assert biosfuente.ruta_valida("bk/DISK_327.ROM")
    assert biosfuente.ruta_valida("basic2.rom")
    assert not biosfuente.ruta_valida("/etc/passwd")
    assert not biosfuente.ruta_valida("../../etc/passwd")
    assert not biosfuente.ruta_valida("bk/../../etc/passwd")
    assert not biosfuente.ruta_valida("")
    assert not biosfuente.ruta_valida("C:/Windows")


# ── La descarga ─────────────────────────────────────────────────────────

def test_se_descargan_las_bios_que_faltan_y_se_avisa_del_progreso(tmp_path):
    fuente = FuenteFalsa(
        carpetas={"": [], "bk/": ["DISK_327.ROM"]},
        ficheros={"bk/DISK_327.ROM": b"contenido de la bios"},
    )
    estados = []
    resultado = biosfuente.bajar_faltantes(
        str(tmp_path),
        [{"file": "bk/DISK_327.ROM"}, {"file": "BBCMicro/os12.rom"}],
        fuente=fuente,
        progreso=lambda estado: estados.append(dict(estado)),
    )

    assert resultado["ok"] is True
    assert resultado["total"] == 2
    # La que esta en la fuente se descarga; la otra no se inventa.
    assert [d["file"] for d in resultado["descargadas"]] == ["bk/DISK_327.ROM"]
    assert resultado["no_encontradas"] == ["BBCMicro/os12.rom"]
    assert resultado["fallidas"] == []

    # El progreso se ha ido avisando (y termina al 100 %).
    assert estados
    assert estados[-1]["porcentaje"] == 100
    assert estados[-1]["terminado"] is True


def test_lo_que_ya_esta_no_se_toca(tmp_path):
    """Solo se baja lo que falta: una ruta invalida se ignora."""
    fuente = FuenteFalsa(carpetas={"": ["bbc.zip"]}, ficheros={"bbc.zip": b"zip"})
    resultado = biosfuente.bajar_faltantes(
        str(tmp_path),
        [{"file": "bbc.zip"}, {"file": "../fuera.zip"}],
        fuente=fuente,
    )
    assert [d["file"] for d in resultado["descargadas"]] == ["bbc.zip"]
    assert resultado["no_encontradas"] == []


def test_un_fichero_que_no_se_puede_bajar_no_tumba_el_resto(tmp_path):
    fuente = FuenteFalsa(
        carpetas={"": [], "bk/": ["DISK_327.ROM", "OTRO.ROM"]},
        ficheros={"bk/DISK_327.ROM": b"contenido"},
    )
    resultado = biosfuente.bajar_faltantes(
        str(tmp_path),
        [{"file": "bk/DISK_327.ROM"}, {"file": "bk/OTRO.ROM"}],
        fuente=fuente,
    )
    assert [d["file"] for d in resultado["descargadas"]] == ["bk/DISK_327.ROM"]
    assert [f["file"] for f in resultado["fallidas"]] == ["bk/OTRO.ROM"]
    assert resultado["ok"] is True


def test_la_fuente_por_defecto_es_la_del_usuario():
    assert biosfuente.FUENTE_BIOS == (
        "http://rgsretro1986.ds78102.seedhost.eu/update/Batocera/bios/")
