from __future__ import annotations

import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

CONFIG = REPO / "home/prompt/.config/starship.toml"
USER = pwd.getpwuid(os.getuid()).pw_name
ANSI = re.compile(r"\x1b\[[0-9;]*m|%\{|%\}|\\\[|\\\]")


def prompt_lines(shell: str, cwd: Path, **extra: str) -> list[str]:
    starship = shutil.which("starship")
    if not starship:
        pytest.skip("Starship is not installed")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SSH_", "STARSHIP_", "VIRTUAL_ENV"))
    }
    env.update(STARSHIP_CONFIG=str(CONFIG), STARSHIP_SHELL=shell, PWD=str(cwd), **extra)
    result = subprocess.run(
        [starship, "prompt", "--status=0"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stderr == ""
    return [ANSI.sub("", line) for line in result.stdout.splitlines()]


def first_line(shell: str, cwd: Path, **extra: str) -> str:
    return prompt_lines(shell, cwd, **extra)[0]


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_ssh_session_shows_user_at_host(shell, tmp_path):
    lines = prompt_lines(shell, tmp_path, SSH_CONNECTION="10.0.0.1 50000 10.0.0.2 22")
    assert re.search(rf"{re.escape(USER)}@\S+ \d{{2}}:\d{{2}}:\d{{2}}", lines[0])
    assert lines[-1].startswith("💻 ssh ")


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_local_session_hides_user_and_host(shell, tmp_path):
    lines = prompt_lines(shell, tmp_path)
    assert f"{USER}@" not in lines[0]
    assert "@" not in lines[0]
    assert "💻" not in "".join(lines)


def test_python_segment_only_with_active_virtualenv(tmp_path):
    (tmp_path / "main.py").write_text("")
    assert "🐍" not in first_line("bash", tmp_path)
    venv = tmp_path / "myenv"
    venv.mkdir()
    assert "🐍 (myenv)" in first_line("bash", tmp_path, VIRTUAL_ENV=str(venv))


def test_git_segment_shows_branch_icon_and_change_counts(tmp_path):
    git = shutil.which("git")
    if not git:
        pytest.skip("git is not installed")
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *args: subprocess.run(  # noqa: E731
        [git, "-C", str(repo), *args], check=True, capture_output=True
    )
    run("init", "-q", "-b", "main")
    (repo / "a").write_text("1")
    run("add", "a")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "a")
    assert "\uf126 main" in first_line("bash", repo)
    (repo / "a").write_text("2")
    (repo / "b").write_text("new")
    line = first_line("bash", repo)
    assert "!1" in line and "?1" in line
