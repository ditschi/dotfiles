"""Top-level commands: setup, apply, update, status, commit, push."""

from __future__ import annotations

import types

from . import system
from .commands_apply import ApplyMixin
from .commands_setup import SetupMixin
from .commands_status import StatusMixin

# `log` stays importable here: tests replace `machine_cli.commands.log`, and the setup
# and apply modules log through it.
from .core import die, log  # noqa: F401


class CommandsMixin(SetupMixin, ApplyMixin, StatusMixin):
    """The top-level commands; setup, apply and status live in their own modules."""

    def cmd_commit(self, args: types.SimpleNamespace) -> int:
        self.move_git_overrides(system.is_tty())
        files = [
            "home",
            "ansible",
            "machine",
            "bootstrap",
            "Readme.md",
            "docs",
            "openspec",
            "AGENTS.md",
            "CLAUDE.md",
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
