# Tasks

## 1. Canonical wrapper entry in PATH

- [x] 1.1 In `home/core/.shell/common/environment.sh`, replace each existing `PATH` entry ending in `/github.copilot-chat/copilotCli` with its canonical path (`cd -P`), keeping order, empty entries and all other entries; leave no helper variables behind. Verify `shellcheck` passes via pre-commit.
- [x] 1.2 Add a unit test (e.g. `tests/unit/test_vscode_terminal_path.py`) that builds a fake home symlink `home -> real/home` with a fake `copilotCli/copilot` wrapper (a script that only fails the test, never run) and a fake real `copilot` later in `PATH`, sources `environment.sh` in Bash and in zsh (skip zsh if absent), and asserts: the entry is canonical and at the same position; other entries under the symlink are unchanged; a second load is a no-op; a missing wrapper dir is untouched; and after applying the shim's literal filter (`replaceAll("<dirname>:", "")`, `replaceAll(":<dirname>", "")` with the canonical dirname) `command -v copilot` resolves to the fake real CLI. Verify with `pytest tests/unit/test_vscode_terminal_path.py -q`.
- [x] 1.3 Document the behaviour in the shell section of `Readme.md` (one short paragraph) and verify the link/paths are correct.

## 2. Aliased-home note in machine status

- [x] 2.1 In `machine_cli/commands.py` `cmd_status`, append a dim note `· home is <canonical>` to the host row when `$HOME` differs from its resolved path. Verify with a test in `tests/unit/test_update_and_env.py` that patches `HOME` to a symlink and checks the note appears, and that it is absent for a canonical home.

## 3. Upstream report

- [ ] 3.1 Draft the issue text for `microsoft/vscode-copilot-chat` (symptom, shim version 0.0.394, the literal `replaceAll` filter vs canonical `__dirname`, reproduction without running copilot, suggested fix: compare `realpath` of each `PATH` entry and add a recursion guard env marker), show it to the owner, and file it only after approval. Verify by recording the issue URL in this task. Skipped by the owner at archive time; not filed.

## 4. Validation

- [x] 4.1 Run `pre-commit run --all-files` and `pytest tests/unit -q`; both pass.
- [x] 4.2 On ABTVL421 after `machine update`, in a new VS Code terminal, check without running copilot: `echo "$PATH" | tr : '\n' | grep copilotCli` shows the `/mnt/data/...` path, and `machine status` shows the home note.
