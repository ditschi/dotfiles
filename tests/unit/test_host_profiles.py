from __future__ import annotations

import textwrap
from importlib.machinery import SourceFileLoader
from pathlib import Path

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
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod, "hostname_short", lambda: "testhost")

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
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod, "hostname_short", lambda: "box1")

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
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))
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
    monkeypatch.setenv("MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml"))
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
    monkeypatch.setenv("MACHINE_STATE_DIR", str(home / ".local/share/machine"))
    monkeypatch.setattr(cli_mod, "hostname_short", lambda: hostname)
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
    args = argparse.Namespace(limit="missing-host", playbook="workstation", no_become=True)
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
