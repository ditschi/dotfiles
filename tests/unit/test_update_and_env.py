from __future__ import annotations

import argparse
import json
import os
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
    monkeypatch.setattr(cli, "hostname_short", lambda: "testhost")
    machine = cli.Machine()
    # never let a broken fixture fall back to the real checkout (it would git pull)
    assert machine.repo == repo
    machine.sync_host_profile_from_repo()  # host already in sync before update

    calls: list[str] = []
    monkeypatch.setattr(machine, "run_chezmoi_apply", lambda: calls.append("chezmoi"))
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


def test_update_refuses_dirty_tree(update_env, capsys):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "local-edit.txt").write_text("wip\n")

    with pytest.raises(SystemExit):
        _update(machine)
    assert "uncommitted changes" in capsys.readouterr().err
    assert not (repo / "home/dot_new").exists()
    assert calls == []


def test_update_force_pulls_despite_dirty_tree(update_env):
    machine, repo, other, _home, _calls = update_env
    _push_change(other, "home/dot_new", "x\n")
    (repo / "local-edit.txt").write_text("wip\n")

    assert _update(machine, force=True) == 0
    assert (repo / "home/dot_new").is_file()
    assert (repo / "local-edit.txt").read_text() == "wip\n"


def test_update_stops_on_diverged_history(update_env):
    machine, repo, other, _home, calls = update_env
    _push_change(other, "home/dot_remote", "r\n")
    (repo / "home/dot_local").write_text("l\n")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "local", cwd=repo)

    with pytest.raises(subprocess.CalledProcessError):
        _update(machine)
    assert calls == []


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
    monkeypatch.setattr(cli, "hostname_short", lambda: "testhost")
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


def test_env_pull_layers_class_profile_host_and_fields(tmp_path, monkeypatch, fake_bw):
    items = {
        "env/home-shared": _item("SHARED=1\nLAYER=shared\nFIELD_WINS=from-notes"),
        "env/profiles/home-laptop": _item("LAYER=profile"),
        "env/hosts/testhost": _item("LAYER=host", FIELD_WINS="from-field"),
        # must never be read by a home host
        "env/work-shared": _item("WORK_ONLY=leak"),
    }
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-laptop", items)

    assert machine.cmd_env_pull() == 0
    env_file = home / ".env"
    values = _sourced(env_file)
    assert values["SHARED"] == "1"
    assert values["LAYER"] == "host"
    assert values["FIELD_WINS"] == "from-field"
    assert "WORK_ONLY" not in values
    assert oct(env_file.stat().st_mode & 0o777) == "0o600"


def test_env_pull_work_laptop_reads_work_items_only(tmp_path, monkeypatch, fake_bw):
    items = {
        "env/work-shared": _item("CLASS=work"),
        "env/home-shared": _item("CLASS=home"),
    }
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "work-laptop", items)

    assert machine.cmd_env_pull() == 0
    assert _sourced(home / ".env")["CLASS"] == "work"


def test_env_pull_backs_up_hand_written_env_once(tmp_path, monkeypatch, fake_bw):
    items = {"env/home-shared": _item("A=1")}
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-laptop", items)
    (home / ".env").write_text("HANDMADE=1\n")

    assert machine.cmd_env_pull() == 0
    backups = list((machine.state_dir / "env-backup").iterdir())
    assert len(backups) == 1 and backups[0].read_text() == "HANDMADE=1\n"

    # a generated file is not backed up again
    assert machine.cmd_env_pull() == 0
    assert len(list((machine.state_dir / "env-backup").iterdir())) == 1


def test_env_pull_leaves_env_untouched_without_items(tmp_path, monkeypatch, fake_bw):
    machine, home = _env_machine(tmp_path, monkeypatch, fake_bw, "home-laptop", {})
    (home / ".env").write_text("KEEP=1\n")

    assert machine.cmd_env_pull() == 0
    assert (home / ".env").read_text() == "KEEP=1\n"


def test_env_pull_skips_container_profile(tmp_path, monkeypatch, fake_bw):
    items = {"env/home-shared": _item("A=1")}
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
