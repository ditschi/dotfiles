from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import ANSIBLE, REPO, load_group_vars, load_profile, resolve_packages

PROFILES = [
    "home-laptop",
    "work-laptop",
    "home-server",
    "rpi",
    "rpi-zero",
    "container",
]


def test_profile_yaml_matches_machine_defaults():
    from importlib.machinery import SourceFileLoader

    machine = SourceFileLoader(
        "machine_cli",
        str(REPO / "home/dot_local/bin/executable_machine"),
    ).load_module()
    for name in PROFILES:
        data = load_profile(name)
        assert data["profile"] == name
        assert data["features"] == machine.DEFAULT_FEATURES[name]


@pytest.mark.parametrize("name", PROFILES)
def test_expected_package_invariants(name: str):
    data = load_profile(name)
    packages = resolve_packages(data["profile"], data["features"])
    assert "git" in packages or name == "rpi-zero"
    if name == "rpi-zero":
        assert "eza" not in packages
        assert "ldap-utils" not in packages
        assert "guake" not in packages
        assert "zsh" in packages
        assert "fzf" in packages
    if name == "work-laptop":
        assert "ldap-utils" in packages
        assert "guake" in packages
    if name == "home-laptop":
        assert "ldap-utils" not in packages
        assert "guake" in packages
    if name == "container":
        assert "eza" not in packages
        assert "ldap-utils" not in packages


@pytest.mark.skipif(shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed")
@pytest.mark.parametrize("name", ["home-laptop", "work-laptop", "rpi-zero", "container"])
def test_python_resolver_matches_ansible(name: str, tmp_path: Path):
    dump_path = tmp_path / "packages.json"
    playbook = ANSIBLE / "dump_packages.yml"
    cmd = [
        "ansible-playbook",
        str(playbook),
        "-i",
        str(ANSIBLE / "inventory/local.yml"),
        "-e",
        f"@{ANSIBLE / 'profiles' / f'{name}.yml'}",
        "-e",
        f"dump_path={dump_path}",
    ]
    subprocess.run(cmd, check=True, cwd=ANSIBLE)
    ansible_packages = sorted(json.loads(dump_path.read_text()))
    data = load_profile(name)
    assert ansible_packages == resolve_packages(data["profile"], data["features"], load_group_vars())


def test_group_vars_are_lists():
    variables = load_group_vars()
    for key in (
        "packages_base",
        "packages_zsh",
        "packages_host",
        "packages_desktop",
        "packages_gnome",
        "packages_work",
        "packages_rpi_zero",
    ):
        assert isinstance(variables[key], list)
