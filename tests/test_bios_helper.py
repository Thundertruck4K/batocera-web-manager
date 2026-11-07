"""Tests del asistente de BIOS faltantes (enfoque legal-primero).

La app NO distribuye fuentes de BIOS: solo ofrece un enlace de búsqueda en Google
y una descarga desde una URL que el usuario proporciona. El hash se calcula y se
enseña como dato, pero no decide nada: Batocera no es rígido con él.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


# ─── Enlace de búsqueda en Google ───────────────────────────────────────

def test_busqueda_fichero_url(appmod):
    """El enlace va a Google con el nombre del fichero entrecomillado."""
    url = appmod.busqueda_fichero_url("scph5501.bin")
    assert url.startswith("https://www.google.com/search?q=")
    assert "scph5501.bin" in url
    assert "%22" in url


# ─── Descargador ───────────────────────────────────────────────────────

def test_download_rejects_non_http_scheme(appmod, tmp_path):
    r = appmod.download_bios_from_url(tmp_path, "x.bin", "ftp://evil/x.bin")
    assert r["ok"] is False
    assert "http" in r["error"].lower()


def test_download_rejects_path_traversal(appmod, tmp_path):
    r = appmod.download_bios_from_url(tmp_path, "../evil.bin", "http://e/x.bin")
    assert r["ok"] is False
    assert not (tmp_path.parent / "evil.bin").exists()


def test_download_writes_file_and_reports_md5(appmod, tmp_path, monkeypatch):
    """La descarga deja el fichero y devuelve su hash (sin veredicto)."""
    payload = b"BIOSDATA-1234"
    monkeypatch.setattr(appmod, "_bios_urlopen", lambda url, timeout=30: payload)
    md5 = hashlib.md5(payload).hexdigest()

    r = appmod.download_bios_from_url(tmp_path, "scph5501.bin", "http://e/x.bin", [md5])

    assert r["ok"] is True
    assert (tmp_path / "scph5501.bin").read_bytes() == payload
    assert r["md5"] == md5
    # El hash no decide: no hay veredicto de validez.
    assert "md5_valid" not in r


def test_download_with_another_hash_is_not_a_problem(appmod, tmp_path, monkeypatch):
    """Un hash distinto al publicado no impide la descarga."""
    monkeypatch.setattr(appmod, "_bios_urlopen", lambda url, timeout=30: b"X")
    r = appmod.download_bios_from_url(tmp_path, "a.bin", "http://e/x", ["deadbeef"])
    assert r["ok"] is True
    assert r["md5"] == hashlib.md5(b"X").hexdigest()


def test_download_tolerates_network_error(appmod, tmp_path, monkeypatch):
    def boom(url, timeout=30):
        raise OSError("sin red")

    monkeypatch.setattr(appmod, "_bios_urlopen", boom)
    r = appmod.download_bios_from_url(tmp_path, "a.bin", "http://e/x")
    assert r["ok"] is False and "error" in r


def test_download_enforces_size_limit(appmod, tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "MAX_BIOS_DOWNLOAD", 4)
    monkeypatch.setattr(appmod, "_bios_urlopen", lambda url, timeout=30: b"12345")
    r = appmod.download_bios_from_url(tmp_path, "a.bin", "http://e/x")
    assert r["ok"] is False
    assert not (tmp_path / "a.bin").exists()


def test_download_respects_subfolders(appmod, tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "_bios_urlopen", lambda url, timeout=30: b"Z")
    r = appmod.download_bios_from_url(tmp_path, "neocd/neocd_f.rom", "http://e/x")
    assert r["ok"] is True
    assert (tmp_path / "neocd" / "neocd_f.rom").exists()


# ─── Endpoint ──────────────────────────────────────────────────────────

def test_fetch_endpoint_declared():
    src = APP.read_text(encoding="utf-8")
    assert '"/api/bios/fetch"' in src
    assert "download_bios_from_url(" in src
