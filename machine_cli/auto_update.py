"""Unattended update run by the background job (`machine update --auto`)."""

from __future__ import annotations

import contextlib
import fcntl
import subprocess
import types
from typing import Iterator, Optional

from . import events, system
from .core import log, warn
from .local_changes import classify_paths


class AutoUpdateMixin:
    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return system.run(
            ["git", "-C", str(self.repo), *args], capture=True, check=False
        )

    def is_system_commit(self, commit: str) -> bool:
        """System commits need Ansible or a host-config apply and are never applied unattended."""
        own_profile = self.host_config_path().relative_to(self.repo).as_posix()
        result = self._git(
            "diff-tree",
            "--root",
            "-r",
            "-m",
            "--no-renames",
            "--name-only",
            "--no-commit-id",
            commit,
        )
        paths = [line for line in (result.stdout or "").splitlines() if line]
        if own_profile in paths:
            return True
        return bool(self.read_update_state()["ansible_applied_rev"]) and bool(
            self.system_paths_relevant(paths)
        )

    def safe_update_target(self, upstream: str) -> Optional[str]:
        """Last incoming commit before the first system commit (None if there is none)."""
        result = self._git("rev-list", "--reverse", "--topo-order", f"HEAD..{upstream}")
        target = None
        for commit in (result.stdout or "").split():
            if self.is_system_commit(commit):
                break
            target = commit
        if target and not self._is_ancestor("HEAD", target):
            return None
        return target

    @contextlib.contextmanager
    def try_update_lock(self) -> Iterator[bool]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_dir / "update.lock", "w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            yield True

    def update_auto(self, args: types.SimpleNamespace) -> int:
        with self.try_update_lock() as acquired:
            if not acquired:
                log("another update is running; skipping the background update")
                return 0
            return self._update_auto_locked()

    def _update_auto_locked(self) -> int:
        self.run_local_resolvers()
        plan = self.update_plan(fetch=True)
        if plan["state"] == "no-upstream":
            return 0  # nothing to compare with; no state change, like a failed fetch
        if plan["state"] == "diverged":
            self.write_update_state("attention", plan["blockers"][0])
            self.event("update-auto", "blocked", "diverged")
            return 0
        if plan["state"] == "up-to-date":
            pending_system = "system" in plan["steps"]
            self.set_pending(pending_system)
            self.write_update_state("available" if pending_system else "none")
            return 0

        self.set_pending(True)
        if plan["local_changes"]:
            self.write_update_state(
                "attention",
                "local changes block the automatic update: "
                + ", ".join(plan["local_changes"]),
            )
            self.event("update-auto", "blocked", "local-changes")
            return 0

        target = self.safe_update_target(plan["upstream"])
        if target is None:
            self.write_update_state("available")
            return 0
        failed = self.read_update_state()["failed_revision"]
        if failed == target:
            self.write_update_state(
                "attention",
                f"the automatic update to {target[:8]} broke zsh and was reverted; "
                "run: machine update",
            )
            self.event("update-auto", "blocked", "previously-reverted")
            return 0
        return self._apply_auto(plan["upstream"], target)

    def _apply_auto(self, upstream: str, target: str) -> int:
        timer = events.Timer()
        previous = self.repo_revision()
        steps = set(classify_paths(self.incoming_changes(target)))
        merged = self._git("merge", "--ff-only", target)
        if merged.returncode != 0:
            self.write_update_state(
                "attention", "fast-forward failed; run: machine update"
            )
            self.event("update-auto", "blocked", "fast-forward-failed")
            return 0
        if "dotfiles" in steps and not self._dotfiles_apply_quiet():
            return self._revert_auto(
                previous, target, "dotfile apply failed", "apply-failed", timer
            )
        if "tools" in steps and not self._tools_install_quiet():
            return self._revert_auto(
                previous, target, "tool install failed", "tools-failed", timer
            )

        reason = self.zsh_health_failure()
        if reason:
            return self._revert_auto(previous, target, reason, "zsh-unhealthy", timer)

        remaining = (
            self.repo_revision() != self._git("rev-parse", upstream).stdout.strip()
        )
        self.set_pending(remaining)
        self.write_update_state("available" if remaining else "updated")
        self.event("update-auto", "applied", duration=timer.seconds())
        log(f"updated automatically to {self.repo_revision()[:8]}")
        return 0

    def _dotfiles_apply_quiet(self) -> bool:
        if not (system.have("mise") and self.mise_local_config.is_file()):
            return True
        try:
            self.run_dotfiles_apply()
        except SystemExit:
            return False
        return True

    def zsh_health_failure(self) -> str:
        """Reason why zsh no longer starts cleanly, or an empty string."""
        helper = self.home / ".zsh/zsh-handoff-check.sh"
        if not helper.is_file() or not system.have("zsh"):
            return ""
        result = subprocess.run(
            [
                "bash",
                "-c",
                '. "$1"; _zhc_run_checks "$(command -v zsh)"',
                "bash",
                str(helper),
            ],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        return (
            "" if result.returncode == 0 else (result.stdout.strip() or "zsh unhealthy")
        )

    def _revert_auto(
        self,
        previous: str,
        target: str,
        reason: str,
        code: str,
        timer: events.Timer,
    ) -> int:
        warn(f"automatic update failed ({reason}); reverting to {previous[:8]}")
        self._git("reset", "--hard", previous)
        self.event("update-auto", "reverted", code, timer.seconds())
        self._dotfiles_apply_quiet()
        self.write_update_state(
            "attention",
            f"the automatic update to {target[:8]} was reverted: {reason}; "
            "check it, then run: machine update",
            failed_revision=target,
        )
        return 0
