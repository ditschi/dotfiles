"""Which changed files apply to this host's Ansible run (decided without root)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

import yaml

FEATURE_RE = re.compile(r"""^'([\w-]+)' in \(features \| default\(\[\]\)\)$""")
PROFILE_RE = re.compile(r"""^profile \| default\(''\) not in \[(.*)\]$""")


def _condition_holds(condition: object, features: Sequence[str], profile: str) -> bool:
    """False only when the condition is understood and false; unknown conditions hold."""
    if not isinstance(condition, str):
        return True
    text = condition.strip()
    if match := FEATURE_RE.match(text):
        return match.group(1) in features
    if match := PROFILE_RE.match(text):
        excluded = [part.strip().strip("'\"") for part in match.group(1).split(",")]
        return profile not in excluded
    return True


def role_conditions(ansible_dir: Path) -> dict[str, list[list[object]]]:
    """role name -> one list of `when` conditions per place the role is used."""
    uses: dict[str, list[list[object]]] = {}
    for playbook in sorted(ansible_dir.glob("*.yml")):
        if playbook.name.startswith("dump_"):
            continue
        try:
            plays = yaml.safe_load(playbook.read_text(encoding="utf-8")) or []
        except (OSError, yaml.YAMLError):
            continue
        for play in plays if isinstance(plays, list) else []:
            roles = play.get("roles", []) if isinstance(play, dict) else []
            for entry in roles or []:
                if isinstance(entry, str):
                    uses.setdefault(entry, []).append([])
                elif isinstance(entry, dict):
                    name = entry.get("role") or entry.get("name")
                    when = entry.get("when", [])
                    conditions = when if isinstance(when, list) else [when]
                    if name:
                        uses.setdefault(str(name), []).append(conditions)
    return uses


def is_relevant_path(
    path: str,
    *,
    uses: dict[str, list[list[object]]],
    features: Sequence[str],
    profile: str,
    own_profile: str,
) -> bool:
    if path == own_profile:
        return True
    if not path.startswith("ansible/"):
        return False
    rel = path.removeprefix("ansible/")
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith("inventory/") or name.endswith(".md") or name.startswith("dump_"):
        return False
    if rel.startswith("roles/"):
        parts = rel.split("/")
        role = parts[1] if len(parts) > 2 else ""
        places = uses.get(role)
        if not places:
            return True  # a role no playbook names cannot be evaluated: count it
        return any(
            all(_condition_holds(c, features, profile) for c in conditions)
            for conditions in places
        )
    return True  # playbooks, tasks/, group_vars/, profiles/, requirements, cfg


def relevant_system_paths(
    paths: Iterable[str],
    *,
    ansible_dir: Path,
    features: Sequence[str],
    profile: str,
    own_profile: str,
) -> list[str]:
    uses = role_conditions(ansible_dir)
    return sorted(
        p
        for p in set(paths)
        if is_relevant_path(
            p, uses=uses, features=features, profile=profile, own_profile=own_profile
        )
    )
