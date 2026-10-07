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
        if getattr(args, "command", "") != "migrate" and self.needs_layout_migration():
            if args.yes:
                log(
                    "layout migration needed; continuing setup after clearing stale links"
                )
                old_sha = self.legacy_rollback_sha(getattr(args, "rollback_ref", ""))
                self.backup_migration_state(old_sha)
                self.write_rollback_script(old_sha)
                self.clear_stale_root_links()
            elif system.is_tty() and system.prompt_yes_no(
                "Old root symlinks detected. Migrate now?", True
            ):
                return self.cmd_migrate(args)
            elif not system.is_tty():
                die("layout migration needed; run: machine migrate --yes")

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
        self.ensure_bootstrap_tools(not args.skip_chezmoi, not skip_ansible, need_bw)

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
            self.maybe_login_bitwarden()

        allow_from = self.saved_ssh_allow_from()
        if not args.yes and system.is_tty():
            allow_from = self.prompt_ssh_allow_from(allow_from, profile)

        self.write_profile(profile, features, allow_from)
        self.write_chezmoi_config(profile)
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

        if not args.skip_chezmoi:
            self.run_chezmoi_apply()
            self.preserve_git_host_settings()
            if system.have("systemctl") and profile != "container":
                system.run(
                    ["systemctl", "--user", "daemon-reload"], check=False, capture=True
                )
                system.run(
                    [
                        "systemctl",
                        "--user",
                        "enable",
                        "--now",
                        "dotfiles-update-check.timer",
                    ],
                    check=False,
                    capture=True,
                )
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
        backup = self.backup_local_profile()
        self.sync_host_profile_from_repo()
        if not self.profile_path.is_file():
            die("no local profile; run machine setup first")

        profile = self.current_profile()
        if profile == "container":
            log("container profile: nothing to apply")
            return 0

        features = self.saved_features()
        allow_from = self.saved_ssh_allow_from()
        try:
            self.ensure_bootstrap_tools(False, True, False)
            self.run_ansible(playbook, force_local=True, ask_become=ask_become)
            if "ssh-host-key" in features:
                self.apply_authorized_keys_from_bw(allow_from)
            if not self.health_check_after_apply():
                raise RuntimeError("health check failed")
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            log(f"apply failed: {exc}")
            if backup:
                self.restore_local_profile(backup)
                log("re-running ansible with restored profile")
                try:
                    self.run_ansible(playbook, force_local=True, ask_become=ask_become)
                except subprocess.CalledProcessError:
                    log("revert ansible also failed; check the host manually")
            die("apply aborted and local profile restored where possible")
        log("apply finished")
        return 0

    def cmd_update(self, args: types.SimpleNamespace) -> int:
        gate = self.handle_layout_gate(yes=False, force=args.force)
        if gate == "migrate":
            migrate_args = types.SimpleNamespace(
                profile=None,
                features=None,
                yes=False,
                local=False,
                limit="",
                playbook="workstation",
                skip_ansible=False,
                skip_chezmoi=False,
                no_become=False,
                command="migrate",
            )
            return self.cmd_migrate(migrate_args)

        self.sanitize_git_config()
        if self.git_dirty() and not args.force:
            system.run(["git", "-C", str(self.repo), "status", "--short"])
            die(f"uncommitted changes in {self.repo} (commit/stash, or --force)")
        system.run(["git", "-C", str(self.repo), "pull", "--ff-only"])
        self.sanitize_git_config()

        gate = self.handle_layout_gate(yes=False, force=args.force)
        if gate == "migrate":
            migrate_args = types.SimpleNamespace(
                profile=None,
                features=None,
                yes=False,
                local=False,
                limit="",
                playbook="workstation",
                skip_ansible=False,
                skip_chezmoi=False,
                no_become=False,
                command="migrate",
            )
            return self.cmd_migrate(migrate_args)

        profile_changed = self.sync_host_profile_from_repo()

        if self.chezmoi_config.is_file() and system.have("chezmoi"):
            self.run_chezmoi_apply()
        self.cmd_env_pull()
        if self.update_marker.exists():
            self.update_marker.unlink()

        if profile_changed or args.system:
            apply_args = types.SimpleNamespace(
                limit="",
                playbook="workstation",
                no_become=False,
            )
            log(
                "applying system changes"
                + (" (host profile changed)" if profile_changed else " (--system)")
            )
            return self.cmd_apply(apply_args)

        log("update finished")
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
        print(f"needs migration: {self.needs_layout_migration()}")
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
        if system.have("chezmoi") and self.chezmoi_config.is_file():
            print("chezmoi status:")
            system.run(
                [
                    "chezmoi",
                    "status",
                    "--source",
                    str(self.chezmoi_source),
                    "--destination",
                    str(self.home),
                    "--config",
                    str(self.chezmoi_config),
                ],
                check=False,
            )
        return 0

    def cmd_commit(self, args: types.SimpleNamespace) -> int:
        self.sanitize_git_config()
        files = [
            "home",
            "ansible",
            "machine",
            "bootstrap",
            "install.py",
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
