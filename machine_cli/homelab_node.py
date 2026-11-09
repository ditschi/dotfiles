"""Feature `homelab-node`: settings, the host age key from Bitwarden and attention items.

The role `homelab_node` does the work and records what is still missing in a status
file; `machine attention` reads only that file (no root, no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from .core import log

FEATURE = "homelab-node"
DEFAULT_CLONE = "/opt/homelab"
# Deploy user when machine runs as root (fresh VM, contabo).
ROOT_DEFAULT_USER = "ditschi"
SOPS_VERSION = "3.13.3"
# machine/ssh_keys/homelab-ci.pub: public half of the homelab CI secret COMPOSE_SSH_KEY.
CI_KEY_NAME = "homelab-ci"
STATUS_FILE = Path("/var/lib/machine/homelab-node.json")
# `homelab-age-key` is the personal key; it never goes onto a server.
PERSONAL_KEY_HOST = "key"
_HOST_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]*$")


def resolve_settings(
    block: Mapping[str, object], hostname: str, login_user: str
) -> Dict[str, object]:
    """Effective settings of the `homelab` block of the host config.

    `problems` lists why the role must not set anything up (empty when it may)."""
    problems: List[str] = []
    host = str(block.get("host") or hostname.lower()).strip()
    if host == PERSONAL_KEY_HOST or not _HOST_NAME.match(host):
        problems.append(
            f"homelab.host {host!r} is not a valid homelab host name"
            + (" (homelab-age-key is the personal key)" if host == "key" else "")
        )
    user = str(block.get("user") or "").strip()
    if not user:  # empty for a remote run without homelab.user: the role decides
        user = ROOT_DEFAULT_USER if login_user == "root" else login_user
    if user == "root":
        problems.append("homelab.user is root; the deploy user must not be root")
    clone = str(block.get("clone") or DEFAULT_CLONE).rstrip("/") or DEFAULT_CLONE
    return {
        "host": host,
        "user": user,
        "clone": clone,
        "managed_clone": clone == DEFAULT_CLONE,
        "ci_restrict": block.get("ci_restrict") is True,
        "problems": problems,
    }


def age_item_name(host: str) -> str:
    return f"homelab-age-{host}"


def age_private_key(item: Optional[Mapping[str, object]]) -> str:
    """The hidden field `private_key` of the item, or ''."""
    for field in (item or {}).get("fields") or []:
        if (field.get("name") or "").strip() == "private_key" and field.get("value"):
            value = str(field["value"]).strip()
            if value.startswith("AGE-SECRET-KEY-"):
                return value
    return ""


class HomelabNodeMixin:
    homelab_status_file = STATUS_FILE

    def homelab_age_key(self, settings: Mapping[str, object]) -> str:
        """The host age key from Bitwarden, or '' (logged, never printed)."""
        if settings["problems"]:
            return ""
        name = age_item_name(str(settings["host"]))
        if not self.unlock_bitwarden():
            log(f"Bitwarden not unlocked; homelab age key without item '{name}'")
            return ""
        item = self.bw_get_item_raw(name)
        # `bw get item` also matches by search; only the exact item counts, so a
        # short host name can never pick the personal `homelab-age-key`.
        if not item or item.get("name") != name:
            log(f"Bitwarden item '{name}' not found")
            return ""
        key = age_private_key(item)
        if not key:
            log(f"Bitwarden item '{name}' has no hidden field private_key")
        return key

    def homelab_ansible_vars(
        self, block: Mapping[str, object], hostname: str, login_user: str
    ) -> Dict[str, object]:
        """Extra vars for the role: resolved settings and, if read, the age key.

        `login_user` is empty for a remote run; the role then resolves the user."""
        settings = resolve_settings(block, hostname, login_user)
        values: Dict[str, object] = {"homelab_node": settings}
        key = self.homelab_age_key(settings)
        if key:
            values["homelab_age_private_key"] = key
        return values

    def homelab_status(self) -> Optional[dict]:
        if FEATURE not in self.saved_features():
            return None
        try:
            return json.loads(self.homelab_status_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def homelab_problems(self) -> List[str]:
        """What the last `machine apply` could not finish on this homelab node."""
        status = self.homelab_status()
        if not status:
            return []
        return status_problems(status)


def status_problems(status: Mapping[str, object]) -> List[str]:
    """Attention texts for the role's status file."""
    out: List[str] = list(status.get("problems") or [])
    if out:
        return out  # nothing else was set up
    when = str(status.get("run_at") or "")[:16].replace("T", " ")
    suffix = f" (last apply {when})" if when else ""
    return [text + suffix for text in _status_texts(status)]


def _status_texts(status: Mapping[str, object]) -> List[str]:
    out: List[str] = []
    user = status.get("user") or "the deploy user"
    host = status.get("host") or "?"
    for name in status.get("missing_key_files") or []:
        out.append(
            f"homelab: machine/ssh_keys/{name} is missing; not in authorized_keys"
        )
    if status.get("ci_key_unrestricted") and status.get("clone_state") == "ok":
        out.append(
            f"homelab: the CI key of {user} is not limited to `homelab deploy`; "
            "set homelab.ci_restrict: true once CI uses `homelab deploy`"
        )
    age = status.get("age_key")
    if age == "missing":
        out.append(
            f"homelab: no age key for {user}: Bitwarden item "
            f"'{age_item_name(str(host))}' (hidden field private_key) was not available"
        )
    elif age == "differs":
        out.append(
            f"homelab: ~{user}/.config/sops/age/keys.txt holds another key than "
            f"'{age_item_name(str(host))}'; kept as it is"
        )
    clone = status.get("clone") or DEFAULT_CLONE
    state = status.get("clone_state")
    if state == "not-a-repo":
        out.append(f"homelab: {clone} is not a git checkout")
    elif state == "clone-failed":
        out.append(
            f"homelab: git clone into {clone} failed: "
            f"{status.get('clone_error') or 'see the last machine apply'}"
        )
    elif state == "waiting-for-deploy-key":
        out.append(
            "homelab: GitHub does not accept the deploy key yet; add it under "
            "github.com/ditschi/homelab → Settings → Deploy keys (write access off): "
            f"{status.get('deploy_public_key') or '?'}"
        )
    sops_version = str(status.get("sops_version") or "")
    if SOPS_VERSION not in sops_version:
        found = status.get("sops_path") or "no sops"
        out.append(
            f"homelab: `sops` for {user} in SSH sessions is {found} "
            f"({sops_version or 'not runnable'}), not {SOPS_VERSION} "
            "from /usr/local/bin/sops"
        )
    if not status.get("docker"):
        out.append("homelab: the docker CLI is missing")
    elif not status.get("compose"):
        out.append("homelab: the Docker Compose plugin is missing")
    return out
