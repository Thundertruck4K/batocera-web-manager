"""Linea de comandos de las herramientas de ROMs.

La usa el instalador para dejar los DAT descargados y se puede usar a mano:

    python3 -m romtools dats --list
    python3 -m romtools dats --install
    python3 -m romtools dats --install ps2 gc
    python3 -m romtools dats --remove ps2

Tambien vale la forma corta, sin el grupo `dats`:

    python3 -m romtools list
    python3 -m romtools install ps2
    python3 -m romtools remove ps2
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from . import dats


def _log(message: str) -> None:
    print(f"  {message}", flush=True)


def cmd_list(args) -> int:
    print("DAT disponibles para los sistemas de Batocera:")
    for item in dats.systems_with_dat():
        print(f"  {item['system']:<16} {item['source_name']:<9} {item['dat']}")
    print()
    cache = dats.dat_dir(args.root)
    installed = dats.dat_files(cache)
    if installed:
        print(f"Ya descargados en {cache}:")
        for info in installed:
            games = info.get("games")
            games = f", {games} juegos" if games else ""
            print(f"  {info['system']:<16} {info.get('dat') or '?'}{games}")
    else:
        print(f"No hay ningun DAT descargado todavia ({cache}).")
    return 0


def cmd_install(args) -> int:
    systems = args.systems or [item["system"] for item in dats.systems_with_dat()]
    cache = dats.dat_dir(args.root)
    os.makedirs(cache, exist_ok=True)

    fallos = []
    catalogo = dats.catalogue(cache, timeout=args.timeout)
    for system in systems:
        resolucion = dats.resolve_dat(system, None, catalogo)
        if not resolucion:
            print(f"  [X] {system}: no tiene DAT configurado")
            fallos.append(system)
            continue
        dat_name = resolucion["dat"]
        print(f"  · {system} ({dat_name})")
        try:
            started = time.time()
            info = dats.install_dat(system, cache, timeout=args.timeout,
                                    progress=_log, catalogo=catalogo)
            print(f"    [OK] {info['games']} juegos, "
                  f"{info['size'] / 1048576:.1f} MiB, "
                  f"{time.time() - started:.0f} s")
        except Exception as exc:  # noqa: BLE001 - aqui se informa y se sigue
            print(f"    [X] {exc}")
            fallos.append(system)
    return 1 if fallos else 0


def cmd_dats(args) -> int:
    """El grupo `dats`: los DAT se listan, se bajan o se borran."""
    if getattr(args, "remove", False):
        if not args.systems:
            print("  hay que decir que sistemas borrar")
            return 1
        return cmd_remove(args)
    if getattr(args, "install", False):
        return cmd_install(args)
    return cmd_list(args)


def cmd_remove(args) -> int:
    cache = dats.dat_dir(args.root)
    for system in args.systems:
        info = dats.remove_dat(system, cache)
        print(f"  {system}: {'borrado' if info['removed'] else 'no estaba'}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="romtools",
                                     description="Herramientas de ROMs")
    parser.add_argument("--root", default="/userdata/system",
                        help="donde vive la carpeta de los DAT")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="lista los DAT disponibles")
    p_list.set_defaults(func=cmd_list)

    p_install = sub.add_parser("install", help="descarga los DAT")
    p_install.add_argument("systems", nargs="*", help="sistemas (por defecto, todos)")
    p_install.add_argument("--timeout", type=int, default=900)
    p_install.set_defaults(func=cmd_install)

    p_remove = sub.add_parser("remove", help="borra los DAT de un sistema")
    p_remove.add_argument("systems", nargs="+")
    p_remove.set_defaults(func=cmd_remove)

    # El grupo `dats` es la forma que usa el instalador:
    # `python3 -m romtools dats --install`.
    p_dats = sub.add_parser("dats", help="gestiona los DAT (lista, instala o borra)")
    grupo = p_dats.add_mutually_exclusive_group()
    grupo.add_argument("--list", action="store_true", help="lista los DAT")
    grupo.add_argument("--install", action="store_true", help="descarga los DAT")
    grupo.add_argument("--remove", action="store_true", help="borra los DAT")
    p_dats.add_argument("systems", nargs="*", help="sistemas (por defecto, todos)")
    p_dats.add_argument("--timeout", type=int, default=900)
    p_dats.set_defaults(func=cmd_dats)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        args.func = cmd_list
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
