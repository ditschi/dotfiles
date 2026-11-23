"""Which files are scored, and which of them changed."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Config, Part
from .globs import matches

SHELL_SUFFIXES = (".sh", ".bash", ".zsh")


def _git(root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def tracked_files(root: Path) -> list[str]:
    """Tracked and untracked files that git does not ignore."""
    return sorted(
        set(_git(root, "ls-files", "--cached", "--others", "--exclude-standard"))
    )


def part_of(path: str, config: Config) -> Part | None:
    """The first part whose globs match the file, or None when the file is not scored."""
    if matches(path, config.exclude):
        return None
    for part in config.parts:
        if matches(path, part.files):
            if part.language != "shell" or _is_shell(config.root / path):
                return part
    return None


def _is_shell(path: Path) -> bool:
    if path.suffix in SHELL_SUFFIXES:
        return True
    try:
        with path.open("rb") as handle:
            first = handle.readline(200)
    except OSError:
        return False
    return first.startswith(b"#!") and first.rstrip().split(b"/")[-1].split()[-1] in (
        b"sh",
        b"bash",
        b"zsh",
    )


def scored_files(config: Config) -> dict[str, Part]:
    """Map of path to part for every scored file."""
    found = {}
    for path in tracked_files(config.root):
        part = part_of(path, config) if (config.root / path).is_file() else None
        if part:
            found[path] = part
    return found


def default_base(root: Path) -> str:
    for ref in ("origin/main", "main"):
        try:
            return _git(root, "merge-base", "HEAD", ref)[0]
        except subprocess.CalledProcessError:
            continue
    return "HEAD"


def changed_files(root: Path, base: str) -> list[str]:
    """Files changed since `base`: commits, staged and unstaged edits, and untracked files."""
    changed = _git(root, "diff", "--name-only", "--diff-filter=ACMR", base)
    changed += _git(root, "ls-files", "--others", "--exclude-standard")
    return sorted(set(changed))


def read_at(root: Path, base: str, path: str) -> str | None:
    """The file's content at `base`, or None when it did not exist there."""
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:{path}"],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None
