"""Repository checks for the mise tool fragments.

A tool is declared once: not in two fragments, and not in an Ansible package list
(a tool that mise installs without root must not also be an apt package).
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import yaml

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "openspec", "tests", "node_modules"}

# mise tool name -> the apt package name when they differ
APT_NAMES = {"fd": "fd-find", "node": "nodejs", "tmux-builds": "tmux"}

_SECTION = re.compile(r"^\s*\[(.+?)\]\s*$")
_KEY = re.compile(r"""^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_.:/@-]+))\s*=""")


def _candidates(repo: Path) -> Iterable[Path]:
    """Fragments git knows or would add (ignored paths and nested checkouts such as
    `.claude/worktrees/` are left out); a plain directory walk outside a git checkout.
    """
    listed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*mise/conf.d/*.toml",
        ],
        capture_output=True,
        text=True,
    )
    if listed.returncode == 0 and (repo / ".git").exists():
        return [repo / name for name in listed.stdout.split("\0") if name]
    return repo.glob("**/mise/conf.d/*.toml")


def fragments(repo: Path = REPO) -> List[Path]:
    found = []
    for path in _candidates(repo):
        if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(repo).parts):
            found.append(path)
    return sorted(found)


def tools_of(path: Path) -> List[str]:
    """Names in the [tools] table; a stdlib reader, as tomllib needs Python 3.11."""
    names: List[str] = []
    in_tools = False
    for line in path.read_text().splitlines():
        section = _SECTION.match(line)
        if section:
            in_tools = section.group(1).strip() == "tools"
            continue
        key = _KEY.match(line)
        if in_tools and key:
            names.append(next(g for g in key.groups() if g))
    return names


def short_name(tool: str) -> str:
    """`conda:git` -> `git`, `github:owner/repo` -> `repo`."""
    return re.split(r"[:/]", tool)[-1]


def apt_packages(repo: Path = REPO) -> List[str]:
    variables = yaml.safe_load(
        (repo / "ansible" / "group_vars" / "all" / "packages.yml").read_text()
    )
    names: List[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    for key, value in variables.items():
        if key.startswith("packages_"):
            walk(value)
    return names


def check(repo: Path = REPO) -> List[str]:
    errors: List[str] = []
    declared: Dict[str, List[str]] = defaultdict(list)
    for path in fragments(repo):
        for tool in tools_of(path):
            declared[tool].append(str(path.relative_to(repo)))
    for tool, paths in sorted(declared.items()):
        if len(paths) > 1:
            errors.append(
                f"mise tool {tool!r} is declared in several fragments: {', '.join(paths)}"
            )
    packages = set(apt_packages(repo))
    for tool, paths in sorted(declared.items()):
        name = short_name(tool)
        apt = APT_NAMES.get(name, name)
        if apt in packages or name in packages:
            errors.append(
                f"{name!r} is a mise tool ({paths[0]}) and an Ansible package in "
                "ansible/group_vars/all/packages.yml; keep one"
            )
    return errors


def main(argv: Iterable[str] = ()) -> int:
    errors = check()
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
