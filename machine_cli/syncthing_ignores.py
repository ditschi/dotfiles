"""Shared Syncthing ignore rules: `.stglobalignore` per folder, loaded by `.stignore`."""

from __future__ import annotations

import http.client
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import features as feature_table
from . import system
from .core import log, parse_profile_file, warn

FEATURE = "syncthing"
GLOBAL = ".stglobalignore"
INCLUDE = f"#include {GLOBAL}"
# Keeps the shared file itself synced in folders whose own lines ignore everything
# else (an allow list ending in "*").
UNIGNORE = f"!/{GLOBAL}"
RULES = Path("machine/syncthing/stglobalignore")
# Syncthing trims the name after #include; "./" points at the same file.
INCLUDE_LINE = re.compile(r"^\s*#include\s+(\./)?\.stglobalignore\s*$")
UNIGNORE_LINE = re.compile(r"^\s*!/?\.stglobalignore\s*$")
# Syncthing names a conflict copy <base>.sync-conflict-<date>-<time>-<device><ext>;
# for ".stglobalignore" the whole name counts as the extension.
CONFLICT = re.compile(r"^(.*)\.sync-conflict-\d{8}-\d{6}-[A-Z0-9]{7}(.*)$")
BOM = "\ufeff"
SCAN_TIMEOUT = 2  # seconds


@dataclass
class Folder:
    id: str
    path: Path
    paused: bool


def find_config(home: Path) -> Optional[Path]:
    """The live config.xml: what `syncthing paths` prints, else the first existing one."""
    if system.have("syncthing"):
        result = system.run(["syncthing", "paths"], check=False, capture=True)
        lines = (result.stdout or "").splitlines() if result.returncode == 0 else []
        for i, line in enumerate(lines[:-1]):
            if line.strip() == "Configuration file:":
                path = Path(lines[i + 1].strip())
                return path if path.is_file() else None
    for directory in (".local/state/syncthing", ".config/syncthing"):
        path = home / directory / "config.xml"
        if path.is_file():
            return path
    return None


def folders(config: Path, home: Path) -> list[Folder]:
    """Folders with an absolute path (after expanding ~); others cannot be placed."""
    root = ET.parse(config).getroot()
    result = []
    for node in root.findall("folder"):
        raw = node.get("path", "")
        if raw == "~" or raw.startswith("~/"):
            raw = str(home) + raw[1:]
        if not os.path.isabs(raw):
            continue
        paused = (node.findtext("paused") or "").strip() == "true"
        result.append(Folder(node.get("id", ""), Path(raw), paused))
    return result


def rule_lines(text: str) -> list[str]:
    """The patterns of a rule file, without comments and blank lines."""
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("//")
    ]


def wired(lines: list[str], has_shared: bool) -> list[str]:
    """`.stignore` lines with the include (when the file exists) and the un-ignore on top.

    Every other line keeps its content and order; variants of the two lines are dropped.
    """
    rest = [
        line
        for line in lines
        if not INCLUDE_LINE.match(line) and not UNIGNORE_LINE.match(line)
    ]
    return [*([INCLUDE] if has_shared else []), UNIGNORE, *rest]


class Api:
    """The REST interface of the running Syncthing, from config.xml."""

    def __init__(self, config: Path) -> None:
        gui = ET.parse(config).getroot().find("gui")
        address = (gui.findtext("address") if gui is not None else "") or ""
        scheme = "https" if gui is not None and gui.get("tls") == "true" else "http"
        if address.startswith("/") or address.startswith(":"):
            address = ""  # a unix socket or an address without a host
        self.base = f"{scheme}://{address}/rest/" if address else ""
        self.key = (gui.findtext("apikey") if gui is not None else "") or ""
        # The GUI certificate is self-signed; the address is the local instance.
        handlers: list = [
            urllib.request.ProxyHandler({})
        ]  # never send the key to a proxy
        if scheme == "https":
            handlers.append(
                urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
            )
        self.opener = urllib.request.build_opener(*handlers)

    def call(
        self, method: str, path: str, body: object = None, timeout: float = 10
    ) -> tuple[int, object]:
        """(status, parsed JSON or text); status 0 when Syncthing does not answer."""
        if not self.base or not self.key:
            return 0, None
        request = urllib.request.Request(
            self.base + path,
            method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"X-API-Key": self.key},
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                text = response.read().decode(errors="replace")
                status = response.status
        except urllib.error.HTTPError as error:
            try:
                return error.code, error.read().decode(errors="replace")
            except (OSError, http.client.HTTPException):
                return error.code, ""
        except (OSError, ValueError, http.client.HTTPException):
            return 0, None
        try:
            return status, json.loads(text) if text.strip() else None
        except ValueError:
            return status, text


def global_state(api: Api, folder_id: str) -> str:
    """'unknown' (no device whose index arrived has the shared file), 'present',
    'deleted' (deleted on another device), 'rejected' (API key) or 'no answer'.

    A peer's copy is reported as global even while this device still ignores it.
    """
    query = urllib.parse.urlencode({"folder": folder_id, "file": GLOBAL})
    status, body = api.call("GET", f"db/file?{query}")
    if status == 404:
        return "unknown"
    if status in (401, 403):
        return "rejected"
    if status == 200 and isinstance(body, dict) and body.get("global"):
        return "deleted" if body["global"].get("deleted") else "present"
    return "no answer"


def clean_conflicts(path: Path) -> list[str]:
    """Delete conflict copies of the shared file with its content; report the others."""
    shared = path / GLOBAL
    messages = []
    for copy in sorted(path.glob("*sync-conflict-*")):
        match = CONFLICT.match(copy.name)
        if not match or match.group(1) + match.group(2) != GLOBAL or not copy.is_file():
            continue
        try:
            if shared.is_file() and copy.read_bytes() == shared.read_bytes():
                copy.unlink()
                messages.append(f"{copy}: removed (same content as {GLOBAL})")
            elif shared.is_file():
                messages.append(
                    f"{copy}: conflict copy with other rules; compare it with {GLOBAL} by hand"
                )
            else:
                messages.append(
                    f"{copy}: conflict copy of a missing {GLOBAL}; check it by hand"
                )
        except OSError as error:
            messages.append(f"{copy}: {error}")
    return messages


def _read_lines(path: Path) -> tuple[list[str], bool]:
    """The lines without a byte order mark, and whether there was one: Syncthing takes
    it as part of the first pattern, so a file with one is always rewritten."""
    if not path.is_file():
        return [], False
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    return text.removeprefix(BOM).splitlines(), text.startswith(BOM)


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", errors="surrogateescape")


def ensure_folder(api: Api, folder: Folder, rules_text: str) -> str:
    """'' when in place (or left alone on purpose), else what was done or why it waits."""
    path = folder.path
    if not path.is_dir():
        return "skipped: folder path is missing"
    if not os.access(path, os.W_OK):
        return "skipped: folder is not writable"
    shared = path / GLOBAL
    stignore = path / ".stignore"
    lines, bom = _read_lines(stignore)
    done = []
    if not shared.exists():
        # Without the file there is no include line (it would put the folder into an
        # error state), but the un-ignore line, so that the file can arrive.
        if bom or wired(lines, False) != lines:
            lines, bom = wired(lines, False), False
            _write_lines(stignore, lines)
            done.append(f"added {UNIGNORE}")
        state = "paused" if folder.paused else global_state(api, folder.id)
        if state == "deleted":
            # Deleted on purpose on another device: not recreated, nothing to report.
            return " and ".join(done)
        if state != "unknown":
            reason = {
                "present": f"{GLOBAL} exists on another device and has not arrived yet",
                "rejected": f"Syncthing rejected the API key; {GLOBAL} not checked",
            }.get(state, f"no {GLOBAL} yet (Syncthing not reachable or folder paused)")
            return f"waiting: {reason}" + (f" ({done[0]})" if done else "")
        shared.write_text(rules_text, encoding="utf-8")
        done.append(f"created {GLOBAL}")
    if bom or wired(lines, True) != lines:
        _write_lines(stignore, wired(lines, True))
        done.append(_top_change(lines, bom))
    if done:
        # Let Syncthing load the changed ignores at once instead of at its next scan.
        # The call returns only when the scan is done, which takes minutes on a large
        # folder, so do not wait for it.
        api.call(
            "POST",
            "db/scan?" + urllib.parse.urlencode({"folder": folder.id}),
            timeout=SCAN_TIMEOUT,
        )
    return " and ".join(done)


def _top_change(lines: list[str], bom: bool) -> str:
    """What putting the two lines on top changed in `lines`, for the log."""
    added = [
        name
        for name, pattern in (
            ("the include line", INCLUDE_LINE),
            (UNIGNORE, UNIGNORE_LINE),
        )
        if not any(pattern.match(line) for line in lines)
    ]
    if added:
        return "added " + " and ".join(added)
    if bom and wired(lines, True) == lines:
        return "removed a byte order mark"
    return f"moved the include line and {UNIGNORE} to the top"


def merged_defaults(rules: list[str], current: list[str]) -> list[str]:
    return [*rules, *(line for line in current if line not in rules)]


def ensure_defaults(api: Api, rules: list[str]) -> tuple[Optional[bool], int]:
    """Default ignore patterns: shared rules, then the host's own lines.

    (True: changed, False: in place, None: not checked; the HTTP status).
    """
    status, body = api.call("GET", "config/defaults/ignores")
    if status != 200 or not isinstance(body, dict):
        return None, status
    current = list(body.get("lines") or [])
    wanted = merged_defaults(rules, current)
    if wanted == current:
        return False, status
    status, _ = api.call("PUT", "config/defaults/ignores", {"lines": wanted})
    return (True if status == 200 else None), status


class SyncthingIgnoresMixin:
    def run_syncthing_ignores(self) -> None:
        """Wire every local Syncthing folder up to its shared ignore rules."""
        features, _ = feature_table.split(
            parse_profile_file(self.applied_host_path)["features"],
            self.current_context(),
            self.current_device(),
        )
        if FEATURE not in features:
            return
        config = find_config(self.home)
        if config is None:
            return
        rules_text = (Path(self.repo) / RULES).read_text(encoding="utf-8")
        try:
            api, local = Api(config), folders(config, self.home)
        except ET.ParseError as error:
            warn(f"syncthing: cannot read {config}: {error}")
            return
        for folder in local:
            # One broken folder must not keep the others or the defaults from running.
            try:
                if folder.path.is_dir() and os.access(folder.path, os.W_OK):
                    for message in clean_conflicts(folder.path):
                        log(f"syncthing: {message}")
                outcome = ensure_folder(api, folder, rules_text)
            except (OSError, ValueError) as error:
                outcome = f"skipped: {error}"
            if outcome.startswith("skipped"):
                warn(f"syncthing: {folder.path}: {outcome}")
            elif outcome:
                log(f"syncthing: {folder.path}: {outcome}")
        changed, status = ensure_defaults(api, rule_lines(rules_text))
        if changed:
            log("syncthing: default ignore patterns set to the shared rules")
        elif status in (401, 403):
            warn(
                f"syncthing: the API key in {config} was rejected; defaults not checked"
            )
        # Not running (status 0): silent; the defaults are checked on a later run.
