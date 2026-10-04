"""The Machine object: paths and state shared by all command mixins."""

from __future__ import annotations

import os
from pathlib import Path

from . import system
from .profile import ProfileMixin
from .tools import ToolsMixin
from .migration import MigrationMixin
from .bitwarden import BitwardenMixin
from .commands import CommandsMixin


class Machine(
    ProfileMixin,
    ToolsMixin,
    MigrationMixin,
    BitwardenMixin,
    CommandsMixin,
):
    def __init__(self) -> None:
        self.home = Path.home()
        self.repo = system.detect_repo()
        self.chezmoi_source = self.repo / "home"
        self.ansible_dir = self.repo / "ansible"
        self.host_profiles_dir = self.repo / "machine" / "hosts"
        # Path to local cache. Do not use MACHINE_PROFILE — zsh exports that as the
        # profile *name* (see 00_LOADER.zsh).
        self.profile_path = Path(
            os.environ.get(
                "MACHINE_PROFILE_FILE",
                self.home / ".config/machine/profile.yml",
            )
        )
        self.chezmoi_config = Path(
            os.environ.get("CHEZMOI_CONFIG", self.home / ".config/chezmoi/chezmoi.yaml")
        )
        self.update_marker = Path(
            os.environ.get(
                "DOTFILES_UPDATE_MARKER", self.home / ".dotfiles-update-available"
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
        self.vault_item = os.environ.get("MACHINE_VAULT_BW_ITEM", "ansible-vault")
        os.environ["DOTFILES_REPO"] = str(self.repo)
