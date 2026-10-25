"""The local event log: JSON Lines, capped, best effort, no free text."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import events  # noqa: E402


def _lines(directory: Path) -> list[dict]:
    text = (directory / events.LOG_NAME).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_appends_one_json_line_per_event(tmp_path: Path):
    events.record(tmp_path, "update-auto", "applied", duration=1.26, revision="abc1234")
    events.record(
        tmp_path,
        "update-auto",
        "reverted",
        "zsh-unhealthy",
        context="work",
        device="desktop",
    )

    first, second = _lines(tmp_path)
    assert first["event"] == "update-auto" and first["outcome"] == "applied"
    assert first["duration_s"] == 1.3 and first["rev"] == "abc1234"
    assert second["reason"] == "zsh-unhealthy" and second["context"] == "work"
    assert second["device"] == "desktop"
    assert "ts" in first


def test_only_whitelisted_fields_and_no_free_text(tmp_path: Path):
    events.record(
        tmp_path,
        "env",
        "failed",
        reason="/home/me/.env: bad token SECRET=abc123 for user",
    )

    (entry,) = _lines(tmp_path)
    assert set(entry) <= {
        "ts",
        "event",
        "outcome",
        "reason",
        "duration_s",
        "rev",
        "context",
        "device",
    }
    assert "/" not in entry["reason"] and " " not in entry["reason"]
    assert len(entry["reason"]) <= 40


def test_size_cap_drops_oldest_lines(tmp_path: Path):
    for index in range(40):
        events.record(tmp_path, "usage", "invoked", f"cmd{index}", max_bytes=1024)

    path = tmp_path / events.LOG_NAME
    assert path.stat().st_size <= 1024
    reasons = [entry["reason"] for entry in _lines(tmp_path)]
    assert reasons[-1] == "cmd39" and "cmd0" not in reasons


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_unwritable_state_directory_does_not_raise(tmp_path: Path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        events.record(locked, "usage", "invoked", "status")
    finally:
        locked.chmod(0o700)
    assert not (locked / events.LOG_NAME).exists()


def test_state_path_that_is_a_file_does_not_raise(tmp_path: Path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    events.record(blocker / "state", "usage", "invoked", "status")
