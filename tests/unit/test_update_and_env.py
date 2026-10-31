from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from machine_loader import load_machine_module
from package_sets import REPO

MACHINE = REPO / "machine_cli/machine"

HOST_YAML = """\
---
context: {context}
device: {device}
features:
  - zsh-full
ssh_allow_from: []
"""


def _cli():
    return load_machine_module("machine_cli_update", MACHINE)


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def _base_env(tmp_path: Path, monkeypatch, repo: Path) -> Path:
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
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return home


# --- machine update --------------------------------------------------------


@pytest.fixture
def update_env(tmp_path: Path, monkeypatch):
    """A clone of a bare origin as DOTFILES_REPO, plus a second clone to push from."""
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    repo = tmp_path / "dotfiles"
    other = tmp_path / "other"
    home = _base_env(tmp_path, monkeypatch, repo)

    _git("init", "-q", "--bare", "-b", "main", str(origin), cwd=tmp_path)
    _git("clone", "-q", str(origin), str(seed), cwd=tmp_path)
    (seed / "machine/hosts").mkdir(parents=True)
    (seed / "home").mkdir()
    (seed / "home/dot_placeholder").write_text("")
    (seed / "machine/hosts/testhost.yml").write_text(
        HOST_YAML.format(context="private", device="desktop")
    )
    _git("add", "-A", cwd=seed)
    _git("commit", "-q", "-m", "seed", cwd=seed)
    _git("push", "-q", "origin", "HEAD:main", cwd=seed)
    _git("clone", "-q", str(origin), str(repo), cwd=tmp_path)
    _git("clone", "-q", str(origin), str(other), cwd=tmp_path)

    cli = _cli()
    monkeypatch.setattr(cli.system, "hostname_short", lambda: "testhost")
    machine = cli.Machine()
    # never let a broken fixture fall back to the real checkout (it would git pull)
    assert machine.repo == repo
    machine.sync_host_config_from_repo()  # host already in sync before update
    machine.record_ansible_applied()  # a host that has run Ansible

    calls: list[str] = []
    monkeypatch.setattr(machine, "run_dotfiles_apply", lambda: calls.append("dotfiles"))
    monkeypatch.setattr(machine, "run_tools_install", lambda: calls.append("tools"))
    original_have = cli.system.have
    monkeypatch.setattr(
        cli.system, "have", lambda name: name == "mise" or original_have(name)
    )
    monkeypatch.setattr(machine, "cmd_env_pull", lambda: calls.append("env") or 0)
    monkeypatch.setattr(machine, "cmd_apply", lambda _args: calls.append("apply") or 0)
    return machine, repo, other, home, calls


def machine_system():
    import machine_cli.system as system_module

    return system_module


def _push_change(other: Path, path: str, content: str) -> None:
    target = other / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _git("add", "-A", cwd=other)
    _git("commit", "-q", "-m", f"change {path}", cwd=other)
    _git("push", "-q", "origin", "HEAD:main", cwd=other)


def _update(machine, *, force=False, system=False, skip_ansible=False) -> int:
    return machine.cmd_update(
        argparse.Namespace(force=force, system=system, skip_ansible=skip_ansible)
    )


def test_update_pulls_and_skips_apply_when_profile_unchanged(update_env):
    machine, repo, other, home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    machine.set_pending(True)

    assert _update(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert "env" in calls and "apply" not in calls
    assert not machine.read_update_state()["pending"]


def test_update_writes_updated_state_with_new_revision(update_env):
    machine, repo, other, home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    machine.write_update_state("available")

    assert _update(machine) == 0
    state = machine.read_update_state()
    assert state["state"] == "updated"
    assert state["revision"] == machine.repo_revision() != ""


def _commit_local(repo: Path, path: str, content: str) -> None:
    (repo / path).write_text(content)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", f"local {path}", cwd=repo)


def test_update_blocked_by_conflicting_divergence_writes_attention_state(update_env):
    machine, repo, other, home, _calls = update_env
    _push_change(other, "home/dot_placeholder", "remote\n")
    _commit_local(repo, "home/dot_placeholder", "local\n")

    with pytest.raises(SystemExit):
        _update(machine)
    state = machine.read_update_state()
    assert state["state"] == "attention" and state["pending"] == "1"
    assert "diverged: 1 local and 1 incoming commit" in state["reason"]
    assert "git pull --rebase" in state["reason"]


def test_status_is_compact_and_names_the_blocker(update_env, capsys):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_placeholder", "remote\n")
    _git("fetch", "-q", cwd=repo)
    (repo / "home/dot_placeholder").write_text("local\n")
    machine.write_update_state("attention", "old reason")

    assert machine.cmd_status() == 0
    out = capsys.readouterr().out
    assert "1 behind origin/main" in out
    assert "conflict with local changes in home/dot_placeholder" in out
    assert "then run: machine" in out
    assert "zsh-full" in out and "config in sync" in out
    assert "context:" not in out  # the host config is not dumped
    assert "\x1b[" not in out  # no colors when not a terminal
    assert "update pending" not in out


def test_status_verbose_shows_configs_and_files(update_env, capsys):
    machine, repo, _other, _home, _calls = update_env
    (repo / "wip.txt").write_text("x\n")

    assert machine.cmd_status(verbose=True) == 0
    out = capsys.readouterr().out
    assert "context: private" in out
    assert "local changes" in out and "wip.txt" in out


def test_status_notes_a_symlinked_home(update_env, monkeypatch, capsys):
    machine, _repo, _other, home, _calls = update_env
    alias = home.parent / "home-alias"
    alias.symlink_to(home)
    monkeypatch.setenv("HOME", str(alias))
    assert machine.cmd_status() == 0
    assert f"home is {home.resolve()}" in capsys.readouterr().out

    monkeypatch.setenv("HOME", str(home.resolve()))
    assert machine.cmd_status() == 0
    assert "home is" not in capsys.readouterr().out


def _auto(machine) -> int:
    return machine.cmd_update(argparse.Namespace(auto=True))


def test_auto_update_health_check_uses_relocated_helper(update_env, monkeypatch):
    machine, _repo, _other, home, _calls = update_env
    shell_root = home / ".shell"
    (shell_root / "bash").mkdir(parents=True)
    (shell_root / "zsh").mkdir()
    shutil.copy(
        REPO / "home/core/.shell/bash/zsh-health.bash",
        shell_root / "bash/zsh-health.bash",
    )
    (home / ".zshrc").write_text("")
    (shell_root / "zsh/init.zsh").write_text("")
    antidote = home / ".local/share/antidote/mattmc3/antidote"
    antidote.mkdir(parents=True)
    (home / ".cache/zsh").mkdir(parents=True)
    (home / ".cache/zsh/plugins.zsh").write_text("# generated\n")
    bin_dir = home / "bin"
    bin_dir.mkdir()
    zsh = bin_dir / "zsh"
    zsh.write_text("#!/bin/sh\nexit 3\n")
    zsh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")

    assert "zsh failed to start (exit 3)" in machine.zsh_health_failure()


def test_attention_says_so_when_nothing_is_open(update_env, capsys):
    machine, *_ = update_env

    assert machine.cmd_attention() == 0
    assert "Nothing needs attention" in capsys.readouterr().out


def test_attention_lists_items_without_prompting_when_not_interactive(
    update_env, capsys, monkeypatch
):
    machine, repo, other, _home, calls = update_env
    machine.write_update_state("attention", "the automatic update was reverted")
    _push_change(other, "ansible/new.yml", "x\n")
    _git("fetch", "-q", cwd=repo)
    _git("merge", "-q", "--ff-only", "origin/main", cwd=repo)
    monkeypatch.setattr(
        machine_system(), "prompt_yes_no", lambda *a, **k: pytest.fail("prompted")
    )

    assert machine.cmd_attention() == 0
    out = capsys.readouterr().out
    assert "[update] the automatic update was reverted" in out
    # no `machine apply` on the old checkout while the update item is open
    assert "the pending system step runs with the update" in out
    assert "[system]" not in out
    assert calls == []


def test_attention_offers_apply_for_a_system_update_alone(update_env, capsys):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "ansible/new.yml", "x\n")
    _git("fetch", "-q", cwd=repo)
    _git("merge", "-q", "--ff-only", "origin/main", cwd=repo)

    assert machine.cmd_attention() == 0
    assert "[system] system update pending: ansible/new.yml" in capsys.readouterr().out


def test_attention_resolves_items_on_a_terminal(update_env, capsys, monkeypatch):
    machine, *_ = update_env
    machine.write_update_state("attention", "needs a look")
    ran = []
    monkeypatch.setattr(machine, "cmd_update", lambda args: ran.append("update") or 0)
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    monkeypatch.setattr(machine_system(), "prompt_yes_no", lambda *a, **k: True)

    assert machine.cmd_attention() == 0
    assert ran == ["update"]


def test_auto_update_applies_home_only_changes(update_env):
    machine, repo, other, home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    machine.set_pending(True)

    assert _auto(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert calls == ["dotfiles"]
    assert machine.read_update_state()["state"] == "updated"
    assert not machine.read_update_state()["pending"]


def test_auto_update_leaves_system_change_pending(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "ansible/new.yml", "x\n")

    assert _auto(machine) == 0
    assert not (repo / "ansible/new.yml").exists()
    assert calls == []
    assert machine.read_update_state()["state"] == "available"
    assert machine.read_update_state()["pending"] == "1"


def test_auto_update_stops_before_first_system_commit(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_first", "1\n")
    _push_change(other, "ansible/new.yml", "x\n")
    _push_change(other, "home/dot_last", "2\n")

    assert _auto(machine) == 0
    assert (repo / "home/dot_first").is_file()
    assert not (repo / "ansible/new.yml").exists()
    assert not (repo / "home/dot_last").exists()
    assert calls == ["dotfiles"]
    assert machine.read_update_state()["state"] == "available"


def test_auto_update_treats_own_host_profile_as_system_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(
        other,
        "machine/hosts/testhost.yml",
        HOST_YAML.format(context="private", device="server"),
    )
    assert _auto(machine) == 0
    assert machine.read_update_state()["state"] == "available"
    # another host's profile does not block the automatic update
    _push_change(
        other,
        "machine/hosts/other.yml",
        HOST_YAML.format(context="private", device="server"),
    )
    assert machine.safe_update_target("origin/main") is None


def test_auto_update_keeps_unrelated_local_changes(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "home/dot_placeholder").write_text("edited\n")

    assert _auto(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert (repo / "home/dot_placeholder").read_text() == "edited\n"
    assert machine.read_update_state()["state"] == "updated"
    assert not _git("stash", "list", cwd=repo).strip()


def test_auto_update_merges_cleanly_overlapping_local_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_lines", "a\nb\nc\nd\ne\n")
    _git("pull", "-q", "--ff-only", cwd=repo)
    _push_change(other, "home/dot_lines", "A\nb\nc\nd\ne\n")
    (repo / "home/dot_lines").write_text("a\nb\nc\nd\nE\n")

    assert _auto(machine) == 0
    assert (repo / "home/dot_lines").read_text() == "A\nb\nc\nd\nE\n"
    assert machine.repo_revision() == _git("rev-parse", "origin/main", cwd=repo).strip()
    assert not _git("stash", "list", cwd=repo).strip()


def test_auto_update_records_conflict_without_stashing(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_placeholder", "remote\n")
    (repo / "home/dot_placeholder").write_text("local\n")

    assert _auto(machine) == 0
    assert (repo / "home/dot_placeholder").read_text() == "local\n"
    assert calls == []
    state = machine.read_update_state()
    assert state["state"] == "attention"
    assert "conflict with local changes in home/dot_placeholder" in state["reason"]
    assert not _git("stash", "list", cwd=repo).strip()


def test_auto_update_revert_restores_local_changes(update_env, monkeypatch):
    machine, repo, other, _home, _calls = update_env
    before = machine.repo_revision()
    _push_change(other, "home/dot_new", "x\n")
    (repo / "home/dot_placeholder").write_text("edited\n")
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "zsh failed\ndetails")

    assert _auto(machine) == 0
    assert machine.repo_revision() == before
    assert (repo / "home/dot_placeholder").read_text() == "edited\n"
    assert not _git("stash", "list", cwd=repo).strip()
    assert machine.update_failure_file.read_text() == "zsh failed\ndetails\n"


def test_auto_update_does_not_rebase_diverged_history(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    _commit_local(repo, "home/dot_mine", "y\n")
    head = machine.repo_revision()

    assert _auto(machine) == 0
    assert calls == [] and machine.repo_revision() == head
    state = machine.read_update_state()
    assert state["state"] == "attention"
    assert "rebase cleanly → run: machine update" in state["reason"]


def test_auto_update_reverts_when_zsh_breaks(update_env, monkeypatch):
    machine, repo, other, _home, _calls = update_env
    before = machine.repo_revision()
    _push_change(other, "home/dot_new", "x\n")
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "zsh failed to start")

    assert _auto(machine) == 0
    assert machine.repo_revision() == before
    state = machine.read_update_state()
    assert state["state"] == "attention" and "reverted" in state["reason"]

    # the broken revision is not retried until the owner runs `machine update`
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "")
    assert _auto(machine) == 0
    assert machine.repo_revision() == before
    assert _update(machine) == 0
    assert (repo / "home/dot_new").is_file()


def test_auto_update_reverts_when_dotfile_apply_fails(update_env, monkeypatch):
    machine, _repo, other, _home, _calls = update_env
    before = machine.repo_revision()
    _push_change(other, "home/dot_added", "x\n")  # a new file needs a dotfile apply
    monkeypatch.setattr(machine, "_dotfiles_apply_quiet", lambda: False)

    assert _auto(machine) == 0
    assert machine.repo_revision() == before
    state = machine.read_update_state()
    assert state["state"] == "attention" and "dotfile apply failed" in state["reason"]


def test_auto_update_reverts_when_tool_install_fails(update_env, monkeypatch):
    machine, repo, other, _home, _calls = update_env
    before = machine.repo_revision()
    _push_change(other, "home/core/.config/mise/mise.lock", "x\n")
    monkeypatch.setattr(machine, "_tools_install_quiet", lambda: False)

    assert _auto(machine) == 0
    assert machine.repo_revision() == before
    state = machine.read_update_state()
    assert state["state"] == "attention" and "tool install failed" in state["reason"]

    # not retried; a manual update succeeds and clears the failure
    monkeypatch.setattr(machine, "_tools_install_quiet", lambda: True)
    assert _auto(machine) == 0 and machine.repo_revision() == before
    assert _update(machine) == 0
    assert (repo / "home/core/.config/mise/mise.lock").is_file()
    assert not machine.read_update_state()["failed_revision"]


def test_auto_update_runs_tool_install_for_a_changed_lockfile(update_env, monkeypatch):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "home/core/.config/mise/mise.lock", "x\n")
    monkeypatch.setattr(
        machine, "_tools_install_quiet", lambda: calls.append("tools") or True
    )

    assert _auto(machine) == 0
    assert calls == ["tools"]


def test_auto_update_skips_when_another_update_runs(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    with machine.update_lock():
        assert _auto(machine) == 0
    assert calls == []


def test_update_applies_when_host_profile_changed_upstream(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(
        other,
        "machine/hosts/testhost.yml",
        HOST_YAML.format(context="private", device="server"),
    )

    assert _update(machine) == 0
    assert "device: server" in machine.applied_host_path.read_text()
    # new local group config from the synced profile is applied before ansible
    assert calls == ["dotfiles", "tools", "env", "apply"]


def _failing_ansible_env(machine, monkeypatch, calls):
    monkeypatch.delattr(
        machine, "cmd_apply"
    )  # use the real apply, not the fixture stub

    def ansible(*_a, **_k):
        calls.append("ansible")
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, ["ansible-playbook"])

    monkeypatch.setattr(machine, "run_ansible", ansible)
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)


def test_update_restores_profile_when_ansible_fails(update_env, monkeypatch):
    machine, _repo, other, _home, _calls = update_env
    ansible_calls: list[str] = []
    _failing_ansible_env(machine, monkeypatch, ansible_calls)
    _push_change(
        other,
        "machine/hosts/testhost.yml",
        HOST_YAML.format(context="private", device="server"),
    )

    with pytest.raises(SystemExit):
        _update(machine)
    assert "device: desktop" in machine.applied_host_path.read_text()
    assert ansible_calls == ["ansible", "ansible"]  # failed apply + revert run


def test_update_restores_profile_when_health_check_fails(update_env, monkeypatch):
    machine, _repo, other, _home, _calls = update_env
    ansible_calls: list[str] = []
    monkeypatch.delattr(machine, "cmd_apply")
    monkeypatch.setattr(
        machine, "run_ansible", lambda *_a, **_k: ansible_calls.append("ansible")
    )
    monkeypatch.setattr(machine, "ensure_bootstrap_tools", lambda *_a, **_k: None)
    monkeypatch.setattr(machine, "health_check_after_apply", lambda: False)
    _push_change(
        other,
        "machine/hosts/testhost.yml",
        HOST_YAML.format(context="private", device="server"),
    )

    with pytest.raises(SystemExit):
        _update(machine)
    assert "device: desktop" in machine.applied_host_path.read_text()
    assert ansible_calls == ["ansible", "ansible"]


def test_update_keeps_unchanged_profile_when_ansible_fails(update_env, monkeypatch):
    machine, _repo, _other, _home, _calls = update_env
    ansible_calls: list[str] = []
    _failing_ansible_env(machine, monkeypatch, ansible_calls)
    before = machine.applied_host_path.read_bytes()

    with pytest.raises(SystemExit):
        _update(machine, system=True)
    assert machine.applied_host_path.read_bytes() == before
    assert ansible_calls == ["ansible"]  # not retried


def _fake_loginctl(directory: Path, linger: str) -> Path:
    log = directory / "loginctl.log"
    directory.mkdir(parents=True, exist_ok=True)
    tool = directory / "loginctl"
    tool.write_text(
        "#!/bin/sh\n"
        f'echo "$@" >> "{log}"\n'
        f'[ "$1" = show-user ] && echo {linger}\n'
        "exit 0\n"
    )
    tool.chmod(0o755)
    return log


def _linger_machine(update_env, tmp_path, monkeypatch, linger: str):
    machine, *_ = update_env
    log = _fake_loginctl(tmp_path / "bin", linger)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:{os.environ['PATH']}")
    monkeypatch.setattr(
        machine.ensure_linger.__func__.__globals__["system"], "in_docker", lambda: False
    )
    return machine, log


def test_ensure_linger_enables_it_when_off(update_env, tmp_path, monkeypatch):
    machine, log = _linger_machine(update_env, tmp_path, monkeypatch, "no")
    machine.ensure_linger()
    assert "enable-linger" in log.read_text()


def test_ensure_linger_leaves_enabled_linger_alone(update_env, tmp_path, monkeypatch):
    machine, log = _linger_machine(update_env, tmp_path, monkeypatch, "yes")
    machine.ensure_linger()
    assert "enable-linger" not in log.read_text()


def test_ensure_linger_is_skipped_without_loginctl(update_env, tmp_path, monkeypatch):
    machine, *_ = update_env
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    machine.ensure_linger()  # must not raise


def test_update_system_flag_applies_without_profile_change(update_env):
    machine, _repo, _other, _home, calls = update_env
    assert _update(machine, system=True) == 0
    assert calls[-1] == "apply"


def test_update_skip_ansible_keeps_system_change_pending(update_env, capsys):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "ansible/roles/x.yml", "x\n")

    assert _update(machine, skip_ansible=True) == 0
    assert calls == ["dotfiles", "tools", "env"]
    assert "system changes remain pending" in capsys.readouterr().out
    assert "ansible/roles/x.yml" in machine.pending_system_paths("HEAD")


def test_update_skip_ansible_overrides_system_flag(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "ansible/roles/x.yml", "x\n")

    assert _update(machine, system=True, skip_ansible=True) == 0
    assert calls == ["dotfiles", "tools", "env"]
    assert "ansible/roles/x.yml" in machine.pending_system_paths("HEAD")


def _conflict(repo: Path, other: Path) -> None:
    _push_change(other, "home/dot_placeholder", "remote\n")
    (repo / "home/dot_placeholder").write_text("local\n")


def test_update_stops_on_conflict_without_a_terminal(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _conflict(repo, other)
    head = machine.repo_revision()

    with pytest.raises(SystemExit):
        _update(machine)
    err = capsys.readouterr().err.strip().splitlines()
    assert (
        "1 incoming commit conflict with local changes in home/dot_placeholder"
        in err[-1]
    )
    assert (repo / "home/dot_placeholder").read_text() == "local\n"
    assert machine.repo_revision() == head and calls == []
    state = machine.read_update_state()
    assert state["state"] == "attention" and state["pending"] == "1"


def test_update_conflict_defaults_to_manual_on_a_terminal(
    update_env, capsys, monkeypatch
):
    machine, repo, other, _home, calls = update_env
    _conflict(repo, other)
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    asked = []
    monkeypatch.setattr(
        machine_system(),
        "choose",
        lambda title, choices, default: asked.append(choices) or default,
    )

    with pytest.raises(SystemExit):
        _update(machine)
    assert asked and asked[0][0] == "resolve manually"
    assert "git mergetool" in capsys.readouterr().out
    assert (repo / "home/dot_placeholder").read_text() == "local\n"
    assert calls == []


def test_update_conflict_stash_choice_updates_and_lists_the_entry(
    update_env, capsys, monkeypatch
):
    machine, repo, other, _home, _calls = update_env
    _conflict(repo, other)
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    monkeypatch.setattr(
        machine_system(), "choose", lambda title, choices, default: choices[1]
    )

    assert _update(machine) == 0
    assert (repo / "home/dot_placeholder").read_text() == "remote\n"
    entries = machine.stash_entries()
    assert len(entries) == 1 and "conflicting with origin/main" in entries[0][2]
    monkeypatch.setattr(machine_system(), "is_tty", lambda: False)
    items = machine.attention_items()
    assert [item.kind for item in items] == ["stash"]


def test_update_keeps_cleanly_merging_overlap(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_lines", "a\nb\nc\nd\ne\n")
    _git("pull", "-q", "--ff-only", cwd=repo)
    _push_change(other, "home/dot_lines", "A\nb\nc\nd\ne\n")
    (repo / "home/dot_lines").write_text("a\nb\nc\nd\nE\n")

    plan = machine.update_plan(fetch=True)
    assert plan["merged"] == ["home/dot_lines"] and plan["blockers"] == []
    assert _update(machine) == 0
    assert (repo / "home/dot_lines").read_text() == "A\nb\nc\nd\nE\n"
    assert not _git("stash", "list", cwd=repo).strip()


def test_plan_counts_untracked_file_at_an_added_path_as_conflict(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "remote\n")
    (repo / "home/dot_new").write_text("mine\n")

    plan = machine.update_plan(fetch=True)
    assert plan["conflicts"] == ["home/dot_new"]


def test_update_keeps_unrelated_local_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "local-edit.txt").write_text("wip\n")

    assert _update(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert (repo / "local-edit.txt").read_text() == "wip\n"


def test_update_force_stashes_only_the_conflict(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_lines", "a\nb\nc\nd\ne\n")
    _git("pull", "-q", "--ff-only", cwd=repo)
    _push_change(other, "home/dot_lines", "A\nb\nc\nd\ne\n")
    _conflict(repo, other)
    (repo / "home/dot_lines").write_text("a\nb\nc\nd\nE\n")

    assert _update(machine, force=True) == 0
    assert (repo / "home/dot_placeholder").read_text() == "remote\n"
    assert (repo / "home/dot_lines").read_text() == "A\nb\nc\nd\nE\n"
    entries = machine.stash_entries()
    assert len(entries) == 1
    shown = _git("stash", "show", "--name-only", entries[0][1], cwd=repo)
    assert shown.split() == ["home/dot_placeholder"]


def test_stash_item_restores_or_keeps_the_entry(update_env, capsys, monkeypatch):
    machine, repo, other, _home, _calls = update_env
    _conflict(repo, other)
    assert _update(machine, force=True) == 0
    (item,) = machine.stash_items()
    assert item.question is None  # the item asks restore / drop / keep itself
    monkeypatch.setattr(
        machine_system(), "choose", lambda title, choices, default: choices[0]
    )

    assert item.resolve() == 1  # conflicts with the new upstream text
    assert machine.stash_entries()  # kept
    assert "git stash drop" in capsys.readouterr().out
    _git("reset", "-q", "--hard", cwd=repo)
    _git("stash", "drop", "-q", cwd=repo)
    assert machine.stash_entries() == []  # dropped by hand: the record is cleared
    assert machine.read_update_state()["stash"] == ""


def test_stash_item_keeps_by_default_and_drops_on_request(update_env, monkeypatch):
    machine, repo, other, _home, _calls = update_env
    _conflict(repo, other)
    assert _update(machine, force=True) == 0
    (item,) = machine.stash_items()

    assert item.resolve() == 0  # not a terminal: the default keeps it
    assert machine.stash_entries()
    monkeypatch.setattr(
        machine_system(), "choose", lambda title, choices, default: choices[1]
    )
    assert item.resolve() == 0
    assert machine.stash_entries() == []
    assert (repo / "home/dot_placeholder").read_text() == "remote\n"


def test_status_counts_stash_entries_recognised_by_name(update_env, capsys):
    machine, repo, _other, _home, _calls = update_env
    (repo / "home/dot_placeholder").write_text("aside\n")
    _git(
        "stash", "push", "-q", "-m", "machine update 2026-01-01T00:00:00: old", cwd=repo
    )
    (repo / "home/dot_placeholder").write_text("other\n")
    _git("stash", "push", "-q", "-m", "my own stash", cwd=repo)
    assert machine.read_update_state()["stash"] == ""  # not recorded

    entries = machine.stash_entries()
    assert [message.partition(": ")[2] for _r, _s, message in entries] == [
        "machine update 2026-01-01T00:00:00: old"
    ]
    assert machine.cmd_status() == 0
    out = capsys.readouterr().out
    assert "1 stash entry put aside by machine" in out
    assert "machine attention" in out
    assert machine.cmd_status(verbose=True) == 0
    assert "machine update 2026-01-01T00:00:00: old" in capsys.readouterr().out


def test_update_rebases_clean_diverged_history(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    _commit_local(repo, "home/dot_local", "l\n")
    (repo / "home/dot_placeholder").write_text("wip\n")

    assert _update(machine) == 0
    assert _git("rev-list", "--count", "origin/main..HEAD", cwd=repo).strip() == "1"
    assert _git("rev-list", "--count", "HEAD..origin/main", cwd=repo).strip() == "0"
    assert (repo / "home/dot_remote").is_file()
    assert (repo / "home/dot_placeholder").read_text() == "wip\n"
    assert not _git("stash", "list", cwd=repo).strip()


def _diverged_with_conflict(repo: Path, other: Path) -> None:
    """One local commit to rebase, an uncommitted change that conflicts, one that does not."""
    _commit_local(repo, "home/dot_local", "l\n")
    _conflict(repo, other)
    (repo / "home/dot_local").write_text("wip\n")


def test_diverged_plan_lists_conflicting_uncommitted_files(update_env):
    machine, repo, other, _home, _calls = update_env
    _diverged_with_conflict(repo, other)

    plan = machine.update_plan(fetch=True)
    assert plan["state"] == "diverged"
    assert plan["conflicts"] == ["home/dot_placeholder"]


def test_diverged_conflict_reason_names_files_without_a_terminal(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _diverged_with_conflict(repo, other)
    head = machine.repo_revision()

    with pytest.raises(SystemExit):
        _update(machine)
    err = capsys.readouterr().err.strip().splitlines()
    assert "home/dot_placeholder" in err[-1]
    assert "commit, stash or discard them, then run: machine update" in err[-1]
    assert "git pull --rebase" not in err[-1]
    assert machine.repo_revision() == head and calls == []
    assert machine.read_update_state()["state"] == "attention"


@pytest.mark.parametrize("how", ["choice", "force"])
def test_diverged_conflict_stash_rebases_and_keeps_other_changes(
    update_env, monkeypatch, how
):
    machine, repo, other, _home, _calls = update_env
    _diverged_with_conflict(repo, other)
    if how == "choice":
        monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
        monkeypatch.setattr(
            machine_system(), "choose", lambda title, choices, default: choices[1]
        )

    assert _update(machine, force=how == "force") == 0
    assert _git("rev-list", "--count", "HEAD..origin/main", cwd=repo).strip() == "0"
    assert _git("rev-list", "--count", "origin/main..HEAD", cwd=repo).strip() == "1"
    assert (repo / "home/dot_placeholder").read_text() == "remote\n"
    assert (repo / "home/dot_local").read_text() == "wip\n"
    [entry] = machine.stash_entries()
    shown = _git("stash", "show", "--name-only", entry[1], cwd=repo)
    assert shown.split() == ["home/dot_placeholder"]
    assert machine.stash_items()


def test_diverged_conflict_defaults_to_manual_on_a_terminal(
    update_env, capsys, monkeypatch
):
    machine, repo, other, _home, calls = update_env
    _diverged_with_conflict(repo, other)
    head = machine.repo_revision()
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    asked = []
    monkeypatch.setattr(
        machine_system(),
        "choose",
        lambda title, choices, default: asked.append(choices) or default,
    )

    with pytest.raises(SystemExit):
        _update(machine)
    assert asked and asked[0][0] == "resolve manually"
    assert "git rebase origin/main" in capsys.readouterr().out
    assert machine.repo_revision() == head and calls == []
    assert (repo / "home/dot_placeholder").read_text() == "local\n"
    assert machine.read_update_state()["state"] == "attention"


def test_update_does_not_rebase_a_pushed_local_commit(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    _commit_local(repo, "home/dot_local", "l\n")
    _git("push", "-q", "origin", "HEAD:feature", cwd=repo)
    _git("fetch", "-q", cwd=repo)

    with pytest.raises(SystemExit):
        _update(machine)
    assert "already on a remote branch" in capsys.readouterr().err
    assert calls == []


def test_update_does_not_rebase_with_signing_on(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    _commit_local(repo, "home/dot_local", "l\n")
    _git("config", "commit.gpgsign", "true", cwd=repo)

    with pytest.raises(SystemExit):
        _update(machine)
    assert "commit signing is on" in capsys.readouterr().err


def test_update_does_not_rebase_merge_commits(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    _git("checkout", "-q", "-b", "side", cwd=repo)
    _commit_local(repo, "home/dot_side", "s\n")
    _git("checkout", "-q", "main", cwd=repo)
    _commit_local(repo, "home/dot_local", "l\n")
    _git("merge", "-q", "--no-ff", "-m", "merge side", "side", cwd=repo)

    with pytest.raises(SystemExit):
        _update(machine)
    assert "merge commit" in capsys.readouterr().err


def test_update_reports_zsh_failure_without_reloading(update_env, monkeypatch):
    machine, _repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_placeholder", "changed\n")
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "zsh: parse error")

    assert _update(machine) == 1
    state = machine.read_update_state()
    assert state["state"] == "attention" and "zsh" in state["reason"]
    assert machine.update_failure_file.read_text() == "zsh: parse error\n"


def test_attention_shows_failed_check_output(update_env, capsys, monkeypatch):
    machine, *_ = update_env
    machine.state_dir.mkdir(parents=True, exist_ok=True)
    machine.update_failure_file.write_text("zsh: parse error\n")
    machine.write_update_state("attention", "reverted", failed_revision="abc")
    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    monkeypatch.setattr(machine_system(), "prompt_yes_no", lambda *a, **k: False)

    assert machine.cmd_attention() == 0
    assert "zsh: parse error" in capsys.readouterr().out


def test_attention_conflict_item_runs_update_without_a_yes_no_question(
    update_env, monkeypatch
):
    machine, repo, other, _home, _calls = update_env
    _conflict(repo, other)
    _git("fetch", "-q", cwd=repo)
    (item,) = machine.attention_items()
    assert item.kind == "update" and item.question is None
    assert "conflict with local changes" in item.text


def test_update_content_change_runs_only_the_converge_check(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "home/dot_placeholder", "changed\n")

    assert _update(machine) == 0
    assert calls == ["dotfiles", "tools", "env"]


def test_update_converges_when_nothing_is_incoming(update_env):
    machine, *_rest, calls = update_env

    assert _update(machine) == 0
    assert calls == ["dotfiles", "tools", "env"]


def test_update_reports_no_system_change_for_a_host_without_ansible_runs(update_env):
    machine, _repo, other, _home, calls = update_env
    machine.write_update_state("none", ansible_applied_rev="")
    _push_change(other, "ansible/roles/x.yml", "x\n")

    assert machine.update_plan(fetch=True)["steps"] == []
    assert _update(machine) == 0
    assert "apply" not in calls


def test_update_ignores_docs_and_dump_files_for_the_system_step(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "ansible/README.md", "x\n")
    _push_change(other, "ansible/dump_packages.yml", "x\n")
    _push_change(other, "ansible/inventory/hosts.yml", "x\n")

    assert machine.update_plan(fetch=True)["steps"] == []
    assert _update(machine) == 0
    assert "apply" not in calls


def test_update_runs_system_step_when_ansible_changed(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "ansible/roles/x.yml", "x\n")

    assert _update(machine) == 0
    assert calls == ["dotfiles", "tools", "env", "apply"]


def test_update_check_changes_nothing(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    head = _git("rev-parse", "HEAD", cwd=repo)

    assert (
        machine.cmd_update(
            argparse.Namespace(force=False, system=False, check=True, json=True)
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["steps"] == ["dotfiles", "shell"] and plan["blockers"] == []
    assert _git("rev-parse", "HEAD", cwd=repo) == head
    assert calls == []


def test_update_refuses_second_update_while_locked(update_env, capsys):
    import fcntl

    machine, _repo, _other, _home, _calls = update_env
    machine.state_dir.mkdir(parents=True, exist_ok=True)
    with open(machine.state_dir / "update.lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        with pytest.raises(SystemExit):
            _update(machine)
    assert "already running" in capsys.readouterr().err


BLOCK = (
    "## <!-- BEGIN ANSIBLE MANAGED BLOCK - colors -->\n"
    "export X=1\n"
    "## <!-- END ANSIBLE MANAGED BLOCK - colors -->\n"
)


@pytest.fixture
def overrides(tmp_path):
    _cli()
    from machine_cli import local_overrides

    shared = tmp_path / "repo/dot_bashrc"
    shared.parent.mkdir()
    _git("init", "-q", cwd=shared.parent)
    shared.write_text("echo base\n")
    _git("add", "-A", cwd=shared.parent)
    _git(
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "-m",
        "x",
        cwd=shared.parent,
    )
    return local_overrides, shared, tmp_path / "bashrc-local", tmp_path / "backup"


def test_new_text_moves_only_when_selected(overrides):
    lo, shared, local, backup = overrides
    shared.write_text("echo base\n" + BLOCK)
    assert lo.relocate_text(shared, local, backup).moved == []
    assert shared.read_text().endswith(BLOCK) and not local.exists()
    report = lo.relocate_text(shared, local, backup, select=lambda chunks: chunks)
    assert len(report.moved) == 1
    assert shared.read_text() == "echo base\n"
    assert BLOCK in local.read_text() and "machine-local begin:" in local.read_text()
    assert list(backup.iterdir())


def test_bashrc_override_selection_shows_full_colored_diff(
    update_env, monkeypatch, capfd
):
    machine, repo, _other, _home, _calls = update_env
    shared = repo / "home/core/.bashrc"
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text("echo old\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "bashrc", cwd=repo)
    shared.write_text("echo new\n" + BLOCK)

    system = machine_system()
    monkeypatch.setattr(
        system, "choose_many", lambda _title, choices, _selected: list(choices)
    )

    machine.move_bashrc_overrides(interactive=True)

    output = capfd.readouterr().out
    assert "\x1b[31m-" in output and "\x1b[32m+" in output
    plain_output = system.click.unstyle(output)
    assert "-echo old" in plain_output
    assert "+echo new" in plain_output
    assert "+## <!-- BEGIN ANSIBLE MANAGED BLOCK - colors -->" in plain_output


def test_known_text_is_removed_silently_and_conflict_is_kept(overrides):
    lo, shared, local, backup = overrides
    shared.write_text("echo base\n" + BLOCK)
    lo.relocate_text(shared, local, backup, select=lambda chunks: chunks)
    shared.write_text("echo base\n" + BLOCK)
    assert lo.text_pending(shared, local)
    report = lo.relocate_text(shared, local, backup)
    assert report.removed and shared.read_text() == "echo base\n"

    changed = BLOCK.replace("X=1", "X=2")
    shared.write_text("echo base\n" + changed)
    report = lo.relocate_text(shared, local, backup)
    assert report.conflicts and changed in shared.read_text()
    assert "X=1" in local.read_text()
    lo.relocate_text(shared, local, backup, resolve=lambda *a: "shared")
    assert "X=2" in local.read_text() and shared.read_text() == "echo base\n"


def test_update_removes_known_bashrc_text_without_asking(update_env):
    machine, repo, other, home, _calls = update_env
    (repo / "home/core").mkdir(parents=True, exist_ok=True)
    bashrc = repo / "home/core/.bashrc"
    bashrc.write_text("echo base\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "bashrc", cwd=repo)
    _git("push", "-q", "origin", "HEAD:main", cwd=repo)
    _git("pull", "-q", cwd=other)
    (home / ".bashrc-local").write_text(
        "# machine-local begin: ## <!-- BEGIN ANSIBLE MANAGED BLOCK - colors -->\n"
        + BLOCK
        + "# machine-local end: ## <!-- BEGIN ANSIBLE MANAGED BLOCK - colors -->\n"
    )
    bashrc.write_text("echo base\n" + BLOCK)
    _push_change(other, "home/dot_new", "x\n")

    assert _update(machine) == 0
    assert bashrc.read_text() == "echo base\n"
    assert (repo / "home/dot_new").is_file()


def test_classify_incoming_paths():
    _cli()  # puts machine_cli on sys.path
    from machine_cli.local_changes import classify_paths as classify

    assert classify([("M", "home/core/.zshrc")]) == ["shell"]
    assert classify([("A", "home/core/.new")]) == ["dotfiles", "shell"]
    assert classify([("M", "home/core/.shell/zsh/init.zsh")]) == ["shell"]
    assert classify([("A", "home/core/.shell/common/environment.sh")]) == [
        "dotfiles",
        "shell",
    ]
    assert classify([("D", "home/work/.shell/work/zsh/ldap-helpers.zsh")]) == [
        "dotfiles",
        "shell",
    ]
    assert classify([("M", "home/core/.config/mise/mise.lock")]) == ["tools"]
    assert classify([("M", "machine_cli/machine")]) == []
    assert classify([("A", "machine_cli/updates.py")]) == []
    assert classify([("M", "ansible/site.yml"), ("M", "machine/hosts/h.yml")]) == [
        "host-config",
        "system",
    ]
    assert classify([("M", "docs/x.md")]) == []


# --- machine env pull ------------------------------------------------------


def _env_machine(tmp_path, monkeypatch, fake_bw, profile: str, items: dict):
    bw, store = fake_bw
    store.write_text(json.dumps({"_session": "s", "items": items}))
    repo = tmp_path / "dotfiles"
    (repo / "home").mkdir(parents=True)
    (repo / ".git").mkdir()
    home = _base_env(tmp_path, monkeypatch, repo)
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BW_SESSION", "fake-session")
    cli = _cli()
    monkeypatch.setattr(cli.system, "hostname_short", lambda: "testhost")
    machine = cli.Machine()
    assert machine.repo == repo
    from machine_cli.core import LEGACY_PROFILES

    machine.write_profile(*LEGACY_PROFILES[profile], ["zsh-full"], [])
    return machine, home


def _sourced(env_file: Path) -> dict:
    """Values as a shell sees them after `source ~/.env` (last assignment wins)."""
    out = subprocess.run(
        ["sh", "-c", f'set -a; . "{env_file}"; env'],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": os.environ["PATH"]},
    ).stdout
    return dict(line.split("=", 1) for line in out.splitlines() if "=" in line)


def env_pull():
    import machine_cli.env_pull as env_pull_module

    return env_pull_module


def _bw_set_item(fake_bw, name: str, item: dict) -> None:
    _bw, store = fake_bw
    data = json.loads(store.read_text())
    data["items"][name] = item
    store.write_text(json.dumps(data))


def _bw_item(fake_bw, name: str) -> dict:
    _bw, store = fake_bw
    return json.loads(store.read_text())["items"][name]


def _item(notes: str = "", **fields: str) -> dict:
    return {
        "notes": notes,
        "fields": [{"name": k, "value": v, "type": 1} for k, v in fields.items()],
    }


def test_env_pull_layers_groups_host_and_fields(tmp_path, monkeypatch, fake_bw):
    items = {
        "env/groups/private": _item("SHARED=1\nLAYER=shared\nFIELD_WINS=from-notes"),
        # groups other than private and work are no longer read
        "env/groups/server": _item("LAYER=server"),
        "env/hosts/testhost": _item("LAYER=host", FIELD_WINS="from-field"),
        # must never be read by a home host
        "env/groups/work": _item("WORK_ONLY=leak"),
    }
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-server", items)

    assert machine.cmd_env_pull() == 0
    env_file = home / ".env"
    values = _sourced(env_file)
    assert values["SHARED"] == "1"
    assert values["LAYER"] == "shared"
    assert values["FIELD_WINS"] == "from-notes"
    assert "WORK_ONLY" not in values
    host_values = _sourced(home / ".env.host")
    assert host_values["LAYER"] == "host"
    assert host_values["FIELD_WINS"] == "from-field"
    assert "SHARED" not in host_values
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"
    assert (home / ".env.host").stat().st_mode & 0o777 == 0o600


def test_env_pull_work_laptop_reads_work_items_only(tmp_path, monkeypatch, fake_bw):
    items = {
        "env/groups/work": _item("CLASS=work"),
        "env/groups/private": _item("CLASS=home"),
    }
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "work-machine", items)

    assert machine.cmd_env_pull() == 0
    assert _sourced(home / ".env")["CLASS"] == "work"


def test_env_pull_backs_up_hand_written_env_once(tmp_path, monkeypatch, fake_bw):
    items = {"env/groups/private": _item("A=1")}
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-laptop", items)
    (home / ".env").write_text("HANDMADE=1\n")

    assert machine.cmd_env_pull() == 0
    backups = list((machine.state_dir / "env-backup").iterdir())
    assert len(backups) == 1 and backups[0].read_text() == "HANDMADE=1\n"
    assert backups[0].stat().st_mode & 0o777 == 0o600
    assert not (home / ".env.local").exists()
    assert _sourced(home / ".env")["HANDMADE"] == "1"

    # a generated file is not backed up again
    assert machine.cmd_env_pull() == 0
    assert len(list((machine.state_dir / "env-backup").iterdir())) == 1


def test_env_pull_carries_local_only_keys_over_without_touching_overlay(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=updated")},
    )
    (home / ".env").write_text("A=old\nexport LOCAL_ONLY='secret value'\n")
    (home / ".env.local").write_text("OTHER=unchanged\n")

    assert machine.cmd_env_pull() == 0
    text = (home / ".env").read_text()
    assert text.endswith(
        f"{env_pull().LOCAL_ONLY_HEADER}\nexport LOCAL_ONLY='secret value'\n"
    )
    values = _sourced(home / ".env")
    assert values["A"] == "updated" and values["LOCAL_ONLY"] == "secret value"
    assert (home / ".env.local").read_text() == "OTHER=unchanged\n"
    output = capsys.readouterr().out
    assert "~/.env: LOCAL_ONLY not set by Bitwarden env/groups/work" in output
    assert str(machine.state_dir / "env-backup") in output
    assert "run: machine attention" in output
    assert "secret value" not in output

    # still unresolved: the next sync keeps it in the section, unchanged
    assert machine.cmd_env_pull() == 0
    assert (home / ".env").read_text() == text


def test_env_pull_remembers_keys_deleted_in_the_vault(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=1\nGONE=x")},
    )
    assert machine.cmd_env_pull() == 0
    _bw_set_item(fake_bw, "env/groups/work", _item("A=1"))

    assert machine.cmd_env_pull() == 0
    assert "# was in env/groups/work\nGONE=x\n" in (home / ".env").read_text()
    [report] = machine.env_local_only(
        {home / ".env": "A=1\n", home / ".env.host": ""}, ""
    )
    assert report.was_in == {"GONE": "env/groups/work"}


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_env_pull_preserves_local_session_and_load_order(
    tmp_path, monkeypatch, fake_bw, shell
):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not installed")
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {
            "env/groups/work": _item("LAYER=shared\nGITHUB_PRIVATE_TOKEN=private"),
            "env/hosts/testhost": _item("LAYER=host\nHOST_ONLY=yes"),
        },
    )
    local = (
        "export BW_SESSION=local-session\n"
        "export NODE_USE_ENV_PROXY=1\nexport LAYER=local\n"
    )
    (home / ".env.local").write_text(local)
    (home / ".env.backup").write_text("export LAYER=wrong\n")
    assert machine.cmd_env_pull() == 0
    assert (home / ".env.local").read_text() == local
    assert "BW_SESSION" not in (home / ".env").read_text()
    assert "BW_SESSION" not in (home / ".env.host").read_text()
    result = subprocess.run(
        [
            shell,
            "-c",
            '. "$1" >/dev/null; printf "%s\\n" "$LAYER" "$HOST_ONLY" '
            '"$GITHUB_PRIVATE_TOKEN" "$BW_SESSION" "$NODE_USE_ENV_PROXY"',
            "_",
            str(REPO / "home/core/.shell/common/environment.sh"),
        ],
        env={"HOME": str(home), "PATH": os.environ["PATH"]},
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == [
        "local",
        "yes",
        "private",
        "local-session",
        "1",
    ]


def test_env_pull_backs_up_both_generated_files_on_change(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {
            "env/groups/work": _item("A=new"),
            "env/hosts/testhost": _item("B=new"),
        },
    )
    (home / ".env").write_text("A=old\n")
    (home / ".env.host").write_text("B=old\n")
    assert machine.cmd_env_pull() == 0
    backups = list((machine.state_dir / "env-backup").iterdir())
    assert {p.read_text() for p in backups} == {"A=old\n", "B=old\n"}
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in backups)
    assert machine.cmd_env_pull() == 0
    assert len(list((machine.state_dir / "env-backup").iterdir())) == 2


@pytest.mark.parametrize("name", ["env/groups/work", "env/hosts/testhost"])
@pytest.mark.parametrize("custom_field", [False, True])
def test_env_pull_rejects_vault_session(
    tmp_path, monkeypatch, fake_bw, name, custom_field
):
    item = (
        _item(BW_SESSION="vault-session")
        if custom_field
        else _item("export BW_SESSION=vault-session")
    )
    machine, home = _env_machine(
        tmp_path, monkeypatch, fake_bw, "work-machine", {name: item}
    )
    (home / ".env.local").write_text("export BW_SESSION=local-session\n")
    with pytest.raises(SystemExit):
        machine.cmd_env_pull()
    assert not (home / ".env").exists()
    assert not (home / ".env.host").exists()
    assert (home / ".env.local").read_text() == "export BW_SESSION=local-session\n"


def test_env_pull_migrates_host_keys_from_old_combined_env(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {
            "env/groups/work": _item("A=shared"),
            "env/hosts/testhost": _item("B=host"),
        },
    )
    (home / ".env").write_text("A=shared\nB=host\n")
    (home / ".env.local").write_text("export BW_SESSION=keep\n")
    assert machine.cmd_env_pull() == 0
    assert "B=host" not in (home / ".env").read_text()
    assert _sourced(home / ".env.host")["B"] == "host"
    assert (home / ".env.local").read_text() == "export BW_SESSION=keep\n"


def test_env_pull_leaves_env_untouched_without_items(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-laptop", {})
    (home / ".env").write_text("KEEP=1\n")
    (home / ".env.host").write_text("HOST=keep\n")
    (home / ".env.local").write_text("export BW_SESSION=keep\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".env").read_text() == "KEEP=1\n"
    assert (home / ".env.host").read_text() == "HOST=keep\n"
    assert (home / ".env.local").read_text() == "export BW_SESSION=keep\n"


def test_env_pull_with_host_item_only(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/hosts/testhost": _item("HOST_ONLY=yes")},
    )
    assert machine.cmd_env_pull() == 0
    assert "HOST_ONLY" not in (home / ".env").read_text()
    assert _sourced(home / ".env.host")["HOST_ONLY"] == "yes"


def test_env_pull_keeps_both_files_on_sync_failure(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=new")},
    )
    (home / ".env").write_text("A=old\n")
    (home / ".env.host").write_text("HOST=old\n")
    monkeypatch.setattr(machine, "unlock_bitwarden", lambda: True)
    cli = _cli()
    original_run = cli.system.run

    def fail_sync(command, **kwargs):
        if command == ["bw", "sync"]:
            raise subprocess.CalledProcessError(1, command)
        return original_run(command, **kwargs)

    monkeypatch.setattr(cli.system, "run", fail_sync)
    with pytest.raises(subprocess.CalledProcessError):
        machine.cmd_env_pull()
    assert (home / ".env").read_text() == "A=old\n"
    assert (home / ".env.host").read_text() == "HOST=old\n"


def test_env_pull_keeps_only_the_file_with_shell_code(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=new")},
    )
    (home / ".env").write_text("A=old\n")
    (home / ".env.host").write_text("if true; then\nHOST=old\nfi\n")
    assert machine.cmd_env_pull() == 0
    assert _sourced(home / ".env")["A"] == "new"
    assert (home / ".env.host").read_text() == "if true; then\nHOST=old\nfi\n"
    assert not (home / ".env.local").exists()
    backups = list((machine.state_dir / "env-backup").iterdir())
    assert "if true; then\nHOST=old\nfi\n" in {p.read_text() for p in backups}
    output = capsys.readouterr().out
    assert "~/.env.host contains shell code" in output
    assert "run: machine attention" in output


def test_parse_env_file_hand_written():
    parsed = env_pull().parse_env_file("# mine\nexport A=1\nB='x y'\n")
    assert not parsed.generated
    assert parsed.assignments == [("A", "export A=1", None), ("B", "B='x y'", None)]
    assert parsed.shell_code == []


def test_parse_env_file_generated_with_local_only_section():
    module = env_pull()
    text = (
        f"{module.GENERATED_HEADER}\n# - env/groups/work\n\n"
        "# --- env/groups/work ---\nA=1\n\n"
        f"{module.LOCAL_ONLY_HEADER}\nMINE=1\n# was in env/groups/work\nGONE=1\n"
    )
    parsed = module.parse_env_file(text)
    assert parsed.generated
    assert parsed.assignments == [
        ("A", "A=1", "env/groups/work"),
        ("MINE", "MINE=1", module.LOCAL_ONLY),
        ("GONE", "GONE=1", "env/groups/work"),
    ]


def test_parse_env_file_shell_code():
    parsed = env_pull().parse_env_file("if true; then\nHOST=old\nfi\nBAD='open\n")
    assert parsed.shell_code == ["if true; then", "fi", "BAD='open"]
    assert parsed.keys() == {"HOST"}


def _answer(monkeypatch, machine, *answers: str) -> list:
    """Answer the env prompts in order by label prefix; return (choices, default)."""
    asked = []
    pending = list(answers)

    def choose(_title, choices, default):
        asked.append((list(choices), default))
        want = pending.pop(0)
        return next(c for c in choices if c.startswith(want))

    monkeypatch.setattr(machine_system(), "is_tty", lambda: True)
    monkeypatch.setattr(machine_system(), "choose", choose)
    monkeypatch.setattr(machine, "offer_saving_bitwarden_session", lambda: None)
    return asked


def _local_key_machine(tmp_path, monkeypatch, fake_bw, items=None):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        items or {"env/groups/work": {"id": "work-id", **_item("A=1")}},
    )
    (home / ".env").write_text("A=1\nexport MINE=secret\n")
    return machine, home


def test_env_pull_asks_per_key_with_item_and_skip_preselected(
    tmp_path, monkeypatch, fake_bw
):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    asked = _answer(monkeypatch, machine, "skip")

    assert machine.cmd_env_pull() == 0
    [(choices, default)] = asked
    assert choices == [
        "add to Bitwarden env/groups/work",
        "keep locally (~/.env.local)",
        "remove",
        "skip (decide later)",
    ]
    assert default == "skip (decide later)"
    assert (home / ".env").read_text().endswith("export MINE=secret\n")


def test_env_pull_hints_at_a_key_deleted_in_the_vault(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=1\nGONE=x")},
    )
    assert machine.cmd_env_pull() == 0
    _bw_set_item(fake_bw, "env/groups/work", _item("A=1"))
    asked = _answer(monkeypatch, machine, "skip")

    assert machine.cmd_env_pull() == 0
    assert asked[0][1] == "skip (decide later)"
    assert "(was in env/groups/work; deleted there?)" in capsys.readouterr().out


def test_env_pull_keeps_a_key_locally(tmp_path, monkeypatch, fake_bw):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    (home / ".env.local").write_text("export BW_SESSION=keep")
    _answer(monkeypatch, machine, "keep locally")

    assert machine.cmd_env_pull() == 0
    local = (home / ".env.local").read_text()
    assert local.startswith("export BW_SESSION=keep\n# kept from ~/.env on ")
    assert local.endswith("\nexport MINE=secret\n")
    assert (home / ".env.local").stat().st_mode & 0o777 == 0o600
    assert "MINE" not in (home / ".env").read_text()


def test_env_pull_removes_a_key(tmp_path, monkeypatch, fake_bw):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    _answer(monkeypatch, machine, "remove")

    assert machine.cmd_env_pull() == 0
    assert "MINE" not in (home / ".env").read_text()
    assert not (home / ".env.local").exists()
    backups = (machine.state_dir / "env-backup").iterdir()
    assert any("export MINE=secret" in p.read_text() for p in backups)


def test_env_pull_adds_a_key_to_bitwarden_notes(tmp_path, monkeypatch, fake_bw):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    _answer(monkeypatch, machine, "add to Bitwarden")

    assert machine.cmd_env_pull() == 0
    notes = _bw_item(fake_bw, "env/groups/work")["notes"]
    assert notes.startswith("A=1\n\n# added from testhost on ")
    assert notes.endswith("\nexport MINE=secret")
    text = (home / ".env").read_text()
    assert env_pull().LOCAL_ONLY_HEADER not in text
    assert _sourced(home / ".env")["MINE"] == "secret"


def test_env_pull_creates_a_missing_host_item(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=1")},
    )
    (home / ".env.host").write_text("HOST_ONLY=1\n")
    _answer(monkeypatch, machine, "add to Bitwarden env/hosts/testhost")

    assert machine.cmd_env_pull() == 0
    assert _sourced(home / ".env.host")["HOST_ONLY"] == "1"


def test_env_pull_keeps_the_key_local_only_when_bitwarden_fails(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    _answer(monkeypatch, machine, "add to Bitwarden")
    monkeypatch.setattr(machine, "bw_edit_item", lambda item: False)

    assert machine.cmd_env_pull() == 0
    assert (
        (home / ".env")
        .read_text()
        .endswith(f"{env_pull().LOCAL_ONLY_HEADER}\nexport MINE=secret\n")
    )
    assert "could not write Bitwarden env/groups/work" in capsys.readouterr().out


def test_env_pull_does_not_ask_with_yes(tmp_path, monkeypatch, fake_bw):
    machine, home = _local_key_machine(tmp_path, monkeypatch, fake_bw)
    asked = _answer(monkeypatch, machine)
    machine.unattended = True

    assert machine.cmd_env_pull() == 0
    assert asked == []
    assert (home / ".env").read_text().endswith("export MINE=secret\n")
    assert not (home / ".env.local").exists()


def test_env_pull_keeps_shell_code_locally(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/hosts/testhost": _item("B=1")},
    )
    (home / ".env.host").write_text("if true; then\nHOST=old\nfi\n")
    asked = _answer(monkeypatch, machine, "keep locally")

    assert machine.cmd_env_pull() == 0
    [(choices, default)] = asked
    assert default.startswith("skip") and not any("Bitwarden" in c for c in choices)
    assert (home / ".env.local").read_text().endswith("\nif true; then\nHOST=old\nfi\n")
    assert _sourced(home / ".env.host")["B"] == "1"


def _real_env_pull(update_env, monkeypatch, fake_bw, items):
    machine, _repo, _other, home, calls = update_env
    bw, store = fake_bw
    store.write_text(json.dumps({"_session": "s", "items": items}))
    monkeypatch.setenv("PATH", f"{bw.parent}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("BW_SESSION", "fake-session")
    monkeypatch.setattr(
        machine, "cmd_env_pull", type(machine).cmd_env_pull.__get__(machine)
    )
    monkeypatch.setattr(machine, "check_ssh_key_backup", lambda: calls.append("ssh"))
    return machine, home, calls


def test_update_continues_after_local_only_env_keys(update_env, monkeypatch, fake_bw):
    machine, home, calls = _real_env_pull(
        update_env, monkeypatch, fake_bw, {"env/groups/private": _item("A=1")}
    )
    (home / ".env").write_text("A=1\nMINE=x\n")

    assert _update(machine) == 0
    assert "ssh" in calls
    assert machine.read_update_state()["state"] == "updated"
    assert _sourced(home / ".env")["MINE"] == "x"


def test_attention_lists_and_resolves_local_only_env_keys(
    update_env, monkeypatch, fake_bw, capsys
):
    machine, home, _calls = _real_env_pull(
        update_env,
        monkeypatch,
        fake_bw,
        {"env/groups/private": {"id": "p", **_item("A=1")}},
    )
    (home / ".env").write_text("A=1\nMINE=x\n")
    assert machine.cmd_env_pull() == 0
    capsys.readouterr()

    monkeypatch.setattr(
        machine_system(), "prompt_yes_no", lambda *a, **k: pytest.fail("prompted")
    )
    assert machine.cmd_attention() == 0
    assert (
        "[env] local-only env content: ~/.env: MINE not in Bitwarden "
        "env/groups/private or ~/.env.local"
    ) in capsys.readouterr().out

    _answer(monkeypatch, machine, "remove")
    monkeypatch.setattr(machine_system(), "prompt_yes_no", lambda *a, **k: True)
    monkeypatch.setattr(machine, "cmd_update", lambda args: 0)
    assert machine.cmd_attention() == 0
    assert "MINE" not in (home / ".env").read_text()
    assert not [i for i in machine.attention_items() if i.kind == "env"]


def test_env_pull_skips_container_profile(tmp_path, monkeypatch, fake_bw):
    items = {"env/groups/private": _item("A=1")}
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "container", items)

    assert machine.cmd_env_pull() == 0
    assert not (home / ".env").exists()


def test_item_to_dotenv_skips_empty_fields():
    machine_cls = _cli().Machine
    body = machine_cls.item_to_dotenv(
        None,
        {
            "notes": "A=1\r\nB=2\r\n",
            "fields": [
                {"name": "C", "value": "3"},
                {"name": "", "value": "x"},
                {"name": "D", "value": ""},
            ],
        },
    )
    assert body == textwrap.dedent(
        """\
        A=1
        B=2
        C=3"""
    )


# --- event log ----------------------------------------------------------------


def _events(machine) -> list[dict]:
    path = machine.state_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_auto_update_logs_applied_and_nothing_when_up_to_date(update_env):
    machine, _repo, other, _home, _calls = update_env

    assert _auto(machine) == 0
    assert _events(machine) == []  # nothing new, nothing logged

    _push_change(other, "home/dot_new", "x\n")
    assert _auto(machine) == 0
    (event,) = _events(machine)
    assert (event["event"], event["outcome"]) == ("update-auto", "applied")


def test_auto_update_logs_revert_with_reason(update_env, monkeypatch):
    machine, _repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    monkeypatch.setattr(machine, "zsh_health_failure", lambda: "zsh failed to start")

    assert _auto(machine) == 0
    (event,) = _events(machine)
    assert event["outcome"] == "reverted" and event["reason"] == "zsh-unhealthy"


def test_manual_update_logs_force(update_env):
    machine, _repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")

    assert _update(machine, force=True) == 0
    (event,) = _events(machine)
    assert (event["event"], event["outcome"], event["reason"]) == (
        "update",
        "applied",
        "force",
    )


def test_update_warns_when_the_host_is_not_set_up(update_env, monkeypatch, capsys):
    machine, *_rest, calls = update_env
    monkeypatch.setattr(machine, "mise_local_config", machine.repo / "missing.toml")

    assert _update(machine) == 0
    assert "dotfiles" not in calls
    assert "bootstrap" in capsys.readouterr().out
    assert machine.read_update_state()["state"] == "attention"


def test_user_bin_is_added_to_path_without_a_login_shell(tmp_path, monkeypatch):
    system = machine_system()
    user_bin = tmp_path / ".local/bin"
    user_bin.mkdir(parents=True)
    (user_bin / "mise").write_text("#!/bin/sh\n")
    (user_bin / "mise").chmod(0o755)
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert not system.have("mise")

    system.ensure_user_bin_on_path(tmp_path)
    system.ensure_user_bin_on_path(tmp_path)
    assert os.environ["PATH"] == f"{user_bin}:/usr/bin:/bin"
    assert system.have("mise")


def test_cli_puts_user_bin_on_path_before_running_a_command():
    entry = (REPO / "machine_cli/machine").read_text()
    _head, main = entry.split('if __name__ == "__main__":')
    assert main.index("ensure_user_bin_on_path") < main.index("app(")


@pytest.mark.parametrize("answer, ran", [("", True), ("n", False)], ids=["yes", "no"])
def test_update_offers_bootstrap_in_a_terminal(update_env, monkeypatch, answer, ran):
    machine, *_rest, _calls = update_env
    cli = _cli()
    monkeypatch.setattr(machine, "mise_local_config", machine.repo / "missing.toml")
    monkeypatch.setattr(cli.system, "is_tty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)
    runs = []
    real_run = cli.system.run

    def fake_run(args, **kwargs):
        if str(args[0]).endswith("/bootstrap"):
            runs.append(list(args))
            return None
        return real_run(args, **kwargs)

    monkeypatch.setattr(cli.system, "run", fake_run)

    _update(machine)

    assert (runs == [[str(machine.repo / "bootstrap")]]) is ran


FEATURE_TABLE = """\
feature_table:
  gnome:
    help: {help}
    groups: {groups}
    server: {server}
"""


def _push_feature_table(other: Path, help="GNOME", groups="[]", server="excluded"):
    _push_change(
        other,
        "ansible/group_vars/all/features.yml",
        FEATURE_TABLE.format(help=help, groups=groups, server=server),
    )


def test_feature_table_change_for_the_cli_only_needs_no_system_step(update_env):
    machine, repo, other, _home, calls = update_env
    _push_feature_table(other)
    assert _update(machine) == 0 and calls[-1] == "apply"
    machine.record_ansible_applied()
    calls.clear()

    _push_feature_table(other, help="GNOME and extensions", groups="[gnome]")
    assert "system" not in machine.update_plan(fetch=True)["steps"]
    assert _update(machine) == 0
    assert "apply" not in calls


def test_feature_table_change_for_ansible_needs_the_system_step(update_env):
    machine, repo, other, _home, calls = update_env
    _push_feature_table(other)
    assert _update(machine) == 0
    machine.record_ansible_applied()

    _push_feature_table(other, server="optional")
    assert "system" in machine.update_plan(fetch=True)["steps"]


def test_auto_update_applies_a_cli_only_feature_table_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_feature_table(other)
    assert _update(machine) == 0
    machine.record_ansible_applied()

    _push_feature_table(other, help="new help")
    assert _auto(machine) == 0
    assert machine.read_update_state()["state"] == "updated"


def test_update_logs_the_number_of_kept_local_changes(update_env, capsys):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "wip-a.txt").write_text("a\n")
    (repo / "wip-b.txt").write_text("b\n")

    assert _update(machine) == 0
    out = capsys.readouterr().out
    assert "keeping 2 local changes (machine status -v lists them)" in out
    assert "wip-a.txt" not in out


def test_write_dotfile_groups_reports_a_changed_list(update_env, monkeypatch):
    machine, *_ = update_env
    machine.write_dotfile_groups()
    assert machine.write_dotfile_groups() is False
    monkeypatch.setattr(machine, "host_dotfile_groups", lambda: ["core", "gnome"])
    assert machine.write_dotfile_groups() is True
    assert "gnome" in machine.mise_local_config.read_text()


def test_fetching_records_the_time_of_the_check(update_env, monkeypatch, tmp_path):
    machine, *_ = update_env
    stamp = tmp_path / "last-check"
    monkeypatch.setattr(machine, "update_last_check", stamp)

    machine.update_plan(fetch=False)
    assert not stamp.exists()
    machine.update_plan(fetch=True)
    assert stamp.read_text().startswith("20")


def test_status_shows_a_low_disk(update_env, capsys, tmp_path, monkeypatch):
    machine, *_ = update_env
    assert machine.cmd_status() == 0
    assert "free space: machine attention" not in capsys.readouterr().out

    info = tmp_path / "mountinfo"
    info.write_text(
        "20 1 253:1 / /mnt/data rw,relatime shared:1 - ext4 /dev/vdb rw\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MACHINE_MOUNTINFO", str(info))
    gib = 1024**3
    stat = os.statvfs_result(
        (
            4096,
            4096,
            500 * gib // 4096,
            12 * gib // 4096,
            12 * gib // 4096,
            0,
            0,
            0,
            0,
            255,
        )
    )
    monkeypatch.setattr(type(machine), "statvfs", staticmethod(lambda _p: stat))
    assert machine.cmd_status() == 0
    out = capsys.readouterr().out
    assert "⚠ /mnt/data 98% full → free space: machine attention" in out
    assert "\x1b[" not in out
