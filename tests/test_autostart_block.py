# -*- coding: utf-8 -*-
"""Tests del bloque de arranque automático y del contrato del servicio.

El bloque de `custom.sh` lo escriben dos caminos distintos: `install.sh` y el
backend (`/api/service/install`). Los dos tienen que escribir exactamente lo
mismo y, sobre todo, **reescribirse** cuando cambia el puerto o la ruta: si
no, la consola seguiría levantando el manager con la configuración anterior
(la que tenía el bloque la última vez que se escribió).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def custom_sh(tmp_path, appmod, monkeypatch):
    """custom.sh de mentira, con el módulo apuntando a él."""
    path = tmp_path / "custom.sh"
    monkeypatch.setattr(appmod, "CUSTOM_SH", path)
    return path


def _cmdline(*args: str) -> str:
    """Construye un /proc/<pid>/cmdline (argumentos separados por byte NUL)."""
    return "\0".join(args) + "\0"


# ─── El bloque que se escribe ─────────────────────────────────────────────

def test_el_bloque_mata_la_instancia_anterior(appmod, custom_sh):
    """Sin el pkill, la instancia nueva no encontraría el puerto libre."""
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 5000")
    txt = custom_sh.read_text(encoding="utf-8")
    assert txt.count(appmod.SERVICE_MARKER) == 1
    assert txt.count(appmod.SERVICE_TAG_END) == 1
    assert 'pkill -f "python3.*app\\.py"' in txt
    assert "app.py --port 5000 &" in txt


def test_el_bloque_se_reescribe_si_cambia_el_puerto(appmod, custom_sh):
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 5000")
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 8080")
    txt = custom_sh.read_text(encoding="utf-8")
    assert txt.count(appmod.SERVICE_MARKER) == 1, "no debe duplicar el bloque"
    assert "app.py --port 8080 &" in txt
    assert "app.py --port 5000" not in txt, "el puerto viejo se queda ahí"


def test_el_bloque_se_reescribe_si_cambia_la_ruta(appmod, custom_sh):
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 5000")
    appmod.install_autostart("python3 /userdata/system/otro/app.py --port 5000")
    txt = custom_sh.read_text(encoding="utf-8")
    assert "/userdata/system/otro/app.py" in txt
    assert "/userdata/system/batocera_web/app.py" not in txt


def test_el_bloque_no_toca_el_resto_de_custom_sh(appmod, custom_sh):
    custom_sh.write_text("#!/bin/bash\n# cosas del usuario\n", encoding="utf-8")
    appmod.install_autostart("python3 /x/app.py --port 5000")
    txt = custom_sh.read_text(encoding="utf-8")
    assert "cosas del usuario" in txt
    assert txt.startswith("#!/bin/bash")


def test_quitar_el_bloque_deja_el_resto_intacto(appmod, custom_sh):
    custom_sh.write_text("#!/bin/bash\n# cosas del usuario\n", encoding="utf-8")
    appmod.install_autostart("python3 /x/app.py --port 5000")
    assert appmod.remove_autostart() is True
    txt = custom_sh.read_text(encoding="utf-8")
    assert appmod.SERVICE_MARKER not in txt
    assert "cosas del usuario" in txt


def test_quitar_el_bloque_sin_bloque_no_rompe_nada(appmod, custom_sh):
    custom_sh.write_text("#!/bin/bash\n", encoding="utf-8")
    assert appmod.remove_autostart() is False
    assert custom_sh.read_text(encoding="utf-8") == "#!/bin/bash\n"


# ─── Lo que se lee del bloque ─────────────────────────────────────────────

def test_el_registro_saca_el_comando_aunque_haya_un_pkill(appmod, custom_sh):
    """El pkill va antes: la línea del manager no es la primera."""
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 5000")
    st = appmod.get_autostart_status({})
    assert st["registered"] is True
    assert st["installed"] is True
    assert st["cmd"] == "python3 /userdata/system/batocera_web/app.py --port 5000"


def test_sin_bloque_no_dice_que_esta_instalado(appmod, custom_sh):
    st = appmod.get_autostart_status({})
    assert st["registered"] is False
    assert st["installed"] is False
    assert st["cmd"] is None


def test_un_custom_sh_sin_marcas_no_cuenta_como_instalado(appmod, custom_sh):
    custom_sh.write_text("#!/bin/bash\npython3 /x/app.py --port 5000 &\n", encoding="utf-8")
    st = appmod.get_autostart_status({})
    assert st["registered"] is False


# ─── El estado del servicio ───────────────────────────────────────────────

def test_el_estado_del_servicio_informa_de_pid_y_puerto(appmod, custom_sh, monkeypatch):
    monkeypatch.setattr(appmod, "_run", lambda cmd, default="": "28161")
    monkeypatch.setattr(
        appmod, "_read_proc_cmdline",
        lambda pid: _cmdline("python3", "/userdata/system/batocera_web/app.py",
                             "--port", "5000"),
    )
    st = appmod.get_service_status({})
    assert st["process"]["running"] is True
    assert st["process"]["pid"] == 28161
    assert st["process"]["port"] == 5000
    assert st["autostart"]["manual_mode"] is True, "corre pero no hay bloque: modo manual"


def test_con_bloque_no_esta_en_modo_manual(appmod, custom_sh, monkeypatch):
    appmod.install_autostart("python3 /userdata/system/batocera_web/app.py --port 5000")
    monkeypatch.setattr(appmod, "_run", lambda cmd, default="": "28161")
    monkeypatch.setattr(
        appmod, "_read_proc_cmdline",
        lambda pid: _cmdline("python3", "/x/app.py", "--port", "5000"),
    )
    st = appmod.get_service_status({})
    assert st["autostart"]["manual_mode"] is False
    assert st["autostart"]["registered"] is True


def test_sin_proceso_el_estado_lo_dice(appmod, custom_sh, monkeypatch):
    monkeypatch.setattr(appmod, "_run", lambda cmd, default="": "")
    st = appmod.get_service_status({})
    assert st["process"]["running"] is False
    assert st["process"]["pid"] is None
    assert st["autostart"]["manual_mode"] is False


# ─── El comando de arranque ───────────────────────────────────────────────

def test_el_comando_usa_el_puerto_configurado(appmod):
    cmd = appmod.get_service_cmd({"app_path": "/x/app.py", "server_port": 8080})
    assert cmd.endswith("--port 8080")


def test_un_puerto_invalido_cae_a_5000(appmod):
    assert appmod.get_service_cmd({"app_path": "/x/app.py", "server_port": 99999}).endswith("--port 5000")
    assert appmod.get_service_cmd({"app_path": "/x/app.py", "server_port": "abc"}).endswith("--port 5000")


def test_el_comando_entrecomilla_la_ruta_si_hay_espacios(appmod):
    cmd = appmod.get_service_cmd({"app_path": "/mi ruta/app.py", "server_port": 5000})
    assert "'/mi ruta/app.py'" in cmd
