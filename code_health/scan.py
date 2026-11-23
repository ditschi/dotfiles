"""One run over the repository: every scored file, the part scores and the overall score."""

from __future__ import annotations

from dataclasses import dataclass

from . import files
from .config import Config, Part
from .model import FileReport
from .scoring import part_scores, score_file, weighted_score


@dataclass
class Scan:
    config: Config
    parts_of: dict[str, Part]
    reports: dict[str, FileReport]
    parts: dict[str, float]
    overall: float

    def worst(self) -> FileReport | None:
        scored = [report for report in self.reports.values() if report.loc]
        return min(scored, key=lambda report: (report.score, -report.loc), default=None)


def run(config: Config) -> Scan:
    parts_of = files.scored_files(config)
    reports = {path: score_file(path, part, config) for path, part in parts_of.items()}
    values = list(reports.values())
    return Scan(
        config, parts_of, reports, part_scores(config, values), weighted_score(values)
    )
