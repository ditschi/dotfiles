# Tasks

## 1. Verify the agent integrations

- [x] 1.1 With the installed Claude Code, Copilot CLI and VS Code Copilot Chat, place a throw-away skill `editor-probe` in `~/.claude/skills/` and `~/.copilot/skills/`, and with opencode a command `~/.config/opencode/commands/editor-probe.md`, and check that each client offers it as `/editor-probe <arg>`, passes the argument, and honours or ignores `disable-model-invocation` and `allowed-tools`. Also check that `code <dir> <file>` and `cursor <dir> <file>` open the files in the folder's window. Remove the probe afterwards. Replace the matching Assumptions in design.md with the verified facts, and change the Copilot target in the Implementation outline if a client needs another place or format.
- [x] 1.2 In a scratch group in this worktree, check whether the `mise` dotfile apply (in `machine testenv`, see memory and `docs/testing.md`) links a file that is a relative symbolic link inside the repository. Record in design.md decision 4 whether the second skill target is a link or a copy.

## 2. Feature

- [x] 2.1 Add tests to `tests/unit/test_features.py` for `editor-command` (preselected on private and work desktops, optional on servers, excluded in containers, group `editor-command`; scenarios of `specs/feature-selection/spec.md`) and verify they fail.
- [x] 2.2 Add the row `editor-command` to `ansible/group_vars/all/features.yml` and the group entry to `mise.toml` as in the Implementation outline; verify `pytest tests/unit/test_features.py -q` passes.

## 3. Script `open-in-editor`

- [x] 3.1 Write `tests/unit/test_open_in_editor.py` with the cases listed under Testing in design.md; verify they fail.
- [x] 3.2 Add `home/editor-command/.local/bin/open-in-editor` (executable) as outlined in design.md; verify `pytest tests/unit/test_open_in_editor.py -q` passes and `shellcheck` reports nothing.

## 4. Skill `/editor`

- [x] 4.1 Write the test for the skill files of the group (both skill targets present with the same content, the opencode command with the same body, front matter `name: editor` and `description`, `allowed-tools` limited to `open-in-editor`, `disable-model-invocation: true`); verify it fails.
- [x] 4.2 Add `home/editor-command/.claude/skills/editor/SKILL.md` with the body outlined in design.md, the Copilot target as decided in 1.1 and 1.2, and `home/editor-command/.config/opencode/commands/editor.md`; verify the test of 4.1 passes.
- [x] 4.3 Apply the group on the owner's laptop and check by hand in Claude Code, opencode and VS Code Copilot Chat (and Copilot CLI where it is installed; note how VS Code shows the skill found in two places): `/editor`, `/editor tasks.md`, `/editor change` in this worktree, and `/editor change` in the live checkout on `main` with several active changes (the agent asks). Record the results here.
  - 2026-11-06, before deploy (skill linked in temporarily, editor a logging stub via `editor.open`): Claude Code 2.1.308 `claude -p` with `/editor`, `/editor test_open_in_editor` and `/editor change` in this worktree opened the worktree root, `tests/unit/test_open_in_editor.py`, and proposal, design, tasks and both delta specs. `open-in-editor --change` in this worktree with the real VS Code 1.145.0 (no `editor.open` set) started VS Code with the worktree and the five change files and returned with exit status 0. The checks that need the deployed group are under Workflow follow-up.

## 5. Hosts and docs

- [x] 5.1 Add `editor-command` to the host configs that should have it (desktops in `machine/hosts/`, and `tests/hosts/ci-home-laptop.yml`); verify `pytest tests/unit/test_host_profiles.py -q` passes.
- [x] 5.2 Add the section on `/editor` to `docs/tools.md` (usage, `git config editor.open <cmd>` per repository, global default, `change`), and verify the documented commands work as written.

## 6. Validation

- [x] 6.1 Run `pytest tests/unit/test_features.py tests/unit/test_open_in_editor.py tests/unit/test_dotfiles.py tests/unit/test_host_profiles.py tests/unit/test_package_presets.py -q` (and the skill test file of 4.1, if separate); they cover the feature table and the package resolution that reads it, the script, the new group and the host configs. Record the results here.
  - 2026-11-06: `pytest tests/unit/test_features.py tests/unit/test_open_in_editor.py tests/unit/test_editor_skill.py tests/unit/test_dotfiles.py tests/unit/test_host_profiles.py tests/unit/test_package_presets.py -q`: 190 passed.
- [x] 6.2 Run `pre-commit run --files <changed paths>` (feature table, group, tests, host configs, docs and `openspec/changes/editor-command/**`) and record the result.
  - 2026-11-06: `pre-commit run --files` on all 19 changed and new paths: all hooks passed (shellcheck, shfmt, check-symlinks, black, flake8, codespell, openspec-specs-strict, ...).
- [x] 6.3 Run `openspec validate editor-command --strict` and record the result.
  - 2026-11-06: `openspec validate editor-command --strict`: valid.

## Workflow follow-up

- After `machine update` deploys the group on ThinkPad-L13-Yoga-Gen-2: run `/editor change` in Claude Code in the live checkout on `main` with several active changes (the agent asks), `/editor` in VS Code Copilot Chat (note how it shows the skill found in `~/.claude/skills` and `~/.copilot/skills`), and `/editor tasks.md` in opencode once its model provider works.
- On the first host with `copilot-cli`: `/editor` in Copilot CLI.
