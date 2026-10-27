# -*- coding: utf-8 -*-
"""Tests de install.sh.

El instalador se prueba de verdad: se lanza con bash sobre una carpeta temporal
(BM_BASE_DIR), con el intérprete de Python neutralizado (BM_PYTHON) para no
levantar nada. Si no hay un bash utilizable en la máquina, los tests se saltan.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"

# Candidatos a bash: en Windows, `bash` suele ser el de WSL, que falla sin
# distribución instalada, así que probamos antes el de Git for Windows.
_BASH = [r"C:\Program Files\Git\bin\bash.exe",
         r"C:\Program Files (x86)\Git\bin\bash.exe"]


def _bash_candidates() -> list[str]:
    """Candidatos a bash, empezando por el Git que hay realmente instalado.

    Git se puede instalar en cualquier sitio (y se mueve de la máquina), así que
    derivamos sus rutas de `git.exe` en vez de asumir Program Files. Ojo al
    orden: `bin/bash.exe` es el intérprete de Git for Windows y monta su propio
    entorno (con `dirname`, `sed`...), mientras que `usr/bin/bash.exe` es el
    runtime MSYS a pelo y se queda sin herramientas.
    """
    extras: list[str] = []
    git = shutil.which("git")
    if git:
        root = Path(git).parent.parent          # ...\cmd\git.exe -> raíz de Git
        extras = [str(root / "bin" / "bash.exe"),
                  str(root / "usr" / "bin" / "bash.exe")]
    return extras + list(_BASH)


_bash_path: str | None = None


def _bash() -> str:
    global _bash_path
    if _bash_path:
        return _bash_path
    for cand in _bash_candidates() + [shutil.which("bash"), shutil.which("sh")]:
        if not cand:
            continue
        try:
            p = subprocess.run([cand, "-c", "echo ok"], capture_output=True,
                               text=True, timeout=30)
        except Exception:
            continue
        if p.returncode == 0 and "ok" in p.stdout:
            _bash_path = cand
            return cand
    pytest.skip("no hay un bash utilizable")


def _msys(p: Path) -> str:
    """Ruta estilo Git Bash: C:\\x\\y -> /c/x/y."""
    s = str(p).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/", s)
    return "/" + m.group(1).lower() + s[2:] if m else s


def _run(base: Path, answer: str | None = None, cwd: Path | None = None,
         script: Path | None = None) -> subprocess.CompletedProcess:
    if "BM_BASE_DIR" not in INSTALL.read_text(encoding="utf-8"):
        pytest.fail("install.sh debe aceptar BM_BASE_DIR para poder probarlo sin "
                    "escribir en /userdata/system")
    env = dict(os.environ)
    env["BM_BASE_DIR"] = _msys(base)
    env["BM_PYTHON"] = "echo"          # ni arranca servidores ni necesita python3
    env.pop("BM_AUTOSTART", None)
    if answer is not None:
        env["BM_AUTOSTART"] = answer
    return subprocess.run([_bash(), str(script or INSTALL)], capture_output=True,
                          text=True, encoding="utf-8", cwd=str(cwd or ROOT),
                          env=env, timeout=120)


@pytest.fixture
def base(tmp_path: Path) -> Path:
    d = tmp_path / "base"
    d.mkdir()
    return d


# ── Sintaxis ──────────────────────────────────────────────────────────
def test_script_parses():
    p = subprocess.run([_bash(), "-n", str(INSTALL)], capture_output=True,
                       text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr


# ── Sin terminal interactiva ──────────────────────────────────────────
def test_without_a_tty_it_does_not_touch_autostart(base):
    r = _run(base)                       # sin respuesta y sin TTY
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (base / "custom.sh").exists(), "no debe tocar custom.sh a ciegas"
    assert "app.py" in r.stdout, "debe decir cómo arrancarlo a mano"


def test_plain_output_when_not_a_tty(base):
    r = _run(base)
    assert "\033[" not in r.stdout, "sin terminal no se pintan colores"


# ── Copia de ficheros ─────────────────────────────────────────────────
def test_it_copies_everything_the_app_needs(base):
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    dst = base / "batocera_web"
    assert (dst / "app.py").exists()
    assert (dst / "templates" / "index.html").exists()
    assert (dst / "batocera_systems.json").exists(), \
        "app.py carga este JSON de su carpeta: sin él la app arranca sin sistemas"


def test_it_does_not_copy_onto_itself_when_cloned_in_place(base, tmp_path):
    """Flujo git clone: el script ya vive en su carpeta destino."""
    dst = base / "batocera_web"
    (dst / "templates").mkdir(parents=True)
    shutil.copy2(INSTALL, dst / "install.sh")
    for rel in ("app.py", "batocera_systems.json"):
        shutil.copy2(ROOT / rel, dst / rel)
    shutil.copy2(ROOT / "templates" / "index.html", dst / "templates" / "index.html")

    r = _run(base, answer="n", cwd=dst, script=dst / "install.sh")

    assert r.returncode == 0, r.stdout + r.stderr
    assert (dst / "app.py").exists(), "no debe borrarse a sí mismo"
    assert (dst / "batocera_systems.json").exists()
    assert "ya" in r.stdout.lower()


# ── Arranque automático ───────────────────────────────────────────────
def test_saying_yes_registers_it_in_custom_sh(base):
    r = _run(base, answer="s")
    assert r.returncode == 0, r.stdout + r.stderr
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-manager]" in sh
    assert "# [/batocera-manager]" in sh
    assert "app.py --port 5000" in sh


def test_saying_no_leaves_custom_sh_alone(base):
    _run(base, answer="n")
    assert not (base / "custom.sh").exists()


def test_it_does_not_duplicate_a_previous_registration(base):
    _run(base, answer="s")
    _run(base, answer="s")
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert sh.count("# [batocera-manager]") == 1


def test_it_appends_to_an_existing_custom_sh(base):
    (base / "custom.sh").write_text("#!/bin/bash\n# cosas del usuario\n", encoding="utf-8")
    _run(base, answer="s")
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "cosas del usuario" in sh, "no debe pisar lo que ya había"
    assert "# [batocera-manager]" in sh


def test_it_asks_about_autostart(base):
    """Cuando hay terminal, pregunta; sin ella, avisa y no toca nada."""
    txt = INSTALL.read_text(encoding="utf-8")
    assert "¿Añadir el manager al inicio de Batocera?" in txt
    r = _run(base)          # sin TTY
    assert "terminal interactiva" in r.stdout.lower()
