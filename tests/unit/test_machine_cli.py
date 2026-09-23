from __future__ import annotations

import os
import subprocess
import textwrap
from importlib.machinery import SourceFileLoader
from pathlib import Path

from package_sets import REPO

MACHINE = REPO / "home/dot_local/bin/executable_machine"


def _cli():
    return SourceFileLoader("machine_cli", str(MACHINE)).load_module()


def test_help_lists_setup_migrate_and_env():
    result = subprocess.run(
        ["python3", str(MACHINE), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "setup" in result.stdout
    assert "migrate" in result.stdout
    assert "env" in result.stdout
    assert "ssh" in result.stdout


def test_zsh_completion_contains_profiles():
    result = subprocess.run(
        ["python3", str(MACHINE), "completion", "zsh"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "work-laptop" in result.stdout
    assert "rpi-zero" in result.stdout
    assert "migrate" in result.stdout
    assert "compdef _machine machine" in result.stdout


def test_env_item_names_by_class(tmp_path: Path, monkeypatch):
    cli = _cli()
    assert cli.ENV_CLASS["work-laptop"] == "work"
    assert cli.ENV_CLASS["rpi-zero"] == "iot"
    assert cli.ENV_CLASS["container"] == ""
    monkeypatch.setenv("DOTFILES_REPO", str(REPO))
    monkeypatch.setenv("HOME", str(tmp_path))
    machine = cli.Machine()
    assert "monitoring" in machine.default_features_for("home-laptop")
    assert "monitoring" not in machine.default_features_for("work-laptop")
    assert "ssh-host-key" in machine.default_features_for("home-laptop")


def test_monitoring_resolved_in_ansible_group_vars():
    from package_sets import resolve_monitoring

    assert resolve_monitoring("home-laptop", ["monitoring"]) == [
        "machine/base",
        "machine/laptop",
    ]
    assert resolve_monitoring("home-laptop", ["monitoring", "docker"]) == [
        "machine/base",
        "machine/laptop",
        "machine/docker",
    ]
    assert resolve_monitoring("rpi-zero", ["monitoring"]) == [
        "machine/base",
        "machine/pi",
    ]
    assert resolve_monitoring("work-laptop", ["kerberos"]) == []
    assert resolve_monitoring("home-server", ["monitoring", "docker"]) == [
        "machine/base",
        "machine/server",
        "machine/docker",
    ]


def test_cli_has_no_monitoring_map():
    cli = _cli()
    assert not hasattr(cli, "MONITORING_BY_PROFILE")
    assert not hasattr(cli, "DEFAULT_FEATURES")
    assert not hasattr(cli, "monitoring_configs")


def test_ssh_item_names_separated_by_class():
    cli = _cli()
    assert cli.SSH_CLASS["home-laptop"] == "home"
    assert cli.SSH_CLASS["work-laptop"] == "work"
    assert cli.SSH_CLASS["rpi-zero"] == "home"


def test_parse_profile_file_roundtrip(tmp_path: Path):
    cli = _cli()
    path = tmp_path / "profile.yml"
    path.write_text(
        textwrap.dedent(
            """\
            ---
            profile: home-laptop
            features:
              - zsh-full
              - monitoring
            ssh_allow_from:
              - homeserver
              - laptop2
            """
        ),
        encoding="utf-8",
    )
    data = cli.parse_profile_file(path)
    assert data["profile"] == "home-laptop"
    assert data["features"] == ["zsh-full", "monitoring"]
    assert data["ssh_allow_from"] == ["homeserver", "laptop2"]


def test_parse_empty_ssh_allow_from(tmp_path: Path):
    cli = _cli()
    path = tmp_path / "profile.yml"
    path.write_text(
        "---\nprofile: home-laptop\nfeatures:\n  - zsh-full\nssh_allow_from: []\n",
        encoding="utf-8",
    )
    data = cli.parse_profile_file(path)
    assert data["ssh_allow_from"] == []


def test_needs_layout_migration_detects_old_root_symlink(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / "home" / "dot_zshrc").write_text("# new\n", encoding="utf-8")
    (repo / ".git").mkdir()
    (repo / "bootstrap").write_text("#!/bin/sh\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    # old-style symlink into repo root
    (home / ".zshrc").symlink_to(repo / ".zshrc")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    machine = cli_mod.Machine()
    assert machine.needs_layout_migration() is True


def test_write_rollback_script(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))

    machine = cli_mod.Machine()
    path = machine.write_rollback_script("abc123")
    text = path.read_text(encoding="utf-8")
    assert "abc123" in text
    assert "install.py" in text
    assert path.stat().st_mode & 0o100
