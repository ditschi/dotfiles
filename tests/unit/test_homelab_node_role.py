"""homelab_node role: safety boundary, pinned sops, secret handling, CI forced command."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess

import pytest
import yaml

from package_sets import ANSIBLE

ROLE = ANSIBLE / "roles/homelab_node"
TASKS = ROLE / "tasks/main.yml"
WRAPPER = ROLE / "files/homelab-ci"


def _tasks(items=None):
    """All tasks of the role, blocks flattened."""
    items = (
        yaml.safe_load(TASKS.read_text(encoding="utf-8")) if items is None else items
    )
    for task in items:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _tasks(task.get(key) or [])


def _commands():
    """Every command line the role runs (command and shell tasks)."""
    for task in _tasks():
        for module in ("ansible.builtin.command", "ansible.builtin.shell"):
            if module in task:
                args = task[module]
                if isinstance(args, dict):
                    args = " ".join(map(str, args.get("argv") or [args.get("cmd", "")]))
                yield str(args)


def test_role_never_touches_containers_reboots_or_data_roots():
    text = TASKS.read_text(encoding="utf-8")
    for root in (
        "/mnt/volume/containers",
        "/opt/containers",
        "/mnt/data-internal/services",
    ):
        assert root not in text
    for command in _commands():
        assert not re.search(r"\breboot\b|\bprune\b|systemctl", command), command
        if re.search(r"\bdocker\b", command):
            assert command in ("docker --version", "docker compose version"), command


def test_tasks_reading_or_writing_the_age_key_hide_their_values():
    for task in _tasks():
        text = json.dumps(task)
        if "homelab_age_private_key" in text or "keys.txt" in text:
            if task.get("ansible.builtin.file") or "block" in task:
                continue  # directories only, or a block whose tasks are checked
            if (
                task.get("ansible.builtin.set_fact")
                and "age_key" in text
                and "homelab_node_status" in text
            ):
                continue  # records only the state name
            assert task.get("no_log") is True, task.get("name")


def test_pinned_sops_checksums_for_both_architectures():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text(encoding="utf-8"))
    assert str(defaults["homelab_node_sops_version"]) == "3.13.3"
    for arch in ("amd64", "arm64"):
        assert re.fullmatch(r"[0-9a-f]{64}", defaults["homelab_node_sops_sha256"][arch])
    get_url = [t for t in _tasks() if "ansible.builtin.get_url" in t]
    assert len(get_url) == 1
    assert get_url[0]["ansible.builtin.get_url"]["checksum"].startswith("sha256:")


def test_github_host_keys_are_pinned():
    lines = [
        line
        for line in (ROLE / "files/github_known_hosts").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    assert {line.split()[1] for line in lines} == {
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ssh-rsa",
    }
    assert all(line.startswith("github.com ") for line in lines)


def test_deploy_key_is_not_identities_only_in_the_clone():
    """Push with a forwarded agent key needs the agent offered first."""
    clone_block = next(
        t for t in _tasks() if t.get("name") == "Clone with the read-only deploy key"
    )
    assert "IdentitiesOnly" not in clone_block["vars"]["ssh_command"]
    check = next(t for t in _tasks() if t.get("name", "").startswith("Ask GitHub"))
    assert "IdentityAgent=none" in check["environment"]["GIT_SSH_COMMAND"]


def test_existing_clone_is_never_fetched_or_reset():
    git = [c for c in _commands() if c.startswith("git ")]
    assert git, "the role runs git"
    for command in git:
        assert command.split()[1] in ("ls-remote", "clone", "-C"), command
        if command.startswith("git -C"):
            assert " config " in command, command
    assert not [t for t in _tasks() if "ansible.builtin.git" in t]


def test_ci_key_gets_the_forced_command():
    task = next(
        t
        for t in _tasks()
        if t.get("name") == "Allow the CI key only for `homelab deploy`"
    )
    options = task["ansible.posix.authorized_key"]["key_options"]
    assert options.startswith("restrict,command=")


# --- forced command -------------------------------------------------------------


def _wrapper():
    spec = importlib.util.spec_from_loader(
        "homelab_ci", importlib.machinery.SourceFileLoader("homelab_ci", str(WRAPPER))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("sha", ["0803d4e", "0803d4e" + "a" * 33])
def test_wrapper_accepts_homelab_deploy_with_a_sha(sha):
    assert _wrapper().requested_sha(f"homelab deploy {sha}") == sha


@pytest.mark.parametrize(
    "command",
    [
        "",
        "homelab deploy",
        "homelab deploy 0803d4",  # too short
        "homelab deploy " + "a" * 41,  # too long
        "homelab deploy 0803D4E",  # not lower-case hex
        "homelab deploy main",
        "homelab deploy 0803d4e --dirty",
        "homelab deploy 0803d4e; id",
        "homelab deploy 0803d4e\nid",
        "homelab deploy $(id)",
        "hl deploy 0803d4e",
        "docker ps",
        "rsync --server -logDtpre.iLsfxC . /opt/containers",
    ],
)
def test_wrapper_refuses_everything_else(command):
    assert _wrapper().requested_sha(command) is None


def test_wrapper_refusal_exits_non_zero_without_running_anything():
    result = subprocess.run(
        [str(WRAPPER)],
        env={**os.environ, "SSH_ORIGINAL_COMMAND": "docker ps"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "only `homelab deploy <sha>`" in result.stderr


# --- refused setup writes only the status ---------------------------------------

needs_ansible = pytest.mark.skipif(
    not shutil.which("ansible-playbook"), reason="ansible-playbook not installed"
)


@needs_ansible
def test_refused_setup_changes_nothing_but_the_status(tmp_path):
    status = tmp_path / "state/homelab-node.json"
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        json.dumps(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "machine_login_user": "root",
                        "homelab_node_status_file": str(status),
                        "homelab_node": {
                            "host": "contabo",
                            "user": "root",
                            "clone": "/opt/homelab",
                            "managed_clone": True,
                            "ci_restrict": False,
                            "problems": [
                                "homelab.user is root; the deploy user must not be root"
                            ],
                        },
                    },
                    "roles": [{"role": str(ROLE)}],
                }
            ]
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["ansible-playbook", "-i", "localhost,", str(playbook)],
        env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(status.read_text())
    assert data["problems"] == [
        "homelab.user is root; the deploy user must not be root"
    ]
    # at most the state directory; the status file is bookkeeping
    assert re.search(r"changed=[01]\b", result.stdout), result.stdout
