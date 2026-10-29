"""Whether the Docker tests skip TLS verification (test image and containers only)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Optional

from machine_loader import load_machine_module

MACHINE = Path(__file__).resolve().parents[2] / "machine_cli/machine"


def _default_context() -> Optional[str]:
    """The context `machine` would pick on this host, or None if it cannot run."""
    try:
        module = load_machine_module("machine_cli_tls", MACHINE)
        return module.Machine().default_context()
    except Exception:  # missing dependency or unreadable profile: keep verification
        return None
    finally:
        sys.modules.pop("machine_cli_tls", None)


def insecure_tls(
    env: Mapping[str, str] = os.environ,
    context: Callable[[], Optional[str]] = _default_context,
) -> bool:
    """An explicit 0 or 1 wins; otherwise on for work hosts only."""
    explicit = env.get("DOTFILES_TEST_INSECURE_TLS")
    if explicit in ("0", "1"):
        return explicit == "1"
    return context() == "work"
