"""Inline suppressions: `# code-health: ignore[rule, other-rule] reason`.

A suppression applies to smells reported on its own line or on the line below it
(the `def`/function line when the comment sits above it). The reason is mandatory.
"""

from __future__ import annotations

import re

from .model import Smell

PATTERN = re.compile(r"#\s*code-health:\s*ignore\[([^\]]*)\]\s*(.*)")

Suppressions = dict[int, dict[str, str]]


def parse_suppression(comment: str) -> dict[str, str] | None:
    match = PATTERN.search(comment)
    if not match:
        return None
    rules = [rule.strip() for rule in match.group(1).split(",")]
    return {rule: match.group(2).strip() for rule in rules if rule}


def apply(
    smells: list[Smell], suppressions: Suppressions
) -> tuple[list[Smell], list[str]]:
    """Smells that remain, and errors for suppressions without a reason or without a smell."""
    matched = [_matching(smell, suppressions) for smell in smells]
    kept = [smell for smell, match in zip(smells, matched) if not match]
    return kept, _missing_reasons(suppressions) + _unused(suppressions, set(matched))


def _entries(suppressions: Suppressions) -> list[tuple[int, str, str]]:
    return [
        (line, rule, reason)
        for line, rules in suppressions.items()
        for rule, reason in rules.items()
    ]


def _missing_reasons(suppressions: Suppressions) -> list[str]:
    return [
        f"line {line}: suppression of {rule} needs a reason"
        for line, rule, reason in _entries(suppressions)
        if not reason
    ]


def _unused(suppressions: Suppressions, used: set) -> list[str]:
    return [
        f"line {line}: suppression of {rule} matches no smell"
        for line, rule, _ in _entries(suppressions)
        if (line, rule) not in used
    ]


def _matching(smell: Smell, suppressions: Suppressions) -> tuple[int, str] | None:
    """(line, rule) of the suppression with a reason that covers the smell, if any."""
    lines = [
        line
        for line in (smell.line, smell.line - 1)
        if suppressions.get(line, {}).get(smell.rule)
    ]
    return (lines[0], smell.rule) if lines else None
