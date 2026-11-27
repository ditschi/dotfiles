"""`machine update`: lock and timers, and the execution of an update.

The local-change resolvers, the incoming-change plan, the state file, the conflict
handling and the handoff to new code live in the `update_*` modules; `UpdateMixin`
combines them, so the `machine` CLI class has every method under its old name."""

from __future__ import annotations

import getpass
import json
import subprocess
import types
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from . import events, system
from .core import die, log, warn
from .steps import Steps
from .update_conflicts import UpdateConflictsMixin
from .update_handoff import RESUME_PROTOCOL, UpdateHandoffMixin
from .update_overrides import LocalOverridesMixin, Resolver
from .update_plan import UpdatePlanMixin
from .update_state import STATE_KEYS, UpdateStateMixin

__all__ = [
    "OSD_VPN_CONNECT",
    "RESUME_PROTOCOL",
    "STATE_KEYS",
    "Resolver",
    "UpdateMixin",
]

# The OSD VPN tool of the managed work laptops; the VPN watcher needs it.
OSD_VPN_CONNECT = Path("/usr/bin/osd-vpn-connect")

UPDATE_TIMERS = ("dotfiles-update-check.timer", "machine-disk-check.timer")


@dataclass
class UpdateRun:
    """What the steps after the checkout update share."""

    args: types.SimpleNamespace
    steps: set[str]
    runner: Steps
    profile_backup: Optional[Path]
    profile_changed: bool
    ansible_reason: str
    skip_ansible: bool
    sudo_failed: bool = False
    not_set_up: str = ""
    zsh_failure: str = ""

    def restores_host_config(self) -> bool:
        """True when the new host config must not count as applied (sudo failed)."""
        if not self.sudo_failed:
            return False
        return bool(self.profile_changed and self.profile_backup)


class UpdateMixin(
    LocalOverridesMixin,
    UpdatePlanMixin,
    UpdateStateMixin,
    UpdateConflictsMixin,
    UpdateHandoffMixin,
):
    # --- timers -----------------------------------------------------------

    def ensure_update_timer(self) -> None:
        """Enable the update check and the low-disk check timers of the systemd group,
        and enable or disable the units that follow a feature."""
        units = self.home / ".config/systemd/user"
        timers = [name for name in UPDATE_TIMERS if (units / name).is_file()]
        work_net = self.work_net_units(units) + self.ssh_tunnel_units(units)
        if not (timers or work_net):
            return
        if not system.have("systemctl"):
            return
        system.run(["systemctl", "--user", "daemon-reload"], check=False, capture=True)
        for timer in timers:
            system.run(
                ["systemctl", "--user", "enable", "--now", timer],
                check=False,
                capture=True,
            )
        self._apply_unit_states(units, work_net)
        self.ensure_linger()

    def _apply_unit_states(self, units: Path, wanted_units: List[Tuple[str, bool]]):
        """Enable the wanted units and disable the others."""
        for unit, wanted in wanted_units:
            system.run(
                [
                    "systemctl",
                    "--user",
                    "enable" if wanted else "disable",
                    "--now",
                    unit,
                ],
                check=False,
                capture=True,
            )
        # A unit whose group was unlinked leaves its enable link behind.
        for unit, wanted in wanted_units:
            link = units / "default.target.wants" / unit
            if not wanted and link.is_symlink():
                link.unlink()

    def ssh_tunnel_units(self, units: Path) -> List[Tuple[str, bool]]:
        """The reverse tunnel unit (feature ssh-tunnel): present or still enabled."""
        unit = "ssh-tunnel.service"
        if (units / unit).is_file() or (
            units / "default.target.wants" / unit
        ).is_symlink():
            return [(unit, "ssh-tunnel" in self.saved_features())]
        return []

    def work_net_units(self, units: Path) -> List[Tuple[str, bool]]:
        """work-net units of the work group and whether this host wants them."""
        found = []
        if (units / "work-net-kerberos.timer").is_file():
            found.append(
                ("work-net-kerberos.timer", "kerberos" in self.saved_features())
            )
        if (units / "work-net-vpn-watch.service").is_file():
            found.append(
                (
                    "work-net-vpn-watch.service",
                    self.current_device() == "desktop" and OSD_VPN_CONNECT.exists(),
                )
            )
        return found

    def ensure_linger(self) -> None:
        """Keep the user manager running without a login so the timer fires on headless hosts."""
        if not system.have("loginctl") or system.in_docker():
            return
        user = getpass.getuser()
        state = system.run(
            ["loginctl", "show-user", user, "--property=Linger", "--value"],
            check=False,
            capture=True,
        )
        if (state.stdout or "").strip() == "yes":
            return
        result = system.run(
            ["loginctl", "enable-linger", user], check=False, capture=True
        )
        if result.returncode != 0:
            log(
                "could not enable linger; the update timer runs only while you are "
                f"logged in (run: sudo loginctl enable-linger {user})"
            )

    # --- commands ---------------------------------------------------------

    def update_check(self, as_json: bool) -> int:
        plan = self.update_plan(fetch=True)
        if as_json:
            print(json.dumps(plan, indent=2))
        else:
            self.print_update_plan(plan)
        return 0

    def cmd_update(self, args: types.SimpleNamespace) -> int:
        if getattr(args, "check", False):
            return self.update_check(getattr(args, "json", False))
        if getattr(args, "resume_from", ""):
            return self.resume_update(args)
        if getattr(args, "auto", False):
            return self.update_auto(args)
        with self.update_lock():
            timer = events.Timer()
            try:
                code = self._update_locked(args)
            except SystemExit:
                self.event(
                    "update", "failed", "force" if args.force else "", timer.seconds()
                )
                raise
            self.event(
                "update",
                "applied" if code == 0 else "failed",
                "force" if args.force else "",
                timer.seconds(),
            )
            return code

    def _confirm_bootstrap(self) -> bool:
        answer = input("Run bootstrap now? [Y/n]: ").strip().lower()
        return answer in ("", "y", "yes")

    def _update_locked(self, args: types.SimpleNamespace) -> int:
        self.ensure_update_timer()
        self.run_local_resolvers(interactive=True)
        previous = self.repo_revision()
        plan = self.update_plan(fetch=True)
        if plan["state"] == "no-upstream":
            self.write_update_state("attention", plan["blockers"][0])
            die(plan["blockers"][0])
        if plan["state"] == "diverged":
            plan = self._rebase_diverged(plan, args.force)
        elif plan["conflicts"]:
            plan = self.resolve_conflicts(plan, args.force)
        self.merge_upstream(plan)
        if self.hand_over_to_new_code(previous):
            code = self.run_new_machine_code(args, previous)
            if code is not None:
                return code
        return self._update_steps(args, set(plan["steps"]))

    def ansible_reason(
        self, args: types.SimpleNamespace, steps: set[str], profile_changed: bool
    ) -> str:
        """Why this update runs Ansible, or "" when it does not."""
        if not self.saved_ansible():
            return ""
        if profile_changed:
            return "host config changed"
        if args.system:
            return "--system"
        if "system" in steps:
            return "system files changed"
        return ""

    # --- the steps after the checkout update ------------------------------

    def _update_steps(self, args: types.SimpleNamespace, steps: set[str]) -> int:
        """Everything after the checkout update: host config, env, dotfiles, tools, Ansible."""
        profile_backup = self.backup_applied_host()
        profile_changed = self.sync_host_config_from_repo()

        # From here a failing step does not stop the steps that do not need it; the
        # env pull comes first so that its questions come before the tool install.
        run = UpdateRun(
            args=args,
            steps=steps,
            runner=Steps(),
            profile_backup=profile_backup,
            profile_changed=profile_changed,
            ansible_reason=self.ansible_reason(args, steps, profile_changed),
            skip_ansible=getattr(args, "skip_ansible", False),
        )
        self._authenticate_sudo_step(run)
        # Before the env pull, so that {{bw:<user>/password}} references resolve to
        # the passwords just copied from Key Vault.
        run.runner.run("technical user passwords", self.sync_techuser_passwords_step)
        run.runner.run("env pull", self.cmd_env_pull)

        # Converge check: runs also when nothing was incoming; idempotent and cheap.
        self._converge_step(run)
        self.check_ssh_key_backup()
        run.runner.run("ssh key files", self.sync_repo_key_files)
        self._zsh_check_step(run)
        self._ansible_step(run)

        # After Ansible, which installs niri and DMS.
        if not run.not_set_up:
            run.runner.run("niri config", self.run_niri_config)

        # Again after the dotfiles and the host config: the unit of a feature this
        # update added (ssh-tunnel) exists only now.
        if not run.not_set_up and self.current_device() != "container":
            run.runner.run("update timers", self.ensure_update_timer)

        if run.restores_host_config():
            # The steps above used the new host config. Like a failed apply, it only
            # counts as applied when Ansible ran with it; the next update retries.
            self.restore_applied_host(run.profile_backup)
        return self._finish_update(run)

    def _ansible_needs_sudo(self, run: UpdateRun) -> bool:
        if not run.ansible_reason or run.skip_ansible:
            return False
        return self.current_device() != "container"

    def _authenticate_sudo_step(self, run: UpdateRun) -> None:
        """First, so that no sudo prompt interrupts the run later. A failure only
        skips Ansible; the steps that need no root still run."""
        if not self._ansible_needs_sudo(run):
            return
        try:
            self.authenticate_sudo_for_ansible(True)
        except (subprocess.CalledProcessError, OSError) as exc:
            reason = getattr(exc, "output", None) or str(exc)
            run.runner.fail("ansible apply", reason or "sudo is not available")
            run.sudo_failed = True

    def _converge_step(self, run: UpdateRun) -> None:
        """Apply the dotfiles and tools, or record that this host is not set up."""
        if self.mise_local_config.is_file() and system.have("mise"):
            run.runner.run("dotfile apply", self.run_dotfiles_apply)
            run.runner.run("ssh host list", self.pull_ssh_host_list)
            run.runner.run(
                "tool install", self.run_tools_install, needs=["dotfile apply"]
            )
            run.runner.run("syncthing ignores", self.run_syncthing_ignores)
            return
        run.not_set_up = self._offer_bootstrap()
        run.runner.run("ssh host list", self.pull_ssh_host_list)

    def _offer_bootstrap(self) -> str:
        """Warn that this host is not set up and offer bootstrap; returns what is still missing."""
        reason = (
            "mise is not installed"
            if not system.have("mise")
            else f"{self.mise_local_config} is missing"
        )
        message = (
            f"this host is not set up: {reason}, so dotfiles and tools were "
            f"not applied (run: {self.repo}/bootstrap)"
        )
        warn(message)
        if system.is_tty() and self._confirm_bootstrap():
            system.run([str(self.repo / "bootstrap")])
            return ""
        return message

    def _zsh_check_step(self, run: UpdateRun) -> None:
        if not (run.steps & {"dotfiles", "shell"}) or run.not_set_up:
            return
        run.runner.run(
            "zsh health check",
            lambda: self._record_zsh_failure(run),
            needs=["dotfile apply"],
        )
        if run.zsh_failure:
            run.runner.fail("zsh health check", "zsh does not start cleanly")
            warn(f"zsh health check failed after the update:\n{run.zsh_failure}")

    def _record_zsh_failure(self, run: UpdateRun) -> None:
        run.zsh_failure = self.zsh_health_failure()

    def _ansible_step(self, run: UpdateRun) -> None:
        if not self.saved_ansible():
            log("ansible: false in the host config; system changes are not applied")
            return
        if not run.ansible_reason:
            return
        if run.skip_ansible:
            log(
                f"ansible skipped (--skip-ansible); system changes remain pending ({run.ansible_reason})"
            )
            return
        if not run.runner.ok("ansible apply"):
            return
        apply_args = types.SimpleNamespace(
            limit="",
            playbook="workstation",
            no_become=False,
            skip_ansible=False,
            profile_backup=run.profile_backup,
            profile_changed=run.profile_changed,
            user_steps=False,
        )
        log(f"applying system changes ({run.ansible_reason})")
        # cmd_apply restores the host config itself before it fails.
        run.runner.run("ansible apply", lambda: self.cmd_apply(apply_args))

    def _finish_update(self, run: UpdateRun) -> int:
        """Record the result of the update in the state file; the exit code."""
        self.update_failure_file.unlink(missing_ok=True)
        summary = run.runner.report("update")
        if summary:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            details = summary + (f"\n\n{run.zsh_failure}" if run.zsh_failure else "")
            self.update_failure_file.write_text(details + "\n", encoding="utf-8")
            self.write_update_state(
                "attention",
                f"update failed: {', '.join(run.runner.failed_names())}; "
                "see machine attention",
                pending="",  # the checkout is current; only steps failed
            )
            return 1  # the shell wrapper only reloads after a successful update
        if run.not_set_up:
            self.write_update_state("attention", run.not_set_up)
        else:
            self.write_update_state("updated", pending="", failed_revision="")
        log(
            "update finished"
            if not run.not_set_up
            else "update finished, host not set up"
        )
        return 0
