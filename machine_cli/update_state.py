"""`machine update`: the update state file and the update lock."""

from __future__ import annotations

import contextlib
import fcntl
from typing import Iterator

from . import system
from .core import die

STATE_KEYS = (
    "state",
    "reason",
    "revision",
    "pending",
    "failed_revision",
    "ansible_applied_rev",
    "stash",
)


class UpdateStateMixin:
    def repo_revision(self) -> str:
        result = system.run(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
            check=False,
            capture=True,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def write_update_state(self, state: str, reason: str = "", **extra: str) -> None:
        """Write the one state file (key=value lines); shells read state, reason, revision.

        Other keys survive a write unless passed: pending (1 while upstream is ahead),
        failed_revision (reverted automatic update) and ansible_applied_rev."""
        values = self.read_update_state()
        values.update(extra)
        values.update(state=state, reason=reason, revision=self.repo_revision())
        tmp = self.update_state.with_name(self.update_state.name + ".tmp")
        tmp.write_text(
            "".join(f"{key}={values.get(key, '')}\n" for key in STATE_KEYS),
            encoding="utf-8",
        )
        tmp.replace(self.update_state)

    def read_update_state(self) -> dict[str, str]:
        values = {key: "" for key in STATE_KEYS}
        values["state"] = "none"
        if self.update_state.is_file():
            for line in self.update_state.read_text(encoding="utf-8").splitlines():
                key, _, value = line.partition("=")
                if key in values:
                    values[key] = value
        return values

    def _read_update_state_text(self) -> str:
        """The raw state file, "" when there is none."""
        if not self.update_state.is_file():
            return ""
        return self.update_state.read_text(encoding="utf-8")

    def set_pending(self, pending: bool) -> None:
        values = self.read_update_state()
        self.write_update_state(
            values["state"], values["reason"], pending="1" if pending else ""
        )

    def record_ansible_applied(self) -> None:
        values = self.read_update_state()
        self.write_update_state(
            values["state"], values["reason"], ansible_applied_rev=self.repo_revision()
        )

    @contextlib.contextmanager
    def update_lock(self) -> Iterator[None]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_dir / "update.lock", "w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                die("another update is already running")
            yield
