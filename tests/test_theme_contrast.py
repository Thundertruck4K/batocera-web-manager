from __future__ import annotations
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "templates" / "index.html"


def _root_var(name: str) -> str:
    css = HTML.read_text(encoding="utf-8")
    m = re.search(rf"--{name}\s*:\s*(#[0-9a-fA-F]{{6}})", css)
    assert m, f"variable --{name} no encontrada"
    return m.group(1)


def _luminance(hexcolor: str) -> float:
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("fg", ["text2", "text3"])
@pytest.mark.parametrize("bg", ["bg", "panel"])
def test_text_contrast_meets_wcag_aa(fg: str, bg: str):
    ratio = _contrast(_root_var(fg), _root_var(bg))
    assert ratio >= 4.5, f"--{fg} sobre --{bg}: ratio {ratio:.2f} < 4.5"
