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
        packages.extend(variables.get("packages_desktop") or [])
    if "gnome" in features_set:
        packages.extend(variables["packages_gnome"])
    if "cosmic" in features_set:
        packages.extend(variables.get("packages_cosmic") or [])
    if "docker" in features_set:
        packages.extend(variables.get("packages_docker") or [])
    if profile == "work-laptop" or "kerberos" in features_set:
        packages.extend(variables["packages_work"])
    if "monitoring" in features_set:
        packages.extend(variables.get("packages_monitoring") or [])
    if "unattended-upgrades" in features_set:
        packages.extend(variables.get("packages_unattended") or [])
    if "syncthing" in features_set:
        packages.extend(variables.get("packages_syncthing") or [])
    if "stylus-touch-guard" in features_set:
        packages.extend(variables.get("packages_stylus_touch_guard") or [])
    if "sshd-home" in features_set:
        packages.extend(variables.get("packages_sshd_home") or [])
    return sorted(set(packages))


def resolve_monitoring(
    profile: str, features: Iterable[str], variables: dict | None = None
) -> List[str]:
    """Mirror ansible/tasks/resolve_monitoring.yml using group_vars map."""
    variables = variables or load_group_vars()
    features_set: Set[str] = set(features)
    if "monitoring" not in features_set:
        return []
    by_profile = variables.get("monitoring_by_profile") or {}
    names = list(by_profile.get(profile) or [])
    if "docker" in features_set and names:
        names = names + ["machine/docker"]
    return names
