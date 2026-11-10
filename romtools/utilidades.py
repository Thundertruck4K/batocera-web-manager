"""Las utilidades de conversion que el instalador pone por su cuenta.

Las utilidades externas que el manager puede usar (el ``rom-converto``, el
``nodtool`` y el ``3dstool``) se descargan de la release oficial de cada
proyecto, se comprueban con su suma ``sha256`` y se copian a una carpeta que
sobrevive a los reinicios (``/userdata/system/bin`` en la consola).

Lo que no se puede instalar solo queda documentado con el motivo: o no hay
binario de Linux publicado, o el que hay depende de otra cosa, o el manager
ya lo hace en Python y el binario sobra.

Los datos de cada utilidad (version, asset y suma) estan fijados aqui a
proposito: no se descargan de la red, para que un release que cambiase no
pudiese colar un binario distinto del esperado.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tarfile
import time
import urllib.error
import urllib.request

#: Donde vive el ``/userdata/system`` de la consola.
BASE_POR_DEFECTO = "/userdata/system"

#: Carpeta (dentro del base) donde se dejan los binarios.
CARPETA_BIN = "bin"

#: Fichero donde se apunta que hay instalado y de que version.
FICHERO_MANIFIESTO = ".utilidades.json"

#: Cuanto se espera a la descarga antes de darla por fallida.
TIMEOUT_DESCARGA = 900

#: Tamano de los trozos con los que se descarga (no se carga todo en memoria).
TAMANO_TROZO = 262144

#: Como se llama cada arquitectura de la maquina. En la consola puede ser
#: ``x86_64``, ``aarch64`` o ``armv7l``.
ARQUITECTURAS = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "armv7l": "armv7l",
    "armv7": "armv7l",
    "armhf": "armv7l",
    "i386": "i686",
    "i486": "i686",
    "i586": "i686",
    "i686": "i686",
}


def arquitectura() -> str:
    """La arquitectura de esta maquina, en el nombre que usa la tabla."""
    return ARQUITECTURAS.get(platform.machine().lower(), "")


#: Las utilidades que se pueden instalar solas. Cada una dice de que
#: release sale, que asset es el de esta arquitectura y cual es su sha256.
UTILIDADES = (
    {
        "id": "rom-converto",
        "nombre": "rom-converto",
        "binario": "rom-converto",
        "proyecto": "DevYukine/rom-converto",
        "version": "v0.24.0",
        "licencia": "MIT",
        "para": "La mas completa: CSO, ZSO, CHD, RVZ, WBFS, WIA, GCZ, XISO, NSP, XCI, 3DS, PBP y ZAR.",
        "formato": "binario",
        "assets": {
            "x86_64": ("rom-converto-cli-linux-x64",
                       "0d4abd56cfec477ff447f68b656d45ca48f670f464363bca2d895b1eee2c356d"),
            "aarch64": ("rom-converto-cli-linux-arm64",
                        "990286bc3367342b0e04ab6dd0d28d8e95c3133ac2b4c5d6440a119e541b0b43"),
            "armv7l": ("rom-converto-cli-linux-arm7",
                       "00b4cf7a454ae4539459cc5f908f3b42603b59b1035b8b046c6ef5ae1982247f"),
        },
    },
    {
        "id": "nodtool",
        "nombre": "nodtool (nod)",
        "binario": "nodtool",
        "proyecto": "encounter/nod",
        "version": "v2.0.0-alpha.12",
        "licencia": "Apache-2.0",
        "para": "Crea y extrae los comprimidos de Dolphin: CISO, GCZ, RVZ, WBFS, WIA y GCM.",
        "formato": "binario",
        "assets": {
            "x86_64": ("nodtool-linux-x86_64",
                       "ee8345c004248eb82a86dd0c6068e0fcf3dc75baf68d18fe949bf4589822f5a5"),
            "aarch64": ("nodtool-linux-aarch64",
                        "33e801c0e4aee7e714ad84e89521f50e2f79005571b9d4779b695e44ea21ff99"),
            "i686": ("nodtool-linux-i686",
                     "efaa034f4d32a14856d5150c7eee45876ec38c07f75572cb6b4c33423c5850ce"),
        },
    },
    {
        "id": "3dstool",
        "nombre": "3dstool",
        "binario": "3dstool",
        "proyecto": "dnasdw/3dstool",
        "version": "v1.2.6",
        "licencia": "MIT",
        "para": "Empaqueta el contenido de un 3DS en un CIA.",
        "formato": "tar.gz",
        "miembro": "3dstool",
        "assets": {
            "x86_64": ("3dstool_linux_x86_64.tar.gz",
                       "d42e3de7766ee552b3609ac5acb7ad3f07209dd91bc45a21d3fc2b049790ede2"),
        },
    },
)


#: Las que no se pueden instalar solas, con el motivo de por que.
NO_INSTALABLES = (
    {
        "id": "dolphin-tool",
        "nombre": "dolphin-tool",
        "proyecto": "https://github.com/dolphin-emu/dolphin",
        "motivo": "No hay release con binarios: hay que compilarlo. El dolphin-emu de Batocera es la interfaz grafica y no construye la herramienta de linea de comandos.",
    },
    {
        "id": "wiitool",
        "nombre": "wiitool",
        "proyecto": "https://github.com/dolphin-emu/dolphin",
        "motivo": "No hay release con binarios: hay que compilarlo. Los enlaces que se znajaron al repositorio no dan a ningun release oficial.",
    },
    {
        "id": "ndstool",
        "nombre": "ndstool",
        "proyecto": "https://github.com/blocksds/ndstool",
        "motivo": "No hay release con binarios: hay que compilarlo. El unico precompilado va dentro del paquete de BlocksDS y necesita el cargador musl de /opt/wonderful, asi que no funciona solo.",
    },
    {
        "id": "extract-xiso",
        "nombre": "extract-xiso",
        "proyecto": "https://github.com/XboxDev/extract-xiso",
        "motivo": "El repositorio no declara licencia, asi que no se instala solo. Ademas el manager ya extrae el XDVDF en Python.",
    },
    {
        "id": "maxcso",
        "nombre": "maxcso",
        "proyecto": "https://github.com/unknownbrackets/maxcso",
        "motivo": "La release solo trae el binario de Windows. El manager ya comprime en CSO, CSO2, ZSO y DAX en Python.",
    },
    {
        "id": "xorriso",
        "nombre": "xorriso",
        "proyecto": "https://www.gnu.org/software/xorriso/",
        "motivo": "Esta en el buildroot de Batocera pero no esta habilitado en su build: hay que compilarlo.",
    },
    {
        "id": "cdrdao",
        "nombre": "cdrdao",
        "proyecto": "https://cdrdao.sourceforge.net/",
        "motivo": "No hay binario precompilado para descargar. El manager ya convierte NRG, MDS, CCD e IMG en Python.",
    },
    {
        "id": "makecue",
        "nombre": "makecue",
        "proyecto": "https://www.makecue.org/",
        "motivo": "No hay binario precompilado para descargar. El manager escribe el CUE el mismo.",
    },
)


def por_id(identificador: str) -> dict | None:
    """La utilidad de ese id, si existe."""
    for entrada in UTILIDADES:
        if entrada["id"] == identificador:
            return entrada
    return None


def utilidades_dir(base: str = "") -> str:
    """La carpeta donde se dejan los binarios."""
    return os.path.join(base or BASE_POR_DEFECTO, CARPETA_BIN)


def disponibles(arq: str = "") -> list[dict]:
    """Las utilidades que tienen binario para esta arquitectura."""
    arq = arq or arquitectura()
    return [entrada for entrada in UTILIDADES if arq in entrada["assets"]]


def no_instalables() -> list[dict]:
    """Las utilidades que no se pueden instalar solas y por que."""
    return list(NO_INSTALABLES)


def url_de(entrada: dict, asset: str) -> str:
    """De donde se descarga el asset de la release."""
    return ("https://github.com/%s/releases/download/%s/%s"
            % (entrada["proyecto"], entrada["version"], asset))


def _sha256(ruta: str) -> str:
    """La suma sha256 de un fichero, leido a trozos."""
    suma = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for trozo in iter(lambda: fh.read(TAMANO_TROZO), b""):
            suma.update(trozo)
    return suma.hexdigest()


def descarga(url: str, ruta: str, timeout: int = TIMEOUT_DESCARGA,
             progreso=None) -> int:
    """Descarga una URL a un fichero y devuelve cuantos bytes se han escrito.

    Va a trozos para no meter 30 MB en la memoria de la consola de golpe.
    """
    peticion = urllib.request.Request(url, headers={"User-Agent": "batocera-web-manager"})
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        total = 0
        try:
            total = int(respuesta.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            total = 0
        escritos = 0
        with open(ruta, "wb") as fh:
            while True:
                trozo = respuesta.read(TAMANO_TROZO)
                if not trozo:
                    break
                fh.write(trozo)
                escritos += len(trozo)
                if progreso:
                    progreso(escritos, total)
    return escritos


def _extrae_miembro(tarball: str, miembro: str, destino: str) -> None:
    """Saca un fichero de un tar.gz sin dejar salir nada mas."""
    with tarfile.open(tarball, "r:gz") as tar:
        encontrado = None
        for item in tar.getmembers():
            if item.name == miembro or item.name.endswith("/" + miembro):
                encontrado = item
                break
        if encontrado is None:
            raise RuntimeError("el archivo no contiene %s" % miembro)
        if not encontrado.isfile():
            raise RuntimeError("%s no es un fichero" % miembro)
        origen = tar.extractfile(encontrado)
        if origen is None:
            raise RuntimeError("no se puede leer %s" % miembro)
        with open(destino, "wb") as fh:
            shutil.copyfileobj(origen, fh)


def manifiesto(destino: str) -> dict:
    """Lo que el instalador sabe que hay puesto, leido del manifiesto."""
    ruta = os.path.join(destino, FICHERO_MANIFIESTO)
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def guardar_manifiesto(destino: str, datos: dict) -> None:
    """Apunta en el manifiesto lo que hay instalado."""
    os.makedirs(destino, exist_ok=True)
    ruta = os.path.join(destino, FICHERO_MANIFIESTO)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, ruta)


def instalada(entrada: dict, destino: str) -> bool:
    """Si el binario de esa utilidad esta ya puesto."""
    return os.path.isfile(os.path.join(destino, entrada["binario"]))


def instalar(entrada: dict, destino: str, timeout: int = TIMEOUT_DESCARGA,
             progreso=None, forzar: bool = False) -> dict:
    """Descarga e instala una utilidad. Devuelve un resumen de lo que paso.

    El resultado lleva ``estado``: ``instalada``, ``ya-estaba``, ``sin-binario``
    o ``error``.
    """
    arq = arquitectura()
    resumen = {
        "id": entrada["id"],
        "nombre": entrada["nombre"],
        "estado": "error",
        "detalle": "",
        "ruta": "",
        "version": entrada["version"],
    }
    destino = os.path.abspath(destino)
    os.makedirs(destino, exist_ok=True)
    final = os.path.join(destino, entrada["binario"])
    asset = entrada["assets"].get(arq)

    if instalada(entrada, destino) and not forzar:
        resumen["estado"] = "ya-estaba"
        resumen["detalle"] = "ya estaba en %s" % final
        resumen["ruta"] = final
        if asset:
            resumen["sha256"] = asset[1]
        return resumen

    if not asset:
        resumen["estado"] = "sin-binario"
        resumen["detalle"] = "no hay binario para %s" % (arq or "esta arquitectura")
        return resumen
    nombre_asset, esperado = asset

    url = url_de(entrada, nombre_asset)
    descargado = os.path.join(destino, ".%s.descargando" % entrada["id"])
    desempaquetado = os.path.join(destino, ".%s.binario" % entrada["id"])

    try:
        descarga(url, descargado, timeout=timeout, progreso=progreso)
        suma = _sha256(descargado)
        if suma != esperado:
            raise RuntimeError("la suma sha256 no coincide (esperaba %s, es %s)"
                               % (esperado, suma))
        if entrada.get("formato") == "tar.gz":
            _extrae_miembro(descargado, entrada["miembro"], desempaquetado)
        else:
            os.replace(descargado, desempaquetado)
        os.chmod(desempaquetado, 0o755)
        os.replace(desempaquetado, final)
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as exc:
        resumen["estado"] = "error"
        resumen["detalle"] = str(exc)
        for sobra in (descargado, desempaquetado):
            try:
                if os.path.exists(sobra):
                    os.remove(sobra)
            except OSError:
                pass
        return resumen

    resumen["estado"] = "instalada"
    resumen["detalle"] = "%s %s en %s" % (entrada["nombre"], entrada["version"], final)
    resumen["ruta"] = final
    resumen["sha256"] = esperado
    return resumen


def instalar_varias(destino: str, ids: list[str] | None = None, timeout: int = TIMEOUT_DESCARGA,
                    progreso=None, aviso=None, forzar: bool = False) -> list[dict]:
    """Instala las utilidades que se puedan, una detras de otra.

    ``progreso`` lleva el avance de la descarga (bytes escritos y total) y
    ``aviso`` se llama con cada utilidad ya resuelta.
    """
    destino = os.path.abspath(destino)
    os.makedirs(destino, exist_ok=True)
    elegidas = UTILIDADES
    if ids:
        elegidas = tuple(entrada for entrada in UTILIDADES if entrada["id"] in ids)
    resultados = []
    datos = manifiesto(destino)
    for entrada in elegidas:
        resumen = instalar(entrada, destino, timeout=timeout, progreso=progreso,
                           forzar=forzar)
        if resumen["estado"] == "instalada":
            datos[entrada["id"]] = {
                "version": entrada["version"],
                "sha256": resumen.get("sha256", ""),
                "instalado": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        elif resumen["estado"] == "ya-estaba":
            # El binario ya estaba (puesto a mano o en una instalacion
            # anterior): se apunta su suma y se conserva la fecha que habia.
            anterior = datos.get(entrada["id"], {})
            datos[entrada["id"]] = {
                "version": entrada["version"],
                "sha256": resumen.get("sha256", "") or anterior.get("sha256", ""),
                "instalado": anterior.get("instalado", ""),
            }
        if aviso:
            aviso(entrada, resumen)
        resultados.append(resumen)
    guardar_manifiesto(destino, datos)
    return resultados


def quitar(entrada: dict, destino: str) -> bool:
    """Borra el binario de una utilidad. Devuelve si estaba."""
    final = os.path.join(destino, entrada["binario"])
    if not os.path.isfile(final):
        return False
    try:
        os.remove(final)
    except OSError:
        return False
    datos = manifiesto(destino)
    datos.pop(entrada["id"], None)
    guardar_manifiesto(destino, datos)
    return True
