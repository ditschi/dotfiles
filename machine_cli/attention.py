"""`machine attention`: list and guide through everything that needs manual action."""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import Callable

from . import system


@dataclass
class AttentionItem:
    kind: str
    text: str
    question: str
    resolve: Callable[[], object]


class AttentionMixin:
    def attention_items(self) -> list[AttentionItem]:
        items: list[AttentionItem] = []
        state = self.read_update_state()
        if state["state"] == "attention":
            items.append(
                AttentionItem(
                    "update",
                    state["reason"] or "the last update needs attention",
                    "Run `machine update` now?",
                    lambda: self.cmd_update(
                        types.SimpleNamespace(force=False, system=False)
                    ),
                )
            )
        pending = self.pending_system_paths("HEAD")
        if pending:
            items.append(
                AttentionItem(
                    "system",
                    "system update pending: "
                    + ", ".join(pending[:5])
                    + (" …" if len(pending) > 5 else ""),
                    "Run `machine apply` now?",
                    lambda: self.cmd_apply(
                        types.SimpleNamespace(
                            limit="", playbook="workstation", no_become=False
                        )
                    ),
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
            if system.prompt_yes_no(item.question, True):
                item.resolve()
        remaining = len(self.attention_items())
        print(
            "\nNothing needs attention."
            if not remaining
            else f"\n{remaining} item(s) still open."
        )
        return 0
