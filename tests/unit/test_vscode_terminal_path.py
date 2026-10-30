"""PATH rewrite for VS Code's Copilot CLI wrapper on hosts with a symlinked home."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENVIRONMENT = REPO / "home/core/.shell/common/environment.sh"
SUFFIX = ".vscode-server/data/User/globalStorage/github.copilot-chat/copilotCli"
SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]


def _home(tmp_path: Path) -> tuple[Path, Path]:
    """`home` is a symlink to `real/home`, like /home/u -> /mnt/data/home/u."""
    real = tmp_path / "real/home"
    wrapper = real / SUFFIX
    wrapper.mkdir(parents=True)
    # Never executed: it would mean the wrapper was found again.
    (wrapper / "copilot").write_text("#!/bin/sh\nexit 99\n")
    (wrapper / "copilot").chmod(0o755)
    home = tmp_path / "home"
    home.symlink_to(real)
    return home, real


def _load(shell: str, home: Path, path: str, times: int = 1) -> str:
    script = '. "$1"; ' * times + 'printf "%s" "$PATH"'
    result = subprocess.run(
        [shell, "-c", script, "_", str(ENVIRONMENT)],
        env={"HOME": str(home), "PATH": path},
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _system_path() -> str:
    return os.pathsep.join(
        dict.fromkeys(str(Path(shutil.which(s)).parent) for s in SHELLS)
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_wrapper_entry_becomes_canonical_in_place(tmp_path, shell):
    home, real = _home(tmp_path)
    other = home / "bin"
    path = f"{other}:{home / SUFFIX}:{_system_path()}"
    entries = _load(shell, home, path).split(":")
    assert entries[0] == str(other)
    assert entries[1] == str(real / SUFFIX)
    assert entries[2:-1] == _system_path().split(":")
    assert entries[-1] == f"{home}/.local/bin"


@pytest.mark.parametrize("shell", SHELLS)
def test_second_load_is_a_no_op(tmp_path, shell):
    home, real = _home(tmp_path)
    path = f"{home / SUFFIX}:{_system_path()}"
    once = _load(shell, home, path)
    # Only ~/.local/bin is appended again; the wrapper entry stays as it is.
    assert _load(shell, home, once) == f"{once}:{home}/.local/bin"
    twice = _load(shell, home, path, times=2).split(":")
    assert twice[0] == str(real / SUFFIX)


@pytest.mark.parametrize("shell", SHELLS)
def test_canonical_and_missing_entries_are_untouched(tmp_path, shell):
    home, real = _home(tmp_path)
    missing = home / "gone/github.copilot-chat/copilotCli"
    path = f"{real / SUFFIX}::{missing}:{_system_path()}"
    assert _load(shell, home, path) == f"{path}:{home}/.local/bin"


@pytest.mark.parametrize("shell", SHELLS)
def test_shim_filter_then_finds_the_real_cli(tmp_path, shell):
    home, real = _home(tmp_path)
    cli = tmp_path / "mise/bin"
    cli.mkdir(parents=True)
    (cli / "copilot").write_text("#!/bin/sh\n")
    (cli / "copilot").chmod(0o755)
    path = _load(shell, home, f"{home / SUFFIX}:{cli}:{_system_path()}")
    # copilotCLIShim.js: PATH.replaceAll(`${__dirname}:`, "").replaceAll(`:${__dirname}`, "")
    dirname = str(real / SUFFIX)
    filtered = path.replace(f"{dirname}:", "").replace(f":{dirname}", "")
    found = subprocess.run(
        [shell, "-c", "command -v copilot"],
        env={"HOME": str(home), "PATH": filtered},
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert found == str(cli / "copilot")


def test_without_the_rewrite_the_shim_filter_misses(tmp_path):
    """Documents the bug the rewrite prevents."""
    home, real = _home(tmp_path)
    path = f"{home / SUFFIX}:{_system_path()}"
    dirname = str(real / SUFFIX)
    assert path.replace(f"{dirname}:", "").replace(f":{dirname}", "") == path
