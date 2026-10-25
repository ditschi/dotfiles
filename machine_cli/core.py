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

from . import features

MACHINE_PROG_NAME = "machine"
# Context and device of a host; the feature table is the source of feature help.
CONTEXTS = features.CONTEXTS
DEVICES = features.DEVICES
FEATURE_HELP = features.feature_help()
FEATURES = list(FEATURE_HELP)
PLAYBOOKS = ["workstation", "homelab", "site"]
# Former single profile -> (context, device), for an old local file.
LEGACY_PROFILES = {
    "work-machine": ("work", "desktop"),
    "home-laptop": ("private", "desktop"),
    "home-server": ("private", "server"),
    "rpi": ("private", "server"),
    "rpi-zero": ("private", "server"),
    "container": ("", "container"),
}
# Bitwarden env groups per context: items env/groups/<group>.
ENV_GROUPS = {"private": ["private"], "work": ["work"], "": []}
SSH_CLASS = {"private": "home", "work": "work", "": ""}


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
    """A host config (repository file or applied copy) as a dict."""
    return parse_profile_text(
        path.read_text(encoding="utf-8") if path.is_file() else ""
    )


def parse_profile_text(text: str) -> Dict[str, object]:
    """context, device, features, ssh_allow_from and ansible of a host config.

    A former `profile:` key is mapped to context and device when they are missing."""
    data = yaml.safe_load(text) or {}
    context = str(data.get("context") or "")
    device = str(data.get("device") or "")
    legacy = str(data.get("profile") or "")
    if not device and legacy in LEGACY_PROFILES:
        context, device = LEGACY_PROFILES[legacy]
    return {
        "context": context,
        "device": device,
        "features": [str(x) for x in (data.get("features") or [])],
        "ssh_allow_from": [str(x) for x in (data.get("ssh_allow_from") or [])],
        "ansible": data.get("ansible") is not False,
    }


def format_profile_yaml(
    context: str,
    device: str,
    features: Sequence[str],
    ssh_allow_from: Optional[Sequence[str]] = None,
    ansible: bool = True,
) -> str:
    data: Dict[str, object] = {}
    if context:
        data["context"] = context
    data["device"] = device
    if not ansible:
        data["ansible"] = False
    data["features"] = list(features) or ["zsh-full"]
    data["ssh_allow_from"] = list(ssh_allow_from or [])
    return "---\n" + yaml.dump(
        data, Dumper=_IndentDumper, sort_keys=False, default_flow_style=False
    )


def profile_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    data = parse_profile_file(path)
    feats = sorted(str(x) for x in (data.get("features") or []))
    allow = sorted(str(x) for x in (data.get("ssh_allow_from") or []))
    return (
        f"{data.get('context')}|{data.get('device')}|{data.get('ansible')}|"
        f"{','.join(feats)}|{','.join(allow)}"
    )


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
