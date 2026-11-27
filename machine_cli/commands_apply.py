"""`machine apply`: apply the host config and Ansible, locally or to a remote host."""

from __future__ import annotations

import dataclasses
import importlib
import os
import subprocess
import types

from . import steps, system
from .core import die


def log(message: str) -> None:
    """Log through `machine_cli.commands.log`, the name tests replace to watch setup and apply."""
    importlib.import_module(".commands", __package__).log(message)


@dataclasses.dataclass
class _ApplyOptions:
    playbook: str
    ask_become: bool
    skip_ansible: bool
    limit: str

    @classmethod
    def from_args(cls, args: types.SimpleNamespace) -> "_ApplyOptions":
        return cls(
            playbook=getattr(args, "playbook", "workstation") or "workstation",
            ask_become=not getattr(args, "no_become", False),
            skip_ansible=getattr(args, "skip_ansible", False),
            limit=getattr(args, "limit", "") or "",
        )


@dataclasses.dataclass
class _LocalApply:
    """A local apply: what a failure can restore, and the step that was running."""

    options: _ApplyOptions
    backup: object
    profile_changed: bool
    failed_step: str = "sudo"


class ApplyMixin:
    def run_ansible_or_hint(self, playbook, limit, local, ask_become) -> None:
        """Run Ansible; on failure name the host-config setting for hosts without root."""
        try:
            self.run_ansible(playbook, limit, local, ask_become)
        except subprocess.CalledProcessError:
            log(
                "ansible failed; if this host cannot become root, set `ansible: false` "
                f"in {self.host_config_path(limit or None).relative_to(self.repo)}"
            )
            raise

    def cmd_apply(self, args: types.SimpleNamespace) -> int:
        """Apply the host config and Ansible; optionally skip system provisioning."""
        options = _ApplyOptions.from_args(args)
        if options.limit:
            return self._apply_remote(options)
        return self._apply_local(args, options)

    def _apply_remote(self, options: _ApplyOptions) -> int:
        host_file = self.host_config_path(options.limit)
        if not host_file.is_file():
            die(
                f"missing {host_file.relative_to(self.repo)}; "
                f"create it or run setup on that host"
            )
        log(f"remote apply using {host_file.relative_to(self.repo)}")
        if options.skip_ansible:
            log(
                "ansible skipped (--skip-ansible); remote system changes remain pending"
            )
            return 0
        try:
            self.run_ansible(
                options.playbook,
                limit=options.limit,
                force_local=False,
                ask_become=options.ask_become,
                extra_vars_file=host_file,
            )
        except subprocess.CalledProcessError:
            die(
                f"remote apply failed for {options.limit}; "
                "fix the host config / playbook, then re-run. "
                "No automatic remote revert (edit git and apply again)."
            )
        log("remote apply finished")
        return 0

    def _apply_local(self, args: types.SimpleNamespace, options: _ApplyOptions) -> int:
        run = self._prepare_local_apply(args, options)
        data = self.applied_host()
        if self.current_device() == "container":
            log("container: nothing to apply")
            return 0
        self.allowed_features(
            data["features"], self.current_context(), self.current_device()
        )
        # `machine update` runs this step itself before it calls apply.
        if getattr(args, "user_steps", True):
            user_steps = steps.Steps()
            user_steps.run("syncthing ignores", self.run_syncthing_ignores)
            user_steps.report("apply")
        if self._local_ansible_skipped(data, options):
            return 0
        self._apply_system(run)
        log("apply finished")
        return 0

    def _prepare_local_apply(
        self, args: types.SimpleNamespace, options: _ApplyOptions
    ) -> _LocalApply:
        # Local apply: backup first, then repo host file wins
        # `machine update` syncs the host config before calling us; it hands over the
        # pre-sync backup so a failed apply can still revert that change.
        backup = getattr(args, "profile_backup", None) or self.backup_applied_host()
        profile_changed = self.sync_host_config_from_repo() or bool(
            getattr(args, "profile_changed", False)
        )
        if not self.applied_host_path.is_file():
            die("no applied host config; run machine setup first")
        return _LocalApply(options, backup, profile_changed)

    def _local_ansible_skipped(self, data: dict, options: _ApplyOptions) -> bool:
        if not data["ansible"]:
            log("ansible: false in the host config; skipping ansible")
            return True
        if options.skip_ansible:
            log("ansible skipped (--skip-ansible); system changes remain pending")
            return True
        return False

    def _apply_system(self, run: _LocalApply) -> None:
        try:
            self._apply_system_steps(run)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            log(f"apply failed: {exc}")
            if run.backup:
                self.restore_applied_host(run.backup)
                self._recover_failed_apply(run)
            die("apply aborted and the applied host config restored where possible")

    def _apply_system_steps(self, run: _LocalApply) -> None:
        ask_become = run.options.ask_become
        # First, so that no sudo prompt interrupts the run later.
        self.authenticate_sudo_for_ansible(ask_become)
        self.ensure_bootstrap_tools(
            False,
            True,
            not system.in_docker() and os.environ.get("MACHINE_SKIP_BW") != "1",
        )
        # The tool install can outlast the ticket; ask again before Ansible, so
        # that a failure here is still a sudo failure without a recovery run.
        self.authenticate_sudo_for_ansible(ask_become)
        run.failed_step = "Ansible"
        self.run_ansible_or_hint(run.options.playbook, "", True, ask_become=ask_become)
        run.failed_step = "health check"
        if not self.health_check_after_apply():
            raise RuntimeError("the health check after the apply failed (see above)")

    def _recover_failed_apply(self, run: _LocalApply) -> None:
        """After the host config was restored: re-run Ansible or say what to do."""
        if run.failed_step == "sudo":
            log("Ansible did not run; the host config was restored")
        elif run.profile_changed:
            self._rerun_ansible_after_restore(run.options)
        elif run.failed_step == "Ansible":
            log(
                "host config was unchanged; not retrying the failed apply. "
                "Review Ansible's error; where sudo is restricted, running "
                "`sudo ansible-playbook` as root needs administrator "
                "approval, not a different password."
            )
        else:
            log(
                "host config was unchanged; not retrying the failed apply. "
                "Fix the health-check failure above, then run: machine apply"
            )

    def _rerun_ansible_after_restore(self, options: _ApplyOptions) -> None:
        log("re-running ansible with the restored host config")
        try:
            self.run_ansible(
                options.playbook, force_local=True, ask_become=options.ask_become
            )
        except subprocess.CalledProcessError:
            log("revert ansible also failed; check the host manually")
