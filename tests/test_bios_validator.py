"""Tests para el normalizador de md5 de tests/bios_validator.py.

Regresión: el upstream `batocera-systems` puede declarar `md5` como lista, lo
que provocaba `TypeError: unhashable type: 'list'` al construir el set de
entradas BIOS.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bios_validator", _ROOT / "bios_validator.py")
bv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bv)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("abc123", "abc123"),
        ("  abc123  ", "abc123"),
        (["a", "b"], "a,b"),
        (["a", None, ""], "a"),
        ([], None),
        (("x", "y"), "x,y"),
        (123, "123"),
    ],
)
def test_norm_md5(value, expected):
    assert bv._norm_md5(value) == expected


def test_norm_md5_is_hashable_for_lists():
    """El resultado debe poder meterse en un set (era el bug original)."""
    entries = {
        ("scph1001.bin", bv._norm_md5(["aaa", "bbb"])),
        ("scph1001.bin", bv._norm_md5("aaa,bbb")),
    }
    assert len(entries) == 1


def test_norm_md5_sortable_with_none():
    """sorted() con None no debe reventar (key tolerante)."""
    items = [("a.bin", None), ("a.bin", "zzz"), ("b.bin", "aaa")]
    out = sorted(items, key=lambda x: (x[0], x[1] or ""))
    assert out[0] == ("a.bin", None)
