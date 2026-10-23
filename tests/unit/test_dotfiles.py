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


def test_conflicting_targets_are_cleared_without_losing_files(tmp_path):
    from machine_cli.dotfiles import clear_conflicting_targets

    repo = tmp_path / "checkout"
    (repo / "home/core/.config").mkdir(parents=True)
    for name in (".bashrc", ".zshrc", ".config/app"):
        (repo / "home/core" / name).write_text("new")
    home = tmp_path / "h"
    (home / ".config").mkdir(parents=True)
    (home / ".bashrc").write_text("distro default")
    (home / ".zshrc").symlink_to(repo / "home/dot_zshrc")  # old layout, dangling
    (home / ".config/app").symlink_to(repo / "home/core/.config/app")  # already right
    (home / ".bashrc.pre-dotfiles").write_text("older backup")
    (home / ".config/app2").write_text("new")  # identical to the repository file
    (repo / "home/core/.config/app2").write_text("new")

    changed = clear_conflicting_targets(repo, home, ["core"])

    assert sorted(p.name for p, _ in changed) == [".bashrc", ".zshrc", "app2"]
    assert not (home / ".config/app2").exists()
    assert not (home / ".config/app2.pre-dotfiles").exists()
    assert not (home / ".bashrc").exists() and not (home / ".zshrc").is_symlink()
    assert (home / ".bashrc.pre-dotfiles.2").read_text() == "distro default"
    assert (home / ".bashrc.pre-dotfiles").read_text() == "older backup"
    assert (home / ".config/app").is_symlink()


def test_fonts_group_follows_the_feature():
    assert "fonts" in dotfile_groups("home-laptop", ["fonts"])
    assert "fonts" not in dotfile_groups("home-laptop", [])
