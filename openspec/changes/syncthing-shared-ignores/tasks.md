# Tasks

## 0. Owner confirmation

- [x] 0.1 Get the owner's answers to Open Questions 1-10 in design.md (missing include target, creating `.stglobalignore`, `.claude/worktrees`, servers, trigger, location of the rule list, content of the default ignore patterns, configuration directory order, folders of another user, existing default ignore patterns). Question 1 was tested in task 1.1. Record the answers in design.md (move them from Open Questions into Decisions, and update the Implementation outline) and add the resulting scenarios to `specs/syncthing-ignores/spec.md` before any code task.

## 1. Syncthing interface

- [x] 1.1 On a laptop with Syncthing v2.1.x, verify how the running instance reports its configuration path and how the default ignore patterns are set while it runs (REST endpoint or command-line interface), and how a changed `.stignore` is reloaded. Record the result under Assumptions in design.md (replace the assumption with the verified fact).

- [ ] 1.2 In a throwaway Syncthing instance pair (like task 1.1, localhost only), verify that `GET /rest/db/file?folder=<id>&file=.stglobalignore` has a `global` entry once a peer has the file and none while no device has it, and whether two devices that create `.stglobalignore` with identical content before they connect get a `.sync-conflict` copy. Record the result under "Verified with Syncthing v2.1.5" in design.md and adjust decision 4 if needed.

## 2. Ignore step

- [ ] 2.1 Add the shared rule list `machine/syncthing/stglobalignore` with the content in the Implementation outline of design.md (Synology folders, build and cache rules, `**/.claude/worktrees`).
- [ ] 2.2 Write `tests/unit/test_syncthing_ignores.py` with the cases listed under Testing in design.md, against a temporary `HOME` and a hand-written `config.xml`. Verify that they fail before 2.3.
- [ ] 2.3 Add `machine_cli/syncthing_ignores.py` (configuration lookup, folder list, include line, default ignore patterns) as outlined in design.md, with `.stglobalignore` created only when no known device has it and never overwritten (decision 4). Verify that `pytest tests/unit/test_syncthing_ignores.py -q` passes.
- [ ] 2.4 Wire the step `syncthing ignores` into `machine setup`/`machine apply` (`machine_cli/commands.py`) and `machine update` (`machine_cli/updates.py`), only for hosts with the feature `syncthing`. Add tests that it runs in each command, is skipped without the feature, and that its failure does not fail the other steps.
- [ ] 2.5 In `ansible/group_vars/all/features.yml`, make `syncthing` optional on servers (`server: optional`) and change its help text to mention the shared ignore rules. Update the tests in `tests/unit/test_features.py` for the scenarios of `specs/feature-selection/spec.md` first and verify they fail, then verify `pytest tests/unit/test_features.py -q` passes.

## 3. Documentation

- [ ] 3.1 Add a Syncthing paragraph to `docs/features.md`: `.stglobalignore`, the `#include` line, how to add an exception, that the dotfiles create `.stglobalignore` only where no device has one and never overwrite it, the rules to add by hand to the existing `.stglobalignore` of "ALL Documents" (Synology folders, `**/.claude/worktrees`), and the one-time manual setup for hosts without the dotfiles (NAS, phone, Raspberry Pi, family laptops). Add the module to the table in `docs/architecture.md`.

## 4. Validation

- [ ] 4.1 Run `pytest tests/unit/test_syncthing_ignores.py tests/unit/test_features.py tests/unit/test_machine_cli.py tests/unit/test_update_and_env.py -q`; they cover the new module, the feature table and the setup, apply and update flows that run the step. Because the step list of `setup` and `update` changes, also run `pytest tests/unit -q`. Record the results here.
- [ ] 4.2 Run `pre-commit run --files <changed paths>` (including the new module, the tests, the rule list, the docs and `openspec/changes/syncthing-shared-ignores/**`) and record the result.
- [ ] 4.3 Run `openspec validate syncthing-shared-ignores --strict` and record the result.
- [ ] 4.4 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change adds a step to the `machine` setup and update flow; fix findings before archive.

## Workflow follow-up

- After merging, on ThinkPad-L13-Yoga-Gen-2: run `machine update`, add the Synology rules and `**/.claude/worktrees` by hand to the `.stglobalignore` of "ALL Documents", check that its `.stignore` starts with `#include .stglobalignore` and keeps its local lines, that "ALL Photos" and "Photo Sync Ditschi" got a `.stglobalignore` (or are reported as waiting) without a folder error, that the default ignore patterns hold the shared rules followed by `__*`, that the folder shows no error in the Syncthing GUI, and that a fresh `target/` under `DIY/sbx` is not synced. This needs the merged code on the host, so it cannot be done before archiving.
