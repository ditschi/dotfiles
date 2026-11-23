"""Readable table and JSON output."""

from __future__ import annotations

import json

from .model import FileReport
from .scan import Scan


def as_json(scan: Scan, shown: list[FileReport], gate: dict | None = None) -> str:
    low = scan.worst()
    data = {
        "parts": scan.parts,
        "overall_score": scan.overall,
        "worst_file": (
            {"path": low.path, "part": low.part, "score": low.score} if low else None
        ),
        "files": [report.to_dict() for report in sorted(shown, key=_order)],
    }
    if gate is not None:
        data["gate"] = gate
    return json.dumps(data, indent=2)


def as_table(scan: Scan, shown: list[FileReport], show_all: bool = False) -> str:
    lines = [f"{'score':>6}  {'loc':>5}  file"]
    for report in sorted(shown, key=_order):
        if show_all or _has_findings(report):
            lines += _file_lines(report)
    lines.append("")
    target = scan.config.min_file_score
    for part, score in scan.parts.items():
        mark = "ok" if score >= target else f"below {target}"
        lines.append(f"part {part:<14} {score:>5.2f}  {mark}")
    lines.append(
        f"overall {scan.overall:.2f} over {len(scan.reports)} files (information only)"
    )
    low = scan.worst()
    if low:
        lines.append(f"worst file {low.path} {low.score:.2f}")
    return "\n".join(lines)


def _has_findings(report: FileReport) -> bool:
    return bool(report.smells or report.errors)


def _file_lines(report: FileReport) -> list[str]:
    lines = [f"{report.score:>6.2f}  {report.loc:>5}  {report.path}"]
    lines += [f"{'':>15}error: {error}" for error in report.errors]
    lines += [
        f"{'':>15}L{smell.line:<5} {smell.rule:<28} -{smell.penalty:<5} "
        f"{smell.target}: {smell.detail}"
        for smell in report.smells
    ]
    return lines


def _order(report: FileReport) -> tuple:
    return (report.score, -report.loc, report.path)
