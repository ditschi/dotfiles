"""`machine update`: local-change resolvers, incoming-change plan, lock and execution."""

from __future__ import annotations

import contextlib
import fcntl
import getpass
import json
import time
import types
from datetime import datetime
from typing import Callable, Iterable, Iterator

from . import events, local_overrides, system
from .core import die, log, parse_profile_file, parse_profile_text, warn
from .local_changes import classify_paths
from .system_relevance import (
    FEATURE_TABLE_PATH,
    ansible_view_of_feature_table,
    relevant_system_paths,
)
from .profile import host_config_changes

Resolver = tuple[str, str, Callable[[bool], None], Callable[[], bool]]


STATE_KEYS = (
    "state",
    "reason",
    "revision",
    "pending",
    "failed_revision",
    "ansible_applied_rev",
    "stash",
)


class UpdateMixin:
    # --- local overrides (host-local additions in shared files) -------------

    def local_resolvers(self) -> list[Resolver]:
        """(name, repo-relative path, run(interactive), pending) for shared files.

        `pending` is true when text can be taken out without asking (it is known
        in the `.local` file); everything else needs the user's choice."""
        git_shared = self.core_source / ".gitconfig"
        git_local = self.home / ".gitconfig.local"
        bash_shared = self.core_source / ".bashrc"
        bash_local = self.home / ".bashrc-local"
        return [
            (
                "host-only Git settings",
                "home/core/.gitconfig",
                self.move_git_overrides,
                lambda: local_overrides.git_pending(git_shared, git_local),
            ),
            (
                "host-local text in .bashrc",
                "home/core/.bashrc",
                self.move_bashrc_overrides,
                lambda: local_overrides.text_pending(bash_shared, bash_local),
            ),
        ]

    def run_local_resolvers(self, interactive: bool = False) -> None:
        interactive = interactive and system.is_tty()
        for _name, _path, run, _pending in self.local_resolvers():
            run(interactive)

    def _overrides_backup(self):
        return (
            self.state_dir / "local-overrides-backup" / time.strftime("%Y%m%d-%H%M%S")
        )

    def _conflict_resolver(self, interactive: bool):
        if not interactive:
            return None

        def resolve(kind: str, key: str, shared_text: str, local_text: str) -> str:
            print(
                f"\nConflict in {key}:\n  shared: {shared_text.strip()}\n  local:  {local_text.strip()}"
            )
            return system.choose(
                "Keep which value", ["local", "shared", "skip"], "skip"
            )

        return resolve

    def _report_overrides(self, kind: str, local_name: str, report) -> None:
        for key in report.moved:
            log(f"moved to {local_name}: {key}")
        if report.moved:
            self.event("local-overrides", "moved", kind)
        if report.removed:
            self.event("local-overrides", "removed", kind)
        if report.conflicts:
            log(
                f"WARNING: {', '.join(report.conflicts)} differs from {local_name}; "
                "nothing changed (run `machine update` in a terminal to choose)"
            )
            self.event("local-overrides", "conflict", kind)

    def move_git_overrides(self, interactive: bool = False) -> None:
        shared = self.core_source / ".gitconfig"
        if not shared.is_file():
            return
        report = local_overrides.relocate_git(
            shared,
            self.home / ".gitconfig.local",
            self._overrides_backup(),
            self._conflict_resolver(interactive),
        )
        self._report_overrides("gitconfig", "~/.gitconfig.local", report)

    def move_bashrc_overrides(self, interactive: bool = False) -> None:
        shared = self.core_source / ".bashrc"
        if not shared.is_file():
            return

        def select(chunks):
            system.run(
                [
                    "git",
                    "--no-pager",
                    "-C",
                    str(self.repo),
                    "diff",
                    "--color=always",
                    "--no-ext-diff",
                    "--unified=3",
                    "HEAD",
                    "--",
                    str(shared.relative_to(self.repo)),
                ],
                check=False,
            )
            labels = {c.key: f"{c.text.count(chr(10))} line(s)" for c in chunks}
            picked = system.choose_many(
                "Move text added to .bashrc into ~/.bashrc-local", labels, []
            )
            return [c for c in chunks if c.key in picked]

        report = local_overrides.relocate_text(
            shared,
            self.home / ".bashrc-local",
            self._overrides_backup(),
            select if interactive else None,
            self._conflict_resolver(interactive),
        )
        self._report_overrides("bashrc", "~/.bashrc-local", report)

    # --- plan -------------------------------------------------------------

    def local_changes(self) -> list[str]:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "status",
                "--porcelain",
                "-z",
                "--untracked-files=all",
            ],
            capture=True,
            check=False,
        )
        paths: list[str] = []
        entries = (result.stdout or "").split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if len(entry) < 4:
                continue
            paths.append(entry[3:])
            if entry[0] in "RC":  # the next entry is the original path
                if index < len(entries) and entries[index]:
                    paths.append(entries[index])
                index += 1
        return paths

    def upstream_ref(self) -> str:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ],
            capture=True,
            check=False,
        )
        if result.returncode == 0 and (result.stdout or "").strip():
            return result.stdout.strip()
        branch = system.run(
            ["git", "-C", str(self.repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture=True,
            check=False,
        )
        return f"origin/{(branch.stdout or '').strip()}"

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            system.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "merge-base",
                    "--is-ancestor",
                    ancestor,
                    descendant,
                ],
                check=False,
                capture=True,
            ).returncode
            == 0
        )

    def incoming_changes(
        self, upstream: str, base: str = "HEAD"
    ) -> list[tuple[str, str]]:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "diff",
                "--name-status",
                "--no-renames",
                "-z",
                base,
                upstream,
            ],
            capture=True,
            check=False,
        )
        parts = [part for part in (result.stdout or "").split("\0") if part]
        return list(zip(parts[0::2], parts[1::2]))

    def record_update_check(self) -> None:
        """The time of the last successful fetch, shown by `machine status`."""
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.update_last_check.write_text(stamp + "\n", encoding="utf-8")
        except OSError:
            pass  # best effort, like the timer script

    def record_ansible_applied(self) -> None:
        values = self.read_update_state()
        self.write_update_state(
            values["state"], values["reason"], ansible_applied_rev=self.repo_revision()
        )

    def system_paths_relevant(
        self, paths: Iterable[str], old: str = "", new: str = ""
    ) -> list[str]:
        """Changed paths that apply to this host's Ansible run.

        With the revisions `old` and `new`, a feature table whose change touches
        only keys the CLI reads (help, groups) does not count."""
        if not self.saved_ansible():
            return []
        known = self.applied_host_path.is_file()
        relevant = self._relevant_system_paths(paths, known)
        if FEATURE_TABLE_PATH in relevant and old and new:
            before, after = (
                self._git("show", f"{rev}:{FEATURE_TABLE_PATH}") for rev in (old, new)
            )
            if (
                before.returncode == 0
                and after.returncode == 0
                and ansible_view_of_feature_table(before.stdout)
                == ansible_view_of_feature_table(after.stdout)
            ):
                relevant.remove(FEATURE_TABLE_PATH)
        return relevant

    def _relevant_system_paths(self, paths: Iterable[str], known: bool) -> list[str]:
        return relevant_system_paths(
            paths,
            ansible_dir=self.ansible_dir,
            features=self.saved_features() if known else [],
            context=self.current_context() if known else "",
            device=self.current_device() if known else "",
            own_host_config=self.host_config_path().relative_to(self.repo).as_posix(),
        )

    def pending_system_paths(self, ref: str) -> list[str]:
        """Changed files between the last successful Ansible run and `ref` that apply here.

        Empty for a host that never ran Ansible (no root, or a container)."""
        applied = self.read_update_state()["ansible_applied_rev"]
        if not applied:
            return []
        result = self._git("diff", "--name-only", "--no-renames", applied, ref)
        if result.returncode != 0:
            return ["ansible/"]  # unknown revision: cannot evaluate, so it counts
        return self.system_paths_relevant(
            (result.stdout or "").splitlines(), applied, ref
        )

    def plan_steps(self, incoming: list[tuple[str, str]], ref: str) -> list[str]:
        steps = {step for step in classify_paths(incoming) if step != "system"}
        if self.pending_system_paths(ref):
            steps.add("system")
        return sorted(steps)

    def update_plan(self, *, fetch: bool) -> dict:
        if fetch:
            result = system.run(
                ["git", "-C", str(self.repo), "fetch", "--quiet"],
                check=False,
                capture=True,
            )
            if result.returncode != 0:
                warn("git fetch failed; using the last known upstream state")
            else:
                self.record_update_check()
        upstream = self.upstream_ref()
        if (
            not system.run(
                ["git", "-C", str(self.repo), "rev-parse", "--verify", upstream],
                check=False,
                capture=True,
            ).returncode
            == 0
        ):
            return {
                "upstream": upstream,
                "state": "no-upstream",
                "incoming": [],
                "steps": [],
                "local_changes": self.local_changes(),
                "resolvable": [],
                "overlap": [],
                "merged": [],
                "conflicts": [],
                "rebase_blocker": "",
                "incoming_commits": 0,
                "local_commits": 0,
                "host_config_changes": [],
                "blockers": [f"upstream {upstream} not found"],
            }
        rebase_blocker = ""
        if self._is_ancestor("HEAD", upstream):
            incoming = self.incoming_changes(upstream)
            state = "behind" if incoming else "up-to-date"
        elif self._is_ancestor(upstream, "HEAD"):
            incoming, state = [], "up-to-date"
        else:
            state = "diverged"
            base = (self._git("merge-base", "HEAD", upstream).stdout or "").strip()
            incoming = self.incoming_changes(upstream, base) if base else []
            rebase_blocker = self.rebase_blocker(upstream)
        resolvable = [
            path for _name, path, _run, pending in self.local_resolvers() if pending()
        ]
        local = self.local_changes()
        remaining = [path for path in local if path not in resolvable]
        overlap = sorted(set(remaining) & {path for _status, path in incoming})
        conflicts = (
            self.trial_conflicts(
                upstream, overlap, {path for status, path in incoming if status == "A"}
            )
            if overlap and state == "behind"
            else overlap
        )
        plan = {
            "upstream": upstream,
            "state": state,
            "incoming_commits": self.commit_count(f"HEAD..{upstream}"),
            "local_commits": self.commit_count(f"{upstream}..HEAD"),
            "host_config_changes": self.incoming_host_config_changes(
                incoming, upstream
            ),
            "incoming": [{"status": s, "path": p} for s, p in incoming],
            "steps": self.plan_steps(incoming, upstream if incoming else "HEAD"),
            "local_changes": remaining,
            "resolvable": resolvable,
            "overlap": overlap,
            "merged": [path for path in overlap if path not in conflicts],
            "conflicts": conflicts if state == "behind" else [],
            "rebase_blocker": rebase_blocker,
        }
        plan["blockers"] = (
            [self.blocked_reason(plan)] if self.plan_blocked(plan) else []
        )
        return plan

    @staticmethod
    def plan_blocked(plan: dict) -> bool:
        if plan["state"] == "diverged":
            return bool(plan["rebase_blocker"])
        return bool(plan["conflicts"])

    @staticmethod
    def blocked_reason(plan: dict) -> str:
        """The needs-attention reason: what blocks, how much is waiting, what to run next."""
        incoming = plan.get("incoming_commits", 0)
        commits = f"{incoming} incoming commit{'s' if incoming != 1 else ''}"
        if plan["state"] == "diverged":
            local = plan.get("local_commits", 0)
            if not plan["rebase_blocker"]:
                return (
                    f"history diverged: {local} local and {commits}; "
                    "they rebase cleanly → run: machine update"
                )
            return (
                f"history diverged: {local} local and {commits} "
                f"({plan['rebase_blocker']}) → run: git pull --rebase, then machine"
            )
        if plan["state"] == "no-upstream":
            return f"upstream {plan['upstream']} not found"
        return (
            f"{commits} conflict with local changes in "
            + ", ".join(plan["conflicts"])
            + " → resolve them, then run: machine"
        )

    def incoming_host_config_changes(
        self, incoming: list[tuple[str, str]], upstream: str
    ) -> list[str]:
        """What an incoming commit changes in this host's machine/hosts file."""
        try:
            rel = str(self.host_config_path().relative_to(self.repo))
        except ValueError:  # host files outside this checkout
            return []
        if rel not in {path for _status, path in incoming}:
            return []
        shown = system.run(
            ["git", "-C", str(self.repo), "show", f"{upstream}:{rel}"],
            check=False,
            capture=True,
        )
        new_text = shown.stdout if shown.returncode == 0 else ""
        return host_config_changes(
            parse_profile_file(self.applied_host_path), parse_profile_text(new_text)
        )

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

    def set_pending(self, pending: bool) -> None:
        values = self.read_update_state()
        self.write_update_state(
            values["state"], values["reason"], pending="1" if pending else ""
        )

    def print_update_plan(self, plan: dict) -> None:
        print(f"upstream: {plan['upstream']} ({plan['state']})")
        print(f"incoming files: {len(plan['incoming'])}")
        print("steps: " + (", ".join(plan["steps"]) or "none"))
        if plan.get("host_config_changes"):
            print("host config changes: " + "; ".join(plan["host_config_changes"]))
        if plan["resolvable"]:
            print("resolved automatically: " + ", ".join(plan["resolvable"]))
        if plan.get("merged"):
            print("merge cleanly (kept): " + ", ".join(plan["merged"]))
        if plan.get("conflicts"):
            print("conflict: " + ", ".join(plan["conflicts"]))
        if plan["local_changes"]:
            print("local changes (kept): " + ", ".join(plan["local_changes"]))
        if plan["blockers"]:
            for blocker in plan["blockers"]:
                print(f"needs attention: {blocker}")
        else:
            print("blockers: none")

    # --- lock and timer ---------------------------------------------------

    @contextlib.contextmanager
    def update_lock(self) -> Iterator[None]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_dir / "update.lock", "w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                die("another update is already running")
            yield

    def ensure_update_timer(self) -> None:
        """Enable the update check and the low-disk check timers of the systemd group."""
        units = self.home / ".config/systemd/user"
        timers = [
            name
            for name in ("dotfiles-update-check.timer", "machine-disk-check.timer")
            if (units / name).is_file()
        ]
        if not timers or not system.have("systemctl"):
            return
        system.run(["systemctl", "--user", "daemon-reload"], check=False, capture=True)
        for timer in timers:
            system.run(
                ["systemctl", "--user", "enable", "--now", timer],
                check=False,
                capture=True,
            )
        self.ensure_linger()

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

    # --- conflicts ----------------------------------------------------------

    def show_conflict_diff(self, plan: dict) -> None:
        """Colored diff of the conflicting local changes and the commits touching them."""
        files = plan["conflicts"]
        tracked = [path for path in files if path not in set(self.untracked_paths())]
        print(f"\nLocal changes that conflict with {plan['upstream']}:")
        if tracked:
            system.run(["git", "-C", str(self.repo), "diff", "HEAD", "--", *tracked])
        for path in sorted(set(files) - set(tracked)):
            print(f"  untracked here, added upstream: {path}")
        print("\nIncoming commits that touch them:")
        system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "--no-pager",
                "log",
                "--oneline",
                f"HEAD..{plan['upstream']}",
                "--",
                *files,
            ]
        )

    def print_conflict_commands(self, plan: dict) -> None:
        print(
            "\nResolve the conflict outside machine, for example:\n"
            f"  git stash && git merge --ff-only {plan['upstream']} && git stash pop\n"
            "  git mergetool            # or edit the conflict markers by hand\n"
            "  git stash drop           # once the files are resolved\n"
            "  machine\n"
        )

    def block_update(self, plan: dict) -> None:
        """Record needs-attention for a blocked plan and stop; the reason is printed last."""
        reason = plan["blockers"][0]
        self.write_update_state(
            "attention", reason, pending="1" if plan["incoming_commits"] else ""
        )
        die(reason)

    def stash_conflicts(self, plan: dict) -> str:
        sha = self.stash_push(
            f"conflicting with {plan['upstream']} "
            f"{self._rev(plan['upstream'])[:8]}",
            plan["conflicts"],
        )
        if not sha:
            die("could not put the conflicting local changes into the stash")
        log(
            f"conflicting local changes are in {self._stash_ref(sha)}; "
            "restore them with: machine attention"
        )
        return sha

    def resolve_conflicts(self, plan: dict, force: bool) -> dict:
        """Ask (or follow --force) what to do with conflicting changes; returns the new plan."""
        interactive = system.is_tty() and not force
        if interactive:
            self.show_conflict_diff(plan)
        manual, stash = "resolve manually", "put them into the stash and update"
        choice = stash if force else manual
        if interactive:
            choice = system.choose("Conflicting local changes", [manual, stash], manual)
        if choice != stash:
            if interactive:
                self.print_conflict_commands(plan)
            self.block_update(plan)
        self.stash_conflicts(plan)
        return self.update_plan(fetch=False)

    def merge_upstream(self, plan: dict) -> None:
        if plan["local_changes"]:
            count = len(plan["local_changes"])
            log(
                f"keeping {count} local change{'s' if count != 1 else ''} "
                "(machine status -v lists them)"
            )
        if plan["merged"]:
            log(
                "merging local changes with incoming ones: " + ", ".join(plan["merged"])
            )
        if plan["state"] == "behind" and not self.fast_forward_keeping_local(
            plan["upstream"]
        ):
            plan = dict(
                plan,
                blockers=[
                    "the update could not keep the local changes; nothing changed"
                ],
            )
            self.block_update(plan)

    def cmd_update(self, args: types.SimpleNamespace) -> int:
        if getattr(args, "check", False):
            return self.update_check(getattr(args, "json", False))
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
        plan = self.update_plan(fetch=True)
        if plan["state"] == "no-upstream":
            self.write_update_state("attention", plan["blockers"][0])
            die(plan["blockers"][0])
        if plan["state"] == "diverged":
            if plan["rebase_blocker"] or not self.rebase_keeping_local(
                plan["upstream"]
            ):
                if not plan["rebase_blocker"]:
                    plan = dict(
                        plan, rebase_blocker="the rebase failed; nothing changed"
                    )
                    plan["blockers"] = [self.blocked_reason(plan)]
                self.block_update(plan)
            plan = dict(plan, state="up-to-date", local_changes=[], merged=[])
        elif plan["conflicts"]:
            plan = self.resolve_conflicts(plan, args.force)
        self.merge_upstream(plan)
        steps = set(plan["steps"])

        profile_backup = self.backup_applied_host()
        profile_changed = self.sync_host_config_from_repo()

        # Converge check: runs also when nothing was incoming; idempotent and cheap.
        not_set_up = ""
        if self.mise_local_config.is_file() and system.have("mise"):
            self.run_dotfiles_apply()
            self.run_tools_install()
        else:
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
            not_set_up = message
            if system.is_tty() and self._confirm_bootstrap():
                system.run([str(self.repo / "bootstrap")])
                not_set_up = ""
        self.cmd_env_pull()
        self.check_ssh_key_backup()
        if not_set_up:
            self.write_update_state("attention", not_set_up)
        else:
            self.write_update_state("updated", pending="", failed_revision="")
        zsh_failure = (
            self.zsh_health_failure()
            if steps & {"dotfiles", "shell"} and not not_set_up
            else ""
        )
        self.update_failure_file.unlink(missing_ok=True)
        if zsh_failure:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.update_failure_file.write_text(zsh_failure + "\n", encoding="utf-8")
            self.write_update_state(
                "attention",
                "zsh does not start cleanly after the update; see machine attention",
            )
            warn(f"zsh health check failed after the update:\n{zsh_failure}")

        if not self.saved_ansible():
            log("ansible: false in the host config; system changes are not applied")
        elif profile_changed or args.system or "system" in steps:
            apply_args = types.SimpleNamespace(
                limit="",
                playbook="workstation",
                no_become=False,
                profile_backup=profile_backup,
                profile_changed=profile_changed,
            )
            reason = (
                "host config changed"
                if profile_changed
                else "--system" if args.system else "system files changed"
            )
            log(f"applying system changes ({reason})")
            code = self.cmd_apply(apply_args)
            return code or (1 if zsh_failure else 0)

        if zsh_failure:
            return 1  # the shell wrapper only reloads after a successful update
        log("update finished" if not not_set_up else "update finished, host not set up")
        return 0
