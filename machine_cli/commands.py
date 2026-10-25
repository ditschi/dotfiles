"""Top-level commands: setup, apply, update, status, commit, push."""

from __future__ import annotations

import os
import subprocess
import types


from . import system
from .core import (
    CONTEXTS,
    DEVICES,
    log,
    die,
    profile_fingerprint,
)


class CommandsMixin:
    def cmd_setup(self, args: types.SimpleNamespace) -> int:
        self.unattended = args.yes
        context = args.context or ""
        device = args.device or ""
        if context and context not in CONTEXTS:
            die(f"invalid context {context!r}")
        if device and device not in DEVICES:
            die(f"invalid device {device!r}")
        self.ensure_dirs()
        saved = self.applied_host() if self.applied_host_path.is_file() else {}
        if not device:
            device = self.default_device()
            if not args.yes and device != "container":
                device = self.prompt_device(device)
        if not context:
            context = self.default_context()
            if device == "container":
                context = context if system.in_docker() else ""
            elif not args.yes:
                context = self.prompt_context(context)

        skip_ansible = args.skip_ansible
        ask_become = not args.no_become
        if device == "container":
            skip_ansible = True
            ask_become = False
        elif not self.saved_ansible():
            skip_ansible = True

        need_bw = (
            device != "container"
            and not system.in_docker()
            and os.environ.get("MACHINE_SKIP_BW") != "1"
        )
        self.ensure_bootstrap_tools(not args.skip_dotfiles, not skip_ansible, need_bw)

        features = list(args.features or [])
        if not features:
            same_host = (
                saved.get("context") == context and saved.get("device") == device
            )
            defaults = (
                self.saved_features()
                if same_host and self.saved_features()
                else self.default_features_for(context, device)
            )
            features = (
                defaults
                if args.yes
                else self.prompt_features(context, device, defaults)
            )
        features = self.allowed_features(features, context, device)

        # Early, so the SSH host key and env pull find an unlocked vault.
        if need_bw:
            self.setup_bitwarden()

        allow_from = self.saved_ssh_allow_from()
        if not args.yes and system.is_tty():
            allow_from = self.prompt_ssh_allow_from(allow_from, context)

        self.write_profile(context, device, features, allow_from)
        self.write_dotfile_groups()
        if not system.in_docker():
            self.switch_origin_to_ssh(context, device)
        log(
            f"wrote {self.applied_host_path} "
            f"(context={context or 'none'}, device={device})"
        )

        self.persist_host_config(context, device, features, allow_from, yes=args.yes)

        if skip_ansible:
            log(
                "skipping ansible"
                + (
                    ""
                    if self.saved_ansible()
                    else " (ansible: false in the host config)"
                )
            )
        else:
            self.run_ansible_or_hint(args.playbook, args.limit, args.local, ask_become)

        if "ssh-host-key" in features and device != "container":
            self.provision_host_ssh_key()

        self.maybe_tailscale_login(features)

        if not args.skip_dotfiles:
            self.run_dotfiles_apply()
            if os.environ.get("MACHINE_SKIP_TOOLS") != "1":
                self.run_tools_install()
            if device != "container":
                self.ensure_update_timer()
            self.cmd_env_pull()
        log("setup finished")
        return 0

    def run_ansible_or_hint(self, playbook, limit, local, ask_become, **kwargs) -> None:
        """Run Ansible; on failure name the host-config setting for hosts without root."""
        try:
            self.run_ansible(playbook, limit, local, ask_become, **kwargs)
        except subprocess.CalledProcessError:
            log(
                "ansible failed; if this host cannot become root, set `ansible: false` "
                f"in {self.host_config_path(limit or None).relative_to(self.repo)}"
            )
            raise

    def cmd_apply(self, args: types.SimpleNamespace) -> int:
        """Apply the host config (repo → applied copy) + ansible; revert on failure."""
        playbook = getattr(args, "playbook", "workstation") or "workstation"
        ask_become = not getattr(args, "no_become", False)
        limit = getattr(args, "limit", "") or ""

        if limit:
            host_file = self.host_config_path(limit)
            if not host_file.is_file():
                die(
                    f"missing {host_file.relative_to(self.repo)}; "
                    f"create it or run setup on that host"
                )
            log(f"remote apply using {host_file.relative_to(self.repo)}")
            try:
                self.run_ansible(
                    playbook,
                    limit=limit,
                    force_local=False,
                    ask_become=ask_become,
                    extra_vars_file=host_file,
                )
            except subprocess.CalledProcessError:
                die(
                    f"remote apply failed for {limit}; "
                    "fix the host config / playbook, then re-run. "
                    "No automatic remote revert (edit git and apply again)."
                )
            log("remote apply finished")
            return 0

        # Local apply: backup first, then repo host file wins
        # `machine update` syncs the host config before calling us; it hands over the
        # pre-sync backup so a failed apply can still revert that change.
        backup = getattr(args, "profile_backup", None) or self.backup_applied_host()
        profile_changed = self.sync_host_config_from_repo() or bool(
            getattr(args, "profile_changed", False)
        )
        if not self.applied_host_path.is_file():
            die("no applied host config; run machine setup first")

        data = self.applied_host()
        if self.current_device() == "container":
            log("container: nothing to apply")
            return 0
        self.allowed_features(
            data["features"], self.current_context(), self.current_device()
        )
        if not data["ansible"]:
            log("ansible: false in the host config; skipping ansible")
            return 0

        try:
            self.ensure_bootstrap_tools(
                False,
                True,
                not system.in_docker() and os.environ.get("MACHINE_SKIP_BW") != "1",
            )
            self.run_ansible_or_hint(playbook, "", True, ask_become=ask_become)
            if not self.health_check_after_apply():
                raise RuntimeError("health check failed")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            log(f"apply failed: {exc}")
            if backup:
                self.restore_applied_host(backup)
                if profile_changed:
                    log("re-running ansible with the restored host config")
                    try:
                        self.run_ansible(
                            playbook, force_local=True, ask_become=ask_become
                        )
                    except subprocess.CalledProcessError:
                        log("revert ansible also failed; check the host manually")
                else:
                    log(
                        "host config was unchanged; not retrying the failed apply. "
                        "Review Ansible's error; sudo command restrictions require "
                        "administrator approval, not a different password."
                    )
            die("apply aborted and the applied host config restored where possible")
        log("apply finished")
        return 0

    def cmd_status(self) -> int:
        print(f"repo: {self.repo}")
        system.run(["git", "-C", str(self.repo), "status", "-sb"])
        if self.update_last_check.is_file():
            stamp = self.update_last_check.read_text(encoding="utf-8").strip()
            print(f"last check: {stamp}")
        else:
            print("last check: never")
        pending = "yes" if self.read_update_state()["pending"] else "no"
        print(f"update pending: {pending}")
        self.print_update_state()
        self.print_update_plan(self.update_plan(fetch=False))
        repo_host = self.host_config_path()
        print(f"host config: {repo_host}")
        print(f"  exists: {repo_host.is_file()}")
        if repo_host.is_file() and self.applied_host_path.is_file():
            print(
                "  in sync: "
                f"{profile_fingerprint(repo_host) == profile_fingerprint(self.applied_host_path)}"
            )
        if self.applied_host_path.is_file():
            print(f"applied host config: {self.applied_host_path}")
            print(self.applied_host_path.read_text(encoding="utf-8"), end="")
        else:
            print("applied host config: missing")
        if system.have("mise") and self.mise_local_config.is_file():
            print("dotfile groups:")
            print(self.mise_local_config.read_text(encoding="utf-8"), end="")
        return 0

    def cmd_commit(self, args: types.SimpleNamespace) -> int:
        self.move_git_overrides(system.is_tty())
        files = [
            "home",
            "ansible",
            "machine",
            "bootstrap",
            "Readme.md",
            ".gitignore",
            ".pre-commit-config.yaml",
            "tests",
            ".github",
        ]
        system.run(["git", "-C", str(self.repo), "add", *files])
        commit = ["git", "-C", str(self.repo), "commit"]
        if args.message:
            commit.extend(["-m", args.message])
        system.run(commit)
        return 0

    def cmd_push(self) -> int:
        system.run(["git", "-C", str(self.repo), "push"])
        return 0

    def cmd_inventory(self, args: types.SimpleNamespace) -> int:
        if not system.have("ansible-vault"):
            die("ansible-vault not found")
        self.load_vault_password()
        system.run(["ansible-vault", args.action, args.file])
        return 0
