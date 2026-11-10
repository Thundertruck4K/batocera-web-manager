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


# ── Utilidades: git y node ─────────────────────────────────────────────
# La fase 4 del instalador valida que estén git y node. Si están, sigue
# sin preguntar; si faltan, avisa y los instala. Estas pruebas simulan
# una consola sin ellos recortando el PATH: bash mete /ucrt64/bin en el
# PATH siempre, así que se recorta desde BASH_ENV (que bash carga al
# arrancar sin terminal).

def _tool_path(tool: str) -> str:
    """Ruta absoluta de una utilidad tal y como la ve bash."""
    out = subprocess.run([_bash(), "-c", f"command -v {tool}"], capture_output=True,
                         text=True, timeout=30).stdout.strip()
    return out


def _shim(base: Path, tools: list[str], hidden: list[str] | None = None) -> dict:
    """Entorno con un PATH donde sólo están las utilidades indicadas.

    Cada herramienta es un lanzador que invoca la real, así que git (o
    node) desaparecen del PATH sin tocar el sistema.

    ``hidden`` tapa además las utilidades que sí están en el PATH de la
    máquina pero que no deben aparecer: sin esto, un node instalado en el
    /usr/bin de MSYS impediría simular una consola que no lo tiene.
    """
    shim = base / "shim"
    shim.mkdir(parents=True, exist_ok=True)
    for tool in tools:
        src = _tool_path(tool)
        if not src:
            continue
        launcher = shim / tool
        launcher.write_text(f'#!/usr/bin/env bash\nexec "{src}" "$@"\n',
                            encoding="utf-8")
        launcher.chmod(0o755)
    rc = base / "shimrc.sh"
    lineas = [f'export PATH="{_msys(shim)}:/usr/bin"']
    if hidden:
        # `command -v <tapado>` no lo encuentra: es como si no estuviera.
        # Una sola función para todos, que si no la segunda pisa a la primera.
        casos = "|".join(hidden)
        lineas.append(
            'command() { if [ "$1" = "-v" ]; then case "$2" in %s) return 1 ;; esac; fi; '
            'builtin command "$@"; }' % casos)
    rc.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return {"BASH_ENV": _msys(rc)}


def _conda_platform() -> str:
    """Plataforma de conda que elegirá el instalador (según uname -m)."""
    out = subprocess.run([_bash(), "-c", "uname -m"], capture_output=True,
                         text=True, timeout=30).stdout.strip()
    return {"x86_64": "linux-64", "amd64": "linux-64",
            "aarch64": "linux-aarch64", "arm64": "linux-aarch64",
            "ppc64le": "linux-ppc64le"}.get(out, "linux-64")


# Doble de micromamba: no descarga nada, pero deja el entorno tal y como
# el instalador espera encontrarlo y anota los argumentos que recibió.
_STUB_MM = r"""#!/usr/bin/env bash
cmd="${1:-}"; shift || true
root="${MAMBA_ROOT_PREFIX:-/tmp}"
mkdir -p "$root" 2>/dev/null || true
printf '%s %s\n' "$cmd" "$*" >> "$root/mm-args.txt" 2>/dev/null || true
case "$cmd" in
  create|install)
    prefix=""
    while [ $# -gt 0 ]; do
      case "$1" in
        -p) prefix="$2"; shift 2 ;;
        -c|--channel) shift 2 ;;
        -y|--yes) shift ;;
        *) shift ;;
      esac
    done
    if [ -n "$prefix" ]; then
      mkdir -p "$prefix/bin"
      printf '#!/bin/sh\necho "git version 2.56.0"\n' > "$prefix/bin/git"
      chmod +x "$prefix/bin/git"
    fi
    ;;
esac
exit 0
"""


def _fake_micromamba(tmp_path: Path) -> tuple[Path, str]:
    """Espejo local de micro.mamba.pm: un tar.bz2 con bin/micromamba.

    Devuelve (directorio del espejo, sha256 del tarball).
    """
    stage = tmp_path / "mmstage"
    (stage / "bin").mkdir(parents=True)
    mm = stage / "bin" / "micromamba"
    # Con CRLF el shebang acaba en "\r" y el binario no arranca.
    mm.write_text(_STUB_MM.replace("\r\n", "\n"), encoding="utf-8")
    mm.chmod(0o755)

    tarball = tmp_path / "mm.tar.bz2"
    subprocess.run([_bash(), "-c",
                    f"tar -cjf {_msys(tarball)} -C {_msys(stage)} bin/micromamba"],
                   check=True, capture_output=True, timeout=120)
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()

    mirror = tmp_path / "mirror"
    (mirror / _conda_platform()).mkdir(parents=True)
    shutil.copy2(tarball, mirror / _conda_platform() / "2.10.0")
    return mirror, digest


def _git_env(base: Path, mirror: Path, sha: str, **extra) -> dict:
    bindir = base / "gitbin"
    bindir.mkdir(exist_ok=True)
    env = {
        "BM_GIT": "auto",
        "BM_GIT_DIR": _msys(base / "mamba"),
        "BM_GIT_BIN_DIR": _msys(bindir),
        "BM_MICROMAMBA_URL": _file_url(mirror),
        "BM_MICROMAMBA_SHA256": sha,
    }
    env.update(extra)
    return env


def test_git_y_node_ya_estan_no_se_instala_nada(base):
    """Si están los dos, la instalación sigue sin preguntar nada."""
    env = _shim(base, ["git", "node", "curl"])
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No se encontró" not in r.stdout, r.stdout
    assert "git y node listos" in r.stdout, r.stdout
    assert not (base / "mamba").exists(), "no debe instalar git si ya está"
    assert not (base / "node").exists(), "no debe instalar node si ya está"


def test_sin_git_avisa_que_hay_que_instalarlo_y_lo_instala(base, tmp_path):
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["node", "curl", "bzip2"])
    env.update(_git_env(base, mirror, sha))
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ("No se encontró git en el sistema: es necesario instalarlo "
            "para continuar.") in r.stdout, r.stdout
    assert "sha256 verificado" in r.stdout, r.stdout
    assert (base / "mamba" / "envs" / "git" / "bin" / "git").exists(), \
        "no se creó el entorno de git"
    assert (base / "gitbin" / "git").exists(), "no se enlazó git en BM_GIT_BIN_DIR"


def test_sin_node_avisa_que_hay_que_instalarlo_y_lo_instala(base, tmp_path):
    dist, name = _fake_node_dist(tmp_path)
    env = _shim(base, ["git", "curl"], hidden=["node"])
    env.update(_node_env(base, dist))
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ("No se encontró node en el sistema: es necesario instalarlo "
            "para continuar.") in r.stdout, r.stdout
    assert (base / "node" / name / "bin" / "node").exists(), "no se instaló node"


def test_sin_git_y_sin_node_avisa_de_las_dos_utilidades(base, tmp_path):
    dist, name = _fake_node_dist(tmp_path)
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["curl", "bzip2"], hidden=["node", "git"])
    env.update(_node_env(base, dist))
    env.update(_git_env(base, mirror, sha))
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No se encontró git en el sistema" in r.stdout, r.stdout
    assert "No se encontró node en el sistema" in r.stdout, r.stdout
    assert "git y node listos" in r.stdout, r.stdout


def test_el_gestor_sigue_adelante_aunque_falten_utilidades(base, tmp_path):
    """Faltar git o node no puede parar la instalación del manager."""
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["curl", "bzip2"])
    env.update(_git_env(base, mirror, sha, BM_GIT="skip"))
    env.update({"BM_NODE": "skip"})
    r = _run(base, answer="s", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sin git" in r.stdout, r.stdout
    assert (base / "batocera_web" / "app.py").exists(), "no copió los ficheros"
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-manager]" in sh, "no registró el arranque automático"


def test_bm_git_skip_no_instala_git(base):
    env = _shim(base, ["node", "curl"])
    env.update({"BM_GIT": "skip"})
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No se encontró git en el sistema" in r.stdout, r.stdout
    assert "Omitida la instalación de git (BM_GIT=skip)" in r.stdout, r.stdout
    assert not (base / "mamba").exists(), "no debe instalar git con BM_GIT=skip"


def test_un_sha256_de_micromamba_que_no_cuadra_no_instala_nada(base, tmp_path):
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["node", "curl", "bzip2"])
    env.update(_git_env(base, mirror, sha))
    env["BM_MICROMAMBA_SHA256"] = "0" * 64
    r = _run(base, answer="n", env_extra=env)
    assert "sha256 incorrecto" in r.stdout, r.stdout
    assert not (base / "mamba" / "envs" / "git").exists(), \
        "no debe instalar git con un sha256 que no cuadra"


def test_git_se_instala_desde_el_canal_conda_forge(base, tmp_path):
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["node", "curl", "bzip2"])
    env.update(_git_env(base, mirror, sha))
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    args = (base / "mamba" / "root" / "mm-args.txt").read_text(encoding="utf-8")
    assert "create" in args, args
    assert "-c conda-forge" in args, args


def test_el_bloque_de_git_recrea_el_enlace_al_arrancar(base, tmp_path):
    """El bloque se escribe en custom.sh: /usr es un overlay y se pierde."""
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["node", "curl", "bzip2"])
    env.update(_git_env(base, mirror, sha))
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-git]" in sh
    assert "# [/batocera-git]" in sh
    assert "envs/git/bin/git" in sh, sh
    assert "ln -sf" in sh, sh


def test_el_bloque_de_git_se_escribe_aunque_git_ya_estuviera(base):
    """Git ya instalado: no se reinstala, pero el bloque queda escrito."""
    prefix = base / "mamba" / "envs" / "git" / "bin"
    prefix.mkdir(parents=True)
    git = prefix / "git"
    git.write_text('#!/bin/sh\necho "git version 2.56.0"\n', encoding="utf-8")
    git.chmod(0o755)
    env = _shim(base, ["git", "node", "curl"])
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No se encontró" not in r.stdout, r.stdout
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-git]" in sh, sh


def test_el_bloque_de_git_no_se_duplica(base, tmp_path):
    mirror, sha = _fake_micromamba(tmp_path)
    env = _shim(base, ["node", "curl", "bzip2"])
    env.update(_git_env(base, mirror, sha))
    _run(base, answer="n", env_extra=env)
    _run(base, answer="n", env_extra=env)
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert sh.count("# [batocera-git]") == 1, sh


def test_el_bloque_de_node_se_escribe_si_el_node_ya_esta(base):
    """Node ya instalado: no se reinstala, pero el bloque queda escrito."""
    node_dir = base / "node"
    (node_dir / "current" / "bin").mkdir(parents=True)
    node = node_dir / "current" / "bin" / "node"
    node.write_text('#!/bin/sh\necho v26.13.0\n', encoding="utf-8")
    node.chmod(0o755)
    env = _shim(base, ["git", "node", "curl"])
    env.update({"BM_NODE_DIR": _msys(node_dir)})
    r = _run(base, answer="n", env_extra=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No se encontró" not in r.stdout, r.stdout
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-node]" in sh, sh
    assert "npm_config_prefix" in sh, sh


# ── El bloque de las utilidades de conversion ──────────────────────────
def test_it_writes_the_tools_block(base, tmp_path):
    """El bloque # [batocera-tools] deja las utilidades en el PATH."""
    destino = tmp_path / "usrbin"
    destino.mkdir()
    _run(base, answer="s", env_extra={"BM_TOOLS_BIN_DIR": _msys(destino)})
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "# [batocera-tools]" in sh, sh
    assert "# [/batocera-tools]" in sh


def test_the_tools_block_links_the_real_files(base, tmp_path):
    """El bloque enlaza las utilidades de verdad y no toca los enlaces."""
    destino = tmp_path / "usrbin"
    destino.mkdir()
    _run(base, answer="s", env_extra={"BM_TOOLS_BIN_DIR": _msys(destino)})
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    bloque = sh.split("# [batocera-tools]")[1].split("# [/batocera-tools]")[0]
    bloque = "# [batocera-tools]" + bloque + "# [/batocera-tools]"

    # Una utilidad de verdad (el rom-converto) y un enlace que ya hay.
    herramientas = base / "bin"
    herramientas.mkdir()
    ejecutable = herramientas / "rom-converto"
    ejecutable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ejecutable.chmod(0o755)
    (herramientas / "npsget").symlink_to(base / "npsget")

    r = subprocess.run([_bash(), "-c", bloque], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    # En Windows el `ln -s` de MSYS copia en vez de enlazar, asi que lo que se
    # comprueba es que el ejecutable ha llegado al destino.
    assert (destino / "rom-converto").exists(), "debe enlazar el ejecutable"
    assert not (destino / "npsget").exists(), "no debe tocar los enlaces que ya hay"


def test_the_tools_block_does_not_break_with_set_e(base, tmp_path):
    """El bloque no puede dejar el arranque a medias si algo falla."""
    destino = tmp_path / "usrbin"
    destino.mkdir()
    _run(base, answer="s", env_extra={"BM_TOOLS_BIN_DIR": _msys(destino)})
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    bloque = sh.split("# [batocera-tools]")[1].split("# [/batocera-tools]")[0]
    bloque = "# [batocera-tools]" + bloque + "# [/batocera-tools]"

    herramientas = base / "bin"
    herramientas.mkdir()
    ejecutable = herramientas / "rom-converto"
    ejecutable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ejecutable.chmod(0o755)

    r = subprocess.run([_bash(), "-c", "set -e\n" + bloque + "\necho LLEGADO"],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "LLEGADO" in r.stdout, r.stdout


# ── Las utilidades de conversion ────────────────────────────────────────
# El instalador deja listas las utilidades que se pueden descargar (el
# rom-converto, el nodtool y el 3dstool). El modo lo manda BM_UTILS:
# auto (por defecto) instala las que falten, all las reinstalla y skip no
# instala ninguna.

def test_it_installs_the_utilities_by_default(base):
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "utilidades --install --destino" in r.stdout, r.stdout


def test_bm_utils_skip_does_not_install_them(base):
    r = _run(base, answer="n", env_extra={"BM_UTILS": "skip"})
    assert r.returncode == 0, r.stdout + r.stderr
    # El comando de instalacion siempre lleva --destino: si no aparece, no se
    # lanza (el texto de ayuda si menciona el comando, pero sin --destino).
    assert "--destino" not in r.stdout, r.stdout
    assert "omitidas" in r.stdout, r.stdout


def test_bm_utils_all_reinstalls_them(base):
    r = _run(base, answer="n", env_extra={"BM_UTILS": "all"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--forzar" in r.stdout, r.stdout


def test_an_unknown_bm_utils_falls_back_to_auto(base):
    r = _run(base, answer="n", env_extra={"BM_UTILS": "inventado"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "utilidades --install" in r.stdout, r.stdout


def test_it_says_the_utilities_go_to_the_tools_folder(base):
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "bin" in r.stdout, r.stdout


def test_it_links_the_utilities_to_the_path(base, tmp_path):
    """Lo que se instala tiene que quedar en el PATH del sistema."""
    destino = tmp_path / "usrbin"
    destino.mkdir()
    herramientas = base / "bin"
    herramientas.mkdir()
    ejecutable = herramientas / "rom-converto"
    ejecutable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    ejecutable.chmod(0o755)

    r = _run(base, answer="n", env_extra={"BM_TOOLS_BIN_DIR": _msys(destino)})

    assert r.returncode == 0, r.stdout + r.stderr
    assert (destino / "rom-converto").exists(), "debe enlazar la utilidad"


def test_the_tools_block_is_written_in_an_existing_custom_sh(base):
    """Con un custom.sh ya hecho, el bloque de las utilidades se añade."""
    (base / "custom.sh").write_text("#!/bin/bash\n# cosas del usuario\n", encoding="utf-8")
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    sh = (base / "custom.sh").read_text(encoding="utf-8")
    assert "cosas del usuario" in sh, "no debe pisar lo que ya había"
    assert "# [batocera-tools]" in sh, sh


def test_it_does_not_create_a_custom_sh_without_autostart(base):
    """Sin arranque automático no se inventa un custom.sh."""
    r = _run(base, answer="n")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (base / "custom.sh").exists()

