# Proposal

## Why

Typing the beginning of a command and then pasting the whole command can duplicate its leading words. After the original command fails, the owner wants the duplicate removed in an editable suggestion at the prompt, requiring confirmation before execution.

## What Changes

- Run the submitted command unchanged first; never deduplicate a successful command.
- After failure, detect adjacent repeated leading words, such as `git git status` or `git remote git remote -v`.
- Put the cleaned command into the next editable command line without executing it.
- Keep the existing pasted prompt-character and sudo helpers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `zsh-plugins`: add failed-command duplicate-prefix suggestions to interactive zsh.
- `bash-shared-config`: provide the same confirmation-based helper in interactive bash.

## Impact

Shell configuration under `home/core/.zsh/config/` and `home/core/.bashrc`, shell tests, and the shell section of `Readme.md`. Applies to work and private profiles on desktops, servers and containers using interactive shells. No Ansible, machine CLI, new package, or non-interactive shell behavior changes are planned.

## Assumptions

- Apply the helper to both shells, matching the existing paste helpers.
- Initially support simple, single-line commands with unquoted literal words; leave complex shell syntax untouched.
- Match adjacent complete words at the beginning only, choose the longest matching prefix, and remove one copy per failed submission.
- Preserve the original exit status, output and history entry; only an explicitly submitted suggestion becomes another command.
- Discard suggestions when another command is submitted, and do not overwrite existing or queued input.
