"""Relevance filter: which changed files apply to this host's Ansible run."""

from __future__ import annotations

import sys

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli.system_relevance import relevant_system_paths  # noqa: E402

PLAYBOOK = """\
- name: Stylus
  hosts: all
  roles:
    - role: stylus_touch_guard
      when: "'stylus-touch-guard' in machine_features"
    - role: sshd_home
      when: "'sshd-home' in machine_features"
    - role: odd
      when: ansible_facts.os_family == 'Debian'
"""


@pytest.fixture
def ansible_dir(tmp_path):
    (tmp_path / "workstation.yml").write_text(PLAYBOOK)
    return tmp_path


def relevant(ansible_dir, paths, features=(), context="private", device="desktop"):
    return relevant_system_paths(
        paths,
        ansible_dir=ansible_dir,
        features=list(features),
        context=context,
        device=device,
        own_host_config="machine/hosts/me.yml",
    )


def test_always_relevant_paths(ansible_dir):
    paths = [
        "ansible/workstation.yml",
        "ansible/tasks/resolve_packages.yml",
        "ansible/group_vars/all/packages.yml",
        "machine/hosts/me.yml",
    ]
    assert relevant(ansible_dir, paths) == sorted(paths)


def test_ignored_paths(ansible_dir):
    paths = [
        "ansible/README.md",
        "ansible/dump_packages.yml",
        "ansible/inventory/local.yml",
        "machine/hosts/other.yml",
        "home/core/.zshrc",
    ]
    assert relevant(ansible_dir, paths) == []


def test_role_not_enabled_is_ignored_and_enabled_counts(ansible_dir):
    path = ["ansible/roles/stylus_touch_guard/tasks/main.yml"]
    assert relevant(ansible_dir, path) == []
    assert relevant(ansible_dir, path, features=["stylus-touch-guard"]) == path


def test_excluded_feature_is_not_relevant(ansible_dir):
    path = ["ansible/roles/sshd_home/tasks/main.yml"]
    assert relevant(ansible_dir, path, ["sshd-home"], "work", "desktop") == []
    assert relevant(ansible_dir, path, ["sshd-home"], "private", "server") == path


def test_unknown_conditions_and_roles_count(ansible_dir):
    paths = ["ansible/roles/odd/tasks/main.yml", "ansible/roles/unlisted/x.yml"]
    assert relevant(ansible_dir, paths) == sorted(paths)
