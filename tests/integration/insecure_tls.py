"""Whether the Docker tests skip TLS verification (test image and containers only)."""

from __future__ import annotations

import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Callable, Mapping, Optional

MACHINE = Path(__file__).resolve().parents[2] / "machine_cli/machine"


def _default_profile() -> Optional[str]:
    """The profile `machine` would pick on this host, or None if it cannot run."""
    try:
        module = SourceFileLoader("machine_cli_tls", str(MACHINE)).load_module()
        return module.Machine().default_profile()
    except Exception:  # missing dependency or unreadable profile: keep verification
        return None
    finally:
        sys.modules.pop("machine_cli_tls", None)


def insecure_tls(
    env: Mapping[str, str] = os.environ,
    profile: Callable[[], Optional[str]] = _default_profile,
) -> bool:
    """An explicit 0 or 1 wins; otherwise on for work machines only."""
    explicit = env.get("DOTFILES_TEST_INSECURE_TLS")
    if explicit in ("0", "1"):
        return explicit == "1"
    return profile() == "work-machine"
