"""Local runs start ansible-playbook as root, so `become: false` means root.

Tasks for the login user name it with `become_user`; only controller-side reads may
keep `become: false`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from package_sets import ANSIBLE

# (file relative to ansible/, task or play name)
ROOT_ON_PURPOSE = {
    (
        "roles/sshd_home/tasks/main.yml",
        "Build list of present pubkey files for ssh_allow_from",
    ),
}

LOGIN_USER_TASKS = {
    ("workstation.yml", "Check existing Docker CLI as the login user"),
    ("workstation.yml", "Check existing Compose capability"),
    ("workstation.yml", "Touch device (GNOME extensions for the login user)"),
}


def _playbook_files() -> list[Path]:
    files = sorted(ANSIBLE.glob("*.yml"))
    files += sorted(ANSIBLE.glob("tasks/*.yml"))
    files += sorted(ANSIBLE.glob("roles/*/tasks/*.yml"))
    files += sorted(ANSIBLE.glob("roles/*/handlers/*.yml"))
    return files


def _entries(node):
    """Every play, task and block mapping in a loaded playbook or task file."""
    if isinstance(node, list):
        for item in node:
            yield from _entries(item)
    elif isinstance(node, dict):
        if {"name", "hosts", "block", "become"} & set(node):
            yield node
        for key in ("tasks", "pre_tasks", "post_tasks", "handlers", "block"):
            yield from _entries(node.get(key))
        for key in ("rescue", "always"):
            yield from _entries(node.get(key))


def _all_entries():
    for path in _playbook_files():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        rel = str(path.relative_to(ANSIBLE))
        for entry in _entries(data):
            yield rel, entry


def test_become_false_only_where_root_is_intended():
    found = {
        (rel, entry.get("name", ""))
        for rel, entry in _all_entries()
        if entry.get("become") is False
    }
    assert found == ROOT_ON_PURPOSE


def test_login_user_tasks_switch_to_the_login_user():
    entries = {(rel, entry.get("name", "")): entry for rel, entry in _all_entries()}
    for key in LOGIN_USER_TASKS:
        entry = entries[key]
        assert entry.get("become") == "{{ machine_runs_as_root | bool }}", key
        assert entry.get("become_user") == "{{ machine_login_user }}", key
