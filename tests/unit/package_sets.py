"""Resolve apt package sets the same way as ansible/tasks/resolve_packages.yml."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Set

import yaml

REPO = Path(__file__).resolve().parents[2]
ANSIBLE = REPO / "ansible"
sys.path.insert(0, str(REPO))


def load_group_vars() -> dict:
    variables: dict = {}
    for path in sorted((ANSIBLE / "group_vars" / "all").glob("*.yml")):
        variables.update(yaml.safe_load(path.read_text()) or {})
    return variables


# Test hosts: chosen context and device plus the hardware Ansible would detect.
HOSTS = {
    "private-laptop": {"context": "private", "device": "desktop", "hw_laptop": True},
    "private-desktop": {"context": "private", "device": "desktop"},
    "work-desktop": {"context": "work", "device": "desktop"},
    "private-server": {"context": "private", "device": "server"},
    "private-vm-server": {"context": "private", "device": "server", "hw_virtual": True},
    "pi": {"context": "private", "device": "server", "hw_pi": True},
    "pi-zero": {
        "context": "private",
        "device": "server",
        "hw_pi": True,
        "hw_pi_zero": True,
    },
    "container": {"context": "", "device": "container"},
}


def host_vars(name: str, features: Iterable[str] | None = None) -> dict:
    """Extra vars for Ansible: context, device, hardware facts and features."""
    from machine_cli import features as feature_table

    host = {
        "hw_laptop": False,
        "hw_pi": False,
        "hw_pi_zero": False,
        "hw_virtual": False,
        **HOSTS[name],
    }
    host["features"] = (
        list(features)
        if features is not None
        else feature_table.defaults(host["context"], host["device"])
    )
    return host


def _allowed(host: dict) -> Set[str]:
    from machine_cli import features as feature_table

    kept, _ = feature_table.split(host["features"], host["context"], host["device"])
    return set(kept)


def resolve_packages(host: dict, variables: dict | None = None) -> List[str]:
    variables = variables or load_group_vars()
    features_set = _allowed(host)
    if host["hw_pi_zero"]:
        packages = list(variables["packages_rpi_zero"])
    else:
        packages = list(variables["packages_base"])
    if not host["hw_pi_zero"] and host["device"] != "container":
        packages.extend(variables["packages_host"])
    if host["context"] == "work":
        packages.extend(variables["packages_work"])
    if not host["hw_laptop"]:
        features_set -= {"lid-switch", "power-profile-switch", "battery-charge-limit"}
    if host["hw_pi"]:
        features_set -= {"zram-swap"}
    for feature, feature_packages in variables["packages_by_feature"].items():
        if feature in features_set:
            packages.extend(feature_packages)
    return sorted(set(packages))


def resolve_monitoring(host: dict) -> List[str]:
    """Mirror ansible/tasks/resolve_monitoring.yml."""
    features_set = _allowed(host)
    if "monitoring" not in features_set:
        return []
    names = ["machine/base"]
    if host["hw_laptop"]:
        names.append("machine/laptop")
    if host["hw_pi"]:
        names.append("machine/pi")
    if host["device"] == "server" and not host["hw_pi"]:
        names.append("machine/server")
    if (
        not host["hw_virtual"]
        and not host["hw_pi"]
        and not host.get("influx_telegraf_config_base")
    ):
        names.append("machine/smart")
    if "docker" in features_set:
        names.append("machine/docker")
    return names
