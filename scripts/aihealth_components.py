#!/usr/bin/env python3
"""Component scores of a revision, and the CI check that no component got worse.

    scripts/aihealth_components.py                  scores of the working tree
    scripts/aihealth_components.py REV              scores of REV
    scripts/aihealth_components.py --compare BASE [HEAD]
                                                    exit 1 when a component of HEAD scores
                                                    more than 0.01 below BASE

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
from typing import TypeAlias

# One file of an ai-health scan, all files of the "code" and "tests" scans, and the
# score per component.
ScanEntry: TypeAlias = dict[str, object]
ScanResults: TypeAlias = dict[str, dict]
ComponentScores: TypeAlias = dict[str, float]

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "aihealth"
TOLERANCE = 0.01
SHELL_LANGUAGES = {"bash", "zsh", "sh", "shell"}


def code_component(entry: ScanEntry) -> str | None:
    """Component of a file from the code scan: python-cli or shell."""
    if entry["language"] == "python":
        return "python-cli"
    return "shell" if entry["language"] in SHELL_LANGUAGES else None


def tests_component(entry: ScanEntry) -> str | None:
    """The tests scan holds the python-tests component only."""
    return "python-tests" if entry["language"] == "python" else None


def component_scores(scans: ScanResults) -> ComponentScores:
    """LoC-weighted mean of the file scores per component, from ai-health scan JSON."""
    files = [(code_component(e), e) for e in scans["code"]["files"]]
    files += [(tests_component(e), e) for e in scans["tests"]["files"]]
    totals: dict[str, list[float]] = {}
    for name, entry in files:
        total = totals.setdefault(name, [0.0, 0.0])
        total[0] += entry["score"] * entry["loc"]
        total[1] += entry["loc"]
    totals.pop(None, None)
    return {
        name: round(weighted / loc, 2)
        for name, (weighted, loc) in sorted(totals.items())
        if loc
    }


def regressions(base: ComponentScores, head: ComponentScores) -> list[str]:
    return [
        f"{name}: {base[name]:.2f} -> {score:.2f}"
        for name, score in head.items()
        if name in base and score < base[name] - TOLERANCE
    ]


def export(revision: str, target: Path) -> None:
    """The revision's files in `target`, as a git repository so ai-health lists them like in the checkout."""
    archive = subprocess.run(
        ["git", "-C", str(ROOT), "archive", revision], check=True, capture_output=True
    )
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True)
    subprocess.run(["git", "-C", str(target), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(target), "add", "-A"], check=True)


def scan(tree: Path) -> ScanResults:
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
        "raw",
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


def scores_of(revision: str) -> ComponentScores:
    with tempfile.TemporaryDirectory() as directory:
        export(revision, Path(directory))
        return component_scores(scan(Path(directory)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("revisions", nargs="*")
    parser.add_argument("--compare", action="store_true", help="compare BASE [HEAD]")
    args = parser.parse_args(argv)
    if not args.compare:
        scores = (
            scores_of(args.revisions[0])
            if args.revisions
            else component_scores(scan(ROOT))
        )
        print(json.dumps(scores, indent=2))
        return 0
    base, head = (args.revisions + ["HEAD"])[:2]
    before, after = scores_of(base), scores_of(head)
    print(json.dumps({"base": before, "head": after}, indent=2))
    failed = regressions(before, after)
    for line in failed:
        print(f"component got worse: {line}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
