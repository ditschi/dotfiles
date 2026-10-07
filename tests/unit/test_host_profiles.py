from __future__ import annotations

import os
import textwrap
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from package_sets import REPO

MACHINE = REPO / "home/dot_local/bin/executable_machine"


def _cli():
    return SourceFileLoader("machine_cli_hosts", str(MACHINE)).load_module()


def test_format_and_fingerprint_roundtrip(tmp_path: Path):
    cli = _cli()
    text = cli.format_profile_yaml(
        "home-server",
        ["zsh-full", "docker", "monitoring"],
        ["laptop1", "laptop2"],
    )
    path = tmp_path / "h.yml"
    path.write_text(text, encoding="utf-8")
    data = cli.parse_profile_file(path)
    assert data["profile"] == "home-server"
    assert data["features"] == ["zsh-full", "docker", "monitoring"]
    assert data["ssh_allow_from"] == ["laptop1", "laptop2"]
    assert cli.profile_fingerprint(path)


def test_sync_host_profile_from_repo(tmp_path: Path, monkeypatch):
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
            profile: home-server
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
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod.system, "hostname_short", lambda: "testhost")

    machine = cli_mod.Machine()
    assert machine.sync_host_profile_from_repo() is True
    assert machine.current_profile() == "home-server"
    assert machine.saved_features() == ["zsh-full", "docker"]
    assert machine.saved_ssh_allow_from() == ["laptop1"]
    assert machine.sync_host_profile_from_repo() is False


def test_save_host_profile_to_repo(tmp_path: Path, monkeypatch):
    cli_mod = _cli()
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DOTFILES_REPO", str(repo))
    monkeypatch.setenv(
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod.system, "hostname_short", lambda: "box1")

    machine = cli_mod.Machine()
    path = machine.save_host_profile_to_repo(
        "rpi", ["zsh-full", "monitoring"], ["laptop1"]
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
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))

    machine = cli_mod.Machine()
    machine.write_profile("home-laptop", ["zsh-full"], [])
    bak = machine.backup_local_profile()
    assert bak and bak.is_file()
    machine.write_profile("home-server", ["zsh-full", "docker"], ["x"])
    assert machine.current_profile() == "home-server"
    machine.restore_local_profile(bak)
    assert machine.current_profile() == "home-laptop"


def test_help_lists_apply_profile_rollback():
    import subprocess

    result = subprocess.run(
        ["python3", str(MACHINE), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "apply" in result.stdout
    assert "profile" in result.stdout
    assert "rollback" in result.stdout


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
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
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
            profile: home-server
            features:
              - zsh-full
              - docker
            ssh_allow_from: []
            """
        ),
        encoding="utf-8",
    )
    machine.write_profile("home-laptop", ["zsh-full"], [])
    calls: list[str] = []

    def fake_ansible(*_a, **_k):
        calls.append("ansible")

    monkeypatch.setattr(machine, "run_ansible", fake_ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    monkeypatch.setattr(machine, "health_check_after_apply", lambda: True)
    monkeypatch.setattr(machine, "apply_authorized_keys_from_bw", lambda *_a: None)

    args = argparse.Namespace(limit="", playbook="workstation", no_become=True)
    assert machine.cmd_apply(args) == 0
    assert machine.current_profile() == "home-server"
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
            profile: home-server
            features:
              - zsh-full
            ssh_allow_from: []
            """
        ),
        encoding="utf-8",
    )
    machine.write_profile("home-laptop", ["zsh-full", "fonts"], [])
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
    assert machine.current_profile() == "home-laptop"
    assert machine.saved_features() == ["zsh-full", "fonts"]
    assert len(calls) == 2  # fail + revert re-run


def test_apply_reverts_on_health_check_failure(tmp_path: Path, monkeypatch):
    import argparse

    _cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "machine/hosts/testhost.yml").write_text(
        "---\nprofile: home-server\nfeatures:\n  - zsh-full\nssh_allow_from: []\n",
        encoding="utf-8",
    )
    machine.write_profile("home-laptop", ["zsh-full"], [])
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
    assert machine.current_profile() == "home-laptop"
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
    hosts = REPO / "machine" / "hosts"
    files = sorted(p for p in hosts.glob("*.yml") if not p.name.startswith("_"))
    assert files, "expected machine/hosts/*.yml"
    for path in files:
        data = cli.parse_profile_file(path)
        assert data.get("profile") in cli.PROFILES, path.name
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
    machine.write_profile("home-laptop", ["zsh-full", "sshd-home"], [])
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


def test_prompts_use_arrow_key_pickers_on_a_terminal(tmp_path: Path, monkeypatch):
    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    monkeypatch.setattr(cli_mod.system, "is_tty", lambda: True)
    monkeypatch.setattr(cli_mod.system, "choose", lambda _t, choices, _d: choices[1])
    monkeypatch.setattr(
        cli_mod.system,
        "choose_many",
        lambda _t, choices, selected: [*selected, list(choices)[-1]],
    )

    assert machine.prompt_profile("rpi") == cli_mod.PROFILES[1]
    assert machine.prompt_features(["zsh-full"]) == ["zsh-full", cli_mod.FEATURES[-1]]


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


def test_bw_ssh_hosts_lists_same_class_only(tmp_path: Path, monkeypatch):
    import json
    import subprocess

    cli_mod, machine, _repo = _machine_env(tmp_path, monkeypatch)
    names = ["ssh/home/hosts/alpha", "ssh/work/hosts/beta", "ssh/home/hosts-old/x"]
    listing = json.dumps([{"name": name} for name in names])
    monkeypatch.setenv("BW_SESSION", "fake")
    monkeypatch.setattr(cli_mod.system, "have", lambda _name: True)
    monkeypatch.setattr(
        cli_mod.system,
        "run",
        lambda cmd, **_k: subprocess.CompletedProcess(cmd, 0, listing, ""),
    )
    assert machine.bw_ssh_hosts("home-laptop") == ["alpha"]
    assert machine.bw_ssh_hosts("work-laptop") == ["beta"]
    assert machine.bw_ssh_hosts("container") == []


def test_ssh_allow_from_offers_hosts_from_repo_and_bitwarden(tmp_path, monkeypatch):
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    keys = repo / "machine" / "ssh_keys"
    keys.mkdir(parents=True)
    for host in ("homeserver", "testhost"):  # testhost is this machine
        (keys / f"{host}.pub").write_text("ssh-ed25519 AAAA\n", encoding="utf-8")
    monkeypatch.setattr(machine, "bw_ssh_hosts", lambda _p=None: ["homeserver", "pi"])

    assert machine.known_ssh_hosts("home-laptop") == {
        "homeserver": "machine/ssh_keys + Bitwarden",
        "pi": "Bitwarden",
    }
    # repo keys belong to the home fleet only
    assert machine.known_ssh_hosts("work-laptop") == {
        "homeserver": "Bitwarden",
        "pi": "Bitwarden",
    }


def test_run_ansible_uses_classic_sudo_for_local_runs(tmp_path: Path, monkeypatch):
    """sudo-rs prompts are not recognised by Ansible; local runs pick sudo.ws if present."""
    cli_mod, machine, repo = _machine_env(tmp_path, monkeypatch)
    (repo / "ansible/workstation.yml").write_text("---\n", encoding="utf-8")
    commands: list[list[str]] = []
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
