from __future__ import annotations

import sys
from pathlib import Path

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli.dotfiles import (  # noqa: E402
    DotfilesMixin,
    clear_conflicting_targets,
    dotfile_groups,
    render_github_token_config,
    render_local_config,
    sweep_dangling_links,
)


@pytest.mark.parametrize(
    "context, device, expected",
    [
        ("work", "desktop", ["core", "prompt", "systemd", "work"]),
        ("private", "desktop", ["core", "prompt", "systemd"]),
        ("private", "server", ["core", "prompt", "systemd"]),
        ("", "container", ["core", "prompt"]),
    ],
)
def test_groups_per_context_and_device(context, device, expected):
    assert dotfile_groups(context, device, ["zsh-full"]) == expected


def test_work_group_only_for_work_machine():
    hosts = [("private", "desktop"), ("private", "server"), ("", "container")]
    assert all("work" not in dotfile_groups(c, d) for c, d in hosts)


def test_local_config_lists_groups():
    assert render_local_config(["core", "work"]) == (
        '[bootstrap]\ndotfile_groups = ["core", "work"]\n'
    )


class _Host(DotfilesMixin):
    def __init__(self, home: Path):
        self.home = home


@pytest.mark.parametrize(
    "context, device, email",
    [
        ("work", "desktop", "christian.ditscher@de.bosch.com"),
        ("private", "desktop", "chris@ditscher.me"),
        ("", "container", "chris@ditscher.me"),
    ],
)
def test_first_setup_creates_gitconfig_local(tmp_path, context, device, email):
    _Host(tmp_path).ensure_gitconfig_local(context, device)
    text = (tmp_path / ".gitconfig.local").read_text()
    assert f"email = {email}" in text
    assert ("sslCAInfo" in text) == (context == "work")
    assert ("directory = /workspace" in text) == (device == "container")


def test_existing_gitconfig_local_is_left_alone(tmp_path):
    local = tmp_path / ".gitconfig.local"
    local.write_text("[user]\n    email = mine@example.com\n")
    _Host(tmp_path).ensure_gitconfig_local("private", "desktop")
    assert local.read_text() == "[user]\n    email = mine@example.com\n"


def test_work_host_gets_missing_ca_bundle_key_only(tmp_path):
    local = tmp_path / ".gitconfig.local"
    local.write_text("[user]\n    email = mine@example.com\n")
    host = _Host(tmp_path)
    host.ensure_gitconfig_local("work", "desktop")
    seeded = local.read_text()
    assert seeded.startswith("[user]\n    email = mine@example.com\n")
    assert seeded.count("sslCAInfo") == 1
    host.ensure_gitconfig_local("work", "desktop")
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


def test_sweep_resolves_checkout_alias_in_dangling_link_target(tmp_path):
    repo = tmp_path / "checkout"
    (repo / "home").mkdir(parents=True)
    repo_alias = tmp_path / "checkout-alias"
    repo_alias.symlink_to(repo, target_is_directory=True)
    home = tmp_path / "h"
    home.mkdir()
    stale = home / ".zshrc"
    stale.symlink_to(repo_alias / "home/dot_zshrc")

    removed = sweep_dangling_links(home, repo)

    assert removed == [stale]
    assert not stale.is_symlink()


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


def test_conflicting_target_cleanup_resolves_checkout_alias(tmp_path):
    repo = tmp_path / "checkout"
    new_config = repo / "home/core/.zsh/config/05_pyenv.zsh"
    new_config.parent.mkdir(parents=True)
    new_config.write_text("new config")
    repo_alias = tmp_path / "checkout-alias"
    repo_alias.symlink_to(repo, target_is_directory=True)
    home = tmp_path / "h"
    stale = home / ".zsh/config/05_pyenv.zsh"
    stale.parent.mkdir(parents=True)
    stale.symlink_to(repo_alias / "home/dot_zsh/config/05_pyenv.zsh")

    changed = clear_conflicting_targets(repo, home, ["core"])

    assert changed == [(stale, "removed stale link")]
    assert not stale.is_symlink()


def test_conflicting_target_cleanup_removes_stale_parent_directory_link(tmp_path):
    repo = tmp_path / "checkout"
    for name in ("cache-eval.sh", "config/00_LOADER.zsh"):
        (repo / "home/core/.zsh" / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / "home/core/.zsh" / name).write_text(name)
    home = tmp_path / "h"
    home.mkdir()
    stale = home / ".zsh"
    stale.symlink_to(Path("../checkout/.zsh"))  # oldest layout, dangling

    changed = clear_conflicting_targets(repo, home, ["core"])

    assert changed == [(stale, "removed stale link")]
    assert not stale.is_symlink() and not stale.exists()


def test_conflicting_target_cleanup_keeps_parent_link_outside_checkout(tmp_path):
    repo = tmp_path / "checkout"
    (repo / "home/core/.zsh").mkdir(parents=True)
    (repo / "home/core/.zsh/cache-eval.sh").write_text("x")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    home = tmp_path / "h"
    home.mkdir()
    (home / ".zsh").symlink_to(elsewhere, target_is_directory=True)

    assert clear_conflicting_targets(repo, home, ["core"]) == []
    assert (home / ".zsh").is_symlink()


def test_fonts_group_follows_the_feature():
    assert "fonts" in dotfile_groups("private", "desktop", ["fonts"])
    assert "fonts" not in dotfile_groups("private", "desktop", [])
    assert "thunderbird" in dotfile_groups("private", "desktop", ["thunderbird"])
    assert "thunderbird" not in dotfile_groups("private", "desktop", [])
    assert "thunderbird" not in dotfile_groups("work", "desktop", ["thunderbird"])


def test_gnome_group_follows_the_gnome_feature():
    assert "gnome" in dotfile_groups("work", "desktop", ["gnome"])
    assert "gnome" not in dotfile_groups("work", "desktop", [])
    assert "gnome" not in dotfile_groups("work", "server", ["gnome"])


def _checkout_with_cli(tmp_path):
    repo = tmp_path / "repo"
    cli = repo / "machine_cli" / "machine"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n")
    return repo, cli


def test_machine_link_replaces_the_copied_entry_point(tmp_path):
    repo, cli = _checkout_with_cli(tmp_path)
    old = tmp_path / ".local/bin/machine"
    old.parent.mkdir(parents=True)
    old.write_text("old copied script\n")
    host = _Host(tmp_path)
    host.repo = repo

    host.ensure_machine_link()

    assert old.is_symlink() and old.resolve() == cli.resolve()
    host.ensure_machine_link()  # idempotent
    assert old.resolve() == cli.resolve()


def test_machine_link_follows_the_running_checkout(tmp_path):
    repo, cli = _checkout_with_cli(tmp_path)
    link = tmp_path / ".local/bin/machine"
    link.parent.mkdir(parents=True)
    link.symlink_to(tmp_path / "elsewhere/machine_cli/machine")
    host = _Host(tmp_path)
    host.repo = repo

    host.ensure_machine_link()

    assert link.resolve() == cli.resolve()


@pytest.mark.parametrize(
    "context, variable",
    [
        ("work", "GITHUB_PRIVATE_TOKEN"),
        ("private", "GITHUB_TOKEN"),
        ("", "GITHUB_TOKEN"),
    ],
)
def test_github_token_variable_follows_the_context(tmp_path, context, variable):
    host = _Host(tmp_path)
    host.write_github_token_config(context)
    text = (tmp_path / ".config/git/github-token.gitconfig").read_text()
    assert f"git-credential-env {variable}\n" in text
    other = (
        "GITHUB_TOKEN" if variable == "GITHUB_PRIVATE_TOKEN" else "GITHUB_PRIVATE_TOKEN"
    )
    assert f"git-credential-env {other}\n" not in text


def test_private_gitconfig_includes_the_token_file_after_the_reset(tmp_path):
    """Git resolves the helper list: reset, then the helper of the included file."""
    import subprocess

    shared = REPO / "home/core/.config/git/private.gitconfig"
    home = tmp_path
    (home / ".config/git").mkdir(parents=True)
    (home / ".config/git/github-token.gitconfig").write_text(
        render_github_token_config("private")
    )
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"}
    out = subprocess.run(
        ["git", "config", "--file", str(shared), "--includes", "--get-all",
         "credential.https://github.com.helper"],
        env=env, capture_output=True, text=True, check=True,
    ).stdout.splitlines()  # fmt: skip
    assert out == ["", "!$HOME/.local/bin/git-credential-env GITHUB_TOKEN"]


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://github.com/ditschi/dotfiles.git",
            "git@github.com:ditschi/dotfiles.git",
        ),
        (
            "https://github.com/ditschi/dotfiles\n",
            "git@github.com:ditschi/dotfiles.git",
        ),
        ("git@github.com:ditschi/dotfiles.git", ""),
        ("https://github.boschdevcloud.com/x/y.git", ""),
    ],
)
def test_github_ssh_url(url, expected):
    from machine_cli.dotfiles import github_ssh_url

    assert github_ssh_url(url) == expected


@pytest.mark.parametrize(
    "context, ssh_reply, switched",
    [
        ("private", "Hi ditschi! You've successfully authenticated", True),
        ("private", "Permission denied (publickey).", False),
        ("work", "Hi ditschi! You've successfully authenticated", False),
    ],
)
def test_origin_switches_to_ssh_only_when_it_works(
    tmp_path, monkeypatch, context, ssh_reply, switched
):
    import subprocess

    from machine_cli import dotfiles

    calls = []

    def run(args, **_kw):
        calls.append(list(args))
        if args[-2:] == ["get-url", "origin"]:
            return subprocess.CompletedProcess(
                args, 0, "https://github.com/ditschi/dotfiles.git\n", ""
            )
        if args[0] == "ssh":
            return subprocess.CompletedProcess(args, 1, "", ssh_reply)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(dotfiles.system, "run", run)
    monkeypatch.setattr(dotfiles.system, "have", lambda _n: True)
    host = _Host(tmp_path)
    host.repo = tmp_path

    host.switch_origin_to_ssh(context, "desktop")

    set_url = [c for c in calls if "set-url" in c]
    assert bool(set_url) == switched
    if switched:
        assert set_url[0][-1] == "git@github.com:ditschi/dotfiles.git"
