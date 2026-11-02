from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

ALIASES = REPO / "home/core/.shell/common/aliases.sh"
SHELLS = [shell for shell in ("bash", "zsh") if shutil.which(shell)]


def _checkout(path: Path) -> Path:
    (path / ".git").mkdir(parents=True)
    (path / "home").mkdir()
    (path / "machine_cli").mkdir()
    (path / "machine_cli/machine").write_text("#!/bin/sh\n")
    return path


def _link(home: Path, target: Path) -> None:
    link = home / ".local/bin/machine"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def _repo_after_sourcing(
    shell: str, home: Path, **env: str
) -> subprocess.CompletedProcess:
    base = {k: v for k, v in os.environ.items() if k != "DOTFILES_REPO"}
    return subprocess.run(
        [shell, "-c", f'. "{ALIASES}"; printf "%s" "$DOTFILES_REPO"'],
        env={**base, "HOME": str(home), **env},
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_default_follows_the_machine_link_over_a_stale_clone(tmp_path, shell):
    home = tmp_path / "home"
    live = _checkout(tmp_path / "src/dotfiles")
    _checkout(home / "dotfiles")
    _link(home, live / "machine_cli/machine")

    result = _repo_after_sourcing(shell, home)

    assert result.stderr == ""
    assert result.stdout == str(live)


@pytest.mark.parametrize("shell", SHELLS)
def test_explicit_value_is_kept(tmp_path, shell):
    home = tmp_path / "home"
    live = _checkout(tmp_path / "src/dotfiles")
    _link(home, live / "machine_cli/machine")

    result = _repo_after_sourcing(shell, home, DOTFILES_REPO="/elsewhere")

    assert result.stdout == "/elsewhere"


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("case", ["no-link", "dangling", "not-a-checkout"])
def test_falls_back_to_home_dotfiles(tmp_path, shell, case):
    home = tmp_path / "home"
    home.mkdir()
    if case == "dangling":
        _link(home, tmp_path / "gone/machine_cli/machine")
    elif case == "not-a-checkout":
        target = tmp_path / "plain/machine_cli/machine"
        target.parent.mkdir(parents=True)
        target.write_text("")
        _link(home, target)

    result = _repo_after_sourcing(shell, home)

    assert result.stderr == ""
    assert result.stdout == f"{home}/dotfiles"
