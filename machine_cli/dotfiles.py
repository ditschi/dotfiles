"""Dotfile groups: choose the groups for a host and apply them with `mise dot`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from . import system
from .core import die, parse_profile_file

# Groups are directories `home/<group>/` declared in the repository's `mise.toml`.
GROUP_ALWAYS = ("core", "prompt")
GROUP_SYSTEMD_EXCLUDED = ("container",)
GROUP_WORK_PROFILES = ("work-machine",)


def dotfile_groups(profile: str, features: Sequence[str] = ()) -> list[str]:
    """Groups a host receives, derived from its profile (and features)."""
    groups = list(GROUP_ALWAYS)
    if profile not in GROUP_SYSTEMD_EXCLUDED:
        groups.append("systemd")
    if profile in GROUP_WORK_PROFILES:
        groups.append("work")
    return groups


def render_local_config(groups: Sequence[str]) -> str:
    names = ", ".join(f'"{g}"' for g in groups)
    return f"[bootstrap]\ndotfile_groups = [{names}]\n"


class DotfilesMixin:
    def write_dotfile_groups(self, profile: str) -> None:
        """Write the host's group list into the local mise configuration."""
        features = parse_profile_file(self.profile_path)["features"]
        self.ensure_dirs()
        self.mise_local_config.parent.mkdir(parents=True, exist_ok=True)
        self.mise_local_config.write_text(
            render_local_config(dotfile_groups(profile, features)), encoding="utf-8"
        )

    def dotfiles_env(self) -> dict:
        env = dict(os.environ)
        env["MISE_DOTFILES_ROOT"] = str(self.repo)
        return env

    def run_dotfiles_apply(self) -> None:
        if not system.have("mise"):
            die("mise is not installed (run: ./bootstrap)")
        if not self.mise_local_config.is_file():
            die(f"missing {self.mise_local_config} (run: machine setup)")
        env = self.dotfiles_env()
        project = Path(self.repo) / "mise.toml"
        system.run(["mise", "trust", str(project)], env=env, check=False, capture=True)
        system.run(["mise", "dot", "apply", "--prune"], env=env, cwd=self.repo)

    def dotfiles_health_failure(self) -> str:
        """Reason why the group configuration is unusable, or an empty string."""
        if not (system.have("mise") and self.mise_local_config.exists()):
            return ""
        try:
            self.mise_local_config.read_bytes()
        except OSError as exc:
            return f"mise group configuration unreadable: {exc}"
        return ""
