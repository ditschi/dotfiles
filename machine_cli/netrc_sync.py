"""`machine env pull|push` for ~/.netrc: Bitwarden items -> ~/.netrc (spec netrc-files)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import system
from .core import ENV_GROUPS, log, warn, write_private
from .env_pull import (
    DECLINED,
    DISCARD,
    FAILED,
    NOTHING_TO_PUSH,
    PUSH,
    PUSHED,
    SKIP,
    parse_reference,
    reference_value,
)

# A reference is one token although item names contain spaces.
TOKEN = re.compile(r"\{\{bw:.+?\}\}|\S+")
# Not writable unchanged: tools differ in how they read quotes, escapes and blanks.
UNSAFE_VALUE = re.compile(r"[\s'\"\\]")

ADD = "add"
CHANGE = "change"
REMOVE = "remove"


class Unresolved(Exception):
    """A host block that cannot be written; the message names item and target."""


class ListingFailed(Exception):
    """Bitwarden items could not be listed; ~/.netrc stays unchanged."""


@dataclass
class Block:
    host: str  # machine name, or "default"
    lines: List[str]  # leading comments and code lines, no blank lines
    start: int = 0  # first and last line index in the parsed text
    end: int = 0

    def code(self) -> List[str]:
        return [
            line
            for line in self.lines
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def tokens(self) -> List[str]:
        return TOKEN.findall("\n".join(self.code()))


def parse_netrc(text: str) -> List[Block]:
    """Host blocks; comment lines before a block belong to it."""
    blocks: List[Block] = []
    pending: List[Tuple[int, str]] = []
    for index, line in enumerate(text.replace("\r\n", "\n").split("\n")):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            pending.append((index, line))
            continue
        tokens = TOKEN.findall(line)
        comments = [(i, text_) for i, text_ in pending if text_.strip()]
        pending = []
        if tokens[0] in ("machine", "default"):
            host = (
                tokens[1] if tokens[0] == "machine" and len(tokens) > 1 else "default"
            )
            start = comments[0][0] if comments else index
            blocks.append(
                Block(host, [text_ for _i, text_ in comments] + [line], start, index)
            )
        elif blocks:
            blocks[-1].lines.extend(text_ for _i, text_ in comments)
            blocks[-1].lines.append(line)
            blocks[-1].end = index
    return blocks


def replace_tokens(lines: List[str], replacements: Dict[int, str]) -> List[str]:
    """Replace the n-th code token of a block's lines."""
    out: List[str] = []
    count = 0
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            out.append(line)
            continue

        def swap(match: "re.Match[str]") -> str:
            nonlocal count
            value = replacements.get(count, match.group(0))
            count += 1
            return value

        out.append(TOKEN.sub(swap, line))
    return out


def keyed_blocks(text: str) -> Dict[str, Block]:
    """Blocks by key: the host, and `host#2`, `host#3` for repeated hosts."""
    counts: Dict[str, int] = {}
    keyed: Dict[str, Block] = {}
    for block in parse_netrc(text):
        counts[block.host] = counts.get(block.host, 0) + 1
        n = counts[block.host]
        keyed[block.host if n == 1 else f"{block.host}#{n}"] = block
    return keyed


def host_tokens(text: str) -> Dict[str, Tuple[str, ...]]:
    return {key: tuple(b.tokens()) for key, b in keyed_blocks(text).items()}


def read_text(path: Path) -> str:
    """Read a netrc whatever its encoding; encode() writes it back unchanged."""
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def encode(text: str) -> bytes:
    return text.encode("utf-8", errors="surrogateescape")


@dataclass
class NetrcEdit:
    kind: str  # ADD, CHANGE or REMOVE
    host: str
    item: str  # the netrc item that holds the block, or gets it
    local: Optional[Block]  # the block in ~/.netrc; None for a removal
    conflict: bool = False  # Bitwarden changed the block to another value too
    template: Optional[Block] = None  # the block in the item notes
    writes: List[Tuple[str, str, str]] = field(default_factory=list)
    literal: Dict[int, str] = field(default_factory=dict)
    rewrite: bool = False  # the block layout changed: write the local text
    problem: str = ""


class NetrcSyncMixin:
    # --- paths and items -------------------------------------------------

    @property
    def netrc_path(self) -> Path:
        return self.home / ".netrc"

    @property
    def netrc_state_path(self) -> Path:
        """The content machine last wrote to ~/.netrc."""
        return self.state_dir / "netrc-generated" / "netrc"

    @property
    def netrc_origins_path(self) -> Path:
        return self.state_dir / "netrc-generated" / "origins.json"

    @property
    def netrc_unresolved_path(self) -> Path:
        """Host blocks the last pull skipped (hosts and reasons, no values)."""
        return self.state_dir / "netrc-generated" / "unresolved.json"

    def netrc_item_names(self) -> List[str]:
        groups = ENV_GROUPS.get(self.current_context(), [])
        if not groups:
            return []
        return [
            *(f"netrc/groups/{group}" for group in groups),
            f"netrc/hosts/{system.hostname_short()}",
        ]

    def _netrc_origins(self) -> Dict[str, List]:
        """Block key -> [item, n-th block of that host in the item]."""
        try:
            return json.loads(self.netrc_origins_path.read_text())
        except (OSError, ValueError):
            return {}

    # --- generation --------------------------------------------------------

    def _netrc_value(self, name: str, target: str) -> str:
        items = self._referenced_items(name)
        if items is None:
            raise ListingFailed()
        where = f'Bitwarden "{name}" ({target})'
        if not items:
            raise Unresolved(f"{where}: item not found")
        if len(items) > 1:
            raise Unresolved(f"{where}: {len(items)} items with this name")
        value = reference_value(items[0], target)
        if value is None:
            raise Unresolved(f"{where}: item has no {target}")
        if UNSAFE_VALUE.search(value):
            raise Unresolved(
                f"{where}: value has whitespace, a quote or a backslash and cannot "
                "be written unchanged into a netrc"
            )
        return value

    def _token_value(self, match: "re.Match[str]") -> str:
        token = match.group(0)
        if not token.startswith("{{bw:"):
            return token
        reference = parse_reference(token)
        if not reference:
            raise Unresolved("malformed reference")
        return self._netrc_value(*reference)

    def _resolved_block(self, block: Block) -> str:
        if block.host.startswith("{{bw:"):
            raise Unresolved("a reference cannot name the machine")
        out = []
        for line in block.lines:
            if line.lstrip().startswith("#"):
                # never write the text of a reference, not even in a comment
                if "{{bw:" not in line:
                    out.append(line)
            else:
                out.append(TOKEN.sub(self._token_value, line))
        return "\n".join(out)

    def netrc_generated(self) -> Optional[str]:
        """What a pull writes now; None leaves ~/.netrc unchanged."""
        self._env_ref_items = {}
        self.netrc_listing_failed = False
        self.netrc_unresolved: List[Tuple[str, str, str]] = []
        self.netrc_written_origins: Dict[str, List] = {}
        entries: List[Tuple[str, str, int, Block]] = []
        found = False
        # The host item comes first: tools that take the first matching machine
        # then use it, and the text of both items stays as it is.
        for name in reversed(self.netrc_item_names()):
            items = self.bw_items_named(name)
            if items is None:
                self.netrc_listing_failed = True
                warn(f"cannot list Bitwarden items; left ~/.netrc unchanged ({name})")
                return None
            if len(items) > 1:
                self.netrc_listing_failed = True
                warn(
                    f"{len(items)} Bitwarden items are named {name}; left ~/.netrc unchanged"
                )
                return None
            if not items:
                continue
            found = True
            seen: Dict[str, int] = {}
            for block in parse_netrc(items[0].get("notes") or ""):
                entries.append((block.host, name, seen.get(block.host, 0), block))
                seen[block.host] = seen.get(block.host, 0) + 1
        if not found:
            return None
        rendered: List[str] = []
        counts: Dict[str, int] = {}
        for host, name, nth, block in entries:
            try:
                rendered.append(self._resolved_block(block))
            except ListingFailed:
                self.netrc_listing_failed = True
                warn("cannot list Bitwarden items; left ~/.netrc unchanged")
                return None
            except Unresolved as error:
                self.netrc_unresolved.append((host, name, str(error)))
                continue
            counts[host] = counts.get(host, 0) + 1
            key = host if counts[host] == 1 else f"{host}#{counts[host]}"
            self.netrc_written_origins[key] = [name, nth]
        if not rendered:
            return None
        return "\n\n".join(rendered) + "\n"

    # --- unpushed edits ----------------------------------------------------

    def netrc_unpushed_edits(self, new: Optional[str] = None) -> List[Tuple[str, str]]:
        """(kind, host) of blocks changed, removed or added since the last pull.

        With `new` (what a pull would write now), a block that already equals it
        is not an edit."""
        if not self.netrc_state_path.is_file() or not self.netrc_path.is_file():
            return []
        base = host_tokens(read_text(self.netrc_state_path))
        now = host_tokens(read_text(self.netrc_path))
        upcoming = host_tokens(new) if new is not None else None
        edits = []
        for host in [*now, *(host for host in base if host not in now)]:
            if now.get(host) == base.get(host):
                continue
            if upcoming is not None and now.get(host) == upcoming.get(host):
                continue
            kind = REMOVE if host not in now else ADD if host not in base else CHANGE
            edits.append((kind, host))
        return edits

    def netrc_attention(self) -> List[str]:
        """Unpushed edits and skipped blocks, read from the state (no Bitwarden)."""
        if not self.current_context() or not self.netrc_item_names():
            return []
        open_items = []
        edits = self.netrc_unpushed_edits()
        if edits:
            hosts = ", ".join(host for _kind, host in edits)
            open_items.append(
                f"~/.netrc: local edits of {hosts} not in Bitwarden (push or discard)"
            )
        try:
            unresolved = json.loads(self.netrc_unresolved_path.read_text())
        except (OSError, ValueError):
            unresolved = []
        for host, item, why in unresolved:
            open_items.append(f"~/.netrc: {host} skipped ({item}): {why}")
        return open_items

    # --- pull --------------------------------------------------------------

    def _choose_for_netrc_edits(self, edits: List[Tuple[str, str]]) -> str:
        labels = {
            PUSH: "push the edits to Bitwarden now (machine env push)",
            DISCARD: "discard the edits (backup kept)",
            SKIP: "skip (leave ~/.netrc unchanged)",
        }
        hosts = ", ".join(host for _kind, host in edits)
        print(f"\n~/.netrc has local edits not in Bitwarden: {hosts}")
        picked = system.choose("Choose", list(labels.values()), labels[SKIP])
        return next(choice for choice, label in labels.items() if label == picked)

    def _write_netrc(self, content: str) -> bool:
        """Write ~/.netrc and the state; True when the file content changed."""
        path = self.netrc_path
        existing = read_text(path) if path.is_file() else None
        write_private(self.netrc_state_path, encode(content))
        write_private(
            self.netrc_origins_path, json.dumps(self.netrc_written_origins).encode()
        )
        if existing is not None and existing != content:
            backup_dir = self.state_dir / "env-backup"
            backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            backup_dir.chmod(0o700)
            digest = hashlib.sha256(encode(existing)).hexdigest()[:16]
            backup = backup_dir / f"netrc.{digest}"
            if not backup.exists():
                write_private(backup, encode(existing))
            log(f"backed up existing {path} to {backup}")
        if existing != content:
            write_private(path, encode(content))
            return True
        if path.stat().st_mode & 0o077:
            path.chmod(0o600)
        return False

    def _report_netrc_unresolved(self) -> None:
        write_private(
            self.netrc_unresolved_path, json.dumps(self.netrc_unresolved).encode()
        )
        for host, item, why in self.netrc_unresolved:
            warn(
                f"~/.netrc: skipped the block for {host} ({item}): {why}; "
                "run: machine attention"
            )

    def sync_netrc(self, interactive: bool = False, discard=()) -> int:
        """The ~/.netrc part of `machine env pull`; Bitwarden is unlocked."""
        if not self.current_context():
            return 0
        generated = self.netrc_generated()
        if generated is None:
            # No item or no block to write leaves the file alone; a failure to list
            # items leaves the last report of skipped blocks alone too.
            if not self.netrc_listing_failed:
                self._report_netrc_unresolved()
            return 0
        path = self.netrc_path
        ask = system.is_tty() and not getattr(self, "unattended", False)
        held = False
        edits = [] if path in discard else self.netrc_unpushed_edits(generated)
        if edits:
            choice = self._choose_for_netrc_edits(edits) if ask else SKIP
            if choice == PUSH:
                result = self.push_netrc_file(generated, self.netrc_item_names()[0])
                if result in (PUSHED, NOTHING_TO_PUSH):
                    generated = self.netrc_generated()
                    if generated is None:
                        return 1
                else:
                    held = True
            elif choice != DISCARD:
                held = True
        if held:
            hosts = ", ".join(host for _kind, host in edits)
            warn(
                f"~/.netrc: local edits of {hosts} are not in Bitwarden; left "
                "unchanged; run: machine env push (or machine attention)"
            )
        else:
            if self._write_netrc(generated):
                count = len(self.netrc_written_origins)
                log(f"wrote ~/.netrc from {count} Bitwarden host block(s)")
            if any(
                key.split("#")[0].lower() == "github.com"
                for key in self.netrc_written_origins
            ):
                warn(
                    "~/.netrc has a block for github.com: curl then sends these "
                    "credentials up front, so git credential helpers do not run "
                    "for it (see docs/git.md)"
                )
        self._report_netrc_unresolved()
        return 0

    # --- push --------------------------------------------------------------

    def _netrc_item_cached(self, cache: Dict[str, Optional[dict]], name: str):
        if name not in cache:
            found = self.bw_items_named(name) or []
            cache[name] = found[0] if len(found) == 1 else None
            if len(found) > 1:
                warn(f"{len(found)} Bitwarden items are named {name}")
        return cache[name]

    def _netrc_edits(
        self, new: str, default_item: str
    ) -> Tuple[List[NetrcEdit], Dict[str, Optional[dict]]]:
        state = keyed_blocks(read_text(self.netrc_state_path))
        local = keyed_blocks(read_text(self.netrc_path))
        upcoming = host_tokens(new)
        origins = self._netrc_origins()
        items: Dict[str, Optional[dict]] = {}
        edits = []
        for host in [*local, *(host for host in state if host not in local)]:
            mine, before = local.get(host), state.get(host)
            mine_t = tuple(mine.tokens()) if mine else None
            before_t = tuple(before.tokens()) if before else None
            now_t = upcoming.get(host)
            if mine_t == before_t:
                continue
            conflict = now_t != before_t
            if conflict and mine_t == now_t:
                continue
            if mine is None:
                kind = REMOVE
            elif before is None and now_t is None:
                kind = ADD
            else:
                kind = CHANGE
            edit = NetrcEdit(kind, host, default_item, mine, conflict)
            origin = origins.get(host)
            nth = 0
            if origin:
                edit.item, nth = origin
            item = self._netrc_item_cached(items, edit.item)
            if kind != ADD and item is None:
                edit.problem = f"Bitwarden {edit.item} not found or not unique"
            if kind != ADD and item is not None:
                notes = (item.get("notes") or "").replace("\r\n", "\n")
                name = (mine or before).host
                same = [b for b in parse_netrc(notes) if b.host == name]
                edit.template = same[nth] if nth < len(same) else None
            if kind == CHANGE:
                self._align_netrc_edit(edit, before)
            edits.append(edit)
        return edits, items

    @staticmethod
    def _align_netrc_edit(edit: NetrcEdit, before: Optional[Block]) -> None:
        """Map the changed tokens to the item's literals and references."""
        if not edit.template or not before:
            edit.rewrite = True
            return
        template, last, local = (
            edit.template.tokens(),
            before.tokens(),
            edit.local.tokens(),
        )
        if not len(template) == len(last) == len(local):
            edit.rewrite = True
            return
        for index, value in enumerate(local):
            if value == last[index]:
                continue
            reference = (
                parse_reference(template[index])
                if template[index].startswith("{{bw:")
                else None
            )
            if reference and not value.startswith("{{bw:"):
                edit.writes.append((*reference, value))
            else:
                edit.literal[index] = value

    def _describe_netrc_edit(self, edit: NetrcEdit) -> str:
        if edit.kind == REMOVE:
            text = f"remove  {edit.host}"
        elif edit.writes:
            targets = ", ".join(f'{t} of "{n}"' for n, t, _v in edit.writes)
            text = f"{edit.kind:<7} {edit.host}: new {targets}"
        elif edit.rewrite and edit.kind == CHANGE:
            text = f"{edit.kind:<7} {edit.host} (block rewritten as written locally)"
        else:
            text = f"{edit.kind:<7} {edit.host}"
        references = [
            token
            for token in (edit.local.tokens() if edit.local else [])
            if token.startswith("{{bw:")
        ]
        if references:
            text += f" = {' '.join(references)}"
        conflict = " (changed in Bitwarden too)" if edit.conflict else ""
        return f"  {text}  [{edit.item}]{conflict}"

    def _netrc_problems(self, edits: List[NetrcEdit]) -> List[str]:
        problems = []
        for edit in edits:
            if edit.problem:
                problems.append(f"{edit.host}: {edit.problem}")
            new_values = [value for _n, _t, value in edit.writes]
            new_values += [
                value
                for value in edit.literal.values()
                if not value.startswith("{{bw:")
            ]
            if any(UNSAFE_VALUE.search(value) for value in new_values):
                problems.append(
                    f"{edit.host}: a new value has a quote or a backslash and "
                    "cannot be written unchanged into a netrc"
                )
            references = [
                parse_reference(token)
                for token in (edit.local.tokens() if edit.local else [])
                if token.startswith("{{bw:")
            ]
            references += [(name, target) for name, target, _v in edit.writes]
            for reference in references:
                if not reference:
                    problems.append(f"{edit.host}: malformed reference")
                    continue
                try:
                    self._netrc_value(*reference)
                except Unresolved as error:
                    problems.append(f"{edit.host}: {error}")
                except ListingFailed:
                    problems.append(f"{edit.host}: cannot list Bitwarden items")
        return problems

    def _apply_netrc_edits(
        self, edits: List[NetrcEdit], items: Dict[str, Optional[dict]]
    ) -> bool:
        changed: Dict[str, dict] = {}
        spans: Dict[str, List[Tuple[int, int, List[str]]]] = {}
        added: Dict[str, List[str]] = {}
        for edit in edits:
            for name, target, value in edit.writes:
                found = self._referenced_items(name) or []
                if len(found) != 1:
                    warn(f'Bitwarden "{name}" is not unique; {edit.host} not pushed')
                    return False
                referenced = changed.get(found[0]["id"], found[0])
                if target in ("password", "username"):
                    referenced.setdefault("login", {})[target] = value
                else:
                    for f in referenced.get("fields") or []:
                        if f.get("name") == target.removeprefix("field:"):
                            f["value"] = value
                changed[referenced["id"]] = referenced
            item = items.get(edit.item)
            if edit.kind == ADD or (edit.template is None and edit.kind == CHANGE):
                added.setdefault(edit.item, []).extend(edit.local.lines + [""])
                continue
            if item is None or edit.template is None:
                continue
            if edit.kind == REMOVE:
                new_lines: List[str] = []
            elif edit.literal:
                new_lines = replace_tokens(edit.template.lines, edit.literal)
            elif edit.rewrite:
                new_lines = list(edit.local.lines)
            else:
                continue
            item = changed.get(item["id"], item)
            spans.setdefault(item["id"], []).append(
                (edit.template.start, edit.template.end, new_lines)
            )
            changed[item["id"]] = item
        for item_id, operations in spans.items():
            item = changed[item_id]
            lines = (item.get("notes") or "").replace("\r\n", "\n").split("\n")
            for start, end, new_lines in sorted(operations, reverse=True):
                stop = end + 1
                lines[start:stop] = new_lines
            item["notes"] = "\n".join(lines)
        ok = all(self.bw_edit_item(item) for item in changed.values())
        for item_name, lines in added.items():
            ok = self._add_netrc_to_bitwarden(item_name, lines) and ok
        return ok

    def _add_netrc_to_bitwarden(self, item_name: str, lines: List[str]) -> bool:
        if system.run(["bw", "sync"], capture=True, check=False).returncode != 0:
            return False
        block = "\n".join(
            [
                f"# added from {system.hostname_short()} on {time.strftime('%Y-%m-%d')}",
                *lines,
            ]
        ).rstrip("\n")
        found = self.bw_items_named(item_name)
        if found is None or len(found) > 1:
            return False
        if not found:
            created = self.bw_create_item(
                {
                    "type": 2,
                    "name": item_name,
                    "notes": block,
                    "secureNote": {"type": 0},
                }
            )
            return created is not None
        item = found[0]
        notes = (item.get("notes") or "").rstrip("\n")
        item["notes"] = f"{notes}\n\n{block}" if notes else block
        return self.bw_edit_item(item)

    def push_netrc_file(self, new: str, item_name: str) -> str:
        """Write the local edits of ~/.netrc to Bitwarden after confirmation.

        `new` is what a pull would write now; Bitwarden must be unlocked."""
        if not self.netrc_state_path.is_file():
            warn("~/.netrc has no pulled state yet; run: machine env pull")
            return FAILED
        edits, items = self._netrc_edits(new, item_name)
        if not edits:
            log("~/.netrc: nothing to push")
            return NOTHING_TO_PUSH
        print("\n~/.netrc -> Bitwarden:")
        for edit in edits:
            print(self._describe_netrc_edit(edit))
        kept = []
        for edit in edits:
            if edit.kind == REMOVE:
                too = " (it was changed there too)" if edit.conflict else ""
                question = f"Remove {edit.host} from Bitwarden {edit.item}?{too}"
            elif edit.conflict:
                question = (
                    f"{edit.host} was changed in Bitwarden {edit.item} too; "
                    "overwrite it with the local block?"
                )
            else:
                kept.append(edit)
                continue
            if system.prompt_yes_no(question, False):
                kept.append(edit)
        if not kept:
            log("nothing left to push")
            return NOTHING_TO_PUSH
        problems = self._netrc_problems(kept)
        if problems:
            warn("nothing pushed; these changes cannot be written:")
            for problem in problems:
                print(f"  {problem}")
            return FAILED
        if not system.prompt_yes_no(f"Write {len(kept)} change(s) to Bitwarden?", True):
            log("nothing pushed")
            return DECLINED
        if not self._apply_netrc_edits(kept, items):
            warn("could not write every change to Bitwarden; see the messages above")
            return FAILED
        log(f"pushed {len(kept)} change(s) from ~/.netrc to Bitwarden")
        return PUSHED
