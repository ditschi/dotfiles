#!/usr/bin/env python3
# aihealth: disable=primitive_obsession -- ai-health scan JSON arrives as plain dicts; wrapping it adds no value
"""Component scores of a revision, and the CI check that no component got worse.

    scripts/aihealth_components.py                  scores of the working tree
    scripts/aihealth_components.py REV              scores of REV
    scripts/aihealth_components.py --compare BASE [HEAD]
                                                    exit 1 when a component of HEAD scores
                                                    more than 0.01 below BASE, counted over
                                                    the files that exist in both

Both revisions are exported with `git archive` and scanned with the profiles of the
current checkout, so a change of the profile does not count as a change of the code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "aihealth"
TOLERANCE = 0.01
SHELL_LANGUAGES = {"bash", "zsh", "sh", "shell"}


def code_component(entry: dict) -> str | None:
    """Component of a file from the code scan: python-cli or shell."""
    if entry["language"] == "python":
        return "python-cli"
    return "shell" if entry["language"] in SHELL_LANGUAGES else None


def tests_component(entry: dict) -> str | None:
    """The tests scan holds the python-tests component only."""
    return "python-tests" if entry["language"] == "python" else None


def component_files(scans: dict[str, dict]) -> dict[str, tuple[str, float, int]]:
    """Component, score and lines of code per repository path, from ai-health scan JSON."""
    files = {e["path"]: (code_component(e), e) for e in scans["code"]["files"]}
    files |= {
        f"tests/{e['path']}": (tests_component(e), e) for e in scans["tests"]["files"]
    }
    return {
        path: (name, entry["score"], entry["loc"])
        for path, (name, entry) in files.items()
        if name
    }


def component_scores(files: dict[str, tuple[str, float, int]]) -> dict[str, float]:
    """LoC-weighted mean of the file scores per component."""
    totals: dict[str, list[float]] = {}
    for name, score, loc in files.values():
        total = totals.setdefault(name, [0.0, 0.0])
        total[0] += score * loc
        total[1] += loc
    return {
        name: round(weighted / loc, 2)
        for name, (weighted, loc) in sorted(totals.items())
        if loc
    }


def common(files: dict, other: dict) -> dict:
    """The entries of `files` whose path also exists in `other`."""
    return {path: entry for path, entry in files.items() if path in other}


def regressions(base: dict[str, float], head: dict[str, float]) -> list[str]:
    return [
        f"{name}: {base[name]:.2f} -> {score:.2f}"
        for name, score in head.items()
        if name in base and round(base[name] - score, 2) > TOLERANCE
    ]


def export(revision: str, target: Path) -> None:
    """The revision's files in `target`, as a git repository so ai-health lists them like in the checkout."""
    archive = subprocess.run(
        ["git", "-C", str(ROOT), "archive", revision], check=True, capture_output=True
    )
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True)
    subprocess.run(["git", "-C", str(target), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(target), "add", "-A"], check=True)


def scan(tree: Path) -> dict[str, dict]:
    configs = {
        "code": (tree, ".aihealth.toml"),
        "tests": (tree / "tests", ".aihealth-tests.toml"),
    }
    return {
        name: _scan_json(path, ROOT / config)
        for name, (path, config) in configs.items()
    }


def _scan_json(path: Path, config: Path) -> dict:
    command = [
        str(WRAPPER),
        "scan",
        str(path),
        "--config",
        str(config),
        "--format",
        "json",
    ]
    return json.loads(
        subprocess.run(command, check=True, capture_output=True, text=True).stdout
    )


def files_of(revision: str) -> dict[str, tuple[str, float, int]]:
    with tempfile.TemporaryDirectory() as directory:
        export(revision, Path(directory))
        return component_files(scan(Path(directory)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("revisions", nargs="*")
    parser.add_argument("--compare", action="store_true", help="compare BASE [HEAD]")
    args = parser.parse_args(argv)
    if not args.compare:
        files = (
            files_of(args.revisions[0])
            if args.revisions
            else component_files(scan(ROOT))
        )
        scores = component_scores(files)
        print(json.dumps(scores, indent=2))
        return 0
    base, head = (args.revisions + ["HEAD"])[:2]
    base_files, head_files = files_of(base), files_of(head)
    # Only files in both revisions: deleting a healthy file must not count as a drop,
    # and new or changed files are judged per file by `aihealth delta`.
    before = component_scores(common(base_files, head_files))
    after = component_scores(common(head_files, base_files))
    print(json.dumps({"base": before, "head": after}, indent=2))
    failed = regressions(before, after)
    for line in failed:
        print(f"component got worse: {line}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
