"""`machine env push`: local edits of ~/.env and ~/.env.host -> Bitwarden items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import system
from .core import log, warn
from .env_pull import (
    ASSIGNMENT,
    DECLINED,
    FAILED,
    NOTHING_TO_PUSH,
    PUSHED,
    assignment_parts,
    is_sourced,
    item_lines,
    line_value,
    parse_env_file,
    parse_reference,
    same_line,
)

ADD = "add"
CHANGE = "change"
REMOVE_KEY = "remove"


@dataclass
class Edit:
    kind: str  # ADD, CHANGE or REMOVE_KEY
    key: str
    item: str  # the env item that sets the key, or gets it
    line: Optional[str]  # the local line; None for a removal
    conflict: bool = False  # Bitwarden changed the key to another value since the pull
    reference: Optional[Tuple[str, str]] = None  # the line is a new reference
    # the item sets the key from this reference
    target: Optional[Tuple[str, str]] = None
    problem: str = ""  # why the edit cannot be written


def key_place(item: dict, key: str) -> Tuple[Optional[int], List[int]]:
    """(custom field index, note line indices) that set `key` in an env item."""
    field = next(
        (
            index
            for index, f in enumerate(item.get("fields") or [])
            if (f.get("name") or "").strip() == key
        ),
        None,
    )
    notes = (item.get("notes") or "").replace("\r\n", "\n").split("\n")
    lines = [
        index
        for index, line in enumerate(notes)
        if not line.lstrip().startswith("#")
        and (match := ASSIGNMENT.match(line))
        and match.group(1) == key
    ]
    return field, lines


def raw_value(item: dict, key: str) -> Optional[str]:
    """The value an env item sets for `key` before resolving (custom fields win)."""
    field, lines = key_place(item, key)
    if field is not None:
        return str(item["fields"][field].get("value") or "")
    if lines:
        notes = (item.get("notes") or "").replace("\r\n", "\n").split("\n")
        return assignment_parts(notes[lines[-1]])[2]
    return None


class EnvPushMixin:
    def _env_item_cached(self, cache: Dict[str, Optional[dict]], name: str):
        """The env item with exactly this name; None when missing or not unique."""
        if name not in cache:
            found = self.bw_items_named(name) or []
            cache[name] = found[0] if len(found) == 1 else None
            if len(found) > 1:
                warn(f"{len(found)} Bitwarden items are named {name}")
        return cache[name]

    def _env_edits(
        self, path: Path, item_name: str, new: str
    ) -> Tuple[List[Edit], Dict[str, Optional[dict]]]:
        """The keys the file adds, changes or removes relative to the last pull."""
        state = parse_env_file(self.env_state_path(path).read_text())
        base = item_lines(state)
        # Keys carried in the local-only section stay with the pull's own choices.
        carried = state.keys() - set(base)
        current = parse_env_file(path.read_text(encoding="utf-8"))
        local = {key: line for key, line, _section in current.assignments}
        upcoming_parsed = parse_env_file(new)
        upcoming = item_lines(upcoming_parsed)
        sections = {key: section for key, _line, section in upcoming_parsed.assignments}
        items: Dict[str, Optional[dict]] = {}
        edits = []
        for key in [*local, *(key for key in base if key not in local)]:
            mine, before, now = local.get(key), base.get(key), upcoming.get(key)
            if key in carried or same_line(mine, before):
                continue
            conflict = not same_line(now, before)
            if conflict and same_line(mine, now):
                continue
            item = sections.get(key) if now is not None else None
            item = item if item and item.startswith("env/") else item_name
            if mine is None:
                kind = REMOVE_KEY
            elif before is None and now is None:
                kind = ADD
            else:
                kind = CHANGE
            edit = Edit(kind, key, item, mine, conflict)
            if mine is not None:
                edit.reference = parse_reference(assignment_parts(mine)[2])
            raw_item = self._env_item_cached(items, item)
            if kind != ADD and raw_item is None:
                edit.problem = f"Bitwarden {item} not found or not unique"
            if kind == CHANGE and not edit.reference and raw_item:
                raw = raw_value(raw_item, key)
                edit.target = parse_reference(raw) if raw is not None else None
            edits.append(edit)
        return edits, items

    def _describe_edit(self, edit: Edit) -> str:
        if edit.kind == REMOVE_KEY:
            text = f"remove  {edit.key}"
        elif edit.reference:
            name, target = edit.reference
            text = f"{edit.kind:<7} {edit.key} = {{{{bw:{name}/{target}}}}}"
        elif edit.target:
            name, target = edit.target
            text = f'{edit.kind:<7} {edit.key}: new {target} of Bitwarden "{name}"'
        else:
            text = f"{edit.kind:<7} {edit.key}"
        conflict = " (changed in Bitwarden too)" if edit.conflict else ""
        return f"  {text}  [{edit.item}]{conflict}"

    def _reference_problems(self, edits: List[Edit]) -> List[str]:
        problems = []
        for edit in edits:
            if edit.problem:
                problems.append(f"{edit.key}: {edit.problem}")
            reference = edit.reference or edit.target
            if not reference:
                continue
            name, target = reference
            value, why = self.resolve_reference(name, target)
            if value is None:
                problems.append(f'{edit.key}: Bitwarden "{name}" ({target}): {why}')
        return problems

    def _apply_env_edits(
        self, path: Path, edits: List[Edit], items: Dict[str, Optional[dict]]
    ) -> bool:
        sourced = is_sourced(path.read_text(encoding="utf-8"))
        changed: Dict[str, dict] = {}
        added: Dict[str, List[str]] = {}
        for edit in edits:
            if edit.target:
                name, target = edit.target
                found = self._referenced_items(name) or []
                if len(found) != 1:
                    warn(f'Bitwarden "{name}" is not unique; {edit.key} not pushed')
                    return False
                referenced = changed.get(found[0]["id"], found[0])
                value = line_value(edit.line, sourced)
                if target in ("password", "username"):
                    referenced.setdefault("login", {})[target] = value
                else:
                    field_name = target.removeprefix("field:")
                    for f in referenced.get("fields") or []:
                        if f.get("name") == field_name:
                            f["value"] = value
                changed[referenced["id"]] = referenced
                continue
            item = items.get(edit.item)
            if item is None or (
                edit.kind == ADD and key_place(item, edit.key) == (None, [])
            ):
                added.setdefault(edit.item, []).append(edit.line)
                continue
            item = changed.get(item["id"], item)
            field, lines = key_place(item, edit.key)
            notes = (item.get("notes") or "").replace("\r\n", "\n").split("\n")
            if edit.kind == REMOVE_KEY:
                if field is not None:
                    del item["fields"][field]
                notes = [line for i, line in enumerate(notes) if i not in lines]
            elif field is not None:
                item["fields"][field]["value"] = line_value(edit.line, sourced)
            elif lines:
                notes[lines[-1]] = edit.line
            else:
                notes.append(edit.line)
            item["notes"] = "\n".join(notes)
            changed[item["id"]] = item
        ok = all(self.bw_edit_item(item) for item in changed.values())
        for item_name, lines in added.items():
            ok = self._add_to_bitwarden(item_name, lines) and ok
        return ok

    def push_env_file(self, path: Path, item_name: str, new: str) -> str:
        """Write the local edits of one env file to Bitwarden after confirmation.

        `new` is the content a pull would write now; Bitwarden must be unlocked."""
        if not self.env_state_path(path).is_file():
            warn(f"{self.display(path)} has no pulled state yet; run: machine env pull")
            return FAILED
        if parse_env_file(path.read_text(encoding="utf-8")).shell_code:
            warn(f"{self.display(path)} contains shell code; machine cannot push it")
            return FAILED
        edits, items = self._env_edits(path, item_name, new)
        if not edits:
            log(f"{self.display(path)}: nothing to push")
            return NOTHING_TO_PUSH
        print(f"\n{self.display(path)} -> Bitwarden:")
        for edit in edits:
            print(self._describe_edit(edit))
        kept = []
        for edit in edits:
            if edit.kind == REMOVE_KEY:
                too = " (it was changed there too)" if edit.conflict else ""
                question = f"Remove {edit.key} from Bitwarden {edit.item}?{too}"
            elif edit.conflict:
                question = (
                    f"{edit.key} was changed in Bitwarden {edit.item} too; "
                    "overwrite it with the local value?"
                )
            else:
                kept.append(edit)
                continue
            if system.prompt_yes_no(question, False):
                kept.append(edit)
        if not kept:
            log("nothing left to push")
            return NOTHING_TO_PUSH
        problems = self._reference_problems(kept)
        if problems:
            warn("nothing pushed; these changes cannot be written:")
            for problem in problems:
                print(f"  {problem}")
            return FAILED
        if not system.prompt_yes_no(f"Write {len(kept)} change(s) to Bitwarden?", True):
            log("nothing pushed")
            return DECLINED
        if not self._apply_env_edits(path, kept, items):
            warn("could not write every change to Bitwarden; see the messages above")
            return FAILED
        log(f"pushed {len(kept)} change(s) from {self.display(path)} to Bitwarden")
        return PUSHED

    def cmd_env_push(self, host: bool = False) -> int:
        if not self.current_context():
            log("no context (container): no env files to push")
            return 0
        files = list(self.env_files().items())
        path, item_name = files[-1] if host else files[0]
        if not path.is_file():
            warn(f"{self.display(path)} does not exist; nothing to push")
            return 1
        if not self.env_state_path(path).is_file():
            warn(f"{self.display(path)} has no pulled state yet; run: machine env pull")
            return 1
        if not system.is_tty() or getattr(self, "unattended", False):
            warn("machine env push asks before writing; run it in a terminal")
            return 1
        if not self.require_bitwarden() or not self.unlock_bitwarden():
            return 1
        system.run(["bw", "sync"], capture=True)
        generated, _got = self._env_generated(self.env_item_names())
        result = self.push_env_file(path, item_name, self.render_env(generated[path]))
        if result in (FAILED, DECLINED):
            return 1 if result == FAILED else 0
        return self.cmd_env_pull(interactive=True, discard={path})
