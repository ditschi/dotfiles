"""Move host-local additions out of shared files into `.local` files.

Stdlib only, so the pre-commit hook and CI can run it with plain `python3 -m`.

Text moved to a `.local` file stands between marker comments, keyed by the first
line of the text (Git: by the setting's key). The key lets a later run recognise
the text: identical text is removed from the shared file silently, text under the
same key with a different body is a conflict that is never overwritten silently.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

BEGIN = "# machine-local begin: "
END = "# machine-local end: "

# Lines such as "## <!-- BEGIN ANSIBLE MANAGED BLOCK - update colors -->" written by
# external tools (Ansible blockinfile); the END marker equals the BEGIN marker.
_MANAGED_BEGIN = re.compile(r"^#.*\bBEGIN\b.*MANAGED BLOCK")

GIT_HOST_ONLY = (
    r"^(user\.(name|email|signingkey)$|gpg\.|commit\.gpgsign$|tag\.gpgsign$"
    r"|safe\.|credential\.|https?\.|core\.sshcommand$)"
)

# resolve(kind, key, shared_text, local_text) -> "local" | "shared" | "skip"
Resolver = Callable[[str, str, str, str], str]
# select(chunks) -> the chunks to move
Selector = Callable[[Sequence["Chunk"]], Sequence["Chunk"]]


@dataclass
class Chunk:
    key: str
    text: str
    start: int = 0  # line range [start, end) in the shared file (text only)
    end: int = 0


@dataclass
class Report:
    moved: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def managed_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) line indexes, end inclusive, of externally managed blocks."""
    blocks = []
    index = 0
    while index < len(lines):
        if _MANAGED_BEGIN.search(lines[index]):
            end_marker = lines[index].strip().replace("BEGIN", "END", 1)
            for end in range(index + 1, len(lines)):
                if lines[end].strip() == end_marker:
                    blocks.append((index, end))
                    index = end
                    break
        index += 1
    return blocks


def marked_blocks(text: str) -> dict[str, str]:
    """key -> body of every marked block in a `.local` file."""
    blocks: dict[str, str] = {}
    key: Optional[str] = None
    body: list[str] = []
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\n")
        if key is None:
            if bare.startswith(BEGIN):
                key, body = bare.removeprefix(BEGIN), []
        elif bare == END + key:
            blocks[key] = "".join(body)
            key = None
        else:
            body.append(line)
    return blocks


def _wrap(key: str, body: str) -> str:
    return f"{BEGIN}{key}\n{body}{END}{key}\n"


def _replace_or_append(local_text: str, key: str, body: str) -> str:
    block = _wrap(key, body)
    pattern = re.compile(
        rf"^{re.escape(BEGIN + key)}\n.*?^{re.escape(END + key)}\n",
        re.DOTALL | re.MULTILINE,
    )
    if pattern.search(local_text):
        return pattern.sub(lambda _m: block, local_text, count=1)
    if local_text and not local_text.endswith("\n"):
        local_text += "\n"
    if local_text.strip():
        local_text += "\n"
    return local_text + block


def _write(path: Path, text: str, mode: int) -> None:
    descriptor, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _backup(backup_dir: Path, *files: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for source in files:
        if source.is_file():
            descriptor = os.open(
                backup_dir / source.name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(source.read_bytes())


def _check_local(local: Path) -> None:
    if local.is_symlink():
        raise RuntimeError(f"host-local file must not be a symlink: {local}")
    local.parent.mkdir(parents=True, exist_ok=True)


def _decide(
    resolve: Optional[Resolver], kind: str, key: str, shared: str, local: str
) -> str:
    return resolve(kind, key, shared, local) if resolve else "skip"


# --- text files (for example ~/.bashrc) ---------------------------------------


def added_chunks(shared: Path) -> list[Chunk]:
    """Lines of `shared` that differ from the committed version, grouped into chunks.

    A chunk that touches an externally managed block grows to the whole block."""
    if not shared.is_file():
        return []
    result = subprocess.run(
        [
            "git",
            "-C",
            str(shared.parent),
            "diff",
            "--no-color",
            "-U0",
            "HEAD",
            "--",
            shared.name,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    lines = shared.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = []
    for match in re.finditer(
        r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", result.stdout, re.MULTILINE
    ):
        start, count = int(match.group(1)), int(match.group(2) or 1)
        if count:
            spans.append([start - 1, start - 1 + count])
    blocks = managed_blocks([line.rstrip("\n") for line in lines])
    for span in spans:
        for first, last in blocks:
            if span[0] <= last and span[1] > first:
                span[0], span[1] = min(span[0], first), max(span[1], last + 1)
    merged: list[list[int]] = []
    for span in sorted(spans):
        if merged and span[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], span[1])
        else:
            merged.append(span)
    chunks = []
    for start, end in merged:
        text = "".join(lines[start:end])
        if not text.endswith("\n"):
            text += "\n"
        first_line = next(
            (line.strip() for line in text.splitlines() if line.strip()), ""
        )
        if first_line:
            chunks.append(Chunk(first_line, text, start, end))
    return chunks


def _classify(
    shared: Path, local: Path
) -> tuple[list[Chunk], list[Chunk], list[Chunk]]:
    known_blocks = (
        marked_blocks(local.read_text(encoding="utf-8")) if local.is_file() else {}
    )
    known, new, conflicts = [], [], []
    for chunk in added_chunks(shared):
        body = known_blocks.get(chunk.key)
        if body is None:
            new.append(chunk)
        elif body == chunk.text:
            known.append(chunk)
        else:
            conflicts.append(chunk)
    return known, new, conflicts


def text_pending(shared: Path, local: Path) -> bool:
    """True when text that is already in the `.local` file is back in `shared`."""
    return bool(_classify(shared, local)[0])


def relocate_text(
    shared: Path,
    local: Path,
    backup_dir: Path,
    select: Optional[Selector] = None,
    resolve: Optional[Resolver] = None,
) -> Report:
    report = Report()
    known, new, conflicts = _classify(shared, local)
    chosen = list(select(new)) if select and new else []
    removals = list(known)
    replacements: dict[str, str] = {}
    for chunk in conflicts:
        local_body = marked_blocks(local.read_text(encoding="utf-8"))[chunk.key]
        choice = _decide(resolve, "text", chunk.key, chunk.text, local_body)
        if choice == "skip":
            report.conflicts.append(chunk.key)
            continue
        removals.append(chunk)
        if choice == "shared":
            replacements[chunk.key] = chunk.text
    if not (removals or chosen):
        return report
    if local.exists() or chosen or replacements:
        _check_local(local)
    local_text = local.read_text(encoding="utf-8") if local.is_file() else ""
    _backup(backup_dir, shared, local)
    for chunk in chosen:
        replacements[chunk.key] = chunk.text
        report.moved.append(chunk.key)
    report.removed.extend(chunk.key for chunk in known)
    if replacements:
        for key, body in replacements.items():
            local_text = _replace_or_append(local_text, key, body)
        _write(local, local_text, 0o644)  # stored before it leaves the shared file
    drop = {
        index
        for chunk in [*removals, *chosen]
        for index in range(chunk.start, chunk.end)
    }
    lines = shared.read_text(encoding="utf-8").splitlines(keepends=True)
    _write(
        shared,
        "".join(line for index, line in enumerate(lines) if index not in drop),
        shared.stat().st_mode & 0o777,
    )
    return report


# --- Git configuration ----------------------------------------------------------


def git_config(path: Path, *args: str) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "config", "--file", str(path), "--no-includes", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"cannot read or update Git configuration: {path}")
    return result


def host_settings(path: Path) -> dict[str, list[str]]:
    """Host-only key -> values in file order."""
    result = git_config(path, "--null", "--get-regexp", GIT_HOST_ONLY)
    settings: dict[str, list[str]] = {}
    for entry in result.stdout.split("\0"):
        if entry:
            key, separator, value = entry.partition("\n")
            settings.setdefault(key, []).append(value if separator else "true")
    return settings


def _git_snippet(key: str, values: list[str]) -> str:
    section, _, rest = key.partition(".")
    subsection, _, name = rest.rpartition(".")
    header = f"[{section}]"
    if subsection:
        header = '[{} "{}"]'.format(
            section, subsection.replace("\\", "\\\\").replace('"', '\\"')
        )
    lines = [header]
    for value in values:
        quoted = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\t", "\\t")
        )
        lines.append(f'\t{name} = "{quoted}"')
    return "\n".join(lines) + "\n"


def relocate_git(
    shared: Path,
    local: Path,
    backup_dir: Path,
    resolve: Optional[Resolver] = None,
    check: bool = False,
) -> Report:
    if not shared.is_file():
        raise RuntimeError(f"shared Git configuration is missing: {shared}")
    report = Report()
    settings = host_settings(shared)
    if not settings:
        return report
    if check:
        report.conflicts = sorted(settings)
        return report
    _check_local(local)
    local_settings = host_settings(local) if local.exists() else {}
    stores: dict[str, list[str]] = {}
    unset: list[str] = []
    for key, values in settings.items():
        current = local_settings.get(key)
        if current is None:
            stores[key] = values
            report.moved.append(key)
        elif current == values:
            report.removed.append(key)
        else:
            choice = _decide(resolve, "git", key, "\n".join(values), "\n".join(current))
            if choice == "skip":
                report.conflicts.append(key)
                continue
            if choice == "shared":
                git_config(local, "--unset-all", key)
                stores[key] = values
            (report.moved if choice == "shared" else report.removed).append(key)
        unset.append(key)
    if not unset:
        return report
    _backup(backup_dir, shared, local)
    if stores:
        if not local.exists():
            os.close(os.open(local, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        local.chmod(0o600)
        text = local.read_text(encoding="utf-8")
        for key, values in stores.items():
            text = _replace_or_append(text, key, _git_snippet(key, values))
        _write(local, text, 0o600)
    for key in unset:
        git_config(shared, "--unset-all", key)
    return report


def git_pending(shared: Path, local: Path) -> bool:
    """True when host-only keys can move or drop without asking the user."""
    if not shared.is_file():
        return False
    local_settings = host_settings(local) if local.exists() else {}
    return any(
        local_settings.get(key) in (None, values)
        for key, values in host_settings(shared).items()
    )


# --- command line for the pre-commit hook and CI --------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Keep host-only Git settings out of the shared Git config."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--shared", type=Path, default=Path("home/dot_gitconfig"))
    parser.add_argument("--local", type=Path, default=Path.home() / ".gitconfig.local")
    args = parser.parse_args(argv)
    backup = (
        Path.home()
        / ".local/share/machine/local-overrides-backup"
        / time.strftime("%Y%m%d-%H%M%S")
    )
    try:
        check = args.check or os.environ.get("CI", "").lower() in {"1", "true"}
        report = relocate_git(args.shared, args.local, backup, check=check)
    except (OSError, RuntimeError) as error:
        print(f"local-overrides: {error}")
        return 1
    if check and report.conflicts:
        print("Host-only keys in shared Git config: " + ", ".join(report.conflicts))
        return 1
    if report.moved or report.removed:
        print(
            f"Moved host-only keys out of {args.shared} into {args.local}; backup: {backup}"
        )
    if report.conflicts:
        print(
            "Different local values kept, shared file still has: "
            + ", ".join(report.conflicts)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
