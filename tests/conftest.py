"""Configuración común de la suite de tests.

Carga `app.py` (que vive en la raíz del repo) como módulo importable `app`,
aunque no sea un paquete. app.py debe poder importarse sin arrancar el
servidor: su ejecución está protegida por `if __name__ == "__main__"`.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (necesita ROOT en sys.path)


@pytest.fixture(scope="session")
def appmod():
    """Devuelve el módulo app.py cargado."""
    return app


@pytest.fixture(scope="session", autouse=True)
def _ajustes_aislados(tmp_path_factory):
    """Redirige los ajustes (y la cache de RA) a una carpeta temporal.

    El manager guarda los ajustes y la cache de RetroAchievements en
    /userdata/system. En el PC de desarrollo esa ruta no existe y se acabaría
    creando una carpeta `userdata` en la raiz del disco, asi que los tests
    apuntan a un temporal.
    """
    destino = tmp_path_factory.mktemp("ajustes")
    app.SETTINGS_FILE = destino / "batocera_manager_settings.json"
    return app.SETTINGS_FILE
