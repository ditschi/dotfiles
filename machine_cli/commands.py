"""Top-level commands: setup, apply, update, status, commit, push."""

from __future__ import annotations

import os
import subprocess
import types


from rich.columns import Columns
from rich.console import Console
from rich.table import Table
from rich.text import Text

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
        """Apply the host config and Ansible; optionally skip system provisioning."""
        playbook = getattr(args, "playbook", "workstation") or "workstation"
        ask_become = not getattr(args, "no_become", False)
        skip_ansible = getattr(args, "skip_ansible", False)
        limit = getattr(args, "limit", "") or ""

        if limit:
            host_file = self.host_config_path(limit)
            if not host_file.is_file():
                die(
                    f"missing {host_file.relative_to(self.repo)}; "
                    f"create it or run setup on that host"
                )
            log(f"remote apply using {host_file.relative_to(self.repo)}")
            if skip_ansible:
                log(
                    "ansible skipped (--skip-ansible); remote system changes remain pending"
                )
                return 0
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
        if skip_ansible:
            log("ansible skipped (--skip-ansible); system changes remain pending")
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

    def cmd_status(self, verbose: bool = False) -> int:
        """Compact overview; colors only on a terminal (rich honours NO_COLOR)."""
        console = Console(highlight=False)
        if not console.is_terminal:
            console.width = 400  # piped: keep each row on one line, greppable
        plan = self.update_plan(fetch=False)
        state = self.read_update_state()
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", no_wrap=True)
        grid.add_column()

        branch = (self._git("rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
        behind, ahead = plan["incoming_commits"], plan["local_commits"]
        position = Text(f"{branch or '?'} · ")
        if behind or ahead:
            parts = [f"{behind} behind"] if behind else []
            parts += [f"{ahead} ahead"] if ahead else []
            position.append(" / ".join(parts) + f" {plan['upstream']}", style="yellow")
        else:
            position.append(f"up to date with {plan['upstream']}", style="green")
        stamp = (
            self.update_last_check.read_text(encoding="utf-8").strip()
            if self.update_last_check.is_file()
            else "never"
        )
        position.append(f" · checked {stamp[:16].replace('T', ' ')}", style="dim")
        grid.add_row("repo", position)

        if state["state"] == "attention" or plan["blockers"]:
            reason = plan["blockers"][0] if plan["blockers"] else state["reason"]
            grid.add_row(
                Text("attention", style="bold red"),
                Text(f"⚠ {reason or 'see machine attention'}", style="red"),
            )
            if "→" not in (reason or ""):
                grid.add_row("", Text("→ run: machine", style="bold"))

        if plan["incoming"]:
            grid.add_row(
                "incoming",
                f"{len(plan['incoming'])} files → "
                + (", ".join(plan["steps"]) or "no steps"),
            )
        local = set(self.local_changes())
        if local:
            untracked = len(local & set(self.untracked_paths()))
            parts = [f"{len(local) - untracked} modified", f"{untracked} untracked"]
            if plan["merged"]:
                parts.append(f"{len(plan['merged'])} merge cleanly")
            if plan["conflicts"]:
                parts.append(f"{len(plan['conflicts'])} conflict")
            grid.add_row("local", ", ".join(parts) + " (kept)")
        stashes = self.stash_entries()
        if stashes:
            count = len(stashes)
            grid.add_row(
                "stash",
                Text(
                    f"{count} stash entr{'y' if count == 1 else 'ies'} put aside by "
                    "machine → restore or drop them: machine attention",
                    style="yellow",
                ),
            )

        repo_host = self.host_config_path()
        host = Text(repo_host.stem)
        if self.applied_host_path.is_file():
            host.append(f" · {self.current_context() or '-'} · {self.current_device()}")
        if not repo_host.is_file():
            host.append(" · no host config in the repo", style="yellow")
        elif not self.applied_host_path.is_file():
            host.append(" · not applied yet", style="yellow")
        elif profile_fingerprint(repo_host) == profile_fingerprint(
            self.applied_host_path
        ):
            host.append(" · config in sync", style="green")
        else:
            host.append(" · config differs from the repo", style="yellow")
        grid.add_row("host", host)
        if self.applied_host_path.is_file():
            features = self.saved_features()
            grid.add_row(
                "features",
                (
                    Columns(features, column_first=True, padding=(0, 2))
                    if features
                    else "-"
                ),
            )
            grid.add_row("groups", " ".join(self.host_dotfile_groups()) or "-")
        console.print(grid)

        if verbose:
            if plan["incoming"]:
                console.print("\n[bold]incoming files[/bold]")
                for item in plan["incoming"]:
                    console.print(f"  {item['status']} {item['path']}", markup=False)
            if stashes:
                console.print("\n[bold]stash entries[/bold]")
                for ref, _sha, message in stashes:
                    console.print(
                        f"  {ref}: {message.partition(': ')[2]}", markup=False
                    )
            if local:
                console.print("\n[bold]local changes[/bold]")
                for path in sorted(local):
                    console.print(f"  {path}", markup=False)
            if self.applied_host_path.is_file():
                console.print(
                    f"\n[bold]applied host config[/bold] {self.applied_host_path}"
                )
                console.print(
                    self.applied_host_path.read_text(encoding="utf-8").rstrip(),
                    markup=False,
                )
            if self.mise_local_config.is_file():
                console.print(f"\n[bold]dotfile groups[/bold] {self.mise_local_config}")
                console.print(
                    self.mise_local_config.read_text(encoding="utf-8").rstrip(),
                    markup=False,
                )
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
