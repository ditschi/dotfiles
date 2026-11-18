"""The `niri config` step: one-time DMS setup, include lines, dms.service for niri only."""

from __future__ import annotations

import subprocess
import sys

import pytest

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import niri_config as nc  # noqa: E402
from machine_cli.machine import Machine  # noqa: E402

DMS_NIRI = 'include optional=true "dms/binds.kdl"\n'
DMS_GHOSTTY = "font-size = 12\n"


@pytest.fixture
def host(tmp_path, monkeypatch):
    """A Machine on a scratch HOME with a stubbed `dms` that writes what DMS writes."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOTFILES_REPO", str(REPO))
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(tmp_path / "profile.yml"))
    machine = Machine()
    machine.home = tmp_path
    calls: list[list[str]] = []

    def run(args, **_kw):
        calls.append(list(args))
        if list(args) == nc.DMS_SETUP:
            (tmp_path / ".config/niri").mkdir(parents=True, exist_ok=True)
            (tmp_path / nc.NIRI_CONFIG).write_text(DMS_NIRI)
            (tmp_path / ".config/ghostty").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".config/ghostty/config").write_text(DMS_GHOSTTY)
            _wants(tmp_path)
        elif list(args) == nc.DMS_ENABLE:
            _wants(tmp_path)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(nc.system, "run", run)
    monkeypatch.setattr(nc.system, "have", lambda name: name == "dms")
    # Never the host's /etc/systemd/user (the dms package links it there).
    monkeypatch.setattr(
        nc, "DMS_GLOBAL_FOR_EVERY_SESSION", tmp_path / "etc-user/graphical.wants/dms"
    )
    return machine, calls


@pytest.fixture
def messages(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(nc, "log", seen.append)
    monkeypatch.setattr(nc, "warn", lambda m: seen.append(f"WARN {m}"))
    return seen


def _wants(home, path=nc.DMS_FOR_NIRI):
    link = home / path
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.is_symlink():
        link.symlink_to("/usr/lib/systemd/user/dms.service")


def _profile(machine, features, device="desktop"):
    machine.applied_host_path.write_text(
        f"context: private\ndevice: {device}\nfeatures:\n"
        + "".join(f"  - {f}\n" for f in features)
    )


def _niri(home):
    return (home / nc.NIRI_CONFIG).read_text()


def _ghostty(home):
    return (home / ".config/ghostty/config").read_text()


def test_fresh_host_runs_dms_setup_and_adds_the_includes(host, tmp_path):
    machine, calls = host
    _profile(machine, ["niri"])

    machine.run_niri_config()

    assert calls == [nc.DMS_SETUP]  # dms setup enabled dms.service itself
    assert _niri(tmp_path) == DMS_NIRI + nc.NIRI_INCLUDE + "\n"
    assert _ghostty(tmp_path) == DMS_GHOSTTY + nc.GHOSTTY_INCLUDE + "\n"


def test_second_run_changes_nothing(host, tmp_path, messages):
    machine, calls = host
    _profile(machine, ["niri"])
    machine.run_niri_config()
    calls.clear()
    messages.clear()

    machine.run_niri_config()

    assert calls == []
    assert messages == []
    assert _niri(tmp_path).count("dotfiles.kdl") == 1
    assert _ghostty(tmp_path).count("dotfiles.conf") == 1


def test_existing_config_is_kept_and_gets_only_the_include(host, tmp_path):
    machine, calls = host
    _profile(machine, ["niri"])
    own = 'binds {\n    F12 { spawn "ghostty" "+toggle-quick-terminal"; }\n}'  # no newline
    (tmp_path / ".config/niri").mkdir(parents=True)
    (tmp_path / nc.NIRI_CONFIG).write_text(own)
    (tmp_path / ".config/ghostty").mkdir(parents=True)
    (tmp_path / ".config/ghostty/config").write_text(DMS_GHOSTTY)

    machine.run_niri_config()

    assert nc.DMS_SETUP not in calls
    assert calls == [nc.DMS_ENABLE]  # niri did not want dms.service yet
    assert _niri(tmp_path) == own + "\n" + nc.NIRI_INCLUDE + "\n"
    assert _ghostty(tmp_path) == DMS_GHOSTTY + nc.GHOSTTY_INCLUDE + "\n"


def test_includes_already_present_are_not_added_again(host, tmp_path, messages):
    machine, calls = host
    _profile(machine, ["niri"])
    niri = DMS_NIRI + 'include  optional=true  "./dotfiles.kdl"\n'
    ghostty = DMS_GHOSTTY + 'config-file = "?dotfiles.conf"\n'
    (tmp_path / ".config/niri").mkdir(parents=True)
    (tmp_path / nc.NIRI_CONFIG).write_text(niri)
    (tmp_path / ".config/ghostty").mkdir(parents=True)
    (tmp_path / ".config/ghostty/config").write_text(ghostty)
    _wants(tmp_path)

    machine.run_niri_config()

    assert calls == []
    assert messages == []
    assert _niri(tmp_path) == niri
    assert _ghostty(tmp_path) == ghostty


def test_missing_ghostty_config_is_created_with_only_the_include(host, tmp_path):
    machine, _calls = host
    _profile(machine, ["niri"])
    (tmp_path / ".config/niri").mkdir(parents=True)
    (tmp_path / nc.NIRI_CONFIG).write_text(DMS_NIRI)
    _wants(tmp_path)

    machine.run_niri_config()

    assert _ghostty(tmp_path) == nc.GHOSTTY_INCLUDE + "\n"


def test_config_ghostty_with_the_include_counts(host, tmp_path):
    machine, _calls = host
    _profile(machine, ["niri"])
    (tmp_path / ".config/niri").mkdir(parents=True)
    (tmp_path / nc.NIRI_CONFIG).write_text(DMS_NIRI)
    (tmp_path / ".config/ghostty").mkdir(parents=True)
    (tmp_path / ".config/ghostty/config.ghostty").write_text(nc.GHOSTTY_INCLUDE + "\n")
    _wants(tmp_path)

    machine.run_niri_config()

    assert not (tmp_path / ".config/ghostty/config").exists()


def test_warns_when_dms_starts_in_every_session(host, tmp_path, messages):
    machine, _calls = host
    _profile(machine, ["niri"])
    machine.run_niri_config()
    _wants(tmp_path, nc.DMS_FOR_EVERY_SESSION)
    messages.clear()

    machine.run_niri_config()

    assert len(messages) == 1
    assert messages[0].startswith("WARN ") and "graphical-session.target" in messages[0]


def test_warns_when_dms_is_enabled_globally(host, tmp_path, messages):
    machine, _calls = host
    _profile(machine, ["niri"])
    machine.run_niri_config()
    link = nc.DMS_GLOBAL_FOR_EVERY_SESSION
    link.parent.mkdir(parents=True)
    link.symlink_to("/usr/lib/systemd/user/dms.service")
    messages.clear()

    machine.run_niri_config()

    assert len(messages) == 1
    assert "sudo systemctl --global disable dms.service" in messages[0]


def test_config_that_is_not_utf8_does_not_abort(host, tmp_path):
    machine, _calls = host
    _profile(machine, ["niri"])
    (tmp_path / ".config/niri").mkdir(parents=True)
    (tmp_path / nc.NIRI_CONFIG).write_bytes(b"// \xff\xfe latin-1 \xe4\n")
    _wants(tmp_path)

    machine.run_niri_config()

    assert nc.NIRI_INCLUDE in _niri_bytes(tmp_path)


def _niri_bytes(home):
    return (home / nc.NIRI_CONFIG).read_bytes().decode("utf-8", errors="replace")


def test_nothing_without_the_feature(host, tmp_path):
    machine, calls = host
    _profile(machine, ["zsh-full", "cosmic"])

    machine.run_niri_config()

    assert calls == []
    assert not (tmp_path / ".config").exists()


def test_nothing_in_a_container(host, tmp_path):
    machine, calls = host
    _profile(machine, ["niri"], device="container")

    machine.run_niri_config()

    assert calls == []
    assert not (tmp_path / ".config").exists()


def test_nothing_without_dms(host, tmp_path, monkeypatch):
    machine, calls = host
    _profile(machine, ["niri"])
    monkeypatch.setattr(nc.system, "have", lambda name: False)

    machine.run_niri_config()

    assert calls == []
    assert not (tmp_path / ".config").exists()


def test_failing_dms_setup_fails_the_step(host, monkeypatch):
    machine, _calls = host
    _profile(machine, ["niri"])

    def run(args, **_kw):
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(nc.system, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        machine.run_niri_config()
