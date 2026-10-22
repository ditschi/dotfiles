"""Pure helpers for `machine update`: managed-block relocation and incoming-change classification."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Iterable

# Lines such as "## <!-- BEGIN ANSIBLE MANAGED BLOCK - update colors -->" written by
# external tools (Ansible blockinfile); the END marker equals the BEGIN marker.
_BEGIN = re.compile(r"^#.*\bBEGIN\b.*MANAGED BLOCK")


def managed_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) line indexes, end inclusive, of externally managed blocks."""
    blocks = []
    index = 0
    while index < len(lines):
        if _BEGIN.search(lines[index]):
            end_marker = lines[index].strip().replace("BEGIN", "END", 1)
            for end in range(index + 1, len(lines)):
                if lines[end].strip() == end_marker:
                    blocks.append((index, end))
                    index = end
                    break
        index += 1
    return blocks


def _write(path: Path, text: str, mode: int) -> None:
    descriptor, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def relocate_managed_blocks(shared: Path, local: Path, backup_dir: Path) -> list[str]:
    """Move externally managed blocks from `shared` into `local`; returns their BEGIN lines.

    The block in `local` is replaced when it has the same BEGIN line, otherwise appended.
    `shared` may be a symlink target in the repository; it is rewritten in place.
    """
    if not shared.is_file():
        return []
    text = shared.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    blocks = managed_blocks([line.rstrip("\n") for line in lines])
    if not blocks:
        return []
    if local.is_symlink():
        raise RuntimeError(
            f"host-local bash configuration must not be a symlink: {local}"
        )
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / shared.name).write_text(text, encoding="utf-8")
    if local.is_file():
        (backup_dir / local.name).write_text(
            local.read_text(encoding="utf-8"), encoding="utf-8"
        )

    local_lines = (
        local.read_text(encoding="utf-8").splitlines(keepends=True)
        if local.is_file()
        else []
    )
    moved = []
    for start, end in blocks:
        block = lines[slice(start, end + 1)]
        if not block[-1].endswith("\n"):
            block[-1] += "\n"
        begin = block[0].strip()
        moved.append(begin)
        existing = [
            span
            for span in managed_blocks([line.rstrip("\n") for line in local_lines])
            if local_lines[span[0]].strip() == begin
        ]
        if existing:
            first, last = existing[0]
            local_lines[slice(first, last + 1)] = block
        else:
            if local_lines and not local_lines[-1].endswith("\n"):
                local_lines[-1] += "\n"
            if local_lines and local_lines[-1].strip():
                local_lines.append("\n")
            local_lines.extend(block)

    keep = [
        line
        for index, line in enumerate(lines)
        if not any(start <= index <= end for start, end in blocks)
    ]
    _write(local, "".join(local_lines), 0o644)
    _write(shared, "".join(keep), shared.stat().st_mode & 0o777)
    return moved


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
