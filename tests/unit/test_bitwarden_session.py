"""Expected Bitwarden: renew an expired session in a terminal, notice otherwise."""

from __future__ import annotations

import json
import os
from pathlib import Path

from machine_loader import load_machine_module
from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"


def bw_machine(tmp_path, monkeypatch, fake_bw, saved="old-session"):
    bw, store = fake_bw
    log = tmp_path / "bw-calls"
    wrapper = tmp_path / "bin" / "bw"
    wrapper.parent.mkdir()
    wrapper.write_text(f'#!/bin/sh\necho "$1" >> "{log}"\nexec "{bw}" "$@"\n')
    wrapper.chmod(0o755)
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    if saved:
        (home / ".env.local").write_text(f"BW_SESSION={saved}\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv("PATH", f"{wrapper.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/p.yml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    cli = load_machine_module("machine_bw_session", MACHINE)
    monkeypatch.setattr(cli.system, "is_tty", lambda: False)
    machine = cli.Machine()
    machine.write_profile("private", "desktop", ["zsh-full"], [])
    return cli, machine, home, store, log


def expire(store: Path) -> None:
    """fake bw: an exported session counts as unlocked; make status say locked."""
    data = json.loads(store.read_text())
    data.pop("_session", None)
    store.write_text(json.dumps(data))


def logged_in(store: Path) -> None:
    data = json.loads(store.read_text())
    data["_session"] = "x"
    store.write_text(json.dumps(data))


def locked_status(monkeypatch, machine):
    calls = []

    def status() -> bool:
        calls.append("status")
        return False

    monkeypatch.setattr(machine, "bitwarden_session_valid", status)
    return calls


def test_not_expected_without_session(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, _store, _log = bw_machine(
        tmp_path, monkeypatch, fake_bw, saved=""
    )
    assert machine.bitwarden_expected() is False
    machine.check_bitwarden_session_quietly()
    assert not machine.bitwarden_notice_path.exists()


def test_expected_with_saved_session(tmp_path, monkeypatch, fake_bw):
    _cli, machine, *_ = bw_machine(tmp_path, monkeypatch, fake_bw)
    assert machine.bitwarden_expected() is True


def test_background_check_records_notice_with_status_only(
    tmp_path, monkeypatch, fake_bw
):
    _cli, machine, _home, _store, log = bw_machine(tmp_path, monkeypatch, fake_bw)
    locked_status(monkeypatch, machine)
    machine.check_bitwarden_session_quietly()
    assert "bitwarden" in machine.bitwarden_notice_path.read_text()
    assert not log.exists()  # bitwarden_session_valid is stubbed: no other bw call
    kinds = [item.kind for item in machine.attention_items()]
    assert "bitwarden" in kinds


def test_background_check_clears_notice_when_valid(tmp_path, monkeypatch, fake_bw):
    _cli, machine, _home, _store, log = bw_machine(tmp_path, monkeypatch, fake_bw)
    machine.record_bitwarden_notice()
    machine.check_bitwarden_session_quietly()
    assert not machine.bitwarden_notice_path.exists()
    assert log.read_text().split() == ["status"]


def test_non_interactive_ready_records_notice(tmp_path, monkeypatch, fake_bw):
    _cli, machine, *_ = bw_machine(tmp_path, monkeypatch, fake_bw)
    locked_status(monkeypatch, machine)
    assert machine.bitwarden_session_ready() is False
    assert machine.bitwarden_notice_path.exists()


def test_interactive_ready_renews_without_question(tmp_path, monkeypatch, fake_bw):
    cli, machine, home, store, _log = bw_machine(tmp_path, monkeypatch, fake_bw)
    logged_in(store)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system,
        "prompt_yes_no",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("asked")),
    )
    states = iter([False, False])
    monkeypatch.setattr(machine, "bitwarden_session_valid", lambda: next(states, True))
    machine.record_bitwarden_notice()
    assert machine.bitwarden_session_ready() is True
    assert "BW_SESSION=fake-session" in (home / ".env.local").read_text()
    assert not machine.bitwarden_notice_path.exists()


def test_interactive_logged_out_logs_in_at_once(tmp_path, monkeypatch, fake_bw):
    cli, machine, _home, store, log = bw_machine(tmp_path, monkeypatch, fake_bw)
    expire(store)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system,
        "prompt_yes_no",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("asked")),
    )
    monkeypatch.setattr("builtins.input", lambda *_a: "")
    states = iter([False, False])
    monkeypatch.setattr(machine, "bitwarden_session_valid", lambda: next(states, True))
    monkeypatch.delenv("BW_SESSION", raising=False)
    assert machine.unlock_bitwarden(expected=True) is True
    assert "login" in log.read_text().split()


def test_require_bitwarden_renews_instead_of_setup_question(
    tmp_path, monkeypatch, fake_bw
):
    cli, machine, home, store, _log = bw_machine(tmp_path, monkeypatch, fake_bw)
    logged_in(store)
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr(
        cli.system,
        "prompt_yes_no",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("asked")),
    )
    states = iter([False])
    monkeypatch.setattr(machine, "bitwarden_session_valid", lambda: next(states, True))
    assert machine.require_bitwarden() is True
    assert "BW_SESSION=fake-session" in (home / ".env.local").read_text()
