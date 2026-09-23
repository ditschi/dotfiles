from __future__ import annotations

import subprocess
from importlib.machinery import SourceFileLoader

from package_sets import REPO

MACHINE = REPO / "home/dot_local/bin/executable_machine"


def _cli():
    return SourceFileLoader("machine_cli", str(MACHINE)).load_module()


def test_help_lists_setup_and_env():
    result = subprocess.run(
        ["python3", str(MACHINE), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "setup" in result.stdout
    assert "env" in result.stdout


def test_zsh_completion_contains_profiles():
    result = subprocess.run(
        ["python3", str(MACHINE), "completion", "zsh"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "work-laptop" in result.stdout
    assert "rpi-zero" in result.stdout
    assert "compdef _machine machine" in result.stdout


def test_env_item_names_by_class():
    cli = _cli()
    assert cli.ENV_CLASS["work-laptop"] == "work"
    assert cli.ENV_CLASS["rpi-zero"] == "iot"
    assert cli.ENV_CLASS["container"] == ""
    assert cli.DEFAULT_FEATURES["home-laptop"] == [
        "zsh-full",
        "fonts",
        "starship",
        "desktop",
        "gnome",
    ]
