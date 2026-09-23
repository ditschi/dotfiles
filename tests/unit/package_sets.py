"""Resolve apt package sets the same way as ansible/tasks/resolve_packages.yml."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set

import yaml

REPO = Path(__file__).resolve().parents[2]
ANSIBLE = REPO / "ansible"


def load_group_vars() -> dict:
    return yaml.safe_load((ANSIBLE / "group_vars" / "all.yml").read_text())


def load_profile(name: str) -> dict:
    path = ANSIBLE / "profiles" / f"{name}.yml"
    return yaml.safe_load(path.read_text())


def resolve_packages(profile: str, features: Iterable[str], variables: dict | None = None) -> List[str]:
    variables = variables or load_group_vars()
    features_set: Set[str] = set(features)
    if profile == "rpi-zero":
        packages = list(variables["packages_rpi_zero"])
    else:
        packages = list(variables["packages_base"])
    if "zsh-full" in features_set:
        packages.extend(variables["packages_zsh"])
    if profile not in {"rpi-zero", "container"}:
        packages.extend(variables["packages_host"])
    if "desktop" in features_set:
        packages.extend(variables["packages_desktop"])
    if "gnome" in features_set:
        packages.extend(variables["packages_gnome"])
    if profile == "work-laptop":
        packages.extend(variables["packages_work"])
    return sorted(set(packages))
