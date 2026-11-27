"""`machine status`: compact overview of the repo, local work, disks and host config."""

# aihealth: disable=primitive_obsession -- reads the JSON update plan as dicts; needs a plan model first
from __future__ import annotations

import os
from typing import Any, Iterable

from rich.columns import Columns
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .core import profile_fingerprint


def _tilde(path: str) -> str:
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        return "~" + path.removeprefix(home)
    return path


def _sync_state(plan: dict[str, Any]) -> tuple:
    """(text, style) for how the checkout stands to its upstream."""
    behind, ahead = plan["incoming_commits"], plan["local_commits"]
    if not (behind or ahead):
        return f"up to date with {plan['upstream']}", "green"
    parts = [f"{behind} behind"] if behind else []
    parts += [f"{ahead} ahead"] if ahead else []
    return " / ".join(parts) + f" {plan['upstream']}", "yellow"


def _add_attention_rows(
    grid: Table, plan: dict[str, Any], state: dict[str, str]
) -> None:
    if state["state"] != "attention" and not plan["blockers"]:
        return
    reason = plan["blockers"][0] if plan["blockers"] else state["reason"]
    grid.add_row(
        Text("attention", style="bold red"),
        Text(f"⚠ {reason or 'see machine attention'}", style="red"),
    )
    if "→" not in (reason or ""):
        grid.add_row("", Text("→ run: machine", style="bold"))


def _add_incoming_row(grid: Table, plan: dict[str, Any]) -> None:
    if plan["incoming"]:
        grid.add_row(
            "incoming",
            f"{len(plan['incoming'])} files → "
            + (", ".join(plan["steps"]) or "no steps"),
        )


def _local_summary(
    local: set[str], untracked_paths: set[str], plan: dict[str, Any]
) -> str:
    untracked = len(local & untracked_paths)
    parts = [f"{len(local) - untracked} modified", f"{untracked} untracked"]
    if plan["merged"]:
        parts.append(f"{len(plan['merged'])} merge cleanly")
    if plan["conflicts"]:
        parts.append(f"{len(plan['conflicts'])} conflict")
    return ", ".join(parts) + " (kept)"


def _stash_text(count: int) -> Text:
    return Text(
        f"{count} stash entr{'y' if count == 1 else 'ies'} put aside by "
        "machine → restore or drop them: machine attention",
        style="yellow",
    )


def _disk_text(lows: list[Any]) -> Text:
    names = (f"{low.short()} full" if low.space_low else low.short() for low in lows)
    return Text(
        "⚠ " + ", ".join(names) + " → free space: machine attention", style="red"
    )


def _append_home_note(host: Text) -> None:
    home = os.environ.get("HOME", "")
    if home and os.path.realpath(home) != os.path.normpath(home):
        host.append(f" · home is {os.path.realpath(home)}", style="dim")


def _print_section(console: Console, title: str, lines: Iterable[str]) -> None:
    if lines:
        console.print(f"\n[bold]{title}[/bold]")
        for line in lines:
            console.print(f"  {line}", markup=False)


def _print_file(console: Console, title: str, path) -> None:
    if path.is_file():
        console.print(f"\n[bold]{title}[/bold] {path}")
        console.print(path.read_text(encoding="utf-8").rstrip(), markup=False)


class StatusMixin:
    def cmd_status(self, verbose: bool = False) -> int:
        """Compact overview; colors only on a terminal (rich honours NO_COLOR)."""
        console = Console(highlight=False)
        if not console.is_terminal:
            console.width = 400  # piped: keep each row on one line, greppable
        plan = self.update_plan(fetch=False)
        state = self.read_update_state()
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", no_wrap=True)
        grid.add_column()

        self._add_status_repo_row(grid, plan)
        _add_attention_rows(grid, plan, state)
        _add_incoming_row(grid, plan)
        local = self._add_status_local_row(grid, plan)
        stashes = self._add_status_stash_row(grid)
        self._add_status_disk_row(grid)
        self._add_status_host_rows(grid)
        console.print(grid)

        if verbose:
            self._print_status_details(console, plan, stashes, local)
        return 0

    def _add_status_repo_row(self, grid: Table, plan: dict[str, Any]) -> None:
        branch = (self._git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
        position = Text(f"{_tilde(str(self.repo))} · {branch or '?'} · ")
        text, style = _sync_state(plan)
        position.append(text, style=style)
        stamp = (
            self.update_last_check.read_text(encoding="utf-8").strip()
            if self.update_last_check.is_file()
            else "never"
        )
        position.append(f" · checked {stamp[:16].replace('T', ' ')}", style="dim")
        grid.add_row("repo", position)

    def _add_status_local_row(self, grid: Table, plan: dict[str, Any]) -> set[str]:
        local = set(self.local_changes())
        if local:
            grid.add_row(
                "local", _local_summary(local, set(self.untracked_paths()), plan)
            )
        return local

    def _add_status_stash_row(self, grid: Table) -> list[tuple[str, str, str]]:
        stashes = self.stash_entries()
        if stashes:
            grid.add_row("stash", _stash_text(len(stashes)))
        return stashes

    def _add_status_disk_row(self, grid: Table) -> None:
        lows = self.low_disks(quiet=True)
        if lows:
            grid.add_row(Text("disk", style="bold red"), _disk_text(lows))

    def _add_status_host_rows(self, grid: Table) -> None:
        repo_host = self.host_config_path()
        host = Text(repo_host.stem)
        if self.applied_host_path.is_file():
            host.append(f" · {self.current_context() or '-'} · {self.current_device()}")
        text, style = self._host_config_state(repo_host)
        host.append(text, style=style)
        _append_home_note(host)
        grid.add_row("host", host)
        if self.applied_host_path.is_file():
            self._add_status_feature_rows(grid)

    def _host_config_state(self, repo_host) -> tuple:
        """(text, style) for the repo host config against the applied one."""
        if not repo_host.is_file():
            return " · no host config in the repo", "yellow"
        if not self.applied_host_path.is_file():
            return " · not applied yet", "yellow"
        if profile_fingerprint(repo_host) == profile_fingerprint(
            self.applied_host_path
        ):
            return " · config in sync", "green"
        return " · config differs from the repo", "yellow"

    def _add_status_feature_rows(self, grid: Table) -> None:
        features = self.saved_features()
        grid.add_row(
            "features",
            (Columns(features, column_first=True, padding=(0, 2)) if features else "-"),
        )
        grid.add_row("groups", " ".join(self.host_dotfile_groups()) or "-")

    def _print_status_details(
        self,
        console: Console,
        plan: dict[str, Any],
        stashes: list[tuple[str, str, str]],
        local: set[str],
    ) -> None:
        incoming = [f"{item['status']} {item['path']}" for item in plan["incoming"]]
        _print_section(console, "incoming files", incoming)
        stash_lines = [
            f"{ref}: {message.partition(': ')[2]}" for ref, _sha, message in stashes
        ]
        _print_section(console, "stash entries", stash_lines)
        _print_section(console, "local changes", sorted(local))
        _print_file(console, "applied host config", self.applied_host_path)
        _print_file(console, "dotfile groups", self.mise_local_config)
