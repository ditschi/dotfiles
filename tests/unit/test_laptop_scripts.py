"""power-profile-switch and battery-charge against a fake /sys/class/power_supply."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from package_sets import ANSIBLE

POWER = ANSIBLE / "roles/power_profile_switch/files/power-profile-switch"
CHARGE = ANSIBLE / "roles/battery_charge_limit/files/battery-charge"


def _supply(root: Path, name: str, **files: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    for key, value in files.items():
        (path / key).write_text(f"{value}\n")
    return path


def _stub_powerprofilesctl(bin_dir: Path, offered: list[str]) -> Path:
    log = bin_dir / "calls"
    listing = "".join(f"  {name}:\n    Driver: placeholder\n\n" for name in offered)
    stub = bin_dir / "powerprofilesctl"
    stub.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = list ]; then printf %s "{listing}"; exit 0; fi\n'
        f'echo "$@" >>"{log}"\n'
    )
    stub.chmod(0o755)
    return log


def _run(script: Path, tmp_path: Path, *args: str):
    env = {
        "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        "POWER_SUPPLY_DIR": str(tmp_path / "sys"),
    }
    return subprocess.run(
        ["bash", str(script), *args], env=env, capture_output=True, text=True
    )


def _power_env(tmp_path: Path, online: str, offered: list[str]) -> Path:
    (tmp_path / "bin").mkdir()
    _supply(tmp_path / "sys", "AC", type="Mains", online=online)
    _supply(tmp_path / "sys", "BAT0", type="Battery")
    return _stub_powerprofilesctl(tmp_path / "bin", offered)


def test_power_profile_on_the_charger(tmp_path):
    log = _power_env(tmp_path, "1", ["performance", "balanced", "power-saver"])
    assert _run(POWER, tmp_path).returncode == 0
    assert log.read_text() == "set performance\n"


def test_power_profile_on_battery(tmp_path):
    log = _power_env(tmp_path, "0", ["performance", "balanced", "power-saver"])
    assert _run(POWER, tmp_path).returncode == 0
    assert log.read_text() == "set balanced\n"


def test_power_profile_not_offered_is_skipped(tmp_path):
    log = _power_env(tmp_path, "1", ["balanced", "power-saver"])
    result = _run(POWER, tmp_path)
    assert result.returncode == 0
    assert "not offered" in result.stdout
    assert not log.exists()


def _battery(tmp_path: Path, name: str, start: bool = True) -> Path:
    files = {
        "capacity": "60",
        "status": "Discharging",
        "charge_control_end_threshold": "100",
    }
    if start:
        files["charge_control_start_threshold"] = "0"
    return _supply(tmp_path / "sys", name, **files)


def _thresholds(bat: Path) -> tuple[str, str]:
    start = bat / "charge_control_start_threshold"
    end = (bat / "charge_control_end_threshold").read_text().strip()
    return (start.read_text().strip() if start.exists() else "-", end)


def test_charge_start_and_stop_threshold(tmp_path):
    bat = _battery(tmp_path, "BAT0")
    result = _run(CHARGE, tmp_path, "normal")
    assert result.returncode == 0, result.stderr
    assert _thresholds(bat) == ("75", "80")
    assert "BAT0: 60% Discharging, charge between 75% and 80%" in result.stdout


def test_charge_stop_threshold_only(tmp_path):
    bat = _battery(tmp_path, "BAT0", start=False)
    result = _run(CHARGE, tmp_path, "normal")
    assert result.returncode == 0, result.stderr
    assert _thresholds(bat) == ("-", "80")


def test_charge_two_batteries_and_full(tmp_path):
    first, second = _battery(tmp_path, "BAT0"), _battery(tmp_path, "BAT1")
    assert _run(CHARGE, tmp_path, "full").returncode == 0
    assert _thresholds(first) == _thresholds(second) == ("95", "100")


def test_charge_without_battery(tmp_path):
    (tmp_path / "sys").mkdir()
    result = _run(CHARGE, tmp_path, "normal")
    assert result.returncode == 0
    assert "no battery with charge thresholds" in result.stdout


def test_charge_rejects_unknown_action(tmp_path):
    (tmp_path / "sys").mkdir()
    assert _run(CHARGE, tmp_path, "boost").returncode == 2
