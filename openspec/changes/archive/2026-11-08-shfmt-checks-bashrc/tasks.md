# Tasks

Work only in the worktree `.worktrees/remove-edit-aliases`.

## 1. Hooks

- [x] 1.1 In `.pre-commit-config.yaml`, exclude only `home/core/.bashrc` (anchored) from the formatting `shfmt` hook, add a `shfmt` hook for `home/core/.bashrc` with `--diff` and no `--write`, and add the local `pygrep` hook `bashrc-no-managed-blocks`.

## 2. Edit aliases

- [x] 2.1 Remove the edit aliases (`zshalias`, `zshconfig`, `zshenv`, `zshplugins`, `zshtheme`, `zshheys`, `zshhistory`, `zshwork`, `zshwork-ldap`, `zshwork-tools`) and the duplicated header in `home/work/.shell/work/common/tools.sh`.

## 3. Validation

- [x] 3.1 Run `pre-commit run --files <changed paths>` and check that the new hooks fail on a `.bashrc` with a managed block and on an unformatted `.bashrc` without changing the file; record the result.
  - Result: all hooks passed on the changed files and `home/core/.bashrc`. With an appended `# BEGIN ANSIBLE MANAGED BLOCK` block indented by 2 spaces, `shfmt (.bashrc, check only)` failed with the diff and `bashrc-no-managed-blocks` failed at line 15; the file was byte-identical afterwards.
- [x] 3.2 Run `pytest tests/unit/test_zsh_handoff.py tests/unit/test_dotfiles.py -q`, because the alias lines are removed from files the shell loads and the zsh check starts them; record the result.
  - Result: 110 passed.
- [x] 3.3 Run `openspec validate shfmt-checks-bashrc --strict`; record the result.
  - Result: valid (after keeping the scenario "Formatting shell files").
