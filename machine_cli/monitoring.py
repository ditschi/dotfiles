"""Telegraf state on hosts with the feature `monitoring` (checked without root)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import system


TELEGRAF_CONF_DIR = Path("/etc/telegraf/telegraf.d")

NOT_INSTALLED = "not-installed"
NO_OUTPUT = "no-output"
NOT_ACTIVE = "not-active"


class MonitoringMixin:
    telegraf_conf_dir = TELEGRAF_CONF_DIR

    def _systemctl(self, *args: str) -> str:
        result = system.run(["systemctl", *args, "telegraf"], check=False, capture=True)
        return (result.stdout or "").strip()

    def telegraf_problem(self) -> Optional[str]:
        """None when Telegraf works or the host has no `monitoring`, else the reason."""
        if "monitoring" not in self.saved_features() or not system.have("systemctl"):
            return None
        if not system.have("telegraf"):
            return NOT_INSTALLED
        if self._systemctl("is-active") in {"active", "activating"}:
            return None
        # /etc/default/telegraf (remote configs) is root-only; the role enables the
        # unit only when Telegraf has an output and disables it otherwise.
        has_output = any(self.telegraf_conf_dir.glob("99_output_*.conf"))
        if not has_output and self._systemctl("is-enabled") != "enabled":
            return NO_OUTPUT
        return NOT_ACTIVE

    def telegraf_problem_text(self, problem: str) -> str:
        return {
            NOT_INSTALLED: "monitoring is on but telegraf is not installed",
            NO_OUTPUT: (
                "telegraf has no output: the Bitwarden item "
                f"'{self.influx_item}' was not available at the last apply"
            ),
            NOT_ACTIVE: "telegraf is not running",
        }[problem]
