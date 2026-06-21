#!/usr/bin/env python3
"""
generate_bios_db.py — Regenera BIOS_DB y NOBIOS_PLATFORMS desde
el script oficial batocera-systems de Batocera (upstream GitHub).

Uso:
    python3 generate_bios_db.py                    # descarga desde GitHub
    python3 generate_bios_db.py --local ruta.py    # usa archivo local

Salida: código Python listo para reemplazar en app.py
"""

import sys, os, json, ast
from pathlib import Path

UPSTREAM_URL = (
    "https://raw.githubusercontent.com/batocera-linux/batocera.linux/"
    "master/package/batocera/core/batocera-scripts/scripts/batocera-systems"
)

# Plataformas Batocera conocidas que NUNCA requieren BIOS
# (son sistemas basados en MAME/FBA/digitales que no cargan firmware)
ALWAYS_NOBIOS = [
    "3ds", "amiga", "amstradcpc", "arcade", "atari2600",
    "atari7800", "c64", "famicom", "fba", "gamegear",
    "gb", "gbc", "gc", "genesis", "jaguar",
    "mame", "mastersystem", "megacd", "megadrive", "n64",
    "nes", "ngp", "pc", "pce", "psp",
    "sega32x", "sg1000", "snes", "tg16", "virtualboy",
    "wii", "wiiu", "wonderswan", "wonderswancolor", "zxspectrum",
]


def fetch_upstream():
    import urllib.request
    req = urllib.request.Request(UPSTREAM_URL, headers={"User-Agent": "BatoceraManager/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def parse_systems(source_code):
    """Extrae el dict `systems` del código fuente Python del script batocera-systems."""
    tree = ast.parse(source_code)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "systems":
                    return _ast_node_to_dict(node.value)
    raise ValueError("No se encontró la variable `systems` en el archivo")


def _ast_node_to_dict(node):
    """Convierte un nodo AST (dict o Call a dict/OrderedDict) a un dict Python."""
    if isinstance(node, ast.Call):
        # OrderedDict({...}), dict({...}), o dict(items=[...])
        if node.args:
            return _ast_node_to_dict(node.args[0])
        for kw in node.keywords:
            if kw.arg == "items":
                return _ast_node_to_dict(kw.value)
        return {}
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            key = ast.literal_eval(k)
            val = _ast_node_to_value(v)
            result[key] = val
        return result
    return {}


def _ast_node_to_value(node):
    """Convierte un nodo AST a valor Python (dict, list, str, etc.)."""
    if isinstance(node, ast.Dict):
        return {ast.literal_eval(k): _ast_node_to_value(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.List):
        return [_ast_node_to_value(el) for el in node.elts]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Call):
        if node.args:
            return _ast_node_to_value(node.args[0])
        return {}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -ast.literal_eval(node.operand)
    return ast.literal_eval(node)


def desc_from_file(filepath):
    """Genera un desc corto a partir del path del BIOS."""
    name = Path(filepath).stem
    # Si el stem es muy largo, usar el nombre base
    return name[:60] if name else Path(filepath).name


def generate_bios_db(systems):
    """Genera el dict BIOS_DB en el formato de app.py."""
    bios_db = {}
    for slug, info in sorted(systems.items()):
        bios_files = info.get("biosFiles", [])
        if not bios_files:
            continue
        entries = []
        for bf in bios_files:
            filepath = bf.get("file", "")
            # Quitar prefijo bios/
            if filepath.startswith("bios/"):
                filepath = filepath[5:]
            md5 = bf.get("md5", "")
            if md5 == "":
                md5 = None
            desc = bf.get("desc", desc_from_file(filepath))
            entries.append({
                "file": filepath,
                "md5": md5,
                "desc": desc,
                "mandatory": True,
            })
        if entries:
            bios_db[slug] = entries
    return bios_db


def generate_nobios(systems_with_bios):
    """Genera NOBIOS_PLATFORMS — sistemas conocidos sin BIOS."""
    known = set(ALWAYS_NOBIOS)
    # También incluir slugs del script que NO tienen biosFiles
    for slug, info in systems_with_bios.items():
        if not info.get("biosFiles"):
            known.add(slug)
    return sorted(known)


def format_bios_db(bios_db):
    """Formatea BIOS_DB como código Python."""
    lines = ["BIOS_DB = {"]
    for slug, entries in bios_db.items():
        lines.append(f'    "{slug}": [')
        for e in entries:
            md5_val = f'"{e["md5"]}"' if e["md5"] else "None"
            lines.append(
                f'        {{"file":"{e["file"]}","md5":{md5_val},'
                f'"desc":"{e["desc"]}","mandatory":{str(e["mandatory"])}}},'
            )
        lines.append("    ],")
    lines.append("}")
    return "\n".join(lines)


def format_nobios(nobios_list):
    """Formatea NOBIOS_PLATFORMS como código Python."""
    lines = ["NOBIOS_PLATFORMS = {"]
    for slug in nobios_list:
        lines.append(f'    "{slug}":[],')
    lines.append("}")
    return "\n".join(lines)


def main():
    if "--local" in sys.argv:
        idx = sys.argv.index("--local")
        path = sys.argv[idx + 1]
        source = Path(path).read_text(encoding="utf-8")
    else:
        print("  Descargando batocera-systems desde GitHub...", file=sys.stderr)
        source = fetch_upstream()

    print("  Parseando systems dict...", file=sys.stderr)
    systems = parse_systems(source)
    print(f"  Encontrados {len(systems)} sistemas en el script upstream", file=sys.stderr)

    bios_db = generate_bios_db(systems)
    nobios = generate_nobios(systems)

    total_entries = sum(len(v) for v in bios_db.values())
    print(f"  BIOS_DB: {len(bios_db)} sistemas, {total_entries} entradas", file=sys.stderr)
    print(f"  NOBIOS_PLATFORMS: {len(nobios)} sistemas", file=sys.stderr)
    print(file=sys.stderr)
    print(file=sys.stderr)

    # Output Python code
    print("# Auto-generated from official batocera-systems script")
    print("# https://github.com/batocera-linux/batocera.linux/blob/master/package/batocera/core/batocera-scripts/scripts/batocera-systems")
    print(f"# Generado: {len(bios_db)} sistemas con BIOS, {total_entries} entradas, {len(nobios)} sistemas sin BIOS")
    print()
    print()
    print(format_bios_db(bios_db))
    print()
    print()
    print(format_nobios(nobios))


if __name__ == "__main__":
    main()
