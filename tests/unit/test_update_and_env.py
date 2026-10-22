from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import textwrap
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from package_sets import REPO

MACHINE = REPO / "home/dot_local/bin/executable_machine"

HOST_YAML = """\
---
profile: {profile}
features:
  - zsh-full
ssh_allow_from: []
"""


def _cli():
    return SourceFileLoader("machine_cli_update", str(MACHINE)).load_module()


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
        "MACHINE_PROFILE_FILE", str(home / ".config/machine/profile.yml")
    )
    monkeypatch.setenv("CHEZMOI_CONFIG", str(home / ".config/chezmoi/chezmoi.yaml"))
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
        HOST_YAML.format(profile="home-laptop")
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
    machine.sync_host_profile_from_repo()  # host already in sync before update

    calls: list[str] = []
    monkeypatch.setattr(machine, "run_chezmoi_apply", lambda: calls.append("chezmoi"))
    original_have = cli.system.have
    monkeypatch.setattr(
        cli.system, "have", lambda name: name == "chezmoi" or original_have(name)
    )
    monkeypatch.setattr(machine, "cmd_env_pull", lambda: calls.append("env") or 0)
    monkeypatch.setattr(machine, "cmd_apply", lambda _args: calls.append("apply") or 0)
    return machine, repo, other, home, calls


def _push_change(other: Path, path: str, content: str) -> None:
    target = other / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _git("add", "-A", cwd=other)
    _git("commit", "-q", "-m", f"change {path}", cwd=other)
    _git("push", "-q", "origin", "HEAD:main", cwd=other)


def _update(machine, *, force=False, system=False) -> int:
    return machine.cmd_update(argparse.Namespace(force=force, system=system))


def test_update_pulls_and_skips_apply_when_profile_unchanged(update_env):
    machine, repo, other, home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    marker = home / ".dotfiles-update-available"
    marker.write_text("")

    assert _update(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert "env" in calls and "apply" not in calls
    assert not marker.exists()


def test_update_applies_when_host_profile_changed_upstream(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(
        other, "machine/hosts/testhost.yml", HOST_YAML.format(profile="home-server")
    )

    assert _update(machine) == 0
    assert "profile: home-server" in machine.profile_path.read_text()
    # new chezmoi config from the synced profile is applied before ansible
    assert calls == ["chezmoi", "env", "apply"]


def test_update_system_flag_applies_without_profile_change(update_env):
    machine, _repo, _other, _home, calls = update_env
    assert _update(machine, system=True) == 0
    assert calls[-1] == "apply"


def test_update_stops_when_local_change_overlaps_incoming(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_placeholder", "remote\n")
    (repo / "home/dot_placeholder").write_text("local\n")

    with pytest.raises(SystemExit):
        _update(machine)
    assert "manual attention needed" in capsys.readouterr().err
    assert (repo / "home/dot_placeholder").read_text() == "local\n"
    assert calls == []


def test_update_keeps_unrelated_local_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "local-edit.txt").write_text("wip\n")

    assert _update(machine) == 0
    assert (repo / "home/dot_new").is_file()
    assert (repo / "local-edit.txt").read_text() == "wip\n"


def test_update_force_stashes_and_restores_overlapping_change(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_placeholder", "remote\n")
    (repo / "home/dot_placeholder").write_text("local\n")

    with pytest.raises(SystemExit):
        _update(machine, force=True)  # the stash pop conflicts: local work is kept
    assert _git("stash", "list", cwd=repo).strip()


def test_update_stops_on_diverged_history(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    (repo / "home/dot_local").write_text("l\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "local", cwd=repo)

    with pytest.raises(SystemExit):
        _update(machine)
    assert "diverged" in capsys.readouterr().err
    assert calls == []


def test_update_content_change_skips_chezmoi_and_apply(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "home/dot_placeholder", "changed\n")

    assert _update(machine) == 0
    assert calls == ["env"]


def test_update_runs_system_step_when_ansible_changed(update_env):
    machine, _repo, other, _home, calls = update_env
    _push_change(other, "ansible/roles/x.yml", "x\n")

    assert _update(machine) == 0
    assert calls == ["env", "apply"]


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
    assert plan["steps"] == ["chezmoi", "shell"] and plan["blockers"] == []
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


def test_update_moves_bashrc_managed_block_to_local_file(update_env):
    machine, repo, other, home, _calls = update_env
    bashrc = repo / "home/dot_bashrc"
    bashrc.write_text("echo base\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "bashrc", cwd=repo)
    _git("push", "-q", "origin", "HEAD:main", cwd=repo)
    _git("pull", "-q", cwd=other)
    block = (
        "## <!-- BEGIN ANSIBLE MANAGED BLOCK - colors -->\n"
        "export X=1\n"
        "## <!-- END ANSIBLE MANAGED BLOCK - colors -->\n"
    )
    bashrc.write_text("echo base\n" + block)
    _push_change(other, "home/dot_new", "x\n")

    assert _update(machine) == 0
    assert bashrc.read_text() == "echo base\n"
    assert (home / ".bashrc-local").read_text() == block
    assert (repo / "home/dot_new").is_file()


def test_classify_incoming_paths():
    _cli()  # puts machine_cli on sys.path
    from machine_cli.local_changes import classify_paths as classify

    assert classify([("M", "home/dot_zshrc")]) == ["shell"]
    assert classify([("A", "home/dot_new")]) == ["chezmoi", "shell"]
    assert classify([("M", "home/.chezmoiignore")]) == ["chezmoi", "shell"]
    assert classify([("M", "home/dot_local/bin/executable_machine")]) == []
    assert classify([("M", "ansible/site.yml"), ("M", "machine/hosts/h.yml")]) == [
        "profile",
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
    machine.write_profile(profile, ["zsh-full"], [])
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


def _item(notes: str = "", **fields: str) -> dict:
    return {
        "notes": notes,
        "fields": [{"name": k, "value": v, "type": 1} for k, v in fields.items()],
    }


def test_env_pull_layers_groups_host_and_fields(tmp_path, monkeypatch, fake_bw):
    items = {
        "env/groups/private": _item("SHARED=1\nLAYER=shared\nFIELD_WINS=from-notes"),
        "env/groups/server": _item("LAYER=profile"),
        "env/hosts/testhost": _item("LAYER=host", FIELD_WINS="from-field"),
        # must never be read by a home host
        "env/groups/work": _item("WORK_ONLY=leak"),
    }
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-server", items)

    assert machine.cmd_env_pull() == 0
    env_file = home / ".env"
    values = _sourced(env_file)
    assert values["SHARED"] == "1"
    assert values["LAYER"] == "profile"
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
    assert (home / ".env.local").read_text() == "HANDMADE=1\n"

    # a generated file is not backed up again
    assert machine.cmd_env_pull() == 0
    assert len(list((machine.state_dir / "env-backup").iterdir())) == 1


def test_env_pull_warns_and_keeps_original_when_overlay_would_need_overwrite(
    tmp_path, monkeypatch, fake_bw, capsys
):
    machine, home = _env_machine(
        tmp_path,
        monkeypatch,
        fake_bw,
        "work-machine",
        {"env/groups/work": _item("A=updated")},
    )
    original = "A=old\nLOCAL_ONLY=preserve\n"
    (home / ".env").write_text(original)
    (home / ".env.local").write_text("OTHER=unchanged\n")
    with pytest.raises(SystemExit):
        machine.cmd_env_pull()
    assert (home / ".env").read_text() == original
    assert (home / ".env.local").read_text() == "OTHER=unchanged\n"
    output = capsys.readouterr().out
    assert "LOCAL_ONLY" in output and str(home / ".env.local") in output
    assert str(machine.state_dir / "env-backup") in output
    assert not (home / ".env.host").exists()


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
            str(REPO / "home/dot_zsh/config/01_env.zsh"),
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


def test_env_pull_keeps_both_files_with_complex_host_content(
    tmp_path, monkeypatch, fake_bw
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
    with pytest.raises(SystemExit):
        machine.cmd_env_pull()
    assert (home / ".env").read_text() == "A=old\n"
    assert (home / ".env.host").read_text() == "if true; then\nHOST=old\nfi\n"
    assert not (home / ".env.local").exists()


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
