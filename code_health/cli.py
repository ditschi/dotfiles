"""Command line: `code-health [paths] [--changed [BASE]] [--json] [--gate] [--update-baseline]`."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import config as config_module
from . import files, gate, report, scan as scan_module


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="code-health", description=__doc__)
    parser.add_argument(
        "paths", nargs="*", help="files to list (default: all scored files)"
    )
    parser.add_argument(
        "--changed",
        nargs="?",
        const="",
        metavar="BASE",
        help="only files changed since BASE (default: merge base with origin/main)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--all", action="store_true", help="list files without smells too"
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="fail on new smells, low scores or a lower part score",
    )
    parser.add_argument(
        "--base", help="revision --gate compares against (default: HEAD)"
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="tighten code-health-baseline.json",
    )
    return parser.parse_args(argv)


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scan = scan_module.run(config_module.load(repository_root()))
    if args.update_baseline:
        baseline = gate.update_baseline(scan)
        print(
            f"baseline: {len(baseline.parts)} parts, {len(baseline.files)} files below target"
        )
        return 0
    base = _base(args, scan)
    selected = _selected(args, scan, base)
    shown = [scan.reports[path] for path in selected]
    result = gate.check(scan, selected, base) if args.gate else None
    _print(args, scan, shown, result)
    return 0 if result is None or result["passed"] else 1


def _base(args: argparse.Namespace, scan: scan_module.Scan) -> str:
    if args.base:
        return args.base
    if args.changed is not None:
        return args.changed or files.default_base(scan.config.root)
    return "HEAD"


def _selected(args: argparse.Namespace, scan: scan_module.Scan, base: str) -> list[str]:
    if args.paths:
        candidates = args.paths
    elif args.changed is not None:
        candidates = files.changed_files(scan.config.root, base)
    else:
        candidates = sorted(scan.reports)
    return [path for path in candidates if path in scan.reports]


def _print(args: argparse.Namespace, scan, shown, result: dict | None) -> None:
    if args.json:
        print(report.as_json(scan, shown, result))
        return
    print(report.as_table(scan, shown, show_all=args.all))
    if result is None:
        return
    for line in result["failures"]:
        print(f"FAIL {line}", file=sys.stderr)
    for line in result["hints"]:
        print(f"hint: {line}")
    if result["failures"]:
        print(
            "Fix the smells instead of suppressing them; see docs/code-health.md.",
            file=sys.stderr,
        )
