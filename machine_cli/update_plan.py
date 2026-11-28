"""`machine update`: the plan of incoming changes (state, steps, conflicts, blockers)."""

# aihealth: disable=primitive_obsession -- the plan is JSON dicts, refs are git strings; plan model later
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, NamedTuple

from . import system
from .core import parse_profile_file, parse_profile_text, warn
from .local_changes import classify_paths
from .profile import host_config_changes
from .system_relevance import (
    FEATURE_TABLE_PATH,
    ansible_view_of_feature_table,
    relevant_system_paths,
)


class UpstreamRelation(NamedTuple):
    """How HEAD and upstream relate, and what that means for the update."""

    state: str
    incoming: list[tuple[str, str]]
    rebase_blocker: str
    rebase_conflicts: list[str]


class LocalSide(NamedTuple):
    """Local changes: taken out automatically, kept, and touched upstream too."""

    resolvable: list[str]
    remaining: list[str]
    overlap: list[str]


class UpdatePlanMixin:
    def local_changes(self) -> list[str]:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "status",
                "--porcelain",
                "-z",
                "--untracked-files=all",
            ],
            capture=True,
            check=False,
        )
        paths: list[str] = []
        entries = (result.stdout or "").split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if len(entry) < 4:
                continue
            paths.append(entry[3:])
            if entry[0] in "RC":  # the next entry is the original path
                if index < len(entries) and entries[index]:
                    paths.append(entries[index])
                index += 1
        return paths

    def upstream_ref(self) -> str:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ],
            capture=True,
            check=False,
        )
        tracked = (result.stdout or "").strip()
        if result.returncode == 0 and tracked:
            return tracked
        branch = system.run(
            ["git", "-C", str(self.repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture=True,
            check=False,
        )
        return f"origin/{(branch.stdout or '').strip()}"

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return (
            system.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "merge-base",
                    "--is-ancestor",
                    ancestor,
                    descendant,
                ],
                check=False,
                capture=True,
            ).returncode
            == 0
        )

    def incoming_changes(
        self, upstream: str, base: str = "HEAD"
    ) -> list[tuple[str, str]]:
        result = system.run(
            [
                "git",
                "-C",
                str(self.repo),
                "diff",
                "--name-status",
                "--no-renames",
                "-z",
                base,
                upstream,
            ],
            capture=True,
            check=False,
        )
        parts = [part for part in (result.stdout or "").split("\0") if part]
        return list(zip(parts[0::2], parts[1::2]))

    def record_update_check(self) -> None:
        """The time of the last successful fetch, shown by `machine status`."""
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            self.update_last_check.write_text(stamp + "\n", encoding="utf-8")
        except OSError:
            pass  # best effort, like the timer script

    def system_paths_relevant(
        self, paths: Iterable[str], old: str = "", new: str = ""
    ) -> list[str]:
        """Changed paths that apply to this host's Ansible run.

        With the revisions `old` and `new`, a feature table whose change touches
        only keys the CLI reads (help, groups) does not count."""
        if not self.saved_ansible():
            return []
        known = self.applied_host_path.is_file()
        relevant = self._relevant_system_paths(paths, known)
        if self._feature_table_change_is_cli_only(relevant, old, new):
            relevant.remove(FEATURE_TABLE_PATH)
        return relevant

    def _feature_table_change_is_cli_only(
        self, relevant: list[str], old: str, new: str
    ) -> bool:
        """True when the feature table changed between `old` and `new` only in keys
        that Ansible does not read."""
        if FEATURE_TABLE_PATH not in relevant:
            return False
        if not (old and new):
            return False
        before, after = (
            self._git("show", f"{rev}:{FEATURE_TABLE_PATH}") for rev in (old, new)
        )
        if before.returncode != 0 or after.returncode != 0:
            return False
        return ansible_view_of_feature_table(
            before.stdout
        ) == ansible_view_of_feature_table(after.stdout)

    def _relevant_system_paths(self, paths: Iterable[str], known: bool) -> list[str]:
        return relevant_system_paths(
            paths,
            ansible_dir=self.ansible_dir,
            features=self.saved_features() if known else [],
            context=self.current_context() if known else "",
            device=self.current_device() if known else "",
            own_host_config=self.host_config_path().relative_to(self.repo).as_posix(),
        )

    def pending_system_paths(self, ref: str) -> list[str]:
        """Changed files between the last successful Ansible run and `ref` that apply here.

        Empty for a host that never ran Ansible (no root, or a container)."""
        applied = self.read_update_state()["ansible_applied_rev"]
        if not applied:
            return []
        result = self._git("diff", "--name-only", "--no-renames", applied, ref)
        if result.returncode != 0:
            return ["ansible/"]  # unknown revision: cannot evaluate, so it counts
        return self.system_paths_relevant(
            (result.stdout or "").splitlines(), applied, ref
        )

    def plan_steps(self, incoming: list[tuple[str, str]], ref: str) -> list[str]:
        steps = {step for step in classify_paths(incoming) if step != "system"}
        if self.pending_system_paths(ref):
            steps.add("system")
        return sorted(steps)

    # --- the plan ---------------------------------------------------------

    def update_plan(self, *, fetch: bool) -> dict[str, Any]:
        if fetch:
            self._fetch_upstream()
        upstream = self.upstream_ref()
        if not self._ref_exists(upstream):
            return self._no_upstream_plan(upstream)
        relation = self._upstream_relation(upstream)
        local = self._local_side(relation.incoming)
        conflicts = self._overlap_conflicts(upstream, relation, local.overlap)
        plan = self._incoming_plan(upstream, relation, local, conflicts)
        plan["blockers"] = (
            [self.blocked_reason(plan)] if self.plan_blocked(plan) else []
        )
        return plan

    def _local_side(self, incoming: list[tuple[str, str]]) -> LocalSide:
        resolvable = [
            path for _name, path, _run, pending in self.local_resolvers() if pending()
        ]
        local = self.local_changes()
        remaining = [path for path in local if path not in resolvable]
        overlap = sorted(set(remaining) & {path for _status, path in incoming})
        return LocalSide(resolvable, remaining, overlap)

    def _incoming_plan(
        self,
        upstream: str,
        relation: UpstreamRelation,
        local: LocalSide,
        conflicts: list[str],
    ) -> dict[str, Any]:
        incoming = relation.incoming
        return {
            "upstream": upstream,
            "state": relation.state,
            "incoming_commits": self.commit_count(f"HEAD..{upstream}"),
            "local_commits": self.commit_count(f"{upstream}..HEAD"),
            "host_config_changes": self.incoming_host_config_changes(
                incoming, upstream
            ),
            "incoming": [{"status": s, "path": p} for s, p in incoming],
            "steps": self.plan_steps(incoming, upstream if incoming else "HEAD"),
            "local_changes": local.remaining,
            "resolvable": local.resolvable,
            "overlap": local.overlap,
            "merged": [path for path in local.overlap if path not in conflicts],
            "conflicts": (
                conflicts if relation.state == "behind" else relation.rebase_conflicts
            ),
            "rebase_blocker": relation.rebase_blocker,
        }

    def _fetch_upstream(self) -> None:
        result = system.run(
            ["git", "-C", str(self.repo), "fetch", "--quiet"],
            check=False,
            capture=True,
        )
        if result.returncode != 0:
            warn("git fetch failed; using the last known upstream state")
        else:
            self.record_update_check()

    def _ref_exists(self, ref: str) -> bool:
        return (
            system.run(
                ["git", "-C", str(self.repo), "rev-parse", "--verify", ref],
                check=False,
                capture=True,
            ).returncode
            == 0
        )

    def _no_upstream_plan(self, upstream: str) -> dict[str, Any]:
        return {
            "upstream": upstream,
            "state": "no-upstream",
            "incoming": [],
            "steps": [],
            "local_changes": self.local_changes(),
            "resolvable": [],
            "overlap": [],
            "merged": [],
            "conflicts": [],
            "rebase_blocker": "",
            "incoming_commits": 0,
            "local_commits": 0,
            "host_config_changes": [],
            "blockers": [f"upstream {upstream} not found"],
        }

    def _upstream_relation(self, upstream: str) -> UpstreamRelation:
        if self._is_ancestor("HEAD", upstream):
            incoming = self.incoming_changes(upstream)
            state = "behind" if incoming else "up-to-date"
            return UpstreamRelation(state, incoming, "", [])
        if self._is_ancestor(upstream, "HEAD"):
            return UpstreamRelation("up-to-date", [], "", [])
        base = (self._git("merge-base", "HEAD", upstream).stdout or "").strip()
        incoming = self.incoming_changes(upstream, base) if base else []
        rebase_blocker, rebase_conflicts = self.rebase_blocker(upstream)
        return UpstreamRelation("diverged", incoming, rebase_blocker, rebase_conflicts)

    def _overlap_conflicts(
        self, upstream: str, relation: UpstreamRelation, overlap: list[str]
    ) -> list[str]:
        """The overlapping local changes that do not merge with the incoming ones."""
        if not overlap or relation.state != "behind":
            return overlap
        added = {path for status, path in relation.incoming if status == "A"}
        return self.trial_conflicts(upstream, overlap, added)

    @staticmethod
    def plan_blocked(plan: dict[str, Any]) -> bool:
        if plan["state"] == "diverged":
            return bool(plan["rebase_blocker"])
        return bool(plan["conflicts"])

    @staticmethod
    def blocked_reason(plan: dict[str, Any]) -> str:
        """The needs-attention reason: what blocks, how much is waiting, what to run next."""
        incoming = plan.get("incoming_commits", 0)
        commits = f"{incoming} incoming commit{'s' if incoming != 1 else ''}"
        if plan["state"] == "diverged":
            return UpdatePlanMixin._diverged_reason(plan, commits)
        if plan["state"] == "no-upstream":
            return f"upstream {plan['upstream']} not found"
        return (
            f"{commits} conflict with local changes in "
            + ", ".join(plan["conflicts"])
            + " → resolve them, then run: machine"
        )

    @staticmethod
    def _diverged_reason(plan: dict[str, Any], commits: str) -> str:
        local = plan.get("local_commits", 0)
        if not plan["rebase_blocker"]:
            return (
                f"history diverged: {local} local and {commits}; "
                "they rebase cleanly → run: machine update"
            )
        if plan["conflicts"]:
            return (
                f"history diverged: {local} local and {commits}; uncommitted "
                f"changes in {', '.join(plan['conflicts'])} conflict with the "
                "incoming ones → commit, stash or discard them, then run: "
                "machine update"
            )
        return (
            f"history diverged: {local} local and {commits} "
            f"({plan['rebase_blocker']}) → run: git pull --rebase, then machine"
        )

    def incoming_host_config_changes(
        self, incoming: list[tuple[str, str]], upstream: str
    ) -> list[str]:
        """What an incoming commit changes in this host's machine/hosts file."""
        try:
            rel = str(self.host_config_path().relative_to(self.repo))
        except ValueError:  # host files outside this checkout
            return []
        if rel not in {path for _status, path in incoming}:
            return []
        shown = system.run(
            ["git", "-C", str(self.repo), "show", f"{upstream}:{rel}"],
            check=False,
            capture=True,
        )
        new_text = shown.stdout if shown.returncode == 0 else ""
        return host_config_changes(
            parse_profile_file(self.applied_host_path), parse_profile_text(new_text)
        )

    def print_update_plan(self, plan: dict[str, Any]) -> None:
        print(f"upstream: {plan['upstream']} ({plan['state']})")
        print(f"incoming files: {len(plan['incoming'])}")
        print("steps: " + (", ".join(plan["steps"]) or "none"))
        optional = (
            ("host_config_changes", "host config changes: ", "; "),
            ("resolvable", "resolved automatically: ", ", "),
            ("merged", "merge cleanly (kept): ", ", "),
            ("conflicts", "conflict: ", ", "),
            ("local_changes", "local changes (kept): ", ", "),
        )
        for key, label, separator in optional:
            if plan.get(key):
                print(label + separator.join(plan[key]))
        for blocker in plan["blockers"]:
            print(f"needs attention: {blocker}")
        if not plan["blockers"]:
            print("blockers: none")
