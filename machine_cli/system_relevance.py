"""Which changed files apply to this host's Ansible run (decided without root)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

import yaml

from . import features as feature_table

FEATURE_RE = re.compile(r"""^'([\w-]+)' in machine_features$""")
FEATURE_TABLE_PATH = "ansible/group_vars/all/features.yml"
# Keys of the feature table that only the machine CLI reads.
CLI_ONLY_FEATURE_KEYS = ("help", "groups")


def ansible_view_of_feature_table(text: str) -> object:
    """The feature table as Ansible sees it: without the keys only the CLI reads.

    Unreadable text yields itself, so that it never compares equal to a valid table."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return text
    table = data.get("feature_table") if isinstance(data, dict) else None
    if isinstance(table, dict):
        for row in table.values():
            if isinstance(row, dict):
                for key in CLI_ONLY_FEATURE_KEYS:
                    row.pop(key, None)
    return data


def _condition_holds(condition: object, features: Sequence[str]) -> bool:
    """False only when the condition is understood and false; unknown conditions hold.

    `features` are the host's features the table allows (Ansible's machine_features)."""
    if not isinstance(condition, str):
        return True
    if match := FEATURE_RE.match(condition.strip()):
        return match.group(1) in features
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
    own_host_config: str,
) -> bool:
    if path == own_host_config:
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
            all(_condition_holds(c, features) for c in conditions)
            for conditions in places
        )
    return True  # playbooks, tasks/, group_vars/, requirements, cfg


def relevant_system_paths(
    paths: Iterable[str],
    *,
    ansible_dir: Path,
    features: Sequence[str],
    context: str,
    device: str,
    own_host_config: str,
) -> list[str]:
    uses = role_conditions(ansible_dir)
    allowed, _ = feature_table.split(features, context, device)
    return sorted(
        p
        for p in set(paths)
        if is_relevant_path(
            p, uses=uses, features=allowed, own_host_config=own_host_config
        )
    )
