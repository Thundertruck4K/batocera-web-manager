"""Tests de endurecimiento de seguridad: validación de rutas e inyección."""

import pytest

BACKSLASH = chr(92)


# ── Validación de componentes de ruta ─────────────────────────────────
def test_is_safe_component_rejects_traversal(appmod):
    assert appmod.is_safe_component("snes") is True
    assert appmod.is_safe_component("Sonic (USA).zip") is True
    assert appmod.is_safe_component("..") is False
    assert appmod.is_safe_component(".") is False
    assert appmod.is_safe_component("") is False
    assert appmod.is_safe_component("a/b") is False
    assert appmod.is_safe_component("a" + BACKSLASH + "b") is False
    assert appmod.is_safe_component("../../etc/passwd") is False
    assert appmod.is_safe_component("a\x00b") is False


def test_safe_path_under_confines_to_base(appmod, tmp_path):
    base = tmp_path / "roms"
    base.mkdir()

    ok = appmod.safe_path_under(base, "snes", "game.zip")
    assert str(ok).startswith(str(base.resolve()))

    with pytest.raises(ValueError):
        appmod.safe_path_under(base, "..", "etc", "passwd")


def test_system_dir_rejects_traversal_slug(appmod, tmp_path):
    settings = {"roms_base": str(tmp_path / "roms")}
    (tmp_path / "roms").mkdir()

    with pytest.raises(ValueError):
        appmod.system_dir(settings, "../../etc")

    assert appmod.system_dir(settings, "snes").name == "snes"


def test_confine_to_base(appmod, tmp_path):
    base = tmp_path / "roms"
    base.mkdir()

    assert appmod.confine_to_base(base, "snes").name == "snes"
    assert appmod.confine_to_base(base, str(base / "snes")).name == "snes"

    with pytest.raises(ValueError):
        appmod.confine_to_base(base, str(tmp_path / "other"))
    with pytest.raises(ValueError):
        appmod.confine_to_base(base, "../other")


# ── Inyección en batocera.conf ────────────────────────────────────────
def test_sanitize_conf_value(appmod):
    assert appmod.sanitize_conf_value("mupen64plus") == "mupen64plus"
    assert appmod.sanitize_conf_value("genesis_plus_gx") == "genesis_plus_gx"

    with pytest.raises(ValueError):
        appmod.sanitize_conf_value("retroarch\nsnes.emulator=evil")
    with pytest.raises(ValueError):
        appmod.sanitize_conf_value("a;rm -rf /")
    with pytest.raises(ValueError):
        appmod.sanitize_conf_value("")
    with pytest.raises(ValueError):
        appmod.sanitize_conf_value("with space")


def test_sanitize_comment_text_strips_newlines(appmod):
    assert appmod.sanitize_comment_text("Super\nNES") == "Super NES"
    assert appmod.sanitize_comment_text("a\r\nb") == "a b"


# ── XML/RSS seguro (anti XXE) ─────────────────────────────────────────
def test_xml_looks_safe_rejects_doctype_and_entity(appmod):
    assert appmod.xml_looks_safe("<rss><channel></channel></rss>") is True
    assert appmod.xml_looks_safe("<!DOCTYPE rss SYSTEM 'x'><rss/>") is False
    assert appmod.xml_looks_safe("<!ENTITY x 'y'><rss/>") is False


def test_xml_looks_safe_accepts_bytes(appmod):
    assert appmod.xml_looks_safe(b"<rss><channel/></rss>") is True
    assert appmod.xml_looks_safe(b"<!DOCTYPE rss [<!ENTITY x 'y'>]><rss/>") is False


# ── Content-Length ────────────────────────────────────────────────────
def test_parse_content_length(appmod):
    assert appmod.parse_content_length("123") == 123
    assert appmod.parse_content_length("0") == 0
    assert appmod.parse_content_length("-5") == 0
    assert appmod.parse_content_length("abc") == 0
    assert appmod.parse_content_length(None) == 0


# ── Comando de servicio (autostart) ───────────────────────────────────
def test_get_service_cmd_quotes_app_path(appmod):
    cmd = appmod.get_service_cmd({"app_path": "/userdata/system/my app/app.py",
                                  "server_port": 5000})
    assert cmd == "python3 '/userdata/system/my app/app.py' --port 5000"


def test_get_service_cmd_neutralizes_injection(appmod):
    cmd = appmod.get_service_cmd({"app_path": "/x; rm -rf /", "server_port": "5000"})
    assert cmd == "python3 '/x; rm -rf /' --port 5000"


def test_get_service_cmd_sanitizes_port(appmod):
    cmd = appmod.get_service_cmd({"app_path": "/a/app.py", "server_port": "abc; reboot"})
    assert cmd == "python3 /a/app.py --port 5000"
