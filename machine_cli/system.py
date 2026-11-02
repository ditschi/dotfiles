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


def boots_graphical() -> bool:
    """True when systemd boots into the graphical target (a desktop)."""
    if not shutil.which("systemctl"):
        return False
    result = subprocess.run(
        ["systemctl", "get-default"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() == "graphical.target"


def have(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_user_bin_on_path(home: Path) -> None:
    """Prepend ~/.local/bin and the mise shims to PATH when missing.

    For `ssh host command` without a login shell; the shims make mise tools such as
    `bw` reachable as in `.zshenv` and `.profile`."""
    parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    wanted = [str(home / ".local/bin")]
    shims = home / ".local/share/mise/shims"
    if shims.is_dir():
        wanted.append(str(shims))
    missing = [path for path in wanted if path not in parts]
    if missing:
        os.environ["PATH"] = os.pathsep.join([*missing, *parts])


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


def _is_checkout(path: Path) -> bool:
    return (path / ".git").exists() and (path / "home").is_dir()


def linked_repo() -> tuple[Optional[Path], str]:
    """The live checkout, which ~/.local/bin/machine links into; else None and why."""
    link = Path.home() / ".local/bin/machine"
    if not link.is_symlink():
        reason = "is not a link" if link.exists() else "does not exist"
        return None, f"{link} {reason}; run bootstrap from the checkout"
    target = link.resolve()
    checkout = target.parent.parent
    if (
        target.parent.name != "machine_cli"
        or not target.is_file()
        or not _is_checkout(checkout)
    ):
        return None, f"{link} does not point into a dotfiles checkout ({target})"
    return checkout, ""


def detect_repo() -> Path:
    env = os.environ.get("DOTFILES_REPO")
    if env:
        candidate = Path(env).expanduser()
        if _is_checkout(candidate):
            return candidate
        print(
            f"machine: DOTFILES_REPO={env} is not a dotfiles checkout; searching elsewhere",
            file=sys.stderr,
        )
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if _is_checkout(parent):
            return parent
    linked, _reason = linked_repo()
    if linked is not None:
        return linked
    fallback = Path.home() / "dotfiles"
    if _is_checkout(fallback):
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


def _checklist(
    title: str, choices: Dict[str, str], selected: Sequence[str]
) -> Optional[List[str]]:
    """Arrow keys move, space toggles, Enter confirms; None when keys cannot be read."""
    names = list(choices)
    chosen = {name for name in names if name in selected}
    cursor = 0
    keys = {"\x1b[A": -1, "\x1b[B": 1, "k": -1, "j": 1}
    click.echo(f"{title} (up/down move, space toggles, a all, n none, Enter confirms)")
    first = True
    while True:
        if not first:
            click.echo(f"\x1b[{len(names)}A\x1b[J", nl=False)
        first = False
        for index, name in enumerate(names):
            pointer = ">" if index == cursor else " "
            mark = "x" if name in chosen else " "
            line = f" {pointer} [{mark}] {name:20} {choices[name]}".rstrip()
            click.echo(line[: shutil.get_terminal_size().columns - 1])
        try:
            key = click.getchar()
        except (OSError, EOFError):
            return None
        if key in ("\r", "\n"):
            return [name for name in names if name in chosen]
        if key in keys:
            cursor = (cursor + keys[key]) % len(names)
        elif key == " ":
            chosen ^= {names[cursor]}
        elif key == "a":
            chosen = set(names)
        elif key == "n":
            chosen = set()


def choose_many(
    title: str, choices: Dict[str, str], selected: Sequence[str]
) -> List[str]:
    """Pick entries of `choices` ({value: help text}); `selected` is preselected.

    Arrow keys + space where the terminal allows it. Otherwise the numbers switch
    entries on or off relative to the pre-selection (marked `*`), so adding one
    feature does not drop the others; Enter keeps the pre-selection, `-` selects
    nothing."""
    if not is_tty():
        return list(selected)
    if sys.stdout.isatty() and choices:
        result = _checklist(title, choices, selected)
        if result is not None:
            return result
    return _choose_many_by_number(title, choices, selected)


def _choose_many_by_number(
    title: str, choices: Dict[str, str], selected: Sequence[str]
) -> List[str]:
    names = list(choices)
    for index, name in enumerate(names, 1):
        mark = "*" if name in selected else " "
        click.echo(f" {mark}{index}) {name:20} {choices[name]}".rstrip())
    while True:
        answer = click.prompt(
            f"{title} (numbers toggle, e.g. 3,7; Enter keeps *; - for none)",
            default="",
            show_default=False,
        ).strip()
        if not answer:
            return list(selected)
        if answer == "-":
            return []
        try:
            toggled = {
                names[int(part) - 1] for part in answer.split(",") if part.strip()
            }
            if any(int(part) < 1 for part in answer.split(",") if part.strip()):
                raise IndexError
            return [n for n in names if (n in selected) != (n in toggled)]
        except (ValueError, IndexError):
            click.echo(f"enter numbers between 1 and {len(names)}")
