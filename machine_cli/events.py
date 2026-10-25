"""Append-only local event log (JSON Lines), best effort.

Only a fixed set of fields is written: no secrets, paths or free text.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOG_NAME = "events.jsonl"
MAX_BYTES = 5 * 1024 * 1024

_CODE = re.compile(r"[^a-z0-9_.-]+")


def _code(value: object, limit: int = 40) -> str:
    return _CODE.sub("-", str(value).lower()).strip("-")[:limit]


def _trim(path: Path, max_bytes: int) -> None:
    if path.stat().st_size <= max_bytes:
        return
    lines = path.read_bytes().splitlines(keepends=True)
    kept: list[bytes] = []
    size = 0
    for line in reversed(lines):
        if size + len(line) > max_bytes:
            break
        kept.append(line)
        size += len(line)
    path.write_bytes(b"".join(reversed(kept)))


def record(
    state_dir: Path,
    event: str,
    outcome: str,
    reason: Optional[str] = None,
    duration: Optional[float] = None,
    revision: Optional[str] = None,
    context: Optional[str] = None,
    device: Optional[str] = None,
    max_bytes: int = MAX_BYTES,
) -> None:
    """Append one event; never raises."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": _code(event),
            "outcome": _code(outcome),
        }
        if reason:
            entry["reason"] = _code(reason)
        if duration is not None:
            entry["duration_s"] = round(float(duration), 1)
        if revision:
            entry["rev"] = _code(revision, 12)
        if context:
            entry["context"] = _code(context)
        if device:
            entry["device"] = _code(device)
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / LOG_NAME
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")
        _trim(path, max_bytes)
    except Exception:
        return


class Timer:
    def __init__(self) -> None:
        self._start = time.monotonic()

    def seconds(self) -> float:
        return time.monotonic() - self._start
