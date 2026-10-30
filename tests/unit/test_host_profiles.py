from __future__ import annotations

import getpass
import subprocess
import os
import re
import textwrap
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest
import yaml

from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"


def _cli():
    return SourceFileLoader("machine_cli_hosts", str(MACHINE)).load_module()


def test_format_and_fingerprint_roundtrip(tmp_path: Path):
    cli = _cli()
    text = cli.format_profile_yaml(
        "private",
        "server",
        ["zsh-full", "docker", "monitoring"],
        ["laptop1", "laptop2"],
    )
    path = tmp_path / "h.yml"
    path.write_text(text, encoding="utf-8")
    data = cli.parse_profile_file(path)
    assert (data["context"], data["device"]) == ("private", "server")
    assert data["ansible"] is True
    assert data["features"] == ["zsh-full", "docker", "monitoring"]
    assert data["ssh_allow_from"] == ["laptop1", "laptop2"]
    assert cli.profile_fingerprint(path)


def test_sync_host_config_from_repo(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    hosts = repo / "machine" / "hosts"
    hosts.mkdir(parents=True)
    host_file = hosts / "testhost.yml"
    host_file.write_text(
        textwrap.dedent(
            """\
            ---
            context: private
            device: server
            features:
              - zsh-full
              - docker
            ssh_allow_from:
              - laptop1
            """
        ),
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod.system, "hostname_short", lambda: "testhost")

    machine = cli_mod.Machine()
    assert machine.sync_host_config_from_repo() is True
    assert machine.current_host() == ("private", "server")
    assert machine.saved_features() == ["zsh-full", "docker"]
    assert machine.saved_ssh_allow_from() == ["laptop1"]
    assert machine.sync_host_config_from_repo() is False


def test_save_host_config_to_repo(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod.system, "hostname_short", lambda: "box1")

    machine = cli_mod.Machine()
    path = machine.save_host_config_to_repo(
        "private", "server", ["zsh-full", "monitoring"], ["laptop1"]
    )
    assert path == repo / "machine/hosts/box1.yml"
    assert "monitoring" in path.read_text(encoding="utf-8")


def test_backup_and_restore_profile(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    machine = cli_mod.Machine()
    machine.write_profile("private", "desktop", ["zsh-full"], [])
    bak = machine.backup_applied_host()
    assert bak and bak.is_file()
    machine.write_profile("private", "server", ["zsh-full", "docker"], ["x"])
    assert machine.current_host() == ("private", "server")
    machine.restore_applied_host(bak)
    assert machine.current_host() == ("private", "desktop")


def test_help_lists_apply_and_profile_but_no_migration():
    import subprocess

    result = subprocess.run(
        ["python3", str(MACHINE), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "apply" in result.stdout
    assert "host" in result.stdout
    assert "profile" not in result.stdout
    assert "migrate" not in result.stdout
    assert "rollback" not in result.stdout


def _machine_env(tmp_path: Path, monkeypatch, hostname: str = "testhost"):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "machine" / "hosts").mkdir(parents=True)
    (repo / "ansible").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_APPLIED_HOST_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv(
        "MISE_LOCAL_CONFIG", str(home / ".config/mise/config.local.toml")
    )
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod.system, "hostname_short", lambda: hostname)
    return cli_mod, cli_mod.Machine(), repo


def test_apply_syncs_then_runs_ansible(tmp_path: Path, monkeypatch):
    import argparse

    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    host_file = repo / "machine/hosts/testhost.yml"
    host_file.write_text(
        textwrap.dedent(
            """\
            ---
            context: private
            device: server
            features:
              - zsh-full
              - docker
            ssh_allow_from: []
            """
        ),
        encoding="utf-8",
    )
    machine.write_profile("private", "desktop", ["zsh-full"], [])
    calls: list[str] = []

    def fake_ansible(*_a, **_k):
        calls.append("ansible")

    monkeypatch.setattr(machine, "run_ansible", fake_ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    monkeypatch.setattr(machine, "health_check_after_apply", lambda: True)

    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    assert machine.cmd_apply(args) == 0
    assert machine.current_host() == ("private", "server")
    assert calls == ["ansible"]


def test_apply_reverts_profile_on_ansible_failure(tmp_path: Path, monkeypatch):
    import argparse
    import subprocess

    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    host_file = repo / "machine/hosts/testhost.yml"
    host_file.write_text(
        textwrap.dedent(
            """\
            ---
            context: private
            device: server
            features:
              - zsh-full
            ssh_allow_from: []
            """
        ),
        encoding="utf-8",
    )
    machine.write_profile("private", "desktop", ["zsh-full", "fonts"], [])
    calls: list[str] = []

    def flaky_ansible(*_a, **_k):
        calls.append("ansible")
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, ["ansible-playbook"])

    monkeypatch.setattr(machine, "run_ansible", flaky_ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    monkeypatch.setattr(machine, "health_check_after_apply", lambda: True)

    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    try:
        machine.cmd_apply(args)
        raise AssertionError("expected SystemExit")
    except SystemExit as exc:
        assert exc.code == 1
    assert machine.current_host() == ("private", "desktop")
    assert machine.saved_features() == ["zsh-full", "fonts"]
    assert len(calls) == 2  # fail + revert re-run


def test_apply_does_not_retry_unchanged_profile_after_failure(tmp_path, monkeypatch):
    import argparse
    import subprocess

    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    machine.write_profile("work", "desktop", ["zsh-full"], [])
    (repo / "machine/hosts/testhost.yml").write_bytes(
        machine.applied_host_path.read_bytes()
    )
    original = machine.applied_host_path.read_bytes()
    calls = []

    def denied_ansible(*_args, **_kwargs):
        calls.append("ansible")
        raise subprocess.CalledProcessError(2, ["ansible-playbook"])

    monkeypatch.setattr(machine, "run_ansible", denied_ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    with pytest.raises(SystemExit):
        machine.cmd_apply(args)
    assert calls == ["ansible"]
    assert machine.applied_host_path.read_bytes() == original


def test_apply_reverts_on_health_check_failure(tmp_path: Path, monkeypatch):
    import argparse

    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "machine/hosts/testhost.yml").write_text(
        "---\ncontext: private\ndevice: server\nfeatures:\n  - zsh-full\nssh_allow_from: []\n",
        encoding="utf-8",
    )
    machine.write_profile("private", "desktop", ["zsh-full"], [])
    revert_runs = {"n": 0}

    def counting_ansible(*_a, **_k):
        revert_runs["n"] += 1

    monkeypatch.setattr(machine, "run_ansible", counting_ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    monkeypatch.setattr(machine, "health_check_after_apply", lambda: False)

    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    try:
        machine.cmd_apply(args)
        raise AssertionError("expected SystemExit")
    except SystemExit as exc:
        assert exc.code == 1
    assert machine.current_host() == ("private", "desktop")
    assert revert_runs["n"] == 2


def test_apply_remote_requires_host_file(tmp_path: Path, monkeypatch):
    import argparse

    _cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    args = argparse.Namespace(
        limit="missing-host", playbook="workstation", no_become=True
    )
    try:
        machine.cmd_apply(args)
        raise AssertionError("expected SystemExit")
    except SystemExit as exc:
        assert exc.code == 1


def test_repo_host_yamls_are_valid():
    cli = _cli()
    files = sorted(
        [*(REPO / "machine/hosts").glob("*.yml"), *(REPO / "tests/hosts").glob("*.yml")]
    )
    assert files, "expected machine/hosts/*.yml"
    # CI fixtures live in tests/hosts, apart from the real hosts
    assert not list((REPO / "machine/hosts").glob("ci-*.yml"))
    for path in files:
        assert "profile:" not in path.read_text(), path.name
        data = cli.parse_profile_file(path)
        assert data["device"] in cli.DEVICES, path.name
        assert data["context"] in [*cli.CONTEXTS, ""], path.name
        feats = data.get("features") or []
        assert isinstance(feats, list)
        for feat in feats:
            assert feat in cli.FEATURES, f"{path.name}: unknown feature {feat}"
        allow = data.get("ssh_allow_from") or []
        assert isinstance(allow, list)


def test_health_check_ignores_sshd_without_root(tmp_path: Path, monkeypatch):
    # As a normal user `sshd -t` fails (host keys unreadable) and `sudo -n`
    # fails without cached credentials; that must not roll back an apply.
    _cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("sshd", "sudo"):
        stub = bin_dir / name
        stub.write_text("#!/bin/sh\nexit 1\n")
        stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    machine.write_profile("private", "desktop", ["zsh-full", "sshd-home"], [])
    assert machine.health_check_after_apply() is True


def test_health_check_fails_when_zsh_is_unhealthy(tmp_path: Path, monkeypatch):
    _cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "zsh failed to start")
    assert machine.health_check_after_apply() is False
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "")
    assert machine.health_check_after_apply() is True


def _fake_tool(directory: Path, name: str, exit_code: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    tool = directory / name
    tool.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    tool.chmod(0o755)


def test_ansible_works_rejects_shim_that_cannot_run(tmp_path: Path, monkeypatch):
    """A leftover shim (e.g. pipx venv after a Python upgrade) is not a working ansible."""
    cli_mod, _machine, _repo = _machine_env(tmp_path, monkeypatch)
    bin_dir = tmp_path / "bin"
    monkeypatch.setenv("PATH", str(bin_dir))

    assert not cli_mod.system.ansible_works()
    _fake_tool(bin_dir, "ansible-playbook", 1)
    assert not cli_mod.system.ansible_works()
    _fake_tool(bin_dir, "ansible-playbook", 0)
    assert cli_mod.system.ansible_works()


def test_bootstrap_reinstalls_broken_ansible(tmp_path: Path, monkeypatch):
    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    commands: list[list[str]] = []
    states = iter([False, True])

    monkeypatch.setattr(cli_mod.system, "have", lambda _name: True)
    monkeypatch.setattr(cli_mod.system, "ansible_works", lambda: next(states))
    monkeypatch.setattr(
        cli_mod.system, "run", lambda cmd, **_k: commands.append(list(cmd))
    )
    monkeypatch.setattr(machine, "ensure_uv", lambda: True)

    machine.ensure_bootstrap_tools(False, True, False)
    assert ["uv", "tool", "install", "--force", "ansible-core"] in commands


def test_pickers_take_numbers_and_defaults(monkeypatch):
    system = _cli().system
    monkeypatch.setattr(system, "is_tty", lambda: True)
    answers = iter(["2", "rpi", "1,3", "", "-", "9", "2"])
    monkeypatch.setattr(system.click, "prompt", lambda *_a, **_k: next(answers))

    assert system.choose("t", ["a", "b"], "a") == "b"
    assert system.choose("t", ["a", "rpi"], "a") == "rpi"
    choices = {"x": "", "y": "", "z": ""}
    assert system.choose_many("t", choices, ["y"]) == ["x", "y", "z"]  # toggles x, z
    assert system.choose_many("t", choices, ["y"]) == ["y"]
    assert system.choose_many("t", choices, ["y"]) == []
    assert system.choose_many("t", choices, []) == ["y"]  # "9" retried, then "2"

    answers = iter(["2", "0", "1"])
    assert system.choose_many("t", choices, ["x", "y"]) == ["x"]  # untick y only
    assert system.choose_many("t", choices, ["x"]) == []  # "0" retried, untick x

    monkeypatch.setattr(system, "is_tty", lambda: False)
    assert system.choose("t", ["a", "b"], "a") == "a"
    assert system.choose_many("t", choices, ["y"]) == ["y"]


def test_prompts_use_pickers_on_a_terminal(tmp_path: Path, monkeypatch):
    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli_mod.system, "choose", lambda _t, choices, _d: choices[1])
    monkeypatch.setattr(
        cli_mod.system,
        "choose_many",
        lambda _t, choices, selected: [*selected, list(choices)[-1]],
    )

    assert machine.prompt_context("private") == "work"
    assert machine.prompt_device("desktop") == "server"
    from machine_cli import features

    offered = list(features.allowed("private", "server"))
    assert machine.prompt_features("private", "server", ["zsh-full", "gnome"]) == [
        "zsh-full",
        offered[-1],
    ]


def test_log_marks_warnings_and_keeps_plain_text_when_piped(tmp_path, capsys):
    cli_mod = _cli()
    cli_mod.log("WARNING: " + "x" * 200)
    with pytest.raises(SystemExit):
        cli_mod.die("boom")
    captured = capsys.readouterr()
    # not a terminal: no colour codes, no wrapping
    assert captured.out == "machine: WARNING: " + "x" * 200 + "\n"
    assert captured.err == "machine: boom\n"


def test_debug_shows_commands_only_when_enabled(tmp_path, monkeypatch, capsys):
    cli_mod, _machine, _repo = _machine_env(tmp_path, monkeypatch)
    cli_mod.system.run(["true"])
    assert capsys.readouterr().out == ""
    cli_mod.core.set_debug(True)
    try:
        cli_mod.system.run(["true"])
    finally:
        cli_mod.core.set_debug(False)
    assert capsys.readouterr().out == "machine: $ true\n"


def test_ssh_allow_from_offers_hosts_with_a_repo_key(tmp_path, monkeypatch):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    keys = repo / "machine" / "ssh_keys"
    keys.mkdir(parents=True)
    for host in ("homeserver", "testhost"):  # testhost is this machine
        (keys / f"{host}.pub").write_text("ssh-ed25519 AAAA\n", encoding="utf-8")
    monkeypatch.setattr(
        cli_mod.system, "run", lambda *_a, **_k: pytest.fail("no Bitwarden lookup")
    )

    assert machine.known_ssh_hosts("private") == {"homeserver": "machine/ssh_keys"}
    # repo keys belong to the home fleet only
    assert machine.known_ssh_hosts("work") == {}


def test_run_ansible_uses_classic_sudo_for_local_runs(tmp_path: Path, monkeypatch):
    """sudo-rs prompts are not recognised by Ansible; local runs pick sudo.ws if present."""
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "ansible/workstation.yml").write_text("---\n", encoding="utf-8")
    commands: list[list[str]] = []
    monkeypatch.setattr(machine, "record_ansible_applied", lambda: None)
    monkeypatch.setattr(
        cli_mod.system, "run", lambda cmd, **_k: commands.append(list(cmd))
    )
    classic_sudo = "ansible_become_exe=sudo.ws"

    monkeypatch.setattr(cli_mod.system, "have", lambda name: name == "sudo.ws")
    machine.run_ansible("workstation", ask_become=False)
    assert classic_sudo in commands[-1]
    machine.run_ansible("workstation", limit="homeserver", ask_become=False)
    assert classic_sudo not in commands[-1]

    monkeypatch.setattr(cli_mod.system, "have", lambda _name: False)
    machine.run_ansible("workstation", ask_become=False)
    assert classic_sudo not in commands[-1]


def test_package_table_only_names_known_features():
    from package_sets import load_group_vars

    unknown = set(load_group_vars()["packages_by_feature"]) - set(_cli().FEATURES)
    assert not unknown, f"packages_by_feature has unknown features: {unknown}"


def _sudo_env(tmp_path, monkeypatch, *, passwordless=False, good="secret"):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "ansible/workstation.yml").write_text("---\n", encoding="utf-8")
    monkeypatch.setattr(machine, "record_ansible_applied", lambda: None)
    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli_mod.system, "have", lambda name: name == "sudo")
    seen = {"ansible": [], "files": [], "checks": 0}

    def fake_run(cmd, **kw):
        if cmd[:3] == ["sudo", "-n", "true"]:
            return subprocess.CompletedProcess(cmd, 0 if passwordless else 1)
        if cmd[:2] == ["sudo", "-S"]:
            seen["checks"] += 1
            ok = kw.get("input_text") == good + "\n"
            return subprocess.CompletedProcess(cmd, 0 if ok else 1)
        seen["ansible"].append(list(cmd))
        if "--become-password-file" in cmd:
            path = Path(cmd[cmd.index("--become-password-file") + 1])
            seen["files"].append(
                (path, path.read_text(), oct(path.stat().st_mode & 0o777))
            )
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(cli_mod.system, "run", fake_run)
    return cli_mod, machine, seen


def test_local_run_without_password_when_sudo_is_passwordless(tmp_path, monkeypatch):
    cli_mod, machine, seen = _sudo_env(tmp_path, monkeypatch, passwordless=True)
    monkeypatch.setattr(getpass, "getpass", lambda _p: pytest.fail("asked"))
    machine.run_ansible("workstation")
    assert "--become-password-file" not in seen["ansible"][-1]
    assert "--ask-become-pass" not in seen["ansible"][-1]


def test_local_run_checks_the_password_and_hands_it_over_once(tmp_path, monkeypatch):
    cli_mod, machine, seen = _sudo_env(tmp_path, monkeypatch)
    answers = iter(["wrong", "secret"])
    monkeypatch.setattr(getpass, "getpass", lambda _p: next(answers))

    machine.run_ansible("workstation")
    machine.run_ansible("workstation")  # e.g. the revert run: no second prompt

    assert seen["checks"] == 2
    assert [(text, mode) for _p, text, mode in seen["files"]] == [
        ("secret", "0o600"),
        ("secret", "0o600"),
    ]
    assert all(not path.exists() for path, _t, _m in seen["files"])


def test_local_run_stops_after_three_wrong_passwords(tmp_path, monkeypatch):
    cli_mod, machine, seen = _sudo_env(tmp_path, monkeypatch)
    monkeypatch.setattr(getpass, "getpass", lambda _p: "wrong")
    with pytest.raises(SystemExit):
        machine.run_ansible("workstation")
    assert seen["checks"] == 3
    assert seen["ansible"] == []


def test_remote_run_lets_ansible_ask_for_the_password(tmp_path, monkeypatch):
    _cli_mod, machine, seen = _sudo_env(tmp_path, monkeypatch)
    machine.run_ansible("workstation", limit="homeserver")
    assert "--ask-become-pass" in seen["ansible"][-1]


def test_require_bitwarden_offers_install_then_login(tmp_path: Path, monkeypatch):
    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.delenv("BW_SESSION", raising=False)
    present = {"bw": False}
    monkeypatch.setattr(cli_mod.system, "have", lambda name: present.get(name, False))
    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: False)
    assert machine.require_bitwarden() is False

    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli_mod.system, "prompt_yes_no", lambda *_a, **_k: True)
    steps: list[str] = []

    def install():
        present["bw"] = True
        steps.append("install")
        return True

    monkeypatch.setattr(machine, "ensure_bitwarden_cli", install)
    monkeypatch.setattr(
        machine, "setup_bitwarden", lambda: steps.append("setup") or True
    )
    assert machine.require_bitwarden() is True
    assert steps == ["install", "setup"]


def test_old_local_profile_is_taken_over_once(tmp_path: Path, monkeypatch):
    cli_mod, _machine, _ = _machine_env(tmp_path, monkeypatch)
    legacy = tmp_path / "home/.config/machine/profile.yml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("profile: home-server\nfeatures:\n  - zsh-full\n")
    monkeypatch.delenv("MACHINE_APPLIED_HOST_FILE")
    machine = cli_mod.Machine()
    assert not legacy.exists()
    assert machine.applied_host_path.name == "applied-host.yml"
    assert machine.current_host() == ("private", "server")
    assert "profile:" not in machine.applied_host_path.read_text()
    assert machine.saved_features() == ["zsh-full"]


def test_unknown_device_falls_back_to_the_default(tmp_path: Path, monkeypatch):
    cli_mod, machine, _ = _machine_env(tmp_path, monkeypatch)
    machine.ensure_dirs()
    machine.applied_host_path.write_text("device: bogus\n")
    monkeypatch.setattr(cli_mod.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli_mod.system, "boots_graphical", lambda: False)
    monkeypatch.delenv("MACHINE_DEVICE", raising=False)
    assert machine.current_device() == "server"


def test_default_context_and_device(tmp_path: Path, monkeypatch):
    import machine_cli.profile as profile_mod

    cli_mod, machine, _ = _machine_env(tmp_path, monkeypatch)
    for name in ("MACHINE_CONTEXT", "MACHINE_DEVICE", "SUDO_USER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cli_mod.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli_mod.system, "boots_graphical", lambda: True)
    monkeypatch.setattr(profile_mod.getpass, "getuser", lambda: "abc1de")
    assert (machine.default_context(), machine.default_device()) == ("work", "desktop")
    monkeypatch.setattr(profile_mod.getpass, "getuser", lambda: "ditschi")
    monkeypatch.setattr(cli_mod.system, "boots_graphical", lambda: False)
    assert (machine.default_context(), machine.default_device()) == (
        "private",
        "server",
    )

    monkeypatch.setattr(cli_mod.system, "in_docker", lambda: True)
    monkeypatch.delenv("MACHINE_CONTEXT_OVERRIDE", raising=False)
    monkeypatch.delenv("MACHINE_DEVICE_OVERRIDE", raising=False)
    assert (machine.default_context(), machine.default_device()) == ("", "container")
    monkeypatch.setenv("MACHINE_CONTEXT_OVERRIDE", "work")
    monkeypatch.setenv("MACHINE_DEVICE_OVERRIDE", "desktop")
    assert (machine.default_context(), machine.default_device()) == ("work", "desktop")


def test_excluded_features_are_reported_and_kept_out(tmp_path, monkeypatch):
    import machine_cli.profile as profile_mod

    _cli_mod, machine, _ = _machine_env(tmp_path, monkeypatch)
    warnings = []
    monkeypatch.setattr(profile_mod, "warn", warnings.append)
    kept = machine.allowed_features(
        ["zsh-full", "monitoring", "starship"], "work", "desktop"
    )
    assert kept == ["zsh-full"]
    assert "monitoring" in warnings[0] and "starship" in warnings[0]


def test_host_config_changes_are_readable():
    from machine_cli.profile import host_config_changes

    old = {
        "context": "private",
        "device": "desktop",
        "features": ["a", "b"],
        "ssh_allow_from": [],
    }
    new = {**old, "features": ["a", "c"], "ssh_allow_from": ["nas"]}
    assert host_config_changes(old, new) == ["+ c, - b", "ssh_allow_from + nas"]
    assert host_config_changes(new, {**new, "device": "server"}) == [
        "device desktop -> server"
    ]
    assert host_config_changes(new, {**new, "ansible": False}) == ["ansible off"]
    assert host_config_changes(new, new) == []


@pytest.mark.parametrize("yes", [True, False])
def test_setup_writes_the_repo_host_file_without_asking(tmp_path, monkeypatch, yes):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_mod.system, "in_docker", lambda: False)
    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: True)
    asked = []
    monkeypatch.setattr(
        cli_mod.system, "prompt_yes_no", lambda q, d: asked.append(q) or False
    )
    host_file = machine.host_config_path()
    host_file.write_text(
        cli_mod.format_profile_yaml("private", "desktop", ["zsh-full"], [])
    )

    machine.persist_host_config(
        "private", "desktop", ["zsh-full", "thunderbird"], [], yes=yes
    )

    assert "thunderbird" in host_file.read_text()
    assert not [q for q in asked if "Update versioned host profile" in q]
    assert [q for q in asked if q.startswith("Commit now")] == (
        [] if yes else [asked[0]]
    )


def test_setup_writes_no_repo_host_file_in_a_container(tmp_path, monkeypatch):
    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    machine.persist_host_config("", "container", ["zsh-full"], [], yes=True)
    assert not machine.host_config_path().exists()


def test_update_applies_the_repo_profile_with_a_notice(tmp_path, monkeypatch):
    import machine_cli.profile as profile_mod

    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    messages = []
    monkeypatch.setattr(profile_mod, "log", messages.append)
    monkeypatch.setattr(machine, "write_dotfile_groups", lambda: None)
    machine.write_profile(
        "private", "desktop", ["zsh-full", "docker"], []
    )  # hand-edited copy
    machine.host_config_path().write_text(
        cli_mod.format_profile_yaml(
            "private", "desktop", ["zsh-full", "thunderbird"], []
        )
    )

    assert machine.sync_host_config_from_repo()
    assert machine.saved_features() == ["zsh-full", "thunderbird"]
    assert any("+ thunderbird, - docker" in m for m in messages)


def test_update_check_lists_incoming_host_config_changes(tmp_path, monkeypatch):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    machine.write_profile("private", "desktop", ["zsh-full"], [])
    rel = str(machine.host_config_path().relative_to(repo))
    upstream = cli_mod.format_profile_yaml(
        "private", "desktop", ["zsh-full", "thunderbird"], []
    )

    def run(args, **_kw):
        out = upstream if args[-1] == f"origin/main:{rel}" else ""
        return subprocess.CompletedProcess(args, 0, out, "")

    monkeypatch.setattr(cli_mod.system, "run", run)
    changes = machine.incoming_host_config_changes([("M", rel)], "origin/main")
    assert changes == ["+ thunderbird"]
    assert (
        machine.incoming_host_config_changes([("M", "README.md")], "origin/main") == []
    )


def test_apply_skips_ansible_when_the_host_config_switches_it_off(
    tmp_path, monkeypatch
):
    import argparse

    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "machine/hosts/testhost.yml").write_text(
        "---\ncontext: work\ndevice: desktop\nansible: false\nfeatures:\n  - zsh-full\n"
    )
    monkeypatch.setattr(
        machine, "run_ansible", lambda *_a, **_k: pytest.fail("ansible must not run")
    )
    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    assert machine.cmd_apply(args) == 0
    assert machine.applied_host()["ansible"] is False
    assert machine.system_paths_relevant(["ansible/workstation.yml"]) == []


def test_ansible_failure_names_the_switch(tmp_path, monkeypatch):
    import machine_cli.commands as commands_mod

    _cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    messages = []
    monkeypatch.setattr(commands_mod, "log", messages.append)

    def denied(*_a, **_k):
        raise subprocess.CalledProcessError(2, ["ansible-playbook"])

    monkeypatch.setattr(machine, "run_ansible", denied)
    with pytest.raises(subprocess.CalledProcessError):
        machine.run_ansible_or_hint("workstation", "", True, True)
    assert any("ansible: false" in m for m in messages)


def test_setup_keeps_ansible_false_from_the_host_config(tmp_path, monkeypatch):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_mod.system, "in_docker", lambda: False)
    (repo / "machine/hosts/testhost.yml").write_text(
        "---\ncontext: work\ndevice: desktop\nansible: false\nfeatures:\n  - zsh-full\n"
    )
    machine.persist_host_config(
        "work", "desktop", ["zsh-full", "kerberos"], [], yes=True
    )
    text = (repo / "machine/hosts/testhost.yml").read_text()
    assert "ansible: false" in text and "kerberos" in text


def test_hosts_dir_can_point_at_the_test_fixtures(tmp_path, monkeypatch):
    _cli_mod, _machine, repo = _machine_env(tmp_path, monkeypatch, hostname="ci-x")
    monkeypatch.setenv("MACHINE_HOSTS_DIR", "tests/hosts")
    machine = _cli_mod.Machine()
    assert machine.host_config_path() == repo / "tests/hosts/ci-x.yml"


def test_checklist_uses_arrows_and_space(monkeypatch):
    system = _cli().system
    monkeypatch.setattr(system, "is_tty", lambda: True)
    monkeypatch.setattr(system.sys.stdout, "isatty", lambda: True, raising=False)
    down, up = "\x1b[B", "\x1b[A"
    keys = iter([down, " ", down, " ", up, " ", "\r"])  # y off, z on, y on again
    monkeypatch.setattr(system.click, "getchar", lambda: next(keys))
    choices = {"x": "", "y": "", "z": ""}

    assert system.choose_many("t", choices, ["x", "y"]) == ["x", "y", "z"]


DISK_SPACE = [
    {"path": "/mnt/data", "min_free": "100G"},
    {"path": "/mnt/scratch", "ignore": True},
]


def test_disk_space_roundtrip_and_fingerprint(tmp_path: Path):
    cli = _cli()
    path = tmp_path / "h.yml"
    path.write_text(
        cli.format_profile_yaml("work", "desktop", ["zsh-full"], [], True, DISK_SPACE),
        encoding="utf-8",
    )
    assert cli.parse_profile_file(path)["disk_space"] == DISK_SPACE
    with_key = cli.profile_fingerprint(path)
    path.write_text(
        cli.format_profile_yaml("work", "desktop", ["zsh-full"], []), encoding="utf-8"
    )
    assert "disk_space" not in path.read_text(encoding="utf-8")
    assert cli.parse_profile_file(path)["disk_space"] == []
    assert cli.profile_fingerprint(path) != with_key


def test_rewrites_keep_disk_space(tmp_path: Path, monkeypatch):
    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    host_file = repo / "machine/hosts/testhost.yml"
    host_file.write_text(
        textwrap.dedent(
            """\
            ---
            context: work
            device: desktop
            features:
              - zsh-full
            ssh_allow_from: []
            disk_space:
              - path: /mnt/data
                min_free: 100G
            """
        ),
        encoding="utf-8",
    )
    assert machine.sync_host_config_from_repo() is True
    entry = [{"path": "/mnt/data", "min_free": "100G"}]
    assert machine.applied_host()["disk_space"] == entry
    # setup: features change, the applied copy and the repository file keep the key
    machine.write_profile("work", "desktop", ["zsh-full", "docker"], [])
    assert machine.applied_host()["disk_space"] == entry
    machine.persist_host_config("work", "desktop", ["zsh-full", "docker"], [], yes=True)
    text = host_file.read_text(encoding="utf-8")
    assert "docker" in text and "/mnt/data" in text
    # host save from the applied copy
    machine.save_host_config_to_repo("work", "desktop", ["zsh-full"], [])
    assert "/mnt/data" in host_file.read_text(encoding="utf-8")


def test_disk_space_change_is_taken_over_with_notice(
    tmp_path: Path, monkeypatch, capsys
):
    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    host_file = repo / "machine/hosts/testhost.yml"
    base = "---\ncontext: work\ndevice: desktop\nfeatures:\n  - zsh-full\nssh_allow_from: []\n"
    host_file.write_text(base, encoding="utf-8")
    machine.sync_host_config_from_repo()
    host_file.write_text(
        base + "disk_space:\n  - path: /mnt/data\n    min_free_percent: 3\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    assert machine.sync_host_config_from_repo() is True
    assert machine.applied_host()["disk_space"] == [
        {"path": "/mnt/data", "min_free_percent": 3}
    ]
    assert "disk_space changed" in capsys.readouterr().out


def test_hosts_readme_disk_space_example_parses():
    lines = (REPO / "machine/hosts/README.md").read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("#   disk_space:")
    )
    block = []
    for line in lines[start:]:
        if not line.startswith("#   ") or (block and not line.startswith("#     ")):
            break
        content = line[4:]
        body = content.lstrip()
        # the explanation follows after a run of spaces
        block.append(" " * (len(content) - len(body)) + re.split(r"\s{2,}", body)[0])
    data = yaml.safe_load("\n".join(block))
    assert data["disk_space"] == [
        {"path": "/mnt/data", "min_free": "100G", "min_free_percent": 3},
        {"path": "/mnt/scratch", "ignore": True},
    ]
