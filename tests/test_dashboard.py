"""Tests del subsistema Dashboard (CPU, GPU, memoria, batería, ventiladores).

Se inyectan rutas temporales (o se monkeypatchea `_run`) para poder ejecutar
en cualquier plataforma sin depender de /sys y /proc de Linux.
"""


# ── Ventiladores (hwmon) ──────────────────────────────────────────────
def test_get_fans_tolerates_non_numeric_min(appmod, tmp_path):
    hw = tmp_path / "hwmon0"
    hw.mkdir()
    (hw / "name").write_text("testchip")
    (hw / "fan1_input").write_text("1500")
    (hw / "fan1_min").write_text("N/A")  # algunos drivers devuelven texto

    fans = appmod.get_fans(str(tmp_path))

    assert len(fans) == 1
    assert fans[0]["min"] is None
    assert fans[0]["status"] == "ok"


def test_get_fans_derives_status(appmod, tmp_path):
    hw = tmp_path / "hwmon0"
    hw.mkdir()
    (hw / "name").write_text("testchip")
    (hw / "fan1_input").write_text("0")                       # detenido
    (hw / "fan2_input").write_text("1200")                    # por debajo del mínimo
    (hw / "fan2_min").write_text("2000")
    (hw / "fan3_input").write_text("3000")                    # fault flag
    (hw / "fan3_fault").write_text("1")

    fans = {f["index"]: f for f in appmod.get_fans(str(tmp_path))}

    assert fans["1"]["status"] == "stopped"
    assert fans["2"]["status"] == "stopped"
    assert fans["3"]["status"] == "fault"


# ── GPU ───────────────────────────────────────────────────────────────
def test_gpu_from_nvidia_smi_reports_mib(appmod, monkeypatch):
    """nvidia-smi ya entrega MiB: no hay que dividir por 1024."""
    monkeypatch.setattr(
        appmod, "_run",
        lambda *a, **k: "0, NVIDIA GeForce RTX 2050, 45, 12, 2048, 4096, 30",
    )

    gpus = appmod._gpu_from_nvidia_smi()

    assert gpus[0]["mem_used"] == "2048 MB"
    assert gpus[0]["mem_total"] == "4096 MB"
    assert gpus[0]["power"] == "30 W"


def test_get_gpu_info_dedups_nvidia_drm_entry(appmod, tmp_path, monkeypatch):
    """La misma NVIDIA no debe aparecer dos veces (nvidia-smi + DRM)."""
    smi = [{"name": "NVIDIA GeForce RTX 2050", "vendor": "NVIDIA",
            "is_nvidia": True, "temp": 50, "util": 10,
            "mem_used": "2048 MB", "mem_total": "4096 MB", "power": "30 W"}]
    drm_gpu = {"name": "NVIDIA (nvidia)", "vendor": "NVIDIA", "is_nvidia": True,
               "temp": 50, "util": 10, "mem_used": "2048 MB", "mem_total": "4096 MB"}
    monkeypatch.setattr(appmod, "_gpu_from_nvidia_smi", lambda: smi)
    monkeypatch.setattr(appmod, "_gpu_from_drm", lambda card: dict(drm_gpu))

    drm = tmp_path / "drm"
    (drm / "card0").mkdir(parents=True)

    info = appmod.get_gpu_info(str(drm))

    assert len(info["gpus"]) == 1
    assert info["gpus"][0]["name"] == "NVIDIA GeForce RTX 2050"


def test_get_gpu_info_keeps_non_nvidia(appmod, tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "_gpu_from_nvidia_smi", lambda: None)
    drm_gpu = {"name": "AMD (amdgpu)", "vendor": "AMD", "is_nvidia": False,
               "temp": 40, "util": 5, "mem_used": "512 MB", "mem_total": "1024 MB"}
    monkeypatch.setattr(appmod, "_gpu_from_drm", lambda card: dict(drm_gpu))

    drm = tmp_path / "drm"
    (drm / "card0").mkdir(parents=True)

    info = appmod.get_gpu_info(str(drm))

    assert info["available"] is True
    assert info["gpus"][0]["vendor"] == "AMD"


# ── Memoria ───────────────────────────────────────────────────────────
def test_get_memory_skips_malformed_line(appmod, tmp_path):
    """Una línea sin ':' no debe descartar todo /proc/meminfo."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:        8000000 kB\n"
        "MemFree:          1000000 kB\n"
        "MemAvailable:     3000000 kB\n"
        "linea-sin-dos-puntos\n"
        "SwapTotal:        2000000 kB\n"
        "SwapFree:         1500000 kB\n"
    )

    mem = appmod.get_memory(str(meminfo))

    assert mem["total_mb"] == round(8000000 / 1024, 1)
    assert mem["free_mb"] == round(3000000 / 1024, 1)
    assert mem["used_pct"] == round(5000000 / 8000000 * 100, 1)


# ── Batería ───────────────────────────────────────────────────────────
def test_get_battery_charge_fallback_wh(appmod, tmp_path):
    """Sin energy_*, se deriva de charge_* (µAh) con el factor correcto."""
    bat = tmp_path / "BAT0"
    bat.mkdir()
    (bat / "type").write_text("Battery")
    (bat / "capacity").write_text("50")
    (bat / "status").write_text("Discharging")
    (bat / "charge_now").write_text("2000000")        # µAh
    (bat / "charge_full").write_text("4000000")
    (bat / "voltage_now").write_text("12000000")      # µV → 12 V
    ac = tmp_path / "AC"
    ac.mkdir()
    (ac / "type").write_text("Mains")
    (ac / "online").write_text("1")

    out = appmod.get_battery(str(tmp_path))

    assert out["available"] is True
    assert out["ac"] is True
    assert out["energy_now_wh"] == 24.0     # 2_000_000 µAh * 12 V / 1e6
    assert out["energy_full_wh"] == 48.0


# ── EmulationStation ──────────────────────────────────────────────────
def test_es_status_uses_full_cmdline_pattern(appmod, monkeypatch):
    """`comm` se trunca a 15 chars; hay que usar `pgrep -f`."""
    seen = {}

    def fake_run(cmd, default=""):
        seen["cmd"] = cmd
        return "1234"

    monkeypatch.setattr(appmod, "_run", fake_run)

    st = appmod.get_es_status()

    assert st["running"] is True
    assert "-f" in seen["cmd"]
