"""open-in-editor: work root, editor from `editor.open`, files and OpenSpec changes."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from package_sets import REPO

SCRIPT = REPO / "home/editor-command/.local/bin/open-in-editor"


@pytest.fixture
def env(tmp_path: Path) -> dict:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("code", "cursor"):
        stub = bin_dir / name
        # One line per argument; the marker line comes last, so a complete log
        # can be told from one that is still being written.
        stub.write_text(
            "#!/bin/sh\n"
            f'log="{tmp_path}/{name}.log"\n'
            'for a in "$@"; do echo "$a"; done >"$log.tmp"\n'
            'echo "#end" >>"$log.tmp"\n'
            'mv "$log.tmp" "$log"\n'
            'if [ -n "$STUB_SLEEP" ]; then sleep "$STUB_SLEEP"; fi\n'
        )
        stub.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    global_config = tmp_path / "gitconfig"
    global_config.write_text("")
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(global_config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }


def git(cwd: Path, env: dict, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def make_repo(path: Path, env: dict, branch: str = "main") -> Path:
    path.mkdir(parents=True)
    git(path, env, "init", "-q", "-b", branch)
    (path / "README.md").write_text("x\n")
    git(path, env, "add", "README.md")
    git(path, env, "commit", "-q", "-m", "init")
    return path


def make_change(repo: Path, name: str, *files: str) -> Path:
    change = repo / "openspec" / "changes" / name
    for rel in files:
        (change / rel).parent.mkdir(parents=True, exist_ok=True)
        (change / rel).write_text(rel)
    change.mkdir(parents=True, exist_ok=True)
    return change


def run(cwd: Path, env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def opened(tmp_path: Path, editor: str = "code") -> list[str]:
    log = tmp_path / f"{editor}.log"
    for _ in range(100):
        if log.is_file():
            lines = log.read_text().splitlines()
            assert lines[-1] == "#end"
            return lines[:-1]
        time.sleep(0.05)
    raise AssertionError(f"{editor} was not started")


def not_started(tmp_path: Path) -> bool:
    time.sleep(0.3)
    return not any(tmp_path.glob("*.log"))


# Work root


def test_opens_top_level_of_main_checkout(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    (repo / "sub").mkdir()
    result = run(repo / "sub", env)
    assert result.returncode == 0, result.stderr
    assert opened(tmp_path) == [str(repo)]


def test_opens_top_level_of_linked_worktree(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    worktree = repo / ".worktrees" / "x"
    git(repo, env, "worktree", "add", "-q", str(worktree), "-b", "x")
    (worktree / "deep").mkdir()
    assert run(worktree / "deep", env).returncode == 0
    assert opened(tmp_path) == [str(worktree)]


def test_outside_git_opens_current_directory(tmp_path, env):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert run(plain, env).returncode == 0
    assert opened(tmp_path) == [str(plain)]


def test_returns_while_editor_still_runs(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    start = time.monotonic()
    result = run(repo, {**env, "STUB_SLEEP": "5"})
    assert result.returncode == 0
    assert time.monotonic() - start < 3
    assert opened(tmp_path) == [str(repo)]


# Editor choice


def test_default_editor_is_code(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    run(repo, env)
    assert opened(tmp_path, "code") == [str(repo)]


def test_global_value(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    git(repo, env, "config", "--global", "editor.open", "cursor")
    run(repo, env)
    assert opened(tmp_path, "cursor") == [str(repo)]


def test_repository_value_wins_over_global(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    git(repo, env, "config", "--global", "editor.open", "code")
    git(repo, env, "config", "editor.open", "cursor")
    run(repo, env)
    assert opened(tmp_path, "cursor") == [str(repo)]
    assert not (tmp_path / "code.log").exists()


def test_linked_worktree_uses_repository_value(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    git(repo, env, "config", "editor.open", "cursor")
    worktree = repo / ".worktrees" / "x"
    git(repo, env, "worktree", "add", "-q", str(worktree), "-b", "x")
    run(worktree, env)
    assert opened(tmp_path, "cursor") == [str(worktree)]


def test_value_with_argument(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    git(repo, env, "config", "editor.open", "code --new-window")
    run(repo, env)
    assert opened(tmp_path) == ["--new-window", str(repo)]


def test_missing_editor_is_reported(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    git(repo, env, "config", "editor.open", "zed-not-installed")
    result = run(repo, env)
    assert result.returncode != 0
    assert "zed-not-installed" in result.stderr
    assert "editor.open" in result.stderr
    assert not_started(tmp_path)


# Files


def test_files_relative_and_absolute(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    (repo / "docs").mkdir()
    (repo / "docs" / "a.md").write_text("a")
    other = tmp_path / "b.txt"
    other.write_text("b")
    result = run(repo / "docs", env, "a.md", str(other))
    assert result.returncode == 0, result.stderr
    assert opened(tmp_path) == [str(repo), str(repo / "docs" / "a.md"), str(other)]


def test_missing_file_is_reported_and_left_out(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    result = run(repo, env, "README.md", "nope.md")
    assert result.returncode != 0
    assert "nope.md" in result.stderr
    assert opened(tmp_path) == [str(repo), str(repo / "README.md")]


def test_file_named_like_an_option_after_double_dash(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    (repo / "--change").write_text("x")
    assert run(repo, env, "--", "--change").returncode == 0
    assert opened(tmp_path) == [str(repo), str(repo / "--change")]


# OpenSpec changes


def test_named_change_opens_planning_files_then_specs(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    change = make_change(
        repo, "foo", "tasks.md", "proposal.md", "specs/b/spec.md", "specs/a/spec.md"
    )
    result = run(repo, env, "--change", "foo")
    assert result.returncode == 0, result.stderr
    assert opened(tmp_path) == [
        str(repo),
        str(change / "proposal.md"),
        str(change / "tasks.md"),
        str(change / "specs/a/spec.md"),
        str(change / "specs/b/spec.md"),
    ]


def test_unknown_change_lists_active_changes(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    make_change(repo, "foo", "proposal.md")
    result = run(repo, env, "--change", "bar")
    assert result.returncode not in (0, 2)
    assert "foo" in result.stdout + result.stderr
    assert not_started(tmp_path)


def test_change_named_like_branch(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env, branch="foo")
    make_change(repo, "other", "proposal.md")
    change = make_change(repo, "foo", "proposal.md", "design.md", "tasks.md")
    assert run(repo, env, "--change").returncode == 0
    assert opened(tmp_path) == [
        str(repo),
        str(change / "proposal.md"),
        str(change / "design.md"),
        str(change / "tasks.md"),
    ]


def test_only_active_change_archive_does_not_count(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    make_change(repo, "archive/2026-01-01-old", "proposal.md")
    change = make_change(repo, "foo", "tasks.md")
    assert run(repo, env, "--change").returncode == 0
    assert opened(tmp_path) == [str(repo), str(change / "tasks.md")]


def test_several_changes_without_match(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    make_change(repo, "foo", "proposal.md")
    make_change(repo, "bar", "proposal.md")
    result = run(repo, env, "--change")
    assert result.returncode == 2
    assert result.stdout.split() == ["bar", "foo"]
    assert not_started(tmp_path)


def test_change_with_files(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    change = make_change(repo, "foo", "proposal.md")
    assert run(repo, env, "--change", "foo", "README.md").returncode == 0
    assert opened(tmp_path) == [
        str(repo),
        str(repo / "README.md"),
        str(change / "proposal.md"),
    ]


def test_script_is_executable():
    assert os.access(SCRIPT, os.X_OK)


def test_no_change_at_all(tmp_path, env):
    repo = make_repo(tmp_path / "repo", env)
    result = run(repo, env, "--change")
    assert result.returncode == 2
    assert result.stdout == ""
    assert not_started(tmp_path)
