"""`machine update`: local overrides (host-local additions in shared files)."""

from __future__ import annotations

import difflib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.text import Text

from . import local_overrides, system
from .core import log

Resolver = tuple[str, str, Callable[[bool], None], Callable[[], bool]]


@dataclass(frozen=True)
class SharedFile:
    """A shared file in home/core and the host-local file its local additions move to."""

    name: str
    local_name: str

    @property
    def kind(self) -> str:
        """The name in events: gitconfig, bashrc."""
        return self.name.lstrip(".")

    @property
    def label(self) -> str:
        return f"~/{self.local_name}"


GITCONFIG = SharedFile(".gitconfig", ".gitconfig.local")
BASHRC = SharedFile(".bashrc", ".bashrc-local")


def resolve_conflict(kind: str, key: str, shared_text: str, local_text: str) -> str:
    """Show both values of a conflicting key as a diff and ask which one to keep."""
    print(f"\nConflict in {key}:")
    diff = difflib.unified_diff(
        shared_text.strip().splitlines(),
        local_text.strip().splitlines(),
        "shared",
        "local",
        lineterm="",
    )
    console = Console(highlight=False, soft_wrap=True)
    for line in diff:
        style = {"-": "red", "+": "green", "@": "cyan"}.get(line[0])
        console.print(Text(line, style=style))
    return system.choose("Keep which value", ["local", "shared", "skip"], "skip")


class LocalOverridesMixin:
    def local_resolvers(self) -> list[Resolver]:
        """(name, repo-relative path, run(interactive), pending) for shared files.

        `pending` is true when text can be taken out without asking (it is known
        in the `.local` file); everything else needs the user's choice."""
        git_shared = self.core_source / ".gitconfig"
        git_local = self.home / ".gitconfig.local"
        bash_shared = self.core_source / ".bashrc"
        bash_local = self.home / ".bashrc-local"
        return [
            (
                "host-only Git settings",
                "home/core/.gitconfig",
                self.move_git_overrides,
                lambda: local_overrides.git_pending(git_shared, git_local),
            ),
            (
                "host-local text in .bashrc",
                "home/core/.bashrc",
                self.move_bashrc_overrides,
                lambda: local_overrides.text_pending(bash_shared, bash_local),
            ),
        ]

    def run_local_resolvers(self, interactive: bool = False) -> None:
        interactive = interactive and system.is_tty()
        for _name, _path, run, _pending in self.local_resolvers():
            run(interactive)

    def _overrides_backup(self):
        return (
            self.state_dir / "local-overrides-backup" / time.strftime("%Y%m%d-%H%M%S")
        )

    def _report_overrides(self, shared_file: SharedFile, report) -> None:
        kind, local_name = shared_file.kind, shared_file.label
        for key in report.moved:
            log(f"moved to {local_name}: {key}")
        if report.moved:
            self.event("local-overrides", "moved", kind)
        if report.removed:
            self.event("local-overrides", "removed", kind)
        if report.conflicts:
            log(
                f"WARNING: {', '.join(report.conflicts)} differs from {local_name}; "
                "nothing changed (run `machine update` in a terminal to choose)"
            )
            self.event("local-overrides", "conflict", kind)

    def _move_overrides(
        self, shared_file: SharedFile, relocate: Callable[[Path, Path], object]
    ) -> None:
        """Run `relocate(shared, local)` for `shared_file` and report it."""
        shared = self.core_source / shared_file.name
        if not shared.is_file():
            return
        report = relocate(shared, self.home / shared_file.local_name)
        self._report_overrides(shared_file, report)

    def move_git_overrides(self, interactive: bool = False) -> None:
        self._move_overrides(
            GITCONFIG,
            lambda shared, local: local_overrides.relocate_git(
                shared,
                local,
                self._overrides_backup(),
                resolve_conflict if interactive else None,
            ),
        )

    def move_bashrc_overrides(self, interactive: bool = False) -> None:
        self._move_overrides(
            BASHRC,
            lambda shared, local: local_overrides.relocate_text(
                shared,
                local,
                self._overrides_backup(),
                self._bashrc_selector(shared) if interactive else None,
                resolve_conflict if interactive else None,
            ),
        )

    def _bashrc_selector(self, shared: Path) -> Callable:
        """Ask which chunks added to the shared .bashrc move."""
        return lambda chunks: self._select_bashrc_chunks(shared, chunks)

    def _select_bashrc_chunks(self, shared: Path, chunks):
        system.run(
            [
                "git",
                "--no-pager",
                "-C",
                str(self.repo),
                "diff",
                "--color=always",
                "--no-ext-diff",
                "--unified=3",
                "HEAD",
                "--",
                str(shared.relative_to(self.repo)),
            ],
            check=False,
        )
        labels = {c.key: f"{c.text.count(chr(10))} line(s)" for c in chunks}
        picked = system.choose_many(
            "Move text added to .bashrc into ~/.bashrc-local", labels, []
        )
        return [c for c in chunks if c.key in picked]
