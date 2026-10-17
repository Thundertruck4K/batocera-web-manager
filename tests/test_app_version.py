# -*- coding: utf-8 -*-
"""La versión de la app se declara una sola vez.

El repo se contradecía: app.py decía v1.2, la portada de la web v1.0 e
install.sh v1.3. Ahora `APP_VERSION` (app.py) es la única fuente y la
plantilla la recibe al renderizar, para que no vuelvan a separarse.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def test_la_api_declara_la_version(appmod):
    assert re.fullmatch(r"\d+\.\d+", appmod.APP_VERSION)


def test_la_portada_recibe_la_version_del_servidor(appmod):
    html = appmod.render_index()
    assert f"v{appmod.APP_VERSION}" in html
    assert "{{app_version}}" not in html, "quedó un marcador sin sustituir"


def test_la_portada_no_lleva_una_version_a_mano():
    assert not re.search(r"Manager Web v1\.\d", HTML.read_text(encoding="utf-8"))
