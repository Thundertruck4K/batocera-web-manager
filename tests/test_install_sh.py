# -*- coding: utf-8 -*-
"""Tests de install.sh.

El instalador se prueba de verdad: se lanza con bash sobre una carpeta temporal
(BM_BASE_DIR), con el intérprete de Python neutralizado (BM_PYTHON) para no
levantar nada. Si no hay un bash utilizable en la máquina, los tests se saltan.
"""
from __future__ import annotations
import hashlib
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
         script: Path | None = None, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    if "BM_BASE_DIR" not in INSTALL.read_text(encoding="utf-8"):
        pytest.fail("install.sh debe aceptar BM_BASE_DIR para poder probarlo sin "
                    "escribir en /userdata/system")
    env = dict(os.environ)
    env["BM_BASE_DIR"] = _msys(base)
    env["BM_PYTHON"] = "echo"          # ni arranca servidores ni necesita python3
    env.pop("BM_AUTOSTART", None)
    if answer is not None:
        env["BM_AUTOSTART"] = answer
    if env_extra:
        env.update({k: v for k, v in env_extra.items() if v is not None})
    return subprocess.run([_bash(), str(script or INSTALL)], capture_output=True,
                          text=True, encoding="utf-8", cwd=str(cwd or ROOT),
                          env=env, timeout=180)


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


# ── El bloque de arranque automático ───────────────────────────────────
def test_el_bloque_mata_la_instancia_anterior(base):
    """Sin el pkill, la instancia nueva no encontraría el puerto libre."""
    r = _run(base, answer="s")
    assert r.returncode == 0, r.stdout + r.stderr
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert 'pkill -f "python3.*app\\.py"' in sh
    assert "app.py --port 5000 &" in sh


def test_el_bloque_se_reescribe_si_cambia_el_puerto(base):
    _run(base, answer="s")
    _run(base, answer="s", env_extra={"BM_PORT": "8080"})
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert sh.count("# [batocera-manager]") == 1, "no debe duplicar el bloque"
    assert "app.py --port 8080 &" in sh
    assert "app.py --port 5000" not in sh, "el puerto viejo se queda ahí"


def test_el_bloque_no_pisa_el_resto_de_custom_sh(base):
    (base / "custom.sh").write_text("#!/bin/bash\n# cosas del usuario\n", encoding="utf-8")
    _run(base, answer="s")
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "cosas del usuario" in sh


# ── El puerto ──────────────────────────────────────────────────────────
def test_un_puerto_que_no_es_numero_falla(base):
    r = _run(base, answer="s", env_extra={"BM_PORT": "abc"})
    assert r.returncode != 0
    assert "no es un número" in r.stdout


def test_un_puerto_fuera_de_rango_falla(base):
    r = _run(base, answer="s", env_extra={"BM_PORT": "99999"})
    assert r.returncode != 0
    assert "fuera de rango" in r.stdout


# ── Node.js (opcional) ─────────────────────────────────────────────────
def _node_arch() -> str:
    """Arquitectura tal y como la ve el script (uname -m → nombre de Node)."""
    out = subprocess.run([_bash(), "-c", "uname -m"], capture_output=True,
                         text=True, timeout=30).stdout.strip()
    return {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64",
            "armv7l": "armv7l", "armv6l": "armv6l"}.get(out, "x64")


def _fake_node_dist(tmp_path: Path, version: str = "v26.13.0") -> tuple[Path, str]:
    """Espejo local de nodejs.org: SHASUMS256.txt y el tarball."""
    arch = _node_arch()
    name = f"node-{version}-linux-{arch}"
    stage = tmp_path / "stage"
    (stage / name / "bin").mkdir(parents=True)
    node = stage / name / "bin" / "node"
    node.write_text(f"#!/bin/sh\necho {version}\n", encoding="utf-8")
    node.chmod(0o755)

    dist = tmp_path / "dist"
    (dist / version).mkdir(parents=True)
    tarball = dist / version / f"{name}.tar.gz"
    subprocess.run([_bash(), "-c",
                    f"tar -czf {_msys(tarball)} -C {_msys(stage)} {name}"],
                   check=True, capture_output=True, timeout=120)
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    (dist / version / "SHASUMS256.txt").write_text(f"{digest}  {name}.tar.gz\n",
                                                    encoding="utf-8")
    return dist, name


def _file_url(p: Path) -> str:
    """URL file:// con ruta Windows: el curl de Windows no entiende /c/... ."""
    return "file:///" + str(p).replace("\\", "/")


def _node_env(base: Path, dist: Path, **extra) -> dict:
    bindir = base / "bin"
    bindir.mkdir(exist_ok=True)
    env = {
        "BM_NODE": "install",
        "BM_NODE_VERSION": "v26.13.0",
        "BM_NODE_URL": _file_url(dist),
        "BM_NODE_BIN_DIR": _msys(bindir),
        "BM_NODE_DIR": _msys(base / "node"),
    }
    env.update(extra)
    return env


def test_node_es_opcional_y_no_se_instala_sin_preguntar(base):
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Node" in r.stdout
    assert not (base / "node").exists(), "sin tocar nada no se instala Node"


def test_node_se_instala_desde_el_espejo_local(base, tmp_path):
    dist, name = _fake_node_dist(tmp_path)
    r = _run(base, answer="n", env_extra=_node_env(base, dist))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (base / "node" / name / "bin" / "node").exists(), "no se descomprimió"
    assert (base / "node" / "current").exists(), "no se creó el enlace current"
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-node]" in sh
    assert "# [/batocera-node]" in sh
    assert "NODE_HOME=" in sh
    assert "npm_config_prefix" in sh


def test_un_sha256_que_no_cuadra_no_instala_nada(base, tmp_path):
    dist, name = _fake_node_dist(tmp_path)
    tarball = dist / "v26.13.0" / f"{name}.tar.gz"
    tarball.write_bytes(b"esto no es un tarball")

    r = _run(base, answer="n", env_extra=_node_env(base, dist))

    assert "sha256 incorrecto" in r.stdout
    assert not (base / "node" / name).exists(), "no debe descomprimir nada"
