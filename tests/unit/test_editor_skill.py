"""The /editor command of the group `editor-command` for Claude Code, Copilot and opencode."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from package_sets import REPO

GROUP = REPO / "home/editor-command"
SKILL = GROUP / ".claude/skills/editor/SKILL.md"
COPILOT = GROUP / ".copilot/skills/editor/SKILL.md"
OPENCODE = GROUP / ".config/opencode/commands/editor.md"


def split(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    head, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(head), body


def test_skill_front_matter():
    meta, body = split(SKILL)
    assert meta["name"] == "editor"
    assert meta["description"]
    assert meta["disable-model-invocation"] is True
    assert meta["allowed-tools"] == "Bash(open-in-editor:*)"
    assert "open-in-editor" in body and "$ARGUMENTS" in body


def test_copilot_target_is_the_same_file():
    assert COPILOT.is_symlink()
    assert not os.path.isabs(os.readlink(COPILOT))
    assert COPILOT.resolve() == SKILL.resolve()


def test_opencode_command_has_the_skill_body():
    meta, body = split(OPENCODE)
    assert set(meta) == {"description"}
    assert body == split(SKILL)[1]


def test_argument_placeholder_appears_once():
    """Claude Code and opencode replace every $ARGUMENTS in the body, so the
    fallback for agents that do not substitute it must not name it again."""
    _meta, body = split(SKILL)
    assert body.count("$ARGUMENTS") == 1
