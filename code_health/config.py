"""Loads `code-health.toml`: the parts, their rules and the gate settings."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .model import Smell

CONFIG_FILE = "code-health.toml"


@dataclass
class Rule:
    """One smell rule. Rule-specific settings (e.g. `similarity`) stay in `options`."""

    name: str = ""
    threshold: float = 0
    inclusive: bool = False
    base: float = 0.5
    step: float = 0.0
    max: float = 1.0
    options: dict = field(default_factory=dict)

    def fires(self, value: float) -> bool:
        return value >= self.threshold if self.inclusive else value > self.threshold

    def penalty(self, value: float) -> float:
        """`base` for the first value that fires, plus `step` per unit above it."""
        first = self.threshold if self.inclusive else self.threshold + 1
        return round(min(self.max, self.base + self.step * max(0.0, value - first)), 3)

    def smell(self, value: float, where: tuple[int, str], detail: str) -> Smell:
        """A smell of this rule at (line, target), deducting the penalty for `value`."""
        line, target = where
        return Smell(self.name, line, target, detail, self.penalty(value))


@dataclass
class Part:
    """A group of files scored with its own rules, e.g. `python-cli` or `shell`."""

    name: str
    language: str
    files: list[str]
    rules: dict[str, Rule]
    tests: bool = False

    def rule(self, name: str) -> Rule | None:
        return self.rules.get(name)


@dataclass
class Config:
    root: Path
    parts: list[Part]
    exclude: list[str]
    min_file_score: float
    baseline: str


def load(root: Path) -> Config:
    data = tomllib.loads((root / CONFIG_FILE).read_text())
    defaults = data["rules"]
    return Config(
        root=root,
        parts=[_part(name, values, defaults) for name, values in data["parts"].items()],
        exclude=data.get("exclude", []),
        min_file_score=data["gate"]["min_file_score"],
        baseline=data["gate"]["baseline"],
    )


def _part(name: str, values: dict, defaults: dict) -> Part:
    overrides = values.get("overrides", {})
    rules = {
        rule: _rule(rule, {**defaults.get(rule, {}), **overrides.get(rule, {})})
        for rule in values["rules"]
    }
    return Part(
        name, values["language"], values["files"], rules, values.get("tests", False)
    )


def _rule(name: str, values: dict) -> Rule:
    known = {key: values[key] for key in ("base", "step", "max") if key in values}
    inclusive = "threshold" not in values
    threshold = values.get("threshold", values.get("min", 0))
    return Rule(name, threshold, inclusive, options=dict(values), **known)
