"""Feature table: help, dotfile groups and defaults per context and device.

The table lives in ansible/group_vars/all/features.yml so that Ansible and the CLI
read the same file; Ansible mirrors `allowed` in the `machine_features` group var.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import yaml

TABLE_PATH = Path(__file__).resolve().parents[1] / "ansible/group_vars/all/features.yml"
CONTEXTS = ["private", "work"]
DEVICES = ["desktop", "server", "container"]
DEFAULT, OPTIONAL, EXCLUDED = "default", "optional", "excluded"
_RANK = {DEFAULT: 0, OPTIONAL: 1, EXCLUDED: 2}

# Groups that do not come from a feature.
GROUP_ALWAYS = ("core", "prompt")


@lru_cache(maxsize=None)
def load_table(path: Path = TABLE_PATH) -> Dict[str, dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return dict(data.get("feature_table") or {})


def feature_help(table: Optional[Dict[str, dict]] = None) -> Dict[str, str]:
    table = load_table() if table is None else table
    return {name: str(row.get("help") or "") for name, row in table.items()}


def level(row: dict, context: str, device: str) -> str:
    """The stricter of the context and device value; no context uses the device only."""
    values = [str(row.get(device) or DEFAULT)]
    if context:
        values.append(str(row.get(context) or DEFAULT))
    return max(values, key=lambda value: _RANK.get(value, 0))


def levels(
    context: str, device: str, table: Optional[Dict[str, dict]] = None
) -> Dict[str, str]:
    table = load_table() if table is None else table
    return {name: level(row, context, device) for name, row in table.items()}


def allowed(
    context: str, device: str, table: Optional[Dict[str, dict]] = None
) -> Dict[str, str]:
    """Features offered on this host, with their help text, in table order."""
    table = load_table() if table is None else table
    resolved = levels(context, device, table)
    return {
        name: str(table[name].get("help") or "")
        for name, value in resolved.items()
        if value != EXCLUDED
    }


def defaults(
    context: str, device: str, table: Optional[Dict[str, dict]] = None
) -> List[str]:
    return [
        name
        for name, value in levels(context, device, table).items()
        if value == DEFAULT
    ]


def split(
    features: Sequence[str],
    context: str,
    device: str,
    table: Optional[Dict[str, dict]] = None,
) -> tuple[List[str], List[str]]:
    """(kept, dropped): dropped are excluded for the host or unknown."""
    offered = allowed(context, device, table)
    kept = [name for name in features if name in offered]
    dropped = [name for name in features if name not in offered]
    return kept, dropped


def dotfile_groups(
    context: str,
    device: str,
    features: Sequence[str] = (),
    table: Optional[Dict[str, dict]] = None,
) -> List[str]:
    """Groups a host receives: always-on, device, context, then those of its features."""
    table = load_table() if table is None else table
    groups = list(GROUP_ALWAYS)
    if device != "container":
        groups.append("systemd")
    if context == "work":
        groups.append("work")
    kept, _ = split(features, context, device, table)
    for name in kept:
        for group in table[name].get("groups") or []:
            if group not in groups:
                groups.append(str(group))
    return groups
