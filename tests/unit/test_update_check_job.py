"""The update-check job without the machine CLI: fetch and the one state file."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

JOB = REPO / "home/core/.local/bin/dotfiles-update-check-job"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def job_env(tmp_path: Path, monkeypatch):
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "test@example.com")
    origin, repo, other = (tmp_path / n for n in ("origin.git", "repo", "other"))
    _git("init", "-q", "--bare", "-b", "main", str(origin), cwd=tmp_path)
    _git("clone", "-q", str(origin), str(other), cwd=tmp_path)
    (other / "a").write_text("1\n")
    _git("add", "-A", cwd=other)
    _git("commit", "-q", "-m", "seed", cwd=other)
    _git("push", "-q", "origin", "HEAD:main", cwd=other)
    _git("clone", "-q", str(origin), str(repo), cwd=tmp_path)

    # a PATH without `machine`, so the job takes the fallback path
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("git", "bash", "date", "rm", "mv", "printf", "readlink"):
        tools.joinpath(name).symlink_to(shutil.which(name))
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": str(tools),
        "HOME": str(home),
        "DOTFILES_REPO": str(repo),
        "DOTFILES_UPDATE_STATE": str(tmp_path / "state"),
        "DOTFILES_UPDATE_LAST_CHECK": str(tmp_path / "last"),
        "GIT_TERMINAL_PROMPT": "0",
    }

    def run(**overrides: str | None) -> subprocess.CompletedProcess:
        merged = {**env, **overrides}
        return subprocess.run(
            [str(tools / "bash"), str(JOB)],
            env={k: v for k, v in merged.items() if v is not None},
            capture_output=True,
            text=True,
        )

    def push() -> None:
        (other / "a").write_text("2\n")
        _git("commit", "-qam", "change", cwd=other)
        _git("push", "-q", "origin", "HEAD:main", cwd=other)

    return run, push, origin, tmp_path / "state"


def test_job_uses_the_linked_checkout_outside_home_dotfiles(job_env, tmp_path):
    run, _push, _origin, _state = job_env
    live = tmp_path / "src/dotfiles"
    (live / "home").mkdir(parents=True)
    (live / ".git").write_text("gitdir: elsewhere\n")  # a linked worktree
    (live / "machine_cli").mkdir()
    calls = tmp_path / "calls"
    stub = live / "machine_cli/machine"
    stub.write_text(f'#!{shutil.which("bash")}\nprintf "%s\\n" "$*" > "{calls}"\n')
    stub.chmod(0o755)
    link = tmp_path / "home/.local/bin/machine"
    link.parent.mkdir(parents=True)
    link.symlink_to(stub)

    result = run(DOTFILES_REPO=None)

    assert result.returncode == 0, result.stderr
    assert calls.read_text() == "update --auto\n"


def test_job_falls_back_to_home_dotfiles_without_the_link(job_env, tmp_path):
    run, push, _origin, state = job_env
    (tmp_path / "repo").rename(tmp_path / "home/dotfiles")
    push()

    assert run(DOTFILES_REPO=None).returncode == 0
    assert "state=available" in state.read_text()


def test_job_marks_pending_update_and_clears_it(job_env):
    run, push, _origin, state = job_env
    assert run().returncode == 0
    assert "state=none" in state.read_text()
    assert "pending=1" not in state.read_text()

    push()
    assert run().returncode == 0
    assert "state=available" in state.read_text()
    assert "pending=1" in state.read_text()


def test_job_keeps_pending_flag_when_fetch_fails(job_env):
    run, push, origin, state = job_env
    push()
    assert run().returncode == 0
    assert "pending=1" in state.read_text()

    origin.rename(origin.with_name("gone.git"))  # offline: the remote is unreachable
    assert run().returncode == 0
    assert "pending=1" in state.read_text()
    assert "state=available" in state.read_text()


def test_job_keeps_failed_revision_and_applied_revision(job_env):
    run, push, _origin, state = job_env
    state.write_text("state=none\nfailed_revision=abc\nansible_applied_rev=def\n")
    push()
    assert run().returncode == 0
    text = state.read_text()
    assert "failed_revision=abc" in text and "ansible_applied_rev=def" in text
