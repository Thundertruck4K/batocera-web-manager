"""Puntuacion de variantes: que juego es "el bueno" cuando hay varios.

Un DAT suele traer el mismo juego en varias versiones: la region, la
revision, el idioma, una demo, un prototipo o un volcado con datos
corruptos. Cuando eso pasa hay que elegir, y la eleccion se hace con una
puntuacion explicable (no con un modelo oculto):

  1. Las versiones preliminares (demo, beta, prototipo, sample) se penalizan.
  2. La region se ordena con la prioridad que elija el usuario
     (por defecto: USA, Europe, Japan).
  3. La revision suma: ``(Rev 2)`` es mejor que ``(Rev 1)``.
  4. El volcado suma o resta: ``[b]`` (datos malos) y ``[x]`` (checksum mal)
     restan; ``[!]`` (verificado), ``[f]`` (arreglado) y ``[t]`` (traducido)
     suman. Ojo: en la tradicion GoodTools, ``!`` significa volcado verificado.
  5. A igualdad, gana el orden alfabetico (que es el del DAT).

Ademas, este modulo sabe que ficheros accompany a una ROM (el CUE de un BIN,
una M3U de varios discos, un save, una captura) para que al renombrar no se
dejen huerfanos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from .identify import normalize_title

#: Ficheros que acompan a una ROM y se renombran con ella.
COMPANION_EXTENSIONS = {
    ".cue", ".m3u", ".m3u8", ".sav", ".srm", ".srmc", ".cht", ".txt", ".nfo",
    ".jpg", ".jpeg", ".png", ".xml", ".dat", ".bak", ".ini", ".state", ".st0",
    ".st1", ".st2", ".st3", ".st4", ".st5", ".st6", ".st7", ".st8", ".st9",
}

#: Extensiones que son juego (no acompanante) en los sistemas de discos.
DISC_EXTENSIONS = {".cue", ".gdi", ".m3u", ".mdf", ".img", ".ccd", ".chd",
                   ".iso", ".bin", ".gcm", ".gciso", ".pbp", ".wbfs", ".wia",
                   ".rvz", ".xiso", ".g64", ".ndd", ".3do", ".wad", ".nsp",
                   ".zip", ".7z", ".gz"}

#: Etiquetas que marcan una version preliminar.
_PRERELEASE_WORDS = ("beta", "proto", "prototype", "demo", "sample",
                     "alpha", "prerelease", "pre-release", "kiosk")
#: Marcas de volcado con datos malos.
_BAD_MARKS = ("[b]", "[x]")
#: Marcas que suman.
_GOOD_MARKS = ("[!]", "[f]", "[t]", "[o]")
#: Marcas de dump trucado o pirata: restan, pero menos que un volcado malo.
_HACK_MARKS = ("[h]", "[p]")
#: Etiquetas de region que se reconocen (minusculas).
_REGION_WORDS = {
    "usa": "usa", "us": "usa", "america": "usa",
    "europe": "europe", "eu": "europe", "eur": "europe", "pal": "europe",
    "japan": "japan", "jp": "japan", "jpn": "japan", "ntsc-j": "japan",
    "world": "world", "multi": "world", "worldwide": "world",
    "asia": "asia", "korea": "korea", "china": "china", "taiwan": "taiwan",
    "brazil": "brazil", "australia": "australia", "canada": "canada",
    "spain": "spain", "italy": "italy", "france": "france", "germany": "germany",
    "netherlands": "netherlands", "sweden": "sweden", "norway": "norway",
    "denmark": "denmark", "finland": "finland", "portugal": "portugal",
    "russia": "russia", "turkey": "turkey", "unknown": "unknown", "und": "unknown",
}

#: Etiquetas que describen el disco o la version (se conservan en el titulo).
_DISC_TAG_RE = re.compile(r"^\s*(disc|disco|cd|dvd|disk|tape|side|track|part)\b", re.I)
#: Etiqueta de revision: ``(Rev 2)``, ``(Revision 3)``, ``(v1.1)``.
_REV_TAG_RE = re.compile(r"^\s*(rev|revision)\s*(\d+)", re.I)
_VERSION_TAG_RE = re.compile(r"^\s*v(\d+)\.(\d+)", re.I)
#: Numero de disco: ``(Disc 1)``, ``(CD 2)``.
_DISC_NUM_RE = re.compile(r"^\s*(?:disc|disco|cd|dvd|disk|side|track)\s*(\d+)", re.I)
#: Numero de variante: ``(1)``, ``(2)``.
_VARIANT_RE = re.compile(r"^\s*(\d+)\s*$")

#: Prioridad de regiones por defecto.
DEFAULT_REGION_PRIORITY = ("usa", "europe", "japan", "world", "asia")


@dataclass
class Score:
    """La puntuacion de una variante, con el porque desglosado."""

    entry: dict
    total: float = 0.0
    reasons: list = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

    def add(self, points: float, why: str) -> None:
        self.total += points
        self.reasons.append(f"{why} ({points:+g})")

    def as_dict(self) -> dict:
        return {"total": round(self.total, 2), "reasons": self.reasons,
                "name": self.entry.get("name"), "description": self.entry.get("description")}


def tags_of(name: str) -> list:
    """Etiquetas entre parentesis de un nombre de DAT."""
    return [m.group(1).strip() for m in re.finditer(r"\(([^()]*)\)", name or "")]


def clean_title(name: str) -> str:
    """El titulo sin etiquetas, salvo las que son de disco.

    ``Ridge Racer (USA) (Track 1)`` -> ``Ridge Racer (Track 1)``: la region se
    puede cambiar, pero el disco no forma parte del titulo.
    """
    text = name or ""
    out = []
    pos = 0
    for match in re.finditer(r"\(([^()]*)\)", text):
        out.append(text[pos:match.start()])
        tag = match.group(1)
        out.append(match.group(0) if _DISC_TAG_RE.match(tag) else " ")
        pos = match.end()
    out.append(text[pos:])
    return re.sub(r"\s{2,}", " ", "".join(out)).strip()


def disc_number(name: str) -> int | None:
    """El numero de disco o pista de un nombre, si lo tiene."""
    for tag in tags_of(name):
        match = _DISC_NUM_RE.match(tag)
        if match:
            return int(match.group(1))
    return None


def variant_number(name: str) -> int | None:
    """El numero de variante entre parentesis: ``(1)``, ``(2)``."""
    for tag in tags_of(name):
        match = _VARIANT_RE.match(tag)
        if match:
            return int(match.group(1))
    return None


def disc_tag(name: str) -> str | None:
    """La etiqueta de disco o pista de un nombre, normalizada.

    ``Game (Disc A)`` -> ``disc a``; ``Game (Track 2)`` -> ``track 2``.
    """
    for tag in tags_of(name):
        if _DISC_TAG_RE.match(tag):
            return re.sub(r"[^a-z0-9]+", " ", tag.lower()).strip()
    return None


def game_key(name: str) -> str:
    """La identidad de un juego: su titulo y su disco, sin region ni marcas.

    Dos entradas del DAT que hablan del mismo juego comparten clave (aunque
    cambien la region, la revision o las marcas); las de otro juego, no. Por
    ejemplo ``Ballz - The Director's Cut (World) (En,Ja)`` y
    ``Ballz - The Director's Cut (USA)`` dan la misma clave, pero
    ``D's Diner - The Director's Cut (Japan) (Disc A)`` da otra distinta.
    """
    return normalize_title(clean_title(name or ""))


def is_companion(filename: str) -> bool:
    """Si el fichero acompaña a una ROM y no es una ROM en si."""
    lower = (filename or "").lower()
    if lower.endswith(".track01.bin") or ".track " in lower:
        return True
    ext = lower[lower.rfind("."):] if "." in lower else ""
    return ext in COMPANION_EXTENSIONS


def score_entry(entry: dict, region_priority: Sequence[str] = DEFAULT_REGION_PRIORITY) -> Score:
    """Puntua una entrada del DAT."""
    score = Score(entry=entry)
    name = entry.get("name") or ""
    tags = tags_of(name)

    # 1 · Pre-releases
    for tag in tags:
        low = tag.lower()
        for word in _PRERELEASE_WORDS:
            if word in low:
                score.add(-50, f"version preliminar ({tag})")
                break

    # 2 · Region
    priority = [r.lower() for r in region_priority]
    region = None
    for tag in tags:
        low = tag.lower()
        for word, canon in _REGION_WORDS.items():
            if low == word or low.startswith(word + ",") or f"({word})" in low:
                region = canon
                break
        if region:
            break
    if region and region in priority:
        score.add(20 - priority.index(region) * 5, f"region {region}")
    elif region:
        score.add(-10, f"region poco comun ({region})")

    # 3 · Revision
    for tag in tags:
        match = _REV_TAG_RE.match(tag)
        if match:
            score.add(int(match.group(2)) * 5, f"revision {match.group(2)}")
            continue
        match = _VERSION_TAG_RE.match(tag)
        if match:
            score.add(int(match.group(1)) * 10 + int(match.group(2)),
                      f"version {match.group(1)}.{match.group(2)}")

    # 4 · Marca del volcado
    for mark in _BAD_MARKS:
        if mark in name:
            score.add(-20, f"volcado con datos malos ({mark})")
    for mark in _HACK_MARKS:
        if mark in name:
            score.add(-10, f"dump trucado o pirata ({mark})")
    for mark in _GOOD_MARKS:
        if mark in name:
            score.add(5, f"marca {mark}")

    # 5 · Numero de variante: el 1 es el original
    variant = variant_number(name)
    if variant:
        score.add(-variant, f"variante {variant}")

    # 6 · Disco: el 1 es el primero
    disc = disc_number(name)
    if disc:
        score.add(-(disc - 1) * 2, f"disco {disc}")

    return score


def pick_best(entries: Iterable[dict],
              region_priority: Sequence[str] = DEFAULT_REGION_PRIORITY) -> tuple:
    """Elige la mejor variante de un grupo.

    Devuelve ``(entrada, puntuacion)``.

    Ojo: esto solo compara variantes **del mismo juego**. Si se le pasan
    juegos distintos, gana el que tenga mejor region, que no es lo que se
    quiere: para eso esta :func:`pick_best_variant`.
    """
    entries = list(entries)
    if not entries:
        return None, None
    scored = [score_entry(entry, region_priority) for entry in entries]
    scored.sort(key=lambda s: (-s.total, s.entry.get("name") or ""))
    return scored[0].entry, scored[0]


def pick_best_variant(candidates: Iterable[dict], source: str | None = None,
                      region_priority: Sequence[str] = DEFAULT_REGION_PRIORITY) -> tuple:
    """Elige la mejor variante **del mismo juego** entre los candidatos.

    ``candidates`` es lo que devuelve ``identify.match_by_title``: una lista de
    ``{"entry": ..., "score": ...}``, donde ``score`` es la similitud del
    titulo. Comparar solo por la puntuacion de variante (region, revision,
    marcas) equivocaria, porque dos juegos distintos pueden compartir
    subtitulo: con «The Director's Cut» el juego con mejor region se
    llevaria el renombrado del otro.

    Por eso aqui primero se agrupan las entradas por juego y solo se comparan
    las del mismo juego. Entre las de un mismo juego decide la puntuacion de
    variante (region, revision, marcas), que es justo para lo que existe.

    Devuelve ``(entrada, puntuacion, grupo)``.
    """
    items = [c for c in (candidates or []) if c.get("entry")]
    if not items:
        return None, None, []

    groups: dict = {}
    for cand in items:
        entry = cand["entry"]
        name = entry.get("name") or entry.get("description") or ""
        groups.setdefault(game_key(name), []).append(cand)

    source_disc = disc_tag(source) if source else None

    def rank(key):
        group = groups[key]
        similarity = max(c.get("score") or 0 for c in group)
        disc = disc_tag(group[0]["entry"].get("name") or "")
        same_disc = 1 if (source_disc and disc and disc == source_disc) else 0
        return (similarity, same_disc)

    key = max(groups, key=rank)
    group = groups[key]

    best, score = pick_best([c["entry"] for c in group], region_priority)
    return best, score, group
