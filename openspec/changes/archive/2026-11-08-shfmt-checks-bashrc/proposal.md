## Why

`shfmt` skips `home/core/.bashrc` because the work Ansible setup adds blocks to `~/.bashrc` that are formatted differently; formatting them would make Ansible add them again. Since `restructure-shell-config`, `.bashrc` is a short stub, and `machine update` moves text added by other tools into `~/.bashrc-local`. The owner asked to drop the exclusion, provided that formatting never touches a block that has not been moved yet.

## What Changes

- `shfmt` checks `home/core/.bashrc` with `--diff` instead of skipping it: a formatting difference fails the hook, but the file is never rewritten. Other shell files are still formatted in place.
- A new local hook `bashrc-no-managed-blocks` rejects a `.bashrc` that contains an externally managed block (`# BEGIN ... MANAGED BLOCK`), so such a block is moved to `~/.bashrc-local` (`machine update`) before it can be committed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pre-commit-checks`: "shfmt skips .bashrc" becomes "shfmt checks .bashrc without rewriting it"; "Pre-commit hooks" lists the new hook.

## Impact

- `.pre-commit-config.yaml` only. No change to `machine` or the shell files.
- Where the change is made: worktree `.worktrees/remove-edit-aliases`, together with removing the edit aliases (owner decision in the baseline `baseline-shell-setup`, investigation 3), because both touch files the host's shell loads or checks.
