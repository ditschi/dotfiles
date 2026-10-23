from __future__ import annotations

import sys

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli.dotfiles import dotfile_groups, render_local_config  # noqa: E402


@pytest.mark.parametrize(
    "profile, expected",
    [
        ("work-machine", ["core", "prompt", "systemd", "work"]),
        ("home-laptop", ["core", "prompt", "systemd"]),
        ("home-server", ["core", "prompt", "systemd"]),
        ("rpi", ["core", "prompt", "systemd"]),
        ("rpi-zero", ["core", "prompt", "systemd"]),
        ("container", ["core", "prompt"]),
    ],
)
def test_groups_per_profile(profile, expected):
    assert dotfile_groups(profile, ["zsh-full"]) == expected


def test_work_group_only_for_work_machine():
    profiles = ["home-laptop", "home-server", "rpi", "rpi-zero", "container"]
    assert all("work" not in dotfile_groups(p) for p in profiles)


def test_local_config_lists_groups():
    assert render_local_config(["core", "work"]) == (
        '[bootstrap]\ndotfile_groups = ["core", "work"]\n'
    )
