# Tasks

## 0. Owner confirmation

- [ ] 0.1 Get the owner's answers to Open Questions 1-9 in design.md (missing include target, creating `.stglobalignore`, `.claude/worktrees`, servers, trigger, location of the rule list, content of the default ignore patterns, configuration directory order, folders of another user). Test question 1 on a scratch folder with Syncthing v2.1.x. Record the answers in design.md (move them from Open Questions into Decisions, and update the Implementation outline) and add the resulting scenarios to `specs/syncthing-ignores/spec.md` before any code task.

## 1. Syncthing interface

- [ ] 1.1 On a laptop with Syncthing v2.1.x, verify how the running instance reports its configuration path and how the default ignore patterns are set while it runs (REST endpoint or command-line interface), and how a changed `.stignore` is reloaded. Record the result under Assumptions in design.md (replace the assumption with the verified fact).

## 2. Ignore step

- [ ] 2.1 Add the shared rule list to the repository at the place chosen in task 0 (for example `machine/syncthing/stglobalignore`), with the rules of the initial content in design.md.
- [ ] 2.2 Write `tests/unit/test_syncthing_ignores.py` with the cases listed under Testing in design.md, against a temporary `HOME` and a hand-written `config.xml`. Verify that they fail before 2.3.
- [ ] 2.3 Add `machine_cli/syncthing_ignores.py` (configuration lookup, folder list, include line, default ignore patterns) as outlined in design.md, without any code path that writes `.stglobalignore` (unless task 0 decides otherwise). Verify that `pytest tests/unit/test_syncthing_ignores.py -q` passes.
- [ ] 2.4 Wire the step `syncthing ignores` into `machine setup`/`machine apply` (`machine_cli/commands.py`) and `machine update` (`machine_cli/updates.py`), or into the trigger chosen in task 0, only for hosts with the feature `syncthing`. Add tests that it runs in each command, is skipped without the feature, and that its failure does not fail the other steps.
- [ ] 2.5 Change the help text of `syncthing` in `ansible/group_vars/all/features.yml` to mention the shared ignore rules; verify `pytest tests/unit/test_features.py -q`.

## 3. Documentation

- [ ] 3.1 Add a Syncthing paragraph to `docs/features.md`: `.stglobalignore`, the `#include` line, how to add an exception, that the dotfiles never write `.stglobalignore`, and the one-time manual setup for hosts without the dotfiles (NAS, phone, Raspberry Pi, family laptops). Add the module to the table in `docs/architecture.md`.

## 4. Validation

- [ ] 4.1 Run `pytest tests/unit/test_syncthing_ignores.py tests/unit/test_features.py tests/unit/test_machine_cli.py tests/unit/test_update_and_env.py -q`; they cover the new module, the feature table and the setup, apply and update flows that run the step. Because the step list of `setup` and `update` changes, also run `pytest tests/unit -q`. Record the results here.
- [ ] 4.2 Run `pre-commit run --files <changed paths>` (including the new module, the tests, the rule list, the docs and `openspec/changes/syncthing-shared-ignores/**`) and record the result.
- [ ] 4.3 Run `openspec validate syncthing-shared-ignores --strict` and record the result.
- [ ] 4.4 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change adds a step to the `machine` setup and update flow; fix findings before archive.

## Workflow follow-up

- After merging, on ThinkPad-L13-Yoga-Gen-2: run `machine update`, check that the `.stignore` of "ALL Documents" starts with `#include .stglobalignore` and keeps its local lines, that the folder shows no error in the Syncthing GUI, and that a fresh `target/` under `DIY/sbx` is not synced. This needs the merged code on the host, so it cannot be done before archiving.
