# Tasks

## 1. Enforce SSH config permissions during dotfile apply

- [x] 1.1 In the existing non-live `/home/dci2lr/dotfiles-openspec` worktree, add regression coverage to `tests/unit/test_dotfiles.py` for a selected `.ssh/config` source at mode `0664`, then enforce mode `0600` on its resolved target after successful `mise dot apply` in `machine_cli/dotfiles.py`. Verify with `pytest tests/unit/test_dotfiles.py -q` that contents and the home-directory symlink are preserved, across work/private/container selections and repeated apply, including permissions becoming unsafe again between applies.
- [x] 1.2 Keep permission repair limited to the selected checkout's installed SSH config; cover missing configs, foreign symlinks, host-local files, checkout aliases and a permission failure without changing ownership, keys, unrelated files or the global umask. Verify those cases in `tests/unit/test_dotfiles.py`, including that a repair error cannot silently succeed.
- [x] 1.3 Add a concise note to the existing dotfile documentation in `Readme.md` describing automatic SSH config permission repair and the unchanged symlink model. Verify the wording matches the delta spec; no new CLI command or dependency is introduced.

## 2. Verify apply consumers and repository checks

- [x] 2.1 Run `pytest tests/unit/test_dotfiles.py tests/unit/test_update_and_env.py tests/unit/test_gitconfig.py tests/unit/test_mise_tools.py -q` to cover the apply path and its existing setup/update, Git and tool consumers. Record commands, results and why this selection covers the bounded change here. If impact becomes broad or uncertain, or failures suggest wider effects, run `pytest tests/unit -q` instead of assuming focused coverage is sufficient.
- [x] 2.2 Verify an isolated config linked to a repaired target can be parsed by OpenSSH without a network connection, using a temporary test home or container that exercises the default user-config ownership check rather than bypassing it with an explicit `-F` file. Do not reapply all dotfiles to the live host for validation. Record the command and result here, or explicitly record an unavailable environment.
- [x] 2.3 Run `openspec validate secure-ssh-config-permissions --strict` and `pre-commit run --files` with every changed path, including untracked artifacts and tests. Rerun after relevant edits and record commands and results here. No Ansible validation is needed unless the implementation expands into Ansible.

## Planning Validation

- `openspec validate secure-ssh-config-permissions --strict`: passed for the proposal and spec delta before tasks were added.
- `pre-commit run --files openspec/changes/secure-ssh-config-permissions/proposal.md openspec/changes/secure-ssh-config-permissions/.openspec.yaml`: passed after the hook corrected the proposal's final newline.
- A separate `design.md` is omitted: this is a bounded change to one existing apply path with no new architecture, dependency or migration. The proposal records the implementation assumptions for review.

## Implementation Validation

- New regression before the fix: `pytest tests/unit/test_dotfiles.py -q -k repairs_ssh_config_permissions` failed in all three host selections because the source remained `0664`, confirming the missing apply-time repair.
- `pytest tests/unit/test_dotfiles.py -q`: 47 passed after implementing repair and boundary coverage. Editor diagnostics reported no errors in either changed Python file.
- `pre-commit run --files Readme.md`: passed.
- `env PATH="$(dirname "$(command -v git)"):/usr/bin:/bin:$PATH" pytest tests/unit/test_dotfiles.py tests/unit/test_update_and_env.py tests/unit/test_gitconfig.py tests/unit/test_mise_tools.py -q`: 200 passed. This selection covers the repair, its boundaries and existing setup/update, Git and tool consumers; no shared API or test configuration changed, so the full unit suite was not required.
- Environment diagnosis: the original PATH selected a mise Python shim for fixture subprocesses, causing 15 environment-related failures (185 passed). Putting all system tools first fixed those but selected an older Git, causing two Git-history failures (198 passed). Keeping the existing user-space Git first and system Python ahead of mise shims made the same 200 tests pass without changing unrelated code or tests.
- Isolated OpenSSH check: passed using `docker run --rm -i --network none --mount "type=bind,src=$PWD,dst=/repo,readonly" --mount type=bind,src=/usr/lib/python3/dist-packages,dst=/host-python,readonly --mount type=bind,src=/usr/bin/ssh,dst=/host-ssh,readonly --env PYTHONPATH=/repo:/host-python --entrypoint /usr/bin/python3 dotfiles-preset-test:local -` with a stdin fixture script. The script created a temporary checkout and config symlink in the container user's passwd home, confirmed `/host-ssh -G permission-test` rejected mode `0666`, ran the actual `run_dotfiles_apply` with only external mise calls mocked, and confirmed mode `0600`, the preserved symlink and successful default-config parsing. No `-F`, network connection or live-home apply was used. The container accepted `0664` before repair, so the negative control used world-writable permissions; unit tests independently cover `0664` repair.
- `openspec validate secure-ssh-config-permissions --strict`: passed for the implementation artifacts.
- `pre-commit run --files machine_cli/dotfiles.py tests/unit/test_dotfiles.py Readme.md openspec/changes/secure-ssh-config-permissions/.openspec.yaml openspec/changes/secure-ssh-config-permissions/proposal.md openspec/changes/secure-ssh-config-permissions/specs/repo-layout/spec.md openspec/changes/secure-ssh-config-permissions/tasks.md`: passed after Black formatted both changed Python files. `pytest tests/unit/test_dotfiles.py -q` then passed again (47 tests); all hooks passed on the rerun.
- `git diff --check`: passed. No Ansible files changed; no Ansible checks were needed. The live installation was not modified during implementation.

## Main Integration Validation

- Archived with the spec synced to `repo-layout`; the owner delegated archive choices, including proceeding without the optional design artifact.
- Integrated only this change onto current `main` in the detached worktree `/home/dci2lr/dotfiles/.worktrees/secure-ssh-config-permissions-publish`. Preserved main's updated README navigation and existing `apply_ssh_client` hook; the permission-test fixture stubs that separate hook. The live checkout's unrelated edits were left untouched.
- `env PATH="$(dirname "$(command -v git)"):/usr/bin:/bin:$PATH" /usr/bin/python3 -c 'import os; os.umask(0o022); os.execv("/usr/bin/pytest", ["pytest", "tests/unit/test_dotfiles.py", "tests/unit/test_ssh_client.py", "tests/unit/test_update_and_env.py", "tests/unit/test_gitconfig.py", "tests/unit/test_mise_tools.py", "-q"])'`: 282 passed on current main. The test process alone uses umask `022`: an existing SSH-client fixture otherwise creates a group-writable included config under this terminal's umask `002`. No production behavior or unrelated tests were changed for this environment issue.
