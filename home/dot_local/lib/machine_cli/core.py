"""Constants and pure helpers shared by all machine CLI modules."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Sequence

import yaml
from rich.console import Console
from rich.text import Text

MACHINE_PROG_NAME = "machine"
PROFILES = [
    "work-laptop",
    "home-laptop",
    "home-server",
    "rpi",
    "rpi-zero",
    "container",
]
FEATURE_HELP = {
    "zsh-full": "Shell stack (zsh, fzf, tmux, jq)",
    "fonts": "Meslo / Nerd fonts for prompts",
    "starship": "Starship prompt config",
    "yazi": "yazi terminal file manager",
    "desktop": "Desktop extras (empty list today)",
    "gnome": "GNOME tools (flameshot, guake, …)",
    "cosmic": "Cosmic desktop packages (Pop OS)",
    "docker": "Docker engine packages",
    "gh-cli": "GitHub CLI (gh)",
    "kerberos": "krb5-user + ldap-utils (work)",
    "azure-cli": "Azure CLI (work)",
    "monitoring": "Telegraf agent (home profiles)",
    "unattended-upgrades": "Automatic security upgrades",
    "syncthing": "Syncthing package",
    "tailscale": "Tailscale package (+ optional login)",
    "ssh-host-key": "Per-host ed25519 key + Bitwarden pub",
    "stylus-touch-guard": "Disable touch while stylus near (Yoga / Xournal++)",
    "thinkpad-tuning": "ThinkPad battery thresholds, power profile, S3, zram, tablet OSK",
    "touch-device": "GNOME touch extensions (TouchUp, Screen Rotate)",
    "sshd-home": "sshd Port 5115 + authorized_keys from machine/ssh_keys",
}
FEATURES = list(FEATURE_HELP)
PLAYBOOKS = ["workstation", "homelab", "site"]
ENV_CLASS = {
    "work-laptop": "work",
    "rpi": "iot",
    "rpi-zero": "iot",
    "container": "",
}
SSH_CLASS = {
    "work-laptop": "work",
    "home-laptop": "home",
    "home-server": "home",
    "rpi": "home",
    "rpi-zero": "home",
    "container": "",
}
OLD_ROOT_LINK_NAMES = [
    ".zshrc",
    ".bashrc",
    ".gitconfig",
    ".p10k.zsh",
    ".tmux.conf",
    ".zprofile",
    ".profile",
]


# Colours only on a terminal (rich also honours NO_COLOR); soft_wrap keeps one
# message on one line so piped output and logs stay greppable.
_stdout = Console(highlight=False, soft_wrap=True)
_stderr = Console(stderr=True, highlight=False, soft_wrap=True)


def _emit(console: Console, message: str, style: Optional[str]) -> None:
    console.print(Text("machine: ", style="bold cyan").append(message, style=style))


class _ConsoleHandler(logging.Handler):
    """Print records as `machine: <message>`; errors go to stderr."""

    STYLES = {
        logging.DEBUG: "dim",
        logging.WARNING: "yellow",
        logging.ERROR: "bold red",
    }

    def emit(self, record: logging.LogRecord) -> None:
        console = _stderr if record.levelno >= logging.ERROR else _stdout
        _emit(console, record.getMessage(), self.STYLES.get(record.levelno))


logger = logging.getLogger("machine")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(_ConsoleHandler())


def set_debug(enabled: bool) -> None:
    logger.setLevel(logging.DEBUG if enabled else logging.INFO)


def debug_enabled() -> bool:
    return logger.isEnabledFor(logging.DEBUG)


def debug(message: str) -> None:
    logger.debug(message)


def log(message: str) -> None:
    # Messages written as "WARNING: ..." predate warn(); keep them highlighted.
    level = logging.WARNING if message.startswith("WARNING") else logging.INFO
    logger.log(level, message)


def warn(message: str) -> None:
    logger.warning(message)


def die(message: str, code: int = 1) -> None:
    logger.error(message)
    raise SystemExit(code)


class _IndentDumper(yaml.SafeDumper):
    """Indent block-sequence items under their key, matching the repo's existing style."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def parse_profile_file(path: Path) -> Dict[str, object]:
    result: Dict[str, object] = {
        "profile": "",
        "features": [],
        "ssh_allow_from": [],
    }
    if not path.is_file():
        return result
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result["profile"] = str(data.get("profile") or "")
    result["features"] = [str(x) for x in (data.get("features") or [])]
    result["ssh_allow_from"] = [str(x) for x in (data.get("ssh_allow_from") or [])]
    return result


def format_profile_yaml(
    profile: str,
    features: Sequence[str],
    ssh_allow_from: Optional[Sequence[str]] = None,
) -> str:
    data = {
        "profile": profile,
        "features": list(features) or ["zsh-full"],
        "ssh_allow_from": list(ssh_allow_from or []),
    }
    return "---\n" + yaml.dump(
        data, Dumper=_IndentDumper, sort_keys=False, default_flow_style=False
    )


def profile_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    data = parse_profile_file(path)
    feats = sorted(str(x) for x in (data.get("features") or []))
    allow = sorted(str(x) for x in (data.get("ssh_allow_from") or []))
    return f"{data.get('profile')}|{','.join(feats)}|{','.join(allow)}"


def write_private(path: Path, content: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
