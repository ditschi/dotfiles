"""Local work during an update: trial merge, named stash entries, guarded rebase.

Every stash entry this module creates is named `machine update <date>: <why>` and
recorded in the update state, so it is either re-applied completely or shown by
`machine attention` until the user restores or drops it."""

from __future__ import annotations

import subprocess
import time
from typing import Optional

from . import system
from .core import log, warn

UNCOMMITTED_CONFLICT = "uncommitted local changes conflict with the incoming ones"
STASH_PREFIX = "machine update"


class LocalWorkMixin:
    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return system.run(
            ["git", "-C", str(self.repo), *args], capture=True, check=False
        )

    def _rev(self, ref: str) -> str:
        result = self._git("rev-parse", "--verify", "--quiet", ref)
        return (result.stdout or "").strip() if result.returncode == 0 else ""

    def untracked_paths(self) -> list[str]:
        result = self._git("ls-files", "--others", "--exclude-standard", "-z")
        return [path for path in (result.stdout or "").split("\0") if path]

    def commit_count(self, revision_range: str) -> int:
        result = self._git("rev-list", "--count", revision_range)
        try:
            return int((result.stdout or "0").strip())
        except ValueError:
            return 0

    # --- trial merge ------------------------------------------------------

    def trial_conflicts(
        self, target: str, overlap: list[str], added: set[str]
    ) -> list[str]:
        """Paths of `overlap` whose local changes do not merge cleanly onto `target`.

        Nothing in the checkout changes. An untracked file at a path the incoming
        commits add is a conflict. Without `git merge-tree --write-tree` (older git)
        every overlapping path counts as a conflict."""
        untracked = set(self.untracked_paths())
        conflicts = {path for path in overlap if path in untracked and path in added}
        tracked = [path for path in overlap if path not in untracked]
        if not tracked:
            return sorted(conflicts)
        local = (self._git("stash", "create").stdout or "").strip()
        if not local:
            return sorted(conflicts | set(tracked))
        result = self._git(
            "merge-tree",
            "--write-tree",
            "--name-only",
            "--no-messages",
            "--merge-base=HEAD",
            target,
            local,
        )
        if result.returncode == 0:
            return sorted(conflicts)
        names = set((result.stdout or "").splitlines()[1:]) & set(tracked)
        if result.returncode != 1 or not names:
            names = set(tracked)  # unknown failure or old git: count every overlap
        return sorted(conflicts | names)

    # --- named stash entries ---------------------------------------------

    def _stash_message(self, why: str) -> str:
        return f"{STASH_PREFIX} {time.strftime('%Y-%m-%dT%H:%M:%S')}: {why}"

    def _record_stash(self, sha: str, add: bool) -> None:
        values = self.read_update_state()
        shas = [entry for entry in values["stash"].split(",") if entry]
        shas = [entry for entry in shas if entry != sha] + ([sha] if add else [])
        self.write_update_state(values["state"], values["reason"], stash=",".join(shas))

    @staticmethod
    def is_machine_stash(message: str) -> bool:
        """`git stash list` shows `On <branch>: <message>`; ours start with STASH_PREFIX."""
        return message.partition(": ")[2].startswith(STASH_PREFIX + " ")

    def stash_entries(self) -> list[tuple[str, str, str]]:
        """(ref, sha, message) of the stash entries `machine` made that still exist.

        Recorded entries and entries recognised by their name (for example from an
        older state file) both count."""
        recorded = [
            entry for entry in self.read_update_state()["stash"].split(",") if entry
        ]
        result = self._git("stash", "list", "--format=%gd%x00%H%x00%gs")
        entries = []
        for line in (result.stdout or "").splitlines():
            ref, sha, message = (line.split("\0") + ["", ""])[:3]
            if sha in recorded or self.is_machine_stash(message):
                entries.append((ref, sha, message))
        existing = {sha for _ref, sha, _message in entries}
        for sha in recorded:
            if sha not in existing:  # dropped or popped by hand
                self._record_stash(sha, add=False)
        return entries

    def stash_push(self, why: str, paths: Optional[list[str]] = None) -> str:
        """Put local changes (all tracked ones, or only `paths`) into a named entry."""
        command = ["stash", "push", "-m", self._stash_message(why)]
        if paths:
            command += ["--include-untracked", "--", *paths]
        before = self._rev("refs/stash")
        result = self._git(*command)
        sha = self._rev("refs/stash")
        if result.returncode != 0 or not sha or sha == before:
            return ""
        self._record_stash(sha, add=True)
        return sha

    def stash_store_copy(self, why: str) -> str:
        """Record the local changes as a named entry without touching the checkout."""
        sha = (self._git("stash", "create").stdout or "").strip()
        if not sha:
            return ""
        if self._git("stash", "store", "-m", self._stash_message(why), sha).returncode:
            return ""
        self._record_stash(sha, add=True)
        return sha

    def _stash_ref(self, sha: str) -> str:
        for ref, entry, _message in self.stash_entries():
            if entry == sha:
                return ref
        return ""

    def stash_drop(self, sha: str) -> None:
        ref = self._stash_ref(sha)
        if ref:
            self._git("stash", "drop", ref)
        self._record_stash(sha, add=False)

    def has_unmerged_paths(self) -> bool:
        result = self._git("diff", "--name-only", "--diff-filter=U")
        return bool((result.stdout or "").strip())

    def stash_apply(self, sha: str) -> bool:
        """Re-apply an entry; drop it only when it applied completely."""
        result = self._git("stash", "apply", sha)
        if result.returncode == 0 and not self.has_unmerged_paths():
            self.stash_drop(sha)
            return True
        return False

    # --- updates that keep local work -----------------------------------

    def fast_forward_keeping_local(self, target: str) -> bool:
        """Fast-forward to `target` and keep every local change, or change nothing."""
        previous = self.repo_revision()
        changed = set(
            (self._git("diff", "--name-only", "HEAD", target).stdout or "").splitlines()
        )
        tracked = set(self.local_changes()) - set(self.untracked_paths())
        if not (tracked & changed):
            return self._git("merge", "--ff-only", target).returncode == 0
        sha = self.stash_push("kept during the update")
        if not sha:
            return False
        if self._git("merge", "--ff-only", target).returncode == 0 and self.stash_apply(
            sha
        ):
            return True
        warn("local changes did not apply on the new revision; going back")
        self._git("reset", "--hard", previous)
        if not self.stash_apply(sha):
            warn(f"local changes kept in the stash entry {self._stash_ref(sha)}")
        return False

    # --- diverged history -------------------------------------------------

    def operation_in_progress(self) -> bool:
        for name in (
            "rebase-merge",
            "rebase-apply",
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
        ):
            path = (self._git("rev-parse", "--git-path", name).stdout or "").strip()
            if path and (self.repo / path).exists():
                return True
        return False

    def rebase_blocker(self, upstream: str) -> tuple[str, list[str]]:
        """Why the local commits cannot be rebased onto `upstream` unattended ('' if they can).

        The list names the uncommitted files that conflict with the rebased commits; it is
        only filled when they are the sole reason."""
        if self.operation_in_progress():
            return "a rebase, merge or cherry-pick is in progress", []
        branch = (
            self._git("symbolic-ref", "--short", "-q", "HEAD").stdout or ""
        ).strip()
        if not branch:
            return "no branch is checked out", []
        local = (
            self._git("rev-list", "--reverse", f"{upstream}..HEAD").stdout or ""
        ).split()
        if not local:
            return "", []
        if (
            self._git("rev-list", "--merges", f"{upstream}..HEAD").stdout or ""
        ).strip():
            return "the local commits contain a merge commit", []
        remote = self._git("branch", "-r", "--contains", local[0])
        if (remote.stdout or "").strip():
            return "a local commit is already on a remote branch", []
        signing = self._git("config", "--type=bool", "--get", "commit.gpgsign")
        if (signing.stdout or "").strip() == "true":
            return "commit signing is on", []
        replay = self._git(
            "replay", "--ref-action=print", "--onto", upstream, f"{upstream}..{branch}"
        )
        if replay.returncode != 0:
            return "the local commits conflict with the incoming ones", []
        tip = ""
        for line in (replay.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "update":
                tip = parts[2]
        if not tip:
            return "the trial rebase did not finish", []
        overlap = sorted(
            set(self.local_changes())
            & set(
                (
                    self._git("diff", "--name-only", "HEAD", tip).stdout or ""
                ).splitlines()
            )
        )
        conflicts = self.trial_conflicts(tip, overlap, set()) if overlap else []
        if conflicts:
            return UNCOMMITTED_CONFLICT, conflicts
        return "", []

    def rebase_keeping_local(self, upstream: str) -> bool:
        """Rebase the local commits onto `upstream`, keeping uncommitted changes."""
        previous = self.repo_revision()
        sha = ""
        if set(self.local_changes()) - set(self.untracked_paths()):
            sha = self.stash_push("kept during the rebase")
            if not sha:
                return False
        rebased = self._git("rebase", upstream)
        if rebased.returncode != 0:
            self._git("rebase", "--abort")
            self._git("reset", "--hard", previous)
            if sha and not self.stash_apply(sha):
                warn(f"local changes kept in the stash entry {self._stash_ref(sha)}")
            return False
        if sha and not self.stash_apply(sha):
            warn(f"local changes kept in the stash entry {self._stash_ref(sha)}")
            return False
        log(f"rebased the local commits onto {upstream}")
        return True
