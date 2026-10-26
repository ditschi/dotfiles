"""`machine update`: local-change resolvers, incoming-change plan, lock and execution."""

from __future__ import annotations

import contextlib
import fcntl
import getpass
import json
import time
import types
from typing import Callable, Iterable, Iterator

from . import events, local_overrides, system
from .core import die, log, parse_profile_file, parse_profile_text, warn
from .local_changes import classify_paths
from .system_relevance import relevant_system_paths
from .profile import host_config_changes

Resolver = tuple[str, str, Callable[[bool], None], Callable[[], bool]]


STATE_KEYS = (
    "state",
    "reason",
    "revision",
    "pending",
    "failed_revision",
    "ansible_applied_rev",
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

    def incoming_changes(self, upstream: str) -> list[tuple[str, str]]:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "diff",
                "--name-status",
                "--no-renames",
                "-z",
                "HEAD",
                upstream,
            ],
            capture=True,
            check=False,
        )
        parts = [part for part in (result.stdout or "").split("\0") if part]
        return list(zip(parts[0::2], parts[1::2]))

    def record_ansible_applied(self) -> None:
        values = self.read_update_state()
        self.write_update_state(
            values["state"], values["reason"], ansible_applied_rev=self.repo_revision()
        )

    def system_paths_relevant(self, paths: Iterable[str]) -> list[str]:
        if not self.saved_ansible():
            return []
        known = self.applied_host_path.is_file()
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
        return self.system_paths_relevant((result.stdout or "").splitlines())

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
                "blockers": [f"upstream {upstream} not found"],
            }
        if self._is_ancestor("HEAD", upstream):
            incoming = self.incoming_changes(upstream)
            state = "behind" if incoming else "up-to-date"
        elif self._is_ancestor(upstream, "HEAD"):
            incoming, state = [], "up-to-date"
        else:
            incoming, state = [], "diverged"
        resolvable = [
            path for _name, path, _run, pending in self.local_resolvers() if pending()
        ]
        local = self.local_changes()
        remaining = [path for path in local if path not in resolvable]
        overlap = sorted(set(remaining) & {path for _status, path in incoming})
        blockers = []
        if state == "diverged":
            blockers.append(f"history has diverged from {upstream}")
        if overlap:
            blockers.append(
                "locally changed files are also changed upstream: " + ", ".join(overlap)
            )
        return {
            "upstream": upstream,
            "state": state,
            "host_config_changes": self.incoming_host_config_changes(
                incoming, upstream
            ),
            "incoming": [{"status": s, "path": p} for s, p in incoming],
            "steps": self.plan_steps(incoming, upstream if incoming else "HEAD"),
            "local_changes": remaining,
            "resolvable": resolvable,
            "overlap": overlap,
            "blockers": blockers,
        }

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

    def print_update_state(self) -> None:
        values = self.read_update_state()
        state = values["state"]
        print(f"update state: {state}")
        if state == "attention":
            print(f"  reason: {values['reason']}")
        fixes = {
            "available": "run: machine update",
            "updated": "run: reload (restarts the current shell) or open a new shell",
            "attention": "run: machine update --check, resolve the reason, then machine update",
        }
        if state in fixes:
            print(f"  fix: {fixes[state]}")

    def print_update_plan(self, plan: dict) -> None:
        print(f"upstream: {plan['upstream']} ({plan['state']})")
        print(f"incoming files: {len(plan['incoming'])}")
        print("steps: " + (", ".join(plan["steps"]) or "none"))
        if plan.get("host_config_changes"):
            print("host config changes: " + "; ".join(plan["host_config_changes"]))
        if plan["resolvable"]:
            print("resolved automatically: " + ", ".join(plan["resolvable"]))
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
        unit = self.home / ".config/systemd/user/dotfiles-update-check.timer"
        if not unit.is_file() or not system.have("systemctl"):
            return
        system.run(["systemctl", "--user", "daemon-reload"], check=False, capture=True)
        system.run(
            ["systemctl", "--user", "enable", "--now", "dotfiles-update-check.timer"],
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

    def merge_upstream(self, plan: dict, force: bool) -> None:
        repo = str(self.repo)
        stashed = False
        if plan["overlap"]:
            system.run(["git", "-C", repo, "status", "--short"])
            if not force:
                die(
                    "manual attention needed: "
                    + plan["blockers"][0]
                    + " (--force stashes them, merges and restores them)"
                )
            system.run(
                ["git", "-C", repo, "stash", "push", "--include-untracked", "--"]
                + plan["overlap"]
            )
            stashed = True
        elif plan["local_changes"]:
            log("keeping local changes: " + ", ".join(plan["local_changes"]))
        if plan["state"] == "behind":
            system.run(["git", "-C", repo, "merge", "--ff-only", plan["upstream"]])
        if stashed:
            popped = system.run(["git", "-C", repo, "stash", "pop"], check=False)
            if popped.returncode != 0:
                die("local changes kept in `git stash`; resolve the conflict manually")

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
        if plan["state"] in ("diverged", "no-upstream"):
            self.write_update_state("attention", plan["blockers"][0])
            die(plan["blockers"][0])
        if plan["overlap"] and not args.force:
            self.write_update_state("attention", plan["blockers"][0])
        self.merge_upstream(plan, args.force)
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
            return self.cmd_apply(apply_args)

        log("update finished" if not not_set_up else "update finished, host not set up")
        return 0
