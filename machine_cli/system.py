"""The CLI's only door to the outside world (processes, tty, hostname).

Call these as `system.<name>(...)` so tests can replace them in one place."""

from __future__ import annotations

import os
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import click

from .core import (
    debug,
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
    interactive_stdout: bool = False,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """interactive_stdout: capture stdout only so prompts on stderr stay visible."""
    debug("$ " + shlex.join(str(arg) for arg in args))
    return subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        input=input_text,
        env=env,
        stdout=subprocess.PIPE if (capture or interactive_stdout) else None,
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
    return click.confirm(question, default=default)


def choose(title: str, choices: Sequence[str], default: str) -> str:
    """Pick one of `choices` by number or name; `default` when not on a terminal."""
    if not is_tty():
        return default
    for index, name in enumerate(choices, 1):
        click.echo(f"  {index}) {name}")
    value = click.prompt(
        title,
        default=default,
        show_default=True,
        type=click.Choice([*choices, *map(str, range(1, len(choices) + 1))]),
        show_choices=False,
    )
    return choices[int(value) - 1] if value.isdigit() else value


def choose_many(
    title: str, choices: Dict[str, str], selected: Sequence[str]
) -> List[str]:
    """Tick any of `choices` ({value: help text}) by number, comma separated.

    Enter keeps the pre-selection (marked `*`), `-` selects nothing."""
    if not is_tty():
        return list(selected)
    names = list(choices)
    for index, name in enumerate(names, 1):
        mark = "*" if name in selected else " "
        click.echo(f" {mark}{index}) {name:20} {choices[name]}")
    while True:
        answer = click.prompt(
            f"{title} (numbers, Enter keeps *, - for none)",
            default="",
            show_default=False,
        ).strip()
        if not answer:
            return list(selected)
        if answer == "-":
            return []
        try:
            return [names[int(part) - 1] for part in answer.split(",") if part.strip()]
        except (ValueError, IndexError):
            click.echo(f"enter numbers between 1 and {len(names)}")
