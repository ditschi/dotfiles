"""The CLI's only door to the outside world (processes, tty, hostname).

Call these as `system.<name>(...)` so tests can replace them in one place."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from .core import (
    die,
)


def in_docker() -> bool:
    return Path("/.dockerenv").is_file() or os.environ.get("MACHINE_IN_DOCKER") == "1"


def have(name: str) -> bool:
    return shutil.which(name) is not None


def ansible_works() -> bool:
    """True when ansible-playbook exists and its interpreter can still import ansible."""
    if not have("ansible-playbook"):
        return False
    return (
        subprocess.run(
            ["ansible-playbook", "--version"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def is_tty() -> bool:
    return sys.stdin.isatty()


def run(
    args: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = False,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def detect_repo() -> Path:
    env = os.environ.get("DOTFILES_REPO")
    if env:
        candidate = Path(env).expanduser()
        if (candidate / ".git").exists() and (candidate / "home").is_dir():
            return candidate
        print(
            f"machine: DOTFILES_REPO={env} is not a dotfiles checkout; searching elsewhere",
            file=sys.stderr,
        )
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / ".git").exists() and (parent / "home").is_dir():
            return parent
    fallback = Path.home() / "dotfiles"
    if (fallback / ".git").exists() and (fallback / "home").is_dir():
        return fallback
    die("cannot find dotfiles repository")
    raise AssertionError


def hostname_short() -> str:
    return socket.gethostname().split(".")[0]


def prompt_yes_no(question: str, default: bool = False) -> bool:
    if not is_tty():
        return default
    hint = "Y/n" if default else "y/N"
    answer = input(f"{question} [{hint}]: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}
