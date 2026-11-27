"""`machine update`: the handoff to the machine code of the new revision."""

from __future__ import annotations

import os
import sys
import types
from typing import Optional

from . import core, system
from .core import log, warn

# The handoff to the code of a new revision (`update --resume-*`); the new
# checkout lists the versions it accepts in machine_cli/resume-protocol.
RESUME_PROTOCOL = "1"


class UpdateHandoffMixin:
    def machine_code_changed(self, previous: str) -> bool:
        """True when `machine_cli/` differs between `previous` and the checkout."""
        result = self._git(
            "diff", "--name-only", previous, "HEAD", "--", "machine_cli/"
        )
        return bool((result.stdout or "").strip())

    def hand_over_to_new_code(self, previous: str) -> bool:
        """True when `machine_cli/` changed and the new code accepts the handoff.

        A revision without this handoff (for example after a rollback) would reject
        the resume options; its steps run with the code that is running."""
        if not self.machine_code_changed(previous):
            return False
        marker = self.repo / "machine_cli" / "resume-protocol"
        try:
            lines = marker.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        words = [w for line in lines if not line.startswith("#") for w in line.split()]
        if RESUME_PROTOCOL in words:
            return True
        log(
            "machine_cli changed, but the new code does not accept the handoff; "
            "running the remaining steps with the code that is running"
        )
        return False

    def machine_entry_command(self) -> list[str]:
        """Start the checkout's CLI; run directly, uv resolves its dependencies."""
        script = self.repo / "machine_cli" / "machine"
        command = (
            [str(script)]
            if os.access(script, os.X_OK)
            else [sys.executable, str(script)]
        )
        return command + (["--debug"] if core.debug_enabled() else [])

    def run_new_machine_code(
        self, args: types.SimpleNamespace, previous: str
    ) -> Optional[int]:
        """Run the remaining update steps with the new code; None if it cannot start.

        This process keeps the update lock while the child runs. Older revisions
        call `update --resume-from`, so its meaning must stay the same."""
        command = self.machine_entry_command() + ["update", "--resume-from", previous]
        if getattr(args, "system", False):
            command.append("--system")
        if getattr(args, "skip_ansible", False):
            command.append("--skip-ansible")
        state_before = self._read_update_state_text()
        log("machine_cli changed; running the remaining steps with the new code")
        try:
            result = system.run(command, check=False)
        except OSError as exc:
            warn(
                f"could not start the new machine code ({exc}); "
                "running the remaining steps with the code that is running"
            )
            return None
        if result.returncode != 0 and self._read_update_state_text() == state_before:
            # The child stopped before it recorded a result, e.g. on a traceback.
            self.write_update_state(
                "attention",
                f"update failed: the new machine code stopped (exit "
                f"{result.returncode}); run: machine update",
                pending="",
            )
        return result.returncode

    def resume_update(self, args: types.SimpleNamespace) -> int:
        """The steps after the checkout update, for an older `machine` that holds the lock."""
        previous = args.resume_from
        if getattr(args, "auto", False):
            return self.resume_auto(previous, args.resume_result)
        incoming = self.incoming_changes("HEAD", previous)
        return self._update_steps(args, set(self.plan_steps(incoming, "HEAD")))
