"""`machine setup`: choose device, context and features, then run the setup steps."""

from __future__ import annotations

import dataclasses
import importlib
import os
import types

from . import steps, system
from .core import CONTEXTS, DEVICES, die, parse_profile_file


def log(message: str) -> None:
    """Log through `machine_cli.commands.log`, the name tests replace to watch setup and apply."""
    importlib.import_module(".commands", __package__).log(message)


@dataclasses.dataclass
class _SetupPlan:
    """What setup decided before it writes the host config and runs the steps."""

    context: str
    device: str
    skip_ansible: bool
    ask_become: bool
    features: list = dataclasses.field(default_factory=list)
    allow_from: list = dataclasses.field(default_factory=list)


def _validate_setup_args(args: types.SimpleNamespace) -> None:
    if args.context and args.context not in CONTEXTS:
        die(f"invalid context {args.context!r}")
    if args.device and args.device not in DEVICES:
        die(f"invalid device {args.device!r}")


def _needs_bitwarden(device) -> bool:
    return (
        device != "container"
        and not system.in_docker()
        and os.environ.get("MACHINE_SKIP_BW") != "1"
    )


def _shell_ready_before_ansible(runner: steps.Steps, plan: _SetupPlan) -> bool:
    return (
        not plan.skip_ansible
        and runner.ok("dotfile apply")
        and runner.ok("tool install")
    )


class SetupMixin:
    def cmd_setup(self, args: types.SimpleNamespace) -> int:
        self.unattended = args.yes
        _validate_setup_args(args)
        self.ensure_dirs()
        saved = self._setup_saved_host()
        device = args.device or self._setup_device(args.yes)
        context = args.context or self._setup_context(device, args.yes)
        skip_ansible, ask_become = self._setup_ansible_flags(args, device)
        plan = _SetupPlan(context, device, skip_ansible, ask_become)

        need_bw = _needs_bitwarden(device)
        self.ensure_bootstrap_tools(not args.skip_dotfiles, not skip_ansible, need_bw)
        plan.features = self._setup_features(args, saved, plan)

        # Early, so the SSH host key and env pull find an unlocked vault.
        if need_bw:
            self.setup_bitwarden()

        plan.allow_from = self._setup_allow_from(args.yes, saved, context)
        self._write_setup_host_config(plan, args.yes)
        return self._run_setup_steps(args, plan)

    def _setup_saved_host(self) -> dict:
        # A fresh host starts from its repository host config (features, allowed hosts).
        if self.applied_host_path.is_file():
            return self.applied_host()
        if self.host_config_path().is_file():
            return parse_profile_file(self.host_config_path())
        return {}

    def _setup_device(self, yes) -> str:
        device = self.default_device()
        if yes or device == "container":
            return device
        return self.prompt_device(device)

    def _setup_context(self, device, yes) -> str:
        context = self.default_context()
        if device == "container":
            return context if system.in_docker() else ""
        return context if yes else self.prompt_context(context)

    def _setup_ansible_flags(self, args: types.SimpleNamespace, device) -> tuple:
        """(skip_ansible, ask_become) for this device and host config."""
        if device == "container":
            return True, False
        ansible_off = not self.saved_ansible()
        return args.skip_ansible or ansible_off, not args.no_become

    def _setup_features(
        self, args: types.SimpleNamespace, saved: dict, plan: _SetupPlan
    ) -> list:
        features = list(args.features or [])
        if not features:
            defaults = self._setup_default_features(saved, plan)
            features = (
                defaults
                if args.yes
                else self.prompt_features(plan.context, plan.device, defaults)
            )
        return self.allowed_features(features, plan.context, plan.device)

    def _setup_default_features(self, saved: dict, plan: _SetupPlan) -> list:
        same_host = (
            saved.get("context") == plan.context and saved.get("device") == plan.device
        )
        if same_host and saved["features"]:
            return list(saved["features"])
        return self.default_features_for(plan.context, plan.device)

    def _setup_allow_from(self, yes, saved: dict, context) -> list:
        allow_from = list(saved.get("ssh_allow_from") or [])
        if not yes and system.is_tty():
            allow_from = self.prompt_ssh_allow_from(allow_from, context)
        return allow_from

    def _write_setup_host_config(self, plan: _SetupPlan, yes) -> None:
        self.write_profile(plan.context, plan.device, plan.features, plan.allow_from)
        self.write_dotfile_groups()
        if not system.in_docker():
            self.switch_origin_to_ssh(plan.context, plan.device)
        log(
            f"wrote {self.applied_host_path} "
            f"(context={plan.context or 'none'}, device={plan.device})"
        )
        self.persist_host_config(
            plan.context, plan.device, plan.features, plan.allow_from, yes=yes
        )

    def _run_setup_steps(self, args: types.SimpleNamespace, plan: _SetupPlan) -> int:
        # Shell first, so a new terminal is usable while Ansible runs; a failing step
        # does not stop the steps that do not need it (see Steps).
        runner = steps.Steps()
        if not args.skip_dotfiles:
            self._run_setup_shell_steps(runner, args, plan)
        self._run_setup_ansible(runner, args, plan)
        # After Ansible, which installs niri and DMS; the step needs the dotfile group.
        if not args.skip_dotfiles:
            runner.run("niri config", self.run_niri_config)
        self._run_setup_ssh_key_steps(runner, plan)

        self.maybe_tailscale_login(plan.features)

        # Last: the timer starts the background update, which must not run during Ansible.
        if not args.skip_dotfiles and plan.device != "container":
            runner.run("update timers", self.ensure_update_timer)
        if runner.report("setup"):
            return 1
        log("setup finished")
        return 0

    def _run_setup_shell_steps(
        self, runner: steps.Steps, args: types.SimpleNamespace, plan: _SetupPlan
    ) -> None:
        runner.run("env pull", self.cmd_env_pull)
        runner.run("dotfile apply", self.run_dotfiles_apply)
        # After the dotfile apply, which moves a hand-written ~/.ssh/config aside
        # for the legacy hosts; its questions still come before the tool install.
        runner.run("ssh host list", self.pull_ssh_host_list)
        runner.run(
            "ssh host list entry", lambda: self.offer_self_in_host_list(args.yes)
        )
        if os.environ.get("MACHINE_SKIP_TOOLS") != "1":
            runner.run("tool install", self.run_tools_install, needs=["dotfile apply"])
        runner.run("syncthing ignores", self.run_syncthing_ignores)
        if _shell_ready_before_ansible(runner, plan):
            log(
                "the shell is ready: open a new terminal to work in it "
                "while Ansible continues here"
            )

    def _run_setup_ansible(
        self, runner: steps.Steps, args: types.SimpleNamespace, plan: _SetupPlan
    ) -> None:
        if plan.skip_ansible:
            reason = (
                "" if self.saved_ansible() else " (ansible: false in the host config)"
            )
            log("skipping ansible" + reason)
            return
        runner.run(
            "ansible",
            lambda: self.run_ansible_or_hint(
                args.playbook, args.limit, args.local, plan.ask_become
            ),
        )

    def _run_setup_ssh_key_steps(self, runner: steps.Steps, plan: _SetupPlan) -> None:
        if "ssh-host-key" in plan.features and plan.device != "container":

            def ssh_host_key() -> None:
                # A key left unprovisioned is reported by the step itself, not a failure.
                self.provision_host_ssh_key()

            runner.run("ssh host key", ssh_host_key)
        runner.run("ssh key files", self.sync_repo_key_files)
