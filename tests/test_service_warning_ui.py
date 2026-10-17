# -*- coding: utf-8 -*-
"""Tests del aviso de «modo manual» del panel Configuración.

Si el manager está corriendo pero NO está registrado en custom.sh, es que se
lanzó a mano (python3 app.py): al reiniciar la consola no volvería a levantarse.
La web avisa arriba del panel y ofrece activar el arranque automático con un
botón. «Ahora no» solo lo oculta en esta visita: el modo manual sigue siendo
un hecho, así que no se silencia para siempre.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _html() -> str:
    return HTML.read_text(encoding="utf-8")


def _tag(tag_id: str) -> str:
    """Devuelve la etiqueta de apertura que lleva ese id."""
    m = re.search(r"<[a-z][^>]*\bid=\"" + re.escape(tag_id) + r"\"[^>]*>", _html())
    assert m, f"no existe el elemento id={tag_id}"
    return m.group(0)


def _helper_source() -> str:
    m = re.search(r"<!-- >>> UI-HELPERS[\s\S]*?<script>(.*?)</script>[\s\S]*?<!-- <<< UI-HELPERS",
                  _html(), re.S)
    assert m, "No se encontró bloque UI-HELPERS"
    return m.group(1)


def _warn(proc, auto, dismissed) -> bool:
    js = ("const console=global.console;\n" + _helper_source() + "\n"
          + "console.log(JSON.stringify(svcManualWarn("
          + json.dumps(proc) + "," + json.dumps(auto) + "," + json.dumps(dismissed) + ")));\n")
    node = shutil.which("node")
    if not node:
        pytest.skip("node no disponible")
    p = subprocess.run([node, "-e", js], capture_output=True, text=True,
                       encoding="utf-8", cwd=str(ROOT))
    assert p.returncode == 0, f"node error:\n{p.stderr}"
    return json.loads(p.stdout.strip())


# ── Regla: cuándo toca avisar ─────────────────────────────────────────
def test_warns_when_running_without_autostart():
    assert _warn({"running": True}, {"registered": False}, False) is True


def test_silent_once_the_user_says_ahora_no():
    assert _warn({"running": True}, {"registered": False}, True) is False


def test_silent_when_autostart_is_configured():
    assert _warn({"running": True}, {"registered": True}, False) is False


def test_silent_when_the_server_is_not_running():
    assert _warn({"running": False}, {"registered": False}, False) is False


def test_silent_with_incomplete_status():
    assert _warn({}, {}, False) is False


# ── Markup ────────────────────────────────────────────────────────────
def test_warning_sits_at_the_top_of_the_settings_panel():
    h = _html()
    panel = h.index('id="panel-settings"')
    warn = h.index('id="svc-manual-warn"')
    autostart = h.index('id="svc-status-box"')
    assert panel < warn < autostart, "el aviso va antes de la tarjeta de autostart"


def test_warning_starts_hidden():
    assert "hidden" in _tag("svc-manual-warn")


def test_warning_offers_to_enable_autostart():
    h = _html()
    blk = h[h.index('id="svc-manual-warn"'):h.index('id="svc-status-box"')]
    assert "installService()" in blk, "el botón debe usar el instalador que ya existe"
    assert "dismissManualWarn()" in blk, "debe poder posponerse"
    assert "python3 app.py" in blk, "hay que decir cómo se está lanzando"


def test_warning_is_dismissed_only_for_this_visit():
    h = _html()
    fn = re.search(r"function dismissManualWarn\(\)\{(.*?)\n\}", h, re.S)
    assert fn, "falta dismissManualWarn()"
    assert "localStorage" not in fn.group(1), "no debe silenciarse para siempre"


# ── Estilo ────────────────────────────────────────────────────────────
def test_warning_is_styled_as_a_warning():
    css = _html()
    m = re.search(r"\.svc-warn\{.*?\.svc-warn-acts\{[^}]*\}", css, re.S)
    assert m, "faltan los estilos .svc-warn*"
    assert "--yellow" in m.group(0), "el aviso va en ámbar, no en azul de acción"
