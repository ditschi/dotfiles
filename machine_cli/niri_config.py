"""niri session with DMS: one-time `dms setup`, the include lines for the dotfile group niri.

Runs after Ansible (which installs niri, dms and ghostty), in `machine setup` and
`machine update`, as the step `niri config`. DMS keeps its own config files; this step
only adds one include line to the niri and the Ghostty config.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import features as feature_table
from . import system
from .core import log, parse_profile_file, warn

FEATURE = "niri"
NIRI_CONFIG = Path(".config/niri/config.kdl")
NIRI_INCLUDE = 'include optional=true "dotfiles.kdl"'
NIRI_INCLUDE_LINE = re.compile(r'^\s*include\b.*"(\./)?dotfiles\.kdl"')
GHOSTTY_DIR = Path(".config/ghostty")
# DMS writes `config`; Ghostty 1.2+ also reads `config.ghostty`.
GHOSTTY_CONFIGS = ("config", "config.ghostty")
GHOSTTY_INCLUDE = "config-file = ?dotfiles.ghostty"
GHOSTTY_INCLUDE_LINE = re.compile(
    r'^\s*config-file\s*=\s*"?\??(\./)?dotfiles\.ghostty"?\s*$'
)
SYSTEMD_USER = Path(".config/systemd/user")
DMS_FOR_NIRI = SYSTEMD_USER / "niri.service.wants/dms.service"
DMS_FOR_EVERY_SESSION = SYSTEMD_USER / "graphical-session.target.wants/dms.service"
# Written by the dms package; the role niri_desktop disables it (systemctl --global).
DMS_GLOBAL_FOR_EVERY_SESSION = Path(
    "/etc/systemd/user/graphical-session.target.wants/dms.service"
)
DMS_SETUP = [
    "dms",
    "setup",
    "headless",
    "--compositor",
    "niri",
    "--terminal",
    "ghostty",
    "--skip-existing",
]
DMS_ENABLE = ["dms", "systemd", "enable", "--compositor", "niri"]


def _has_line(path: Path, pattern: re.Pattern) -> bool:
    return any(
        pattern.match(line)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def append_line(path: Path, line: str) -> None:
    """Append one line, starting a new line when the file does not end with one."""
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    prefix = "\n" if text and not text.endswith("\n") else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{line}\n")


class NiriConfigMixin:
    def run_niri_config(self) -> None:
        """One-time DMS setup for niri, then the includes of the dotfile group niri."""
        if self.current_device() == "container":
            return
        features, _ = feature_table.split(
            parse_profile_file(self.applied_host_path)["features"],
            self.current_context(),
            self.current_device(),
        )
        if FEATURE not in features or not system.have("dms"):
            return
        niri_config = self.home / NIRI_CONFIG
        if not niri_config.exists():
            log("niri: no niri config yet; running the DMS setup for niri and Ghostty")
            system.run(DMS_SETUP)
        self.ensure_niri_include(niri_config)
        self.ensure_ghostty_include()
        self.ensure_dms_for_niri_only()

    def ensure_niri_include(self, niri_config: Path) -> None:
        if not niri_config.exists():
            warn(
                f"niri: {niri_config} is missing; the dotfiles.kdl include was not added"
            )
            return
        if _has_line(niri_config, NIRI_INCLUDE_LINE):
            return
        # Last, so that the binds of dotfiles.kdl win over DMS's includes above it.
        append_line(niri_config, NIRI_INCLUDE)
        log(f"niri: added `{NIRI_INCLUDE}` to {niri_config}")

    def ensure_ghostty_include(self) -> None:
        """Include dotfiles.ghostty from the Ghostty config; create `config` if none exists."""
        directory = self.home / GHOSTTY_DIR
        existing = [
            directory / name for name in GHOSTTY_CONFIGS if (directory / name).is_file()
        ]
        if any(_has_line(path, GHOSTTY_INCLUDE_LINE) for path in existing):
            return
        target = existing[0] if existing else directory / GHOSTTY_CONFIGS[0]
        target.parent.mkdir(parents=True, exist_ok=True)
        append_line(target, GHOSTTY_INCLUDE)
        log(f"niri: added `{GHOSTTY_INCLUDE}` to {target}")

    def ensure_dms_for_niri_only(self) -> None:
        if not os.path.lexists(self.home / DMS_FOR_NIRI):
            log("niri: enabling dms.service for the niri session")
            system.run(DMS_ENABLE)
        every_session = self.home / DMS_FOR_EVERY_SESSION
        if os.path.lexists(every_session):
            warn(
                "niri: dms.service is enabled for graphical-session.target, so it also "
                "starts in GNOME and COSMIC; remove it with: "
                f"rm {every_session} && systemctl --user daemon-reload"
            )
        if os.path.lexists(DMS_GLOBAL_FOR_EVERY_SESSION):
            warn(
                "niri: dms.service is enabled globally for graphical-session.target, so it "
                "also starts in GNOME and COSMIC; Ansible (feature niri) disables it, or: "
                "sudo systemctl --global disable dms.service"
            )
