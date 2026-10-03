from __future__ import annotations

import json
import os
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
    "work-laptop",
    "home-server",
    "rpi",
    "rpi-zero",
    "container",
]


def run_task_fixture(tmp_path, tasks, variables):
    output = tmp_path / "result.json"
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
    "current,status,target,upgrade",
    [
        ("26.9.1", 200, "26.9.1", False),
        ("26.8.1", 200, "26.9.1", True),
        ("27.1.1", 200, "26.9.1", False),
        ("26.8.1", 503, "", False),
    ],
)
def test_yazi_release_policy_with_mocked_mutations(
    tmp_path, current, status, target, upgrade
):
    tasks = yaml.safe_load((ANSIBLE / "roles/yazi/tasks/main.yml").read_text())
    release = {"status": status}
    if status == 200:
        release["json"] = {
            "tag_name": "v" + target,
            "assets": [
                {
                    "name": "yazi-x86_64-unknown-linux-gnu.deb",
                    "browser_download_url": "https://example.invalid/yazi.deb",
                    "digest": "sha256:fixture",
                }
            ],
        }

    def mock_actions(items):
        for task in items:
            if "block" in task:
                mock_actions(task["block"])
            replacements = {
                "ansible.builtin.uri": {"yazi_release": release},
                "ansible.builtin.get_url": {"fixture_download": True},
                "ansible.builtin.apt": {"fixture_installed": True},
            }
            if "ansible.builtin.command" in task:
                name = task.get("register", "yazi_installed")
                replacements["ansible.builtin.command"] = {
                    name: {
                        "rc": 0,
                        "stdout": "Yazi "
                        + (target if name == "yazi_effective" else current),
                    }
                }
            for action, facts in replacements.items():
                if action in task:
                    del task[action]
                    for key in (
                        "register",
                        "environment",
                        "become",
                        "check_mode",
                        "failed_when",
                        "changed_when",
                    ):
                        task.pop(key, None)
                    task["ansible.builtin.set_fact"] = facts

    mock_actions(tasks)
    result = run_task_fixture(
        tmp_path, tasks, {"ansible_architecture": "x86_64", "yazi_version": "latest"}
    )
    assert result["download"] is upgrade
    assert result["installed"] is upgrade


@pytest.mark.skipif(
    shutil.which("ansible-playbook") is None, reason="Ansible unavailable"
)
@pytest.mark.parametrize("role,tool", [("gh_cli", "gh"), ("az_cli", "az")])
def test_existing_cli_skips_all_package_mutations(tmp_path, role, tool):
    binary = tmp_path / tool
    binary.write_text("#!/bin/sh\nprintf 'fixture version\\n'\n")
    binary.chmod(0o755)
    tasks = yaml.safe_load((ANSIBLE / f"roles/{role}/tasks/main.yml").read_text())

    def forbid_mutations(items):
        for task in items:
            if "block" in task:
                forbid_mutations(task["block"])
            for action in list(task):
                if (
                    action.startswith("ansible.builtin.")
                    and action != "ansible.builtin.command"
                ):
                    del task[action]
                    task["ansible.builtin.fail"] = {
                        "msg": "existing CLI must not change packages or sources"
                    }

    forbid_mutations(tasks)
    run_task_fixture(
        tmp_path,
        tasks,
        {
            "machine_user_path": str(tmp_path) + ":" + os.environ["PATH"],
            "ansible_env": {"PATH": os.environ["PATH"]},
        },
    )


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
            "packages_docker": ["docker.io", "docker-compose-v2"],
            "install_packages": ["docker.io", "docker-compose-v2"],
        },
    )
    assert result["packages"] == expected


def test_cli_defaults_match_ansible_profiles(monkeypatch, tmp_path: Path):
    from importlib.machinery import SourceFileLoader

    machine_mod = SourceFileLoader(
        "machine_cli_presets",
        str(REPO / "home/dot_local/bin/executable_machine"),
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
    assert "git" in packages or name == "rpi-zero"
    if name == "rpi-zero":
        assert "eza" not in packages
        assert "ldap-utils" not in packages
        assert "guake" not in packages
        assert "zsh" in packages
        assert "fzf" in packages
        assert "unattended-upgrades" in packages
    if name == "work-laptop":
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
    "name", ["home-laptop", "work-laptop", "rpi-zero", "container"]
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
    for key in (
        "packages_base",
        "packages_zsh",
        "packages_host",
        "packages_desktop",
        "packages_gnome",
        "packages_work",
        "packages_rpi_zero",
        "packages_docker",
        "packages_monitoring",
        "packages_unattended",
        "packages_syncthing",
        "packages_cosmic",
        "packages_stylus_touch_guard",
        "packages_thinkpad_tuning",
        "packages_sshd_home",
    ):
        assert isinstance(variables[key], list)
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
