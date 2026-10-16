#!/usr/bin/env python3
"""
bios_validator.py — Valida BIOS_DB contra el script upstream batocera-systems.

Detecta:
- Sistemas faltantes en nuestra BIOS_DB
- Sistemas extra (obsoletos) en nuestra BIOS_DB
- Entradas BIOS faltantes por sistema
- MD5 desactualizados

Uso:
    python3 tests/bios_validator.py
    python3 tests/bios_validator.py --update  # genera diff con app.py
"""

import sys, os, ast, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

UPSTREAM_URL = (
    "https://raw.githubusercontent.com/batocera-linux/batocera.linux/"
    "master/package/batocera/core/batocera-scripts/scripts/batocera-systems"
)

# -- Import BIOS_DB de app.py -----------------------------------------
def import_bios_db():
    """Importa BIOS_DB y NOBIOS_PLATFORMS desde app.py."""
    app_py = Path(__file__).parent.parent / "app.py"
    source = app_py.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bios_db = None
    nobios = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "BIOS_DB":
                        bios_db = _eval_dict(node.value)
                    elif target.id == "NOBIOS_PLATFORMS":
                        nobios = set(_eval_dict(node.value).keys())
    return bios_db or {}, nobios or set()

def _eval_dict(node):
    if isinstance(node, ast.Call):
        return _eval_dict(node.args[0]) if node.args else {}
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            key = ast.literal_eval(k)
            result[key] = _eval_value(v)
        return result
    return {}

def _eval_value(node):
    if isinstance(node, ast.Dict):
        return {ast.literal_eval(k): _eval_value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.List):
        return [_eval_value(el) for el in node.elts]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -ast.literal_eval(node.operand)
    return ast.literal_eval(node)

def _norm_md5(v):
    """Normaliza un md5 a algo hashable y comparable (str|None).

    El upstream batocera-systems puede declarar `md5` como lista (varios
    hashes válidos para el mismo fichero); meter esa lista en un set revienta
    con TypeError. Aquí se unifica a una cadena (o None si está vacío).
    """
    if v is None:
        return None
    if isinstance(v, (list, tuple, set)):
        vals = [str(x).strip() for x in v if x not in (None, "")]
        return ",".join(vals) if vals else None
    s = str(v).strip()
    return s or None

# -- Fetch / parse upstream -------------------------------------------
def fetch_upstream_systems():
    import urllib.request
    req = urllib.request.Request(UPSTREAM_URL, headers={"User-Agent": "BatoceraManager/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        source = r.read().decode("utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "systems":
                    return _eval_dict(node.value)
    raise ValueError("No se encontro `systems`")

# -- Comparacion ------------------------------------------------------
def main():
    sep = "=" * 60
    print(sep)
    print("  BIOS_DB Validator - Batocera System Manager Web")
    print(sep)

    # Cargar local
    print("\n[*] Leyendo BIOS_DB desde app.py...")
    local_db, local_nobios = import_bios_db()
    local_known = set(local_db.keys()) | local_nobios
    local_total_entries = sum(len(v) for v in local_db.values())
    print(f"     BIOS_DB: {len(local_db)} sistemas, {local_total_entries} entradas")
    print(f"     NOBIOS:  {len(local_nobios)} sistemas")
    print(f"     Total:   {len(local_known)} sistemas conocidos")

    # Cargar upstream
    print("\n[~] Descargando upstream batocera-systems...")
    try:
        upstream = fetch_upstream_systems()
    except Exception as e:
        print(f"  [ERR] Error: {e}")
        sys.exit(1)
    print(f"     {len(upstream)} sistemas en upstream")

    # Comparar
    upstream_slugs = set(upstream.keys())
    local_slugs = set(local_db.keys())

    issues = 0

    # Sistemas en upstream pero no en local
    missing_in_local = upstream_slugs - local_known
    if missing_in_local:
        issues += 1
        print(f"\n[!!] {len(missing_in_local)} sistemas en upstream que NO estan en BIOS_DB ni NOBIOS:")
        for s in sorted(missing_in_local)[:15]:
            bios_count = len(upstream[s].get("biosFiles", []))
            print(f"     - {s} ({bios_count} BIOS files)")

    # Sistemas en local pero no en upstream (obsoletos?)
    extra_in_local = local_slugs - upstream_slugs
    if extra_in_local:
        print(f"\n[i] {len(extra_in_local)} sistemas en BIOS_DB que NO estan en upstream (posiblemente obsoletos):")
        for s in sorted(extra_in_local):
            print(f"     - {s} ({len(local_db[s])} entradas)")

    # Comparar entradas por sistema
    print(f"\n[*] Verificando entradas por sistema...")
    match_count = 0
    mismatch_count = 0

    for slug in sorted(upstream_slugs & local_slugs):
        local_entries = {(e["file"], _norm_md5(e.get("md5"))) for e in local_db[slug]}
        up_files = upstream[slug].get("biosFiles", [])
        up_entries = set()
        for bf in up_files:
            filepath = bf.get("file", "")
            if filepath.startswith("bios/"):
                filepath = filepath[5:]
            up_entries.add((filepath, _norm_md5(bf.get("md5"))))

        missing_entries = up_entries - local_entries
        extra_entries = local_entries - up_entries

        if missing_entries or extra_entries:
            mismatch_count += 1
            pin = "[!!]" if missing_entries else "[i]"
            print(f"\n  {pin} {slug}:")
            for filepath, md5 in sorted(missing_entries, key=lambda x: (x[0], x[1] or "")):
                md5_str = md5 or "None"
                print(f"       + falta: {filepath}  md5={md5_str}")
            for filepath, md5 in sorted(extra_entries, key=lambda x: (x[0], x[1] or ""))[:5]:
                md5_str = md5 or "None"
                print(f"       - extra: {filepath}  md5={md5_str}")
        else:
            match_count += 1

    # Resumen
    print(f"\n{'=' * 60}")
    if mismatch_count == 0 and not missing_in_local:
        print("  [OK] VALIDACION COMPLETA - Sin diferencias")
    else:
        print(f"  {'[!!]' if issues else '[i]'} Resumen:")
        if issues:
            print(f"     Sistemas faltantes: {len(missing_in_local)}")
        print(f"     Sistemas con BIOS:         {len(local_db)}")
        print(f"     Entradas totales local:     {local_total_entries}")
        print(f"     Entradas totales upstream:  {sum(len(s.get('biosFiles',[])) for s in upstream.values())}")
        print(f"     Sistemas coincidentes:      {match_count}")
        print(f"     Sistemas con diferencias:   {mismatch_count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
