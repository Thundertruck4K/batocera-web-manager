"""Renombrado de ROMs segun las convenciones de set, con vuelta atras.

El flujo es de tres pasos, y el primero no toca el disco:

1. **Plan**: se recorren los ficheros de un sistema, se identifican contra el
   DAT y se calcula el nombre destino. El plan se enseña entero antes de
   hacer nada.
2. **Aplicar**: se renombran los ficheros y sus acompanantes (el CUE de un
   BIN, la M3U de varios discos), sin sobrescribir nada.
3. **Deshacer**: cada aplicacion deja un journal en disco, asi que la ultima
   tanda se puede revertir.

Las reglas de seguridad son las de siempre: nunca se sale de la carpeta del
sistema, nunca se pisa un fichero que ya existe y un plan con poca confianza
se marca para que lo revise el usuario en vez de renombrar a ciegas.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from . import naming, sets
from .identify import Match, identify

#: Donde se guarda el journal de renombrados.
JOURNAL_NAME = "batocera_manager_renames.json"

#: Ficheros que se renombran junto al juego.
_COMPANIONS = sets.COMPANION_EXTENSIONS


@dataclass
class RenameItem:
    """Un fichero del plan."""

    path: str
    current: str
    proposed: str = ""
    action: str = "skip"
    reason: str = ""
    confidence: float = 0.0
    method: str = ""
    entry: dict | None = None
    companions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "file": os.path.basename(self.path),
            "current": self.current,
            "proposed": self.proposed,
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "method": self.method,
            "title": (self.entry or {}).get("description") if self.entry else None,
            "dat_name": (self.entry or {}).get("name") if self.entry else None,
            "companions": self.companions,
            "warnings": self.warnings,
        }


def journal_path(root: str = "/userdata/system") -> str:
    return os.path.join(root, JOURNAL_NAME)


def _read_journal(root: str) -> list:
    try:
        with open(journal_path(root), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _write_journal(root: str, entries: list) -> None:
    path = journal_path(root)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entries, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def companions_of(path: str) -> list:
    """Los ficheros que acompañan a este y se renombran con el."""
    stem = os.path.splitext(path)[0]
    out = []
    for ext in sorted(_COMPANIONS):
        candidate = stem + ext
        if os.path.isfile(candidate):
            out.append(candidate)
    # Los discos multiples tienen un BIN por pista: "Juego (Track 2).bin".
    directory = os.path.dirname(path)
    base = os.path.basename(stem)
    try:
        for name in os.listdir(directory):
            low = name.lower()
            if low.startswith(base.lower()) and re_track(low):
                full = os.path.join(directory, name)
                if full != path and os.path.isfile(full) and full not in out:
                    out.append(full)
    except OSError:
        pass
    return out


def re_track(name: str) -> bool:
    """Si el nombre es el de una pista secundaria (``.track 2.bin``)."""
    return ".track " in name or name.endswith(".track01.bin")


def plan_rename(files: Sequence[str], index: dict | None,
                options: naming.NamingOptions | None = None,
                region_priority: Sequence[str] = sets.DEFAULT_REGION_PRIORITY,
                min_confidence: float = 0.75,
                hash_budget: int = 512 * 1024 * 1024) -> dict:
    """Calcula el plan de renombrado de una lista de ficheros.

    ``index`` es el indice del DAT del sistema (o ``None`` si no hay DAT: en
    ese caso solo se ordenan los nombres existentes).
    """
    opts = options or naming.NamingOptions()
    items: list = []
    # El hash obliga a leer el fichero entero: con bibliotecas de 40 GB eso
    # es eterno, asi que se lleva un presupuesto de bytes.
    restante = hash_budget

    for path in sorted(files):
        if not os.path.isfile(path):
            continue
        current = os.path.basename(path)
        ext = os.path.splitext(current)[1]
        item = RenameItem(path=path, current=current)

        if index:
            try:
                tamano = os.path.getsize(path)
            except OSError:
                tamano = 0
            hashear = tamano <= restante
            if hashear:
                restante -= tamano
            match: Match = identify(path, index, title_hint=os.path.splitext(current)[0],
                                    hash_allowed=hashear)
            item.method = match.method
            item.confidence = match.confidence
            item.entry = match.entry
            if match.entry:
                proposed = naming.rom_target_name(match.entry, current, opts)
                if match.method == "titulo" and match.candidates:
                    # Hay varias entradas parecidas: se elige la mejor y se
                    # explica por que. La eleccion se hace entre las entradas
                    # del MISMO juego: si no, un juego distinto que comparta
                    # subtitulo se llevaria el renombrado del otro.
                    best, score, _grupo = sets.pick_best_variant(
                        match.candidates, source=current,
                        region_priority=region_priority)
                    if best is not None and best.get("name") != match.entry.get("name"):
                        item.entry = best
                        proposed = naming.rom_target_name(best, current, opts)
                        item.reason = "de entre varias coincidencias se ha elegido la mejor variante"
                        item.warnings.append(
                            "candidatas: " + ", ".join(
                                c["entry"].get("name", "") for c in match.candidates[:4]))
                    else:
                        item.reason = score.reasons[0] if score and score.reasons else match.note
                else:
                    item.reason = match.note or "coincidencia por " + match.method
                if not hashear and match.method not in ("nombre",):
                    item.warnings.append(
                        "no se ha verificado por hash: la biblioteca es muy grande")
                item.proposed = proposed
                if match.confidence < min_confidence:
                    item.action = "revisar"
                    item.reason = f"la confianza es baja ({match.confidence:.0%}): revisa el nombre"
                elif proposed.lower() == current.lower():
                    item.action = "igual"
                    item.reason = "el nombre ya sigue la convencion"
                else:
                    item.action = "renombrar"
            else:
                item.action = "sin DAT"
                item.reason = match.note or "no aparece en el DAT"
                item.proposed = naming.fallback_name(current, opts)
                item.confidence = 0.0
        else:
            item.action = "sin DAT"
            item.reason = "no hay DAT para este sistema"
            item.proposed = naming.fallback_name(current, opts)

        if item.action in ("renombrar", "revisar"):
            item.companions = [os.path.basename(c) for c in companions_of(path)]

        items.append(item)

    stats = {
        "total": len(items),
        "renombrar": sum(1 for i in items if i.action == "renombrar"),
        "revisar": sum(1 for i in items if i.action == "revisar"),
        "igual": sum(1 for i in items if i.action == "igual"),
        "sin_dat": sum(1 for i in items if i.action == "sin DAT"),
    }
    stats["identificados"] = sum(1 for i in items if i.entry)
    return {"items": [i.as_dict() for i in items], "stats": stats}


def apply_plan(plan: dict, folder: str, root: str = "/userdata/system",
               include_review: bool = False) -> dict:
    """Ejecuta el plan: renombra y deja journal para poder deshacer.

    ``include_review`` permite renombrar tambien los ficheros marcados como
    «revisar» (los que tienen coincidencia por titulo pero poca confianza).
    """
    folder = os.path.abspath(folder)
    moved = []
    skipped = []
    errors = []

    for item in plan.get("items", []):
        action = item.get("action")
        if action == "renombrar" or (include_review and action == "revisar"):
            pass
        else:
            skipped.append({"file": item.get("file"), "reason": item.get("reason")})
            continue

        path = os.path.join(folder, item.get("file", ""))
        proposed = item.get("proposed") or ""
        if not os.path.isfile(path):
            skipped.append({"file": item.get("file"), "reason": "ya no esta en la carpeta"})
            continue
        if not proposed:
            skipped.append({"file": item.get("file"), "reason": "no hay nombre destino"})
            continue
        if os.path.dirname(os.path.abspath(path)) != folder:
            errors.append({"file": item.get("file"), "error": "fuera de la carpeta del sistema"})
            continue

        # El destino va dentro de la carpeta del sistema: si se deja el
        # nombre suelto, el rename intentaria moverlo al directorio actual.
        target = os.path.join(folder, naming.unique_path(folder, proposed))
        try:
            os.rename(path, target)
        except OSError as exc:
            errors.append({"file": item.get("file"), "error": str(exc)})
            continue

        entry = {"from": path, "to": target, "when": time.time()}
        moved.append(entry)

        # Los acompanantes se renombran con el mismo tallo.
        for companion in item.get("companions", []):
            companion_path = os.path.join(folder, companion)
            if not os.path.isfile(companion_path):
                continue
            new_companion = os.path.join(
                folder, os.path.splitext(os.path.basename(target))[0] +
                os.path.splitext(companion)[1])
            try:
                os.rename(companion_path, new_companion)
                moved.append({"from": companion_path, "to": new_companion, "when": time.time()})
            except OSError as exc:
                errors.append({"file": companion, "error": str(exc)})

    if moved:
        journal = _read_journal(root)
        journal.append({"batch": moved, "when": time.time()})
        _write_journal(root, journal[-20:])

    return {"ok": not errors, "renamed": len(moved), "skipped": skipped,
            "errores": errors, "moved": moved}


def undo_last(root: str = "/userdata/system") -> dict:
    """Deshace la ultima tanda de renombrados."""
    journal = _read_journal(root)
    if not journal:
        return {"ok": False, "error": "no hay nada que deshacer"}
    batch = journal[-1]
    restored = []
    errors = []
    for entry in reversed(batch.get("batch", [])):
        source = entry.get("from")
        target = entry.get("to")
        if not source or not os.path.exists(target):
            errors.append({"file": target, "error": "no existe"})
            continue
        try:
            os.rename(target, source)
            restored.append(target)
        except OSError as exc:
            errors.append({"file": target, "error": str(exc)})
    journal.pop()
    _write_journal(root, journal)
    return {"ok": not errors, "restored": restored, "errores": errors}


def journal_batches(root: str = "/userdata/system") -> list:
    """Las tandas que se pueden deshacer (la ultima es la primera)."""
    journal = _read_journal(root)
    out = []
    for entry in reversed(journal):
        batch = entry.get("batch", [])
        out.append({"when": entry.get("when"), "count": len(batch),
                    "files": [os.path.basename(m.get("to", "")) for m in batch[:8]]})
    return out
