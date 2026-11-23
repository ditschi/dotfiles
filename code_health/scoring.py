"""Scores files, parts and the whole repository."""

from __future__ import annotations

from . import ansible_metrics, python_metrics, shell_metrics, smells, suppressions
from .config import Config, Part
from .model import FileReport, SourceFile

ANALYSERS = {
    "python": python_metrics.analyse,
    "shell": shell_metrics.analyse,
    "ansible": ansible_metrics.analyse,
}
MIN_SCORE = 1.0
MAX_SCORE = 10.0


def score_source(source: SourceFile, part: Part) -> FileReport:
    try:
        metrics = ANALYSERS[part.language](source)
    except SyntaxError as error:
        lines = sum(1 for line in source.text.splitlines() if line.strip())
        return FileReport(
            source.path, part.name, lines, MIN_SCORE, [], [f"cannot parse: {error}"]
        )
    found, errors = suppressions.apply(
        smells.detect(metrics, part), metrics.suppressions
    )
    loc = metrics.loc if metrics.has_logic else 0
    score = max(MIN_SCORE, MAX_SCORE - sum(smell.penalty for smell in found))
    return FileReport(
        source.path,
        part.name,
        loc,
        round(score, 2) if loc else MAX_SCORE,
        found,
        errors,
    )


def score_file(path: str, part: Part, config: Config) -> FileReport:
    text = (config.root / path).read_text(errors="replace")
    return score_source(SourceFile(path, text, part.tests), part)


def weighted_score(reports: list[FileReport]) -> float:
    """Mean of the file scores weighted by lines of code; files without logic weigh 0."""
    total = sum(report.loc for report in reports)
    weighted = sum(report.score * report.loc for report in reports)
    return round(weighted / total, 2) if total else MAX_SCORE


def part_scores(config: Config, reports: list[FileReport]) -> dict[str, float]:
    return {
        part.name: weighted_score([r for r in reports if r.part == part.name])
        for part in config.parts
    }
