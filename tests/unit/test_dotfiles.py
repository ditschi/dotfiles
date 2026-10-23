from __future__ import annotations

import sys
from pathlib import Path

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli.dotfiles import (  # noqa: E402
    DotfilesMixin,
    dotfile_groups,
    render_local_config,
    sweep_dangling_links,
)


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


class _Host(DotfilesMixin):
    def __init__(self, home: Path):
        self.home = home


@pytest.mark.parametrize(
    "profile, email",
    [
        ("work-machine", "christian.ditscher@de.bosch.com"),
        ("home-laptop", "chris@ditscher.me"),
        ("container", "chris@ditscher.me"),
    ],
)
def test_first_setup_creates_gitconfig_local(tmp_path, profile, email):
    _Host(tmp_path).ensure_gitconfig_local(profile)
    text = (tmp_path / ".gitconfig.local").read_text()
    assert f"email = {email}" in text
    assert ("sslCAInfo" in text) == (profile == "work-machine")
    assert ("directory = /workspace" in text) == (profile == "container")


def test_existing_gitconfig_local_is_left_alone(tmp_path):
    local = tmp_path / ".gitconfig.local"
    local.write_text("[user]\n    email = mine@example.com\n")
    _Host(tmp_path).ensure_gitconfig_local("home-laptop")
    assert local.read_text() == "[user]\n    email = mine@example.com\n"


def test_work_host_gets_missing_ca_bundle_key_only(tmp_path):
    local = tmp_path / ".gitconfig.local"
    local.write_text("[user]\n    email = mine@example.com\n")
    host = _Host(tmp_path)
    host.ensure_gitconfig_local("work-machine")
    seeded = local.read_text()
    assert seeded.startswith("[user]\n    email = mine@example.com\n")
    assert seeded.count("sslCAInfo") == 1
    host.ensure_gitconfig_local("work-machine")
    assert local.read_text() == seeded


def test_sweep_removes_only_dangling_links_into_the_checkout(tmp_path):
    repo = tmp_path / "checkout"
    (repo / "home").mkdir(parents=True)
    live = repo / "home/.live"
    live.write_text("x")
    home = tmp_path / "h"
    (home / ".config").mkdir(parents=True)
    (home / ".zshrc").symlink_to(repo / "home/dot_zshrc")  # old name, now gone
    (home / ".config/gone").symlink_to(repo / "home/.removed")
    (home / ".live").symlink_to(live)
    (home / ".foreign").symlink_to(tmp_path / "elsewhere")  # broken, not ours
    (home / ".plain").write_text("keep")

    removed = sweep_dangling_links(home, repo)

    assert sorted(p.name for p in removed) == [".zshrc", "gone"]
    assert (home / ".live").is_symlink() and (home / ".foreign").is_symlink()
    assert (home / ".plain").read_text() == "keep"
