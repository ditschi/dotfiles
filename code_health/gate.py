"""The gate for pre-commit and CI, and the ratchet baseline below the target score."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import files
from .model import FileReport, SourceFile
from .scan import Scan
from .scoring import score_source

EPSILON = 0.005


@dataclass
class Baseline:
    parts: dict[str, float] = field(default_factory=dict)
    files: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Baseline | None:
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls(data.get("parts", {}), data.get("files", {}))

    def save(self, path: Path) -> None:
        data = {
            "parts": dict(sorted(self.parts.items())),
            "files": dict(sorted(self.files.items())),
        }
        path.write_text(json.dumps(data, indent=2) + "\n")


def check(scan: Scan, changed: list[str], base: str) -> dict:
    """Failures and hints for the changed files and the part scores."""
    config = scan.config
    baseline = Baseline.load(config.root / config.baseline) or Baseline()
    reports = [scan.reports[path] for path in changed if path in scan.reports]
    failures = [
        f for report in reports for f in _file_failures(scan, report, base, baseline)
    ]
    failures += _part_failures(scan, baseline)
    return {
        "passed": not failures,
        "failures": failures,
        "hints": _hints(scan, baseline),
    }


def _part_failures(scan: Scan, baseline: Baseline) -> list[str]:
    floors = {
        part: baseline.parts.get(part, scan.config.min_file_score)
        for part in scan.parts
    }
    return [
        f"part {part}: score {score:.2f} is below {floors[part]:.2f}"
        for part, score in scan.parts.items()
        if score < floors[part] - EPSILON
    ]


def _file_failures(
    scan: Scan, report: FileReport, base: str, baseline: Baseline
) -> list[str]:
    failures = [f"{report.path}: {error}" for error in report.errors]
    floor = min(scan.config.min_file_score, baseline.files.get(report.path, 10.0))
    if report.score < floor - EPSILON:
        failures.append(f"{report.path}: score {report.score:.2f} is below {floor:.2f}")
    before = _score_at(scan, base, report.path)
    if before is not None and report.score < before - EPSILON:
        failures.append(
            f"{report.path}: score fell from {before:.2f} to {report.score:.2f}"
        )
    return failures


def _score_at(scan: Scan, base: str, path: str) -> float | None:
    """The file's score at the base revision, or None when it did not exist there."""
    old = files.read_at(scan.config.root, base, path)
    if old is None:
        return None
    part = scan.parts_of[path]
    return score_source(SourceFile(path, old, part.tests), part).score


def _hints(scan: Scan, baseline: Baseline) -> list[str]:
    files_now = {path: report.score for path, report in scan.reports.items()}
    improved = _improved(baseline.files, files_now) + _improved(
        baseline.parts, scan.parts
    )
    if not improved:
        return []
    return [
        f"baseline can be tightened ({len(improved)} entries): run code-health --update-baseline"
    ]


def _improved(entries: dict[str, float], now: dict[str, float]) -> list[str]:
    """Baseline entries that the current scores beat (gone files count as 10)."""
    return [
        key for key, score in entries.items() if now.get(key, 10.0) > score + EPSILON
    ]


def update_baseline(scan: Scan) -> Baseline:
    """Tighten the baseline: entries only rise or disappear; the first run records everything."""
    path = scan.config.root / scan.config.baseline
    current = _below_target(scan)
    old = Baseline.load(path)
    new = (
        current
        if old is None
        else Baseline(
            _tighten(current.parts, old.parts), _tighten(current.files, old.files)
        )
    )
    new.save(path)
    return new


def _below_target(scan: Scan) -> Baseline:
    target = scan.config.min_file_score
    files_below = {
        p: r.score for p, r in scan.reports.items() if r.loc and r.score < target
    }
    return Baseline({p: s for p, s in scan.parts.items() if s < target}, files_below)


def _tighten(current: dict[str, float], old: dict[str, float]) -> dict[str, float]:
    """Keep only entries that already existed; each keeps the higher of both scores."""
    return {key: max(score, old[key]) for key, score in current.items() if key in old}
