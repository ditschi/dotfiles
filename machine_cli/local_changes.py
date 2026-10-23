"""Pure helper for `machine update`: classify incoming changes into steps."""

from __future__ import annotations

from typing import Iterable


def classify_paths(changes: Iterable[tuple[str, str]]) -> list[str]:
    """Steps needed for incoming (git status letter, repo-relative path) pairs.

    Files in $HOME are symlinks into the checkout, so changed content of an existing
    home file is live after the pull; the dotfile apply must run for added, removed or
    replaced files and for the group list (the repository `mise.toml`).
    """
    steps: set[str] = set()
    for status, path in changes:
        if path == "mise.toml":
            steps.add("dotfiles")
        elif path.startswith("home/"):
            parts = path.removeprefix("home/").split("/", 1)
            name = parts[1] if len(parts) == 2 else parts[0]
            if status != "M":
                steps.add("dotfiles")
            if not name.startswith(".local/"):
                steps.add("shell")
        elif path.startswith("ansible/"):
            steps.add("system")
        elif path.startswith("machine/hosts/"):
            steps.add("profile")
    return sorted(steps)
