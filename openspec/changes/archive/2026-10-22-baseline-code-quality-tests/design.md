# Design

## Context

This change writes the confirmed quality and test setup down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `.pre-commit-config.yaml`, `noxfile.py`, `tests/`, `.github/workflows/verify.yml`, `.ansible-lint` and `.yamlfmt`.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep open and planned points visible as investigations.

**Non-Goals:**
- Fixes or improvements.

## Decisions

1. **Checks on commit, tests in CI.** Fast checks run locally; slow Docker and APT tests run in CI.
2. **`.bashrc` is not formatted.** Blocks added by the work Ansible setup would be re-added after formatting.
3. **No co-author trailers.** They add noise; all commits are AI-assisted.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Format `.bashrc` except externally managed blocks.** Possible improvement from the owner. Suggestion: find out how the Ansible blocks are marked, then format everything outside the markers, for example by splitting the file or by a wrapper hook. Why: `.bashrc` is then formatted like the other shell files without Ansible re-adding blocks.
2. **Remove the commented-out `protect-files` hook.** The owner wants it removed. Suggestion: check once that nothing references it (workflows, docs, tooling), then delete the commented lines. Why: dead configuration hides what is really checked.
3. **Checks required before a commit.** Not decided: unit tests only, or also Docker smoke and APT or Ansible tests. Suggestion: measure how long each suite takes and which failures each catches, then pick a default. Why: required checks should be fast enough that nobody skips them.
