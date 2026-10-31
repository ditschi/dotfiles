"""Bitwarden CLI from mise (spec secret-tools): install and removal of the old download."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import system  # noqa: E402
from machine_cli.machine import Machine  # noqa: E402


@pytest.fixture
def host(tmp_path, monkeypatch):
    home = tmp_path / "home"
    repo = tmp_path / "dotfiles"
    home.mkdir()
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(home / "profile.yml"))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    return Machine(), tmp_path


def _fake_mise(monkeypatch, tmp_path, *, install_rc=0, with_bw=True):
    """mise that 'installs' bitwarden into tmp_path/installs and records each call."""
    install_dir = tmp_path / "installs/bitwarden/2026.10.1"
    calls: list[tuple[list[str], dict]] = []

    def run(args, *, env=None, check=True, capture=False, **_kw):
        calls.append((list(args), dict(env or {})))
        if args[:2] == ["mise", "install"]:
            if install_rc == 0 and with_bw:
                install_dir.mkdir(parents=True, exist_ok=True)
                (install_dir / "bw").write_text("")
            return subprocess.CompletedProcess(args, install_rc, "", "")
        if args[:2] == ["mise", "where"]:
            return subprocess.CompletedProcess(args, 0, f"{install_dir}\n", "")
        if args[:3] == ["mise", "which", "bw"]:
            found = (install_dir / "bw").is_file()
            out = f"{install_dir / 'bw'}\n" if found else ""
            return subprocess.CompletedProcess(args, 0 if found else 1, out, "")
        raise AssertionError(f"unexpected command {args}")

    def have(name):
        if name == "mise":
            return True
        if name == "bw":
            return any(
                os.path.isfile(os.path.join(d, "bw"))
                for d in os.environ.get("PATH", "").split(":")
                if d
            )
        return False

    monkeypatch.setattr(system, "run", run)
    monkeypatch.setattr(system, "have", have)
    return calls, install_dir


def test_missing_bw_is_installed_from_the_repository_mise_config(host, monkeypatch):
    machine, tmp_path = host
    calls, install_dir = _fake_mise(monkeypatch, tmp_path)

    assert machine.ensure_bitwarden_cli() is True

    install = next(
        env for args, env in calls if args == ["mise", "install", "bitwarden"]
    )
    assert install["MISE_CONFIG_DIR"] == str(machine.repo / "home/core/.config/mise")
    assert os.environ["PATH"].split(":")[0] == str(install_dir)
    assert system.have("bw")


def test_present_bw_is_not_reinstalled(host, monkeypatch):
    machine, _tmp_path = host
    calls: list = []
    monkeypatch.setattr(system, "have", lambda name: name == "bw")
    monkeypatch.setattr(system, "run", lambda args, **_kw: calls.append(args))

    assert machine.ensure_bitwarden_cli() is True
    assert calls == []


def test_failed_mise_install_returns_false(host, monkeypatch, capsys):
    machine, tmp_path = host
    calls, _ = _fake_mise(monkeypatch, tmp_path, install_rc=1)

    assert machine.ensure_bitwarden_cli() is False
    assert [args for args, _ in calls] == [["mise", "install", "bitwarden"]]
    assert "could not install the Bitwarden CLI with mise" in capsys.readouterr().out


def test_no_mise_returns_false(host, monkeypatch, capsys):
    machine, _tmp_path = host
    monkeypatch.setattr(system, "have", lambda _name: False)

    assert machine.ensure_bitwarden_cli() is False
    assert "mise is not installed" in capsys.readouterr().out


def test_require_bitwarden_reports_a_failed_install(host, monkeypatch, capsys):
    machine, tmp_path = host
    monkeypatch.delenv("BW_SESSION", raising=False)
    _fake_mise(monkeypatch, tmp_path, install_rc=1)
    monkeypatch.setattr(system, "is_tty", lambda: True)
    monkeypatch.setattr(system, "prompt_yes_no", lambda *_a, **_k: True)
    monkeypatch.setattr(
        machine, "setup_bitwarden", lambda: pytest.fail("no login without bw")
    )

    assert machine.require_bitwarden() is False
    assert "Bitwarden CLI not installed; nothing done" in capsys.readouterr().out


def test_old_local_bw_is_removed_once_mise_provides_bw(host, monkeypatch, capsys):
    machine, tmp_path = host
    _fake_mise(monkeypatch, tmp_path)
    old = machine.home / ".local/bin/bw"
    old.parent.mkdir(parents=True)
    old.write_text("old")
    other = tmp_path / "usr-local-bin/bw"
    other.parent.mkdir()
    other.write_text("other")
    system.run(["mise", "install", "bitwarden"])

    machine.remove_old_local_bw({})

    assert not old.exists()
    assert other.read_text() == "other"
    assert f"removed old {old}" in capsys.readouterr().out


def test_old_local_bw_is_kept_without_a_mise_bw(host, monkeypatch):
    machine, tmp_path = host
    _fake_mise(monkeypatch, tmp_path)
    old = machine.home / ".local/bin/bw"
    old.parent.mkdir(parents=True)
    old.write_text("old")

    machine.remove_old_local_bw({})

    assert old.read_text() == "old"
