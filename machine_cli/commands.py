"""Top-level commands: setup, apply, update, status, commit, push."""

from __future__ import annotations

import os
import subprocess
import types


from . import system
from .core import (
    PROFILES,
    log,
    die,
    profile_fingerprint,
)


class CommandsMixin:
    def cmd_setup(self, args: types.SimpleNamespace) -> int:
        self.unattended = args.yes
        profile = args.profile or os.environ.get("MACHINE_PROFILE_NAME", "")
        if profile and profile not in PROFILES:
            die(f"invalid profile {profile!r}")
        self.ensure_dirs()
        saved_profile = self.current_profile() if self.profile_path.is_file() else ""
        if not profile:
            if args.yes:
                profile = self.default_profile()
            else:
                profile = self.prompt_profile(self.default_profile())
        if not profile:
            die("profile is required")

        skip_ansible = args.skip_ansible
        ask_become = not args.no_become
        if profile == "container":
            skip_ansible = True
            ask_become = False

        need_bw = (
            profile != "container"
            and not system.in_docker()
            and os.environ.get("MACHINE_SKIP_BW") != "1"
        )
        self.ensure_bootstrap_tools(not args.skip_dotfiles, not skip_ansible, need_bw)

        features = list(args.features or [])
        if not features:
            defaults = (
                self.saved_features()
                if saved_profile == profile and self.saved_features()
                else self.default_features_for(profile)
            )
            features = defaults if args.yes else self.prompt_features(defaults)

        # Before the ssh_allow_from prompt: it offers the hosts published in Bitwarden.
        if need_bw:
            self.setup_bitwarden()

        allow_from = self.saved_ssh_allow_from()
        if not args.yes and system.is_tty():
            allow_from = self.prompt_ssh_allow_from(allow_from, profile)

        self.write_profile(profile, features, allow_from)
        self.write_dotfile_groups(profile)
        log(f"wrote {self.profile_path} (profile={profile})")

        self.maybe_persist_host_profile(profile, features, allow_from, yes=args.yes)

        if skip_ansible or profile == "container":
            log("skipping ansible")
        else:
            self.run_ansible(args.playbook, args.limit, args.local, ask_become)

        if "ssh-host-key" in features and profile != "container":
            store_private = False
            if system.is_tty() and not args.yes:
                store_private = system.prompt_yes_no(
                    "Also store the private key in Bitwarden?", False
                )
            self.publish_ssh_key(store_private=store_private)
            self.apply_authorized_keys_from_bw(allow_from)

        self.maybe_tailscale_login(features)

        if not args.skip_dotfiles:
            self.run_dotfiles_apply()
            if profile != "container":
                self.ensure_update_timer()
            self.cmd_env_pull()
        log("setup finished")
        return 0

    def cmd_apply(self, args: types.SimpleNamespace) -> int:
        """Apply host profile (repo → local) + ansible; revert local profile on fail."""
        playbook = getattr(args, "playbook", "workstation") or "workstation"
        ask_become = not getattr(args, "no_become", False)
        limit = getattr(args, "limit", "") or ""

        if limit:
            host_file = self.host_profile_path(limit)
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
                    "fix host profile / playbook, then re-run. "
                    "No automatic remote revert (edit git and apply again)."
                )
            log("remote apply finished")
            return 0

        # Local apply: backup first, then repo host file wins
        # `machine update` syncs the profile before calling us; it hands over the
        # pre-sync backup so a failed apply can still revert that change.
        backup = getattr(args, "profile_backup", None) or self.backup_local_profile()
        profile_changed = self.sync_host_profile_from_repo() or bool(
            getattr(args, "profile_changed", False)
        )
        if not self.profile_path.is_file():
            die("no local profile; run machine setup first")

        profile = self.current_profile()
        if profile == "container":
            log("container profile: nothing to apply")
            return 0

        features = self.saved_features()
        allow_from = self.saved_ssh_allow_from()
        try:
            self.ensure_bootstrap_tools(
                False,
                True,
                not system.in_docker() and os.environ.get("MACHINE_SKIP_BW") != "1",
            )
            self.run_ansible(playbook, force_local=True, ask_become=ask_become)
            if "ssh-host-key" in features:
                self.apply_authorized_keys_from_bw(allow_from)
            if not self.health_check_after_apply():
                raise RuntimeError("health check failed")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            log(f"apply failed: {exc}")
            if backup:
                self.restore_local_profile(backup)
                if profile_changed:
                    log("re-running ansible with restored profile")
                    try:
                        self.run_ansible(
                            playbook, force_local=True, ask_become=ask_become
                        )
                    except subprocess.CalledProcessError:
                        log("revert ansible also failed; check the host manually")
                else:
                    log(
                        "profile was unchanged; not retrying the failed apply. "
                        "Review Ansible's error; sudo command restrictions require "
                        "administrator approval, not a different password."
                    )
            die("apply aborted and local profile restored where possible")
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
        marker = "set" if self.update_marker.is_file() else "unset"
        print(f"update marker: {marker}")
        self.print_update_state()
        self.print_update_plan(self.update_plan(fetch=False))
        repo_host = self.host_profile_path()
        print(f"repo host profile: {repo_host}")
        print(f"  exists: {repo_host.is_file()}")
        if repo_host.is_file() and self.profile_path.is_file():
            print(
                "  in sync: "
                f"{profile_fingerprint(repo_host) == profile_fingerprint(self.profile_path)}"
            )
        if self.profile_path.is_file():
            print(f"profile file: {self.profile_path}")
            print(self.profile_path.read_text(encoding="utf-8"), end="")
        else:
            print("profile file: missing")
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
