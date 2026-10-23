"""Pure helper for `machine update`: classify incoming changes into steps."""

from __future__ import annotations

from typing import Iterable


def classify_paths(changes: Iterable[tuple[str, str]]) -> list[str]:
    """Steps needed for incoming (git status letter, repo-relative path) pairs.

    Files in $HOME are symlinks into the checkout, so changed content of an existing
    home file is live after the pull; chezmoi must run for added, removed or
    replaced files and for its own configuration.
    """
    steps: set[str] = set()
    for status, path in changes:
        if path.startswith("home/"):
            name = path.removeprefix("home/")
            if status != "M" or name.startswith(".chezmoi"):
                steps.add("chezmoi")
            if not name.startswith("dot_local/"):
                steps.add("shell")
        elif path.startswith("ansible/"):
            steps.add("system")
        elif path.startswith("machine/hosts/"):
            steps.add("profile")
    return sorted(steps)
