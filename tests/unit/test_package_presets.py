from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from package_sets import (
    ANSIBLE,
    HOSTS,
    REPO,
    host_vars,
    load_group_vars,
    resolve_monitoring,
    resolve_packages,
)


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
        if "ansible.builtin.shell" in nested:
            name = nested.pop("register")
            del nested["ansible.builtin.shell"]
            nested.pop("args", None)
            nested["ansible.builtin.set_fact"] = {
                name: {"stdout_lines": [] if provider == "custom" else [provider]}
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
            "machine_features": ["docker"],
            "packages_by_feature": {"docker": ["docker.io", "docker-compose-v2"]},
            "install_packages": ["docker.io", "docker-compose-v2"],
        },
    )
    assert result["packages"] == expected


@pytest.mark.parametrize("name", list(HOSTS))
def test_expected_package_invariants(name: str):
    packages = resolve_packages(host_vars(name))
    assert "curl" in packages
    assert "guake" not in packages
    if name == "pi-zero":
        assert "eza" not in packages
        assert "ldap-utils" not in packages
        assert "zsh" in packages
        assert "fonts-firacode" not in packages
        assert "unattended-upgrades" in packages
    if name == "work-desktop":
        assert "ldap-utils" in packages
        assert "krb5-user" in packages
        assert "unattended-upgrades" not in packages
        assert "openssh-server" not in packages
    if name == "private-laptop":
        assert "ldap-utils" not in packages
        assert "openssh-server" in packages
        assert "thunderbird" in packages
    if name == "private-server":
        assert "docker.io" in packages
        assert "unattended-upgrades" in packages
        assert "openssh-server" in packages
    if name == "container":
        assert "fonts-firacode" not in packages
        assert "ldap-utils" not in packages


def test_laptop_and_pi_packages_follow_the_hardware():
    laptop = resolve_packages(host_vars("private-laptop"))
    desktop = resolve_packages(host_vars("private-desktop"))
    pi = resolve_packages(host_vars("pi", ["zram-swap"]))
    assert "power-profiles-daemon" in laptop and "systemd-zram-generator" in laptop
    assert "power-profiles-daemon" not in desktop
    assert "systemd-zram-generator" in desktop
    assert "systemd-zram-generator" not in pi


def test_excluded_features_bring_no_packages():
    host = host_vars("work-desktop", ["zsh-full", "monitoring", "sshd-home"])
    assert "openssh-server" not in resolve_packages(host)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("private-laptop", ["machine/base", "machine/laptop", "machine/docker"]),
        ("private-desktop", ["machine/base", "machine/docker"]),
        ("private-server", ["machine/base", "machine/server", "machine/docker"]),
        ("pi", ["machine/base", "machine/pi", "machine/docker"]),
        ("work-desktop", []),
        ("container", []),
    ],
)
def test_monitoring_fragments_from_hardware(name, expected):
    assert resolve_monitoring(host_vars(name)) == expected


def _dump(playbook: str, name: str, tmp_path: Path, features=None):
    dump_path = tmp_path / "dump.json"
    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps(host_vars(name, features)))
    subprocess.run(
        [
            "ansible-playbook",
            str(ANSIBLE / playbook),
            "-i",
            str(ANSIBLE / "inventory/local.yml"),
            "-e",
            f"@{extra}",
            "-e",
            f"dump_path={dump_path}",
        ],
        check=True,
        cwd=ANSIBLE,
        capture_output=True,
    )
    return json.loads(dump_path.read_text())


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)
@pytest.mark.parametrize(
    "name", ["private-laptop", "work-desktop", "pi-zero", "container"]
)
def test_python_resolver_matches_ansible(name: str, tmp_path: Path):
    assert sorted(_dump("dump_packages.yml", name, tmp_path)) == resolve_packages(
        host_vars(name), load_group_vars()
    )


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="ansible-playbook not installed"
)
@pytest.mark.parametrize(
    "name,features",
    [
        ("private-laptop", None),
        ("private-server", None),
        ("pi-zero", None),
        ("private-desktop", ["monitoring"]),
    ],
)
def test_python_monitoring_matches_ansible(name: str, features, tmp_path: Path):
    host = host_vars(name, features)
    assert _dump("dump_monitoring.yml", name, tmp_path, features) == resolve_monitoring(
        host
    )


def test_group_vars_are_lists():
    variables = load_group_vars()
    for key in ("packages_base", "packages_rpi_zero", "packages_host", "packages_work"):
        assert isinstance(variables[key], list)
    for feature, packages in variables["packages_by_feature"].items():
        assert isinstance(packages, list), feature
    assert "monitoring_by_profile" not in variables
    assert isinstance(variables["feature_table"], dict)


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
