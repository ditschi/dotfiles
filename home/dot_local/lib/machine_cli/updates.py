"""`machine update`: local-change resolvers, incoming-change plan, lock and execution."""

from __future__ import annotations

import contextlib
import fcntl
import json
import sys
import time
import types
from typing import Callable, Iterator

from . import system
from .core import die, log, warn
from .local_changes import classify_paths, managed_blocks, relocate_managed_blocks

Resolver = tuple[str, str, Callable[[], None], Callable[[], bool]]


class UpdateMixin:
    # --- local-change resolvers -------------------------------------------

    def local_resolvers(self) -> list[Resolver]:
        """(name, repo-relative path, run, pending) for expected local changes."""
        return [
            (
                "host-only Git settings",
                "home/dot_gitconfig",
                self.sanitize_git_config,
                self.git_config_pending,
            ),
            (
                "externally managed blocks in .bashrc",
                "home/dot_bashrc",
                self.relocate_bashrc_blocks,
                self.bashrc_blocks_pending,
            ),
        ]

    def run_local_resolvers(self) -> None:
        for _name, _path, run, _pending in self.local_resolvers():
            run()

    def git_config_pending(self) -> bool:
        shared = self.chezmoi_source / "dot_gitconfig"
        script = self.repo / "machine/gitconfig.py"
        if not shared.is_file() or not script.is_file():
            return False
        result = system.run(
            [
                sys.executable,
                str(script),
                "--check",
                "--shared",
                str(shared),
                "--local",
                str(self.home / ".gitconfig.local"),
            ],
            capture=True,
            check=False,
        )
        return result.returncode == 1

    def bashrc_blocks_pending(self) -> bool:
        shared = self.chezmoi_source / "dot_bashrc"
        if not shared.is_file():
            return False
        lines = shared.read_text(encoding="utf-8").splitlines()
        return bool(managed_blocks(lines))

    def relocate_bashrc_blocks(self) -> None:
        shared = self.chezmoi_source / "dot_bashrc"
        stamp = time.strftime("%Y%m%d-%H%M%S")
        moved = relocate_managed_blocks(
            shared,
            self.home / ".bashrc-local",
            self.state_dir / "bashrc-backup" / stamp,
        )
        for begin in moved:
            log(f"moved to ~/.bashrc-local: {begin}")

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
            "incoming": [{"status": s, "path": p} for s, p in incoming],
            "steps": classify_paths(incoming),
            "local_changes": remaining,
            "resolvable": resolvable,
            "overlap": overlap,
            "blockers": blockers,
        }

    def print_update_plan(self, plan: dict) -> None:
        print(f"upstream: {plan['upstream']} ({plan['state']})")
        print(f"incoming files: {len(plan['incoming'])}")
        print("steps: " + (", ".join(plan["steps"]) or "none"))
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
        with self.update_lock():
            return self._update_locked(args)

    def _update_locked(self, args: types.SimpleNamespace) -> int:
        self.ensure_update_timer()
        self.run_local_resolvers()
        plan = self.update_plan(fetch=True)
        if plan["state"] in ("diverged", "no-upstream"):
            die(plan["blockers"][0])
        self.merge_upstream(plan, args.force)
        steps = set(plan["steps"])

        profile_backup = self.backup_local_profile()
        profile_changed = self.sync_host_profile_from_repo()

        if (
            self.chezmoi_config.is_file()
            and system.have("chezmoi")
            and ("chezmoi" in steps or profile_changed)
        ):
            self.run_chezmoi_apply()
        self.cmd_env_pull()
        if self.update_marker.exists():
            self.update_marker.unlink()

        if profile_changed or args.system or "system" in steps:
            apply_args = types.SimpleNamespace(
                limit="",
                playbook="workstation",
                no_become=False,
                profile_backup=profile_backup,
                profile_changed=profile_changed,
            )
            reason = (
                "host profile changed"
                if profile_changed
                else "--system" if args.system else "system files changed"
            )
            log(f"applying system changes ({reason})")
            return self.cmd_apply(apply_args)

        log("update finished")
        return 0
