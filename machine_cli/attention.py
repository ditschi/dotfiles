"""`machine attention`: list and guide through everything that needs manual action."""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import Callable, Optional

from . import system
from .monitoring import NOT_ACTIVE


@dataclass
class AttentionItem:
    kind: str
    text: str
    # None: no yes/no question; `resolve` shows the choices or the commands itself.
    question: Optional[str]
    resolve: Callable[[], object]


class AttentionMixin:
    def _run_update(self) -> int:
        return self.cmd_update(types.SimpleNamespace(force=False, system=False))

    def _show_update_failure(self) -> None:
        if self.update_failure_file.is_file():
            print("Output of the failed check:")
            print(self.update_failure_file.read_text(encoding="utf-8").rstrip())

    def update_item(self) -> Optional[AttentionItem]:
        """The update item from the live plan (no fetch), or None when nothing waits."""
        state = self.read_update_state()
        attention = state["state"] == "attention"
        plan = self.update_plan(fetch=False)
        blocked = self.plan_blocked(plan)
        if not attention and not blocked:
            return None
        system_note = (
            " (the pending system step runs with the update)"
            if self.pending_system_paths(plan["upstream"])
            else ""
        )
        if (
            plan["state"] == "diverged"
            and plan["rebase_blocker"]
            and not plan["conflicts"]
        ):

            def show() -> None:
                print(
                    "\nRebase the local commits by hand, then run machine:\n"
                    "  git pull --rebase      # resolve conflicts with git mergetool\n"
                    "  machine\n"
                )

            return AttentionItem("update", plan["blockers"][0], None, show)
        if plan["conflicts"]:
            # `machine update` shows the diff and asks (resolve manually by default).
            return AttentionItem(
                "update", plan["blockers"][0] + system_note, None, self._run_update
            )
        text = state["reason"] or "the last update needs attention"
        if state["failed_revision"] or self.update_failure_file.is_file():

            def show_and_update() -> object:
                self._show_update_failure()
                if system.prompt_yes_no("Run `machine update` now?", True):
                    return self._run_update()
                return 0

            return AttentionItem("update", text + system_note, None, show_and_update)
        return AttentionItem(
            "update",
            text + system_note,
            "Run `machine update` now?",
            self._run_update,
        )

    def stash_items(self) -> list[AttentionItem]:
        items = []
        for ref, sha, message in self.stash_entries():

            def decide(sha: str = sha, ref: str = ref) -> int:
                system.run(
                    ["git", "-C", str(self.repo), "stash", "show", "--stat", sha]
                )
                restore, drop, keep = "restore it", "drop it", "keep it for later"
                choice = system.choose(
                    f"What to do with {ref}", [restore, drop, keep], keep
                )
                if choice == drop:
                    self.stash_drop(sha)
                    print(f"dropped {ref}")
                    return 0
                if choice != restore:
                    return 0
                if self.stash_apply(sha):
                    print(f"restored {ref}")
                    return 0
                print(
                    f"\n{ref} conflicts with the current files; the conflict markers "
                    "are in the files and the entry is kept. Finish by hand:\n"
                    "  git mergetool            # or edit the conflict markers\n"
                    f"  git stash drop {ref}\n"
                )
                return 1

            items.append(
                AttentionItem(
                    "stash",
                    f"local changes put aside in {ref}: {message.partition(': ')[2]}",
                    None,
                    decide,
                )
            )
        return items

    def _run_apply(self) -> int:
        return self.cmd_apply(
            types.SimpleNamespace(limit="", playbook="workstation", no_become=False)
        )

    def monitoring_item(self) -> Optional[AttentionItem]:
        """Telegraf not installed, without output or not running on a monitoring host."""
        problem = self.telegraf_problem()
        if not problem:
            return None
        text = self.telegraf_problem_text(problem)
        if problem != NOT_ACTIVE:
            return AttentionItem(
                "monitoring", text, "Run `machine apply` now?", self._run_apply
            )

        def show_and_restart() -> object:
            # best effort: without the adm/systemd-journal group the journal is empty
            system.run(
                ["journalctl", "-u", "telegraf", "-n", "20", "--no-pager"],
                check=False,
            )
            if system.prompt_yes_no("Restart telegraf now (sudo)?", True):
                return system.run(
                    ["sudo", "systemctl", "restart", "telegraf"], check=False
                ).returncode
            return 0

        return AttentionItem("monitoring", text, None, show_and_restart)

    def attention_items(self) -> list[AttentionItem]:
        items: list[AttentionItem] = []
        update = self.update_item()
        if update:
            items.append(update)
        items.extend(self.stash_items())
        pending = self.pending_system_paths("HEAD")
        if pending and not update:
            items.append(
                AttentionItem(
                    "system",
                    "system update pending: "
                    + ", ".join(pending[:5])
                    + (" …" if len(pending) > 5 else ""),
                    "Run `machine apply` now?",
                    self._run_apply,
                )
            )
        if self.ssh_key_attention.is_file():
            items.append(
                AttentionItem(
                    "ssh-key",
                    self.ssh_key_attention.read_text(encoding="utf-8").strip(),
                    "Choose which SSH key wins now (machine ssh sync)?",
                    self.resolve_ssh_key_difference,
                )
            )
        env = self.env_attention()
        if env:
            items.append(
                AttentionItem(
                    "env",
                    "local-only env content: " + "; ".join(env),
                    "Resolve it now (machine env pull)?",
                    lambda: self.cmd_env_pull(interactive=True),
                )
            )
        monitoring = self.monitoring_item()
        if monitoring:
            items.append(monitoring)
        for low in self.low_disks():
            items.append(
                AttentionItem(
                    "disk", low.text(), None, lambda low=low: self.resolve_low_disk(low)
                )
            )
        local = set(self.local_changes())
        for name, path, run, _pending in self.local_resolvers():
            if path in local:
                items.append(
                    AttentionItem(
                        "local-overrides",
                        f"{name} in {path} (conflicting or new local text)",
                        "Resolve it now?",
                        lambda run=run: run(True),
                    )
                )
        return items

    def cmd_attention(self) -> int:
        items = self.attention_items()
        if not items:
            print("Nothing needs attention.")
            return 0
        print(f"{len(items)} item(s) need attention:")
        for number, item in enumerate(items, 1):
            print(f"  {number}. [{item.kind}] {item.text}")
        if not system.is_tty():
            return 0
        for item in items:
            print(f"\n[{item.kind}] {item.text}")
            if item.question is None or system.prompt_yes_no(item.question, True):
                try:
                    item.resolve()
                except SystemExit:
                    pass  # the command printed why it stopped; the item stays open
        remaining = len(self.attention_items())
        print(
            "\nNothing needs attention."
            if not remaining
            else f"\n{remaining} item(s) still open."
        )
        return 0
