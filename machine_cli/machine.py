"""The Machine object: paths and state shared by all command mixins."""

from __future__ import annotations

import os
from pathlib import Path

from . import events, system
from .core import parse_profile_file
from .profile import ProfileMixin
from .tools import ToolsMixin
from .dotfiles import DotfilesMixin
from .mise_tools import MiseToolsMixin
from .bw_client import BwClientMixin
from .env_pull import EnvPullMixin
from .ssh_keys import SshKeysMixin
from .commands import CommandsMixin
from .updates import UpdateMixin
from .auto_update import AutoUpdateMixin
from .attention import AttentionMixin
from .local_work import LocalWorkMixin


class Machine(
    ProfileMixin,
    ToolsMixin,
    DotfilesMixin,
    MiseToolsMixin,
    BwClientMixin,
    EnvPullMixin,
    SshKeysMixin,
    CommandsMixin,
    UpdateMixin,
    AutoUpdateMixin,
    AttentionMixin,
    LocalWorkMixin,
):
    def __init__(self) -> None:
        self.home = Path.home()
        self.repo = system.detect_repo()
        self.core_source = self.repo / "home" / "core"
        self.ansible_dir = self.repo / "ansible"
        # Where host configs live; tests point it at tests/hosts (relative to the repo).
        self.host_configs_dir = self.repo / os.environ.get(
            "MACHINE_HOSTS_DIR", "machine/hosts"
        )
        self.mise_local_config = Path(
            os.environ.get(
                "MISE_LOCAL_CONFIG", self.home / ".config/mise/config.local.toml"
            )
        )
        self.update_state = Path(
            os.environ.get(
                "DOTFILES_UPDATE_STATE", self.home / ".dotfiles-update-state"
            )
        )
        self.update_last_check = Path(
            os.environ.get(
                "DOTFILES_UPDATE_LAST_CHECK",
                self.home / ".dotfiles-update-last-check",
            )
        )
        self.state_dir = Path(
            os.environ.get("MACHINE_STATE_DIR", self.home / ".local/share/machine")
        )
        # Output of the last failed zsh health check after an update (manual or automatic).
        self.update_failure_file = self.state_dir / "update-failure.txt"
        # The last applied host config: what a failed apply restores, what the shell
        # reads at start, and the host config of containers and new hosts.
        self.applied_host_path = Path(
            os.environ.get(
                "MACHINE_APPLIED_HOST_FILE", self.state_dir / "applied-host.yml"
            )
        )
        self.legacy_profile_path = self.home / ".config/machine/profile.yml"
        self.takeover_legacy_profile()
        self.vault_item = os.environ.get("MACHINE_VAULT_BW_ITEM", "ansible-vault")
        os.environ["DOTFILES_REPO"] = str(self.repo)

    def event(
        self,
        event: str,
        outcome: str,
        reason: str = "",
        duration: float | None = None,
    ) -> None:
        """Append an event to the local log; best effort."""
        try:
            data = parse_profile_file(self.applied_host_path)
            context, device = str(data["context"]), str(data["device"])
            revision = self.repo_revision()
        except Exception:
            context = device = revision = ""
        events.record(
            self.state_dir,
            event,
            outcome,
            reason=reason,
            duration=duration,
            revision=revision,
            context=context,
            device=device,
        )
