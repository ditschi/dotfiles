# Proposal

## Why

On the owner's work host, interactive bash shows the plain Debian prompt instead of Starship. `~/.bashrc-local`, which `~/.bashrc` sources last, holds an externally managed block that assigns `PROMPT_COMMAND`. That assignment replaces the Starship hook, so the prompt, the update and disk segments and the prompt-character state are all lost. The tests did not notice, because they only run in clean containers and use a harmless local file.

## What Changes

- After `~/.bashrc-local` has been sourced, bash re-establishes the Starship prompt hook when the local file removed it. Whatever the local file put into `PROMPT_COMMAND` keeps running.
- `~/.bashrc-local` stays the last file sourced; the requirement "Local bash extension point" is unchanged.
- Tests cover a local file that replaces `PROMPT_COMMAND` and `PS1`, both in the unit tests and in the container profile test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shell-prompt`: a new requirement that the Starship prompt in bash survives a host-local file that replaces the prompt variables.

## Impact

- Profiles: all hosts with bash and Starship; observable today on the work host with the Ansible "update colors" block.
- Code: [home/core/.bashrc](home/core/.bashrc) and [home/core/.shell/bash/prompt.bash](home/core/.shell/bash/prompt.bash).
- Tests: `tests/unit/test_zsh_handoff.py`, `tests/integration/test_profile_containers.py`.
- Docs: [docs/shell.md](docs/shell.md) mentions the host-only extension point.
- Made in the worktree `.worktrees/bash-prompt-survives-local`, because it changes the host's bash startup.
