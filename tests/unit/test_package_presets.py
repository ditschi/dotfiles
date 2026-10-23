from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from package_sets import (
    ANSIBLE,
    REPO,
    load_group_vars,
    load_profile,
    resolve_monitoring,
    resolve_packages,
)

PROFILES = [
    "home-laptop",
    "work-machine",
    "home-server",
    "rpi",
    "rpi-zero",
    "container",
]


def run_task_fixture(tmp_path, tasks, variables, facts=None):
    output = tmp_path / "result.json"
    if facts:
        # gather_facts is off; set_fact on ansible_facts is how facts are injected
        tasks.insert(
            0,
            {
                "name": "Provide fixture facts",
                "ansible.builtin.set_fact": {"ansible_facts": facts},
            },
        )
    tasks.append(
        {
            "name": "Capture resulting facts",
            "ansible.builtin.copy": {
                "dest": str(output),
                "content": (
                    "{{ {'download': fixture_download | default(false), "
                    "'installed': fixture_installed | default(false), "
                    "'packages': install_packages | default([])} | to_json }}"
                ),
            },
        }
    )
    playbook = tmp_path / "fixture.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Provisioning fixture",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": variables,
                    "tasks": tasks,
                }
            ]
        )
    )
    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", str(playbook)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(output.read_text())


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="Ansible unavailable"
)
@pytest.mark.parametrize(
    "provider,compose,expected",
    [
        ("docker-ce", True, []),
        ("docker-ce", False, ["docker-compose-plugin"]),
        ("docker.io", False, ["docker-compose-v2"]),
        ("custom", False, []),
    ],
)
def test_docker_preserves_provider(tmp_path, provider, compose, expected):
    play = yaml.safe_load((ANSIBLE / "workstation.yml").read_text())[0]
    task = next(
        task
        for task in play["tasks"]
        if task["name"] == "Preserve the installed Docker provider"
    )
    for nested in task["block"]:
        if "ansible.builtin.package_facts" in nested:
            del nested["ansible.builtin.package_facts"]
            nested["ansible.builtin.set_fact"] = {
                "ansible_facts": {"packages": {provider: [{"version": "fixture"}]}}
            }
        if "ansible.builtin.command" in nested:
            name = nested.pop("register")
            del nested["ansible.builtin.command"]
            nested.pop("environment", None)
            nested["ansible.builtin.set_fact"] = {
                name: {"rc": 0 if name == "machine_docker" or compose else 1}
            }
    result = run_task_fixture(
        tmp_path,
        [task],
        {
            "features": ["docker"],
            "packages_by_feature": {"docker": ["docker.io", "docker-compose-v2"]},
            "install_packages": ["docker.io", "docker-compose-v2"],
        },
    )
    assert result["packages"] == expected


def test_cli_defaults_match_ansible_profiles(monkeypatch, tmp_path: Path):
    from importlib.machinery import SourceFileLoader

    machine_mod = SourceFileLoader(
        "machine_cli_presets",
        str(REPO / "machine_cli/machine"),
    ).load_module()
    monkeypatch.setenv("DOTFILES_REPO", str(REPO))
    monkeypatch.setenv("HOME", str(tmp_path))
    machine = machine_mod.Machine()
    for name in PROFILES:
        data = load_profile(name)
        assert data["profile"] == name
        assert machine.default_features_for(name) == data["features"]


@pytest.mark.parametrize("name", PROFILES)
def test_expected_package_invariants(name: str):
    data = load_profile(name)
    packages = resolve_packages(data["profile"], data["features"])
    assert "curl" in packages
    if name == "rpi-zero":
        assert "eza" not in packages
        assert "ldap-utils" not in packages
        assert "guake" not in packages
        assert "zsh" in packages
        assert "fzf" not in packages
        assert "unattended-upgrades" in packages
    if name == "work-machine":
        assert "ldap-utils" in packages
        assert "krb5-user" in packages
        assert "guake" in packages
    if name == "home-laptop":
        assert "ldap-utils" not in packages
        assert "guake" in packages
        assert "evtest" in packages
        assert "python3-evdev" in packages
        assert "openssh-server" in packages
    if name == "home-server":
        assert "docker.io" in packages
        assert "unattended-upgrades" in packages
        assert "openssh-server" in packages
    if name == "container":
        assert "eza" not in packages
        assert "ldap-utils" not in packages


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)
@pytest.mark.parametrize(
    "name", ["home-laptop", "work-machine", "rpi-zero", "container"]
)
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
    assert ansible_packages == resolve_packages(
        data["profile"], data["features"], load_group_vars()
    )


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)
@pytest.mark.parametrize(
    "name,features",
    [
        ("home-laptop", None),
        ("home-server", None),
        ("rpi-zero", None),
        ("home-laptop", ["monitoring", "docker"]),
    ],
)
def test_python_monitoring_matches_ansible(name: str, features, tmp_path: Path):
    data = load_profile(name)
    feats = features if features is not None else data["features"]
    dump_path = tmp_path / "monitoring.json"
    # Build a temp extra-vars file so we can override features for docker case
    extra = tmp_path / "extra.yml"
    extra.write_text(
        f"---\nprofile: {name}\nfeatures:\n"
        + "".join(f"  - {f}\n" for f in feats)
        + "ssh_allow_from: []\n",
        encoding="utf-8",
    )
    cmd = [
        "ansible-playbook",
        str(ANSIBLE / "dump_monitoring.yml"),
        "-i",
        str(ANSIBLE / "inventory/local.yml"),
        "-e",
        f"@{extra}",
        "-e",
        f"dump_path={dump_path}",
    ]
    subprocess.run(cmd, check=True, cwd=ANSIBLE)
    ansible_names = json.loads(dump_path.read_text())
    assert ansible_names == resolve_monitoring(name, feats, load_group_vars())


def test_group_vars_are_lists():
    variables = load_group_vars()
    for key in ("packages_base", "packages_rpi_zero", "packages_host", "packages_work"):
        assert isinstance(variables[key], list)
    for feature, packages in variables["packages_by_feature"].items():
        assert isinstance(packages, list), feature
    assert isinstance(variables["monitoring_by_profile"], dict)
    assert "home-laptop" in variables["monitoring_by_profile"]


def test_monitoring_fallback_files_exist():
    files = REPO / "ansible/roles/monitoring/files"
    for name in (
        "machine_base.conf",
        "machine_laptop.conf",
        "machine_pi.conf",
        "machine_server.conf",
        "machine_docker.conf",
    ):
        assert (files / name).is_file()
