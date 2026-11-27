"""`machine update`: local changes that conflict with incoming ones, and the merge."""

from __future__ import annotations

from . import system
from .core import die, log


class UpdateConflictsMixin:
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
        update = (
            f"git rebase {plan['upstream']}"
            if plan["state"] == "diverged"
            else f"git merge --ff-only {plan['upstream']}"
        )
        print(
            "\nResolve the conflict outside machine, for example:\n"
            f"  git stash && {update} && git stash pop\n"
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
            f"conflicting with {plan['upstream']} {self._rev(plan['upstream'])[:8]}",
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

    def _rebase_diverged(self, plan: dict, force: bool) -> dict:
        """Rebase a diverged checkout onto upstream; returns the plan after the rebase."""
        if plan["conflicts"]:
            # Only uncommitted changes block the rebase: same choices as when behind.
            plan = self.resolve_conflicts(plan, force)
        if plan["rebase_blocker"] or not self.rebase_keeping_local(plan["upstream"]):
            self._block_rebase(plan)
        return dict(plan, state="up-to-date", local_changes=[], merged=[])

    def _block_rebase(self, plan: dict) -> None:
        if not plan["rebase_blocker"]:
            plan = dict(plan, rebase_blocker="the rebase failed; nothing changed")
            plan["blockers"] = [self.blocked_reason(plan)]
        self.block_update(plan)

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
