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
