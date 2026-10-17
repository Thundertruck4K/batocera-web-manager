# -*- coding: utf-8 -*-
"""Tests del estado del servicio: qué PID corre y en qué puerto escucha.

Regresión del «puerto 5357»: `get_process_status()` buscaba *el primer python*
en la salida de `ss -tlnp`, así que cualquier otro servicio escrito en Python
que estuviera escuchando en otro puerto (wsdd, por ejemplo) aparecía como si
fuera el puerto del manager, aunque su propia línea de comandos dijera 5000.

El puerto tiene que salir del propio manager: de su línea de comandos
(`--port N`) y, si no aparece ahí, del socket en LISTEN de ese mismo PID.
"""
from __future__ import annotations


def _cmdline(*args: str) -> str:
    """Construye un /proc/<pid>/cmdline (argumentos separados por byte NUL)."""
    return "\0".join(args) + "\0"


# ─── Puerto en la línea de comandos ────────────────────────────────────

def test_puerto_desde_cmdline(appmod):
    raw = _cmdline("python3", "/userdata/system/batocera_web/app.py", "--port", "5000")
    assert appmod._port_from_cmdline(raw) == 5000


def test_puerto_desde_cmdline_con_igual(appmod):
    assert appmod._port_from_cmdline(_cmdline("python3", "app.py", "--port=8080")) == 8080


def test_puerto_desde_cmdline_ignora_el_resto(appmod):
    raw = _cmdline("python3", "app.py", "--verbose", "/ruta con espacios/x")
    assert appmod._port_from_cmdline(raw) is None


def test_puerto_desde_cmdline_valida_el_rango(appmod):
    # Sin --port, sin valor y fuera de rango: ninguno es un puerto usable.
    assert appmod._port_from_cmdline("") is None
    assert appmod._port_from_cmdline(None) is None
    assert appmod._port_from_cmdline(_cmdline("python3", "app.py", "--port")) is None
    assert appmod._port_from_cmdline(_cmdline("python3", "app.py", "--port", "0")) is None
    assert appmod._port_from_cmdline(_cmdline("python3", "app.py", "--port", "70000")) is None
    assert appmod._port_from_cmdline(_cmdline("python3", "app.py", "--port", "abc")) is None


def test_read_proc_cmdline_tolera_la_ausencia_de_proc(appmod):
    assert appmod._read_proc_cmdline("999999999") == ""


# ─── Estado del proceso ────────────────────────────────────────────────

def test_sin_procesos_no_esta_corriendo(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_run", lambda cmd, default="": "")
    assert appmod.get_process_status() == {"running": False, "pids": [], "port": None}


def test_puerto_sale_del_propio_proceso(appmod, monkeypatch):
    """El 5357 de otro servicio Python no debe salir como puerto del manager."""
    llamadas: list[str] = []

    def fake_run(cmd, default=""):
        llamadas.append(cmd)
        if "pgrep" in cmd:
            # 28159 es el envoltorio de shell; 28161 es el servidor de verdad.
            return "28159\n28161"
        if "ss " in cmd:
            # Un Python ajeno escuchando en 5357, listado ANTES que el nuestro.
            return (
                'LISTEN 0 128 127.0.0.1:5357 0.0.0.0:* users:(("python3",pid=999,fd=3))\n'
                'LISTEN 0 128 0.0.0.0:5000 0.0.0.0:* users:(("python3",pid=28161,fd=4))'
            )
        raise AssertionError(f"orden inesperada: {cmd}")

    def fake_cmdline(pid):
        if pid == "28159":
            return _cmdline("sh", "-c", "python3 app.py --port 5000 &")
        return _cmdline("python3", "/userdata/system/batocera_web/app.py", "--port", "5000")

    monkeypatch.setattr(appmod, "_run", fake_run)
    monkeypatch.setattr(appmod, "_read_proc_cmdline", fake_cmdline)

    st = appmod.get_process_status()

    assert st["running"] is True
    assert st["pids"] == ["28159", "28161"]
    assert st["port"] == 5000
    assert not any("ss " in c for c in llamadas), "no hace falta mirar procesos ajenos"


def test_usa_el_socket_si_la_cmdline_no_trae_puerto(appmod, monkeypatch):
    monkeypatch.setattr(appmod, "_run", lambda cmd, default="": "28161")
    monkeypatch.setattr(appmod, "_read_proc_cmdline", lambda pid: _cmdline("python3", "app.py"))
    monkeypatch.setattr(appmod, "_es_listen_port", lambda pid: 5000)

    assert appmod.get_process_status()["port"] == 5000
