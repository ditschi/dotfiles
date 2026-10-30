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


def first_line(shell: str, cwd: Path, **extra: str) -> str:
    starship = shutil.which("starship")
    if not starship:
        pytest.skip("Starship is not installed")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SSH_", "STARSHIP_"))
    }
    env.update(STARSHIP_CONFIG=str(CONFIG), STARSHIP_SHELL=shell, **extra)
    result = subprocess.run(
        [starship, "prompt", "--status=0"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stderr == ""
    return ANSI.sub("", result.stdout.splitlines()[0])


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_ssh_session_shows_user_at_host(shell, tmp_path):
    line = first_line(shell, tmp_path, SSH_CONNECTION="10.0.0.1 50000 10.0.0.2 22")
    assert re.search(rf"{re.escape(USER)}@\S+ \d{{2}}:\d{{2}}:\d{{2}}", line)


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_local_session_hides_user_and_host(shell, tmp_path):
    line = first_line(shell, tmp_path)
    assert f"{USER}@" not in line
    assert "@" not in line
