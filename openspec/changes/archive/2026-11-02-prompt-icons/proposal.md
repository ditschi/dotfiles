# Proposal

## Why

The owner wants the prompt to show at a glance which branch they are on, how the working tree differs from its upstream, whether the shell runs over SSH and which Python virtualenv is active, with one consistent meaning per colour. The `shell-prompt` spec also described the bash prompt character as purple, while it has always been blue.

## What Changes

- Git branch with a git icon in the git logo's orange; status shown as counts (changed, new, staged, conflicts, deletions), the distance to the upstream, and ✓ when in sync.
- Over SSH, `💻 ssh` appears on the second line in front of the container marker and the prompt character.
- 🐍 with the virtualenv name appears only while a virtualenv is active; no Python version.
- One meaning per colour (location, good, attention, problem, distance to origin, remote, venv, background).
- Spec fix: the bash prompt character is blue, orange after a failed command; zsh's is red after a failed command.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shell-prompt`: the segment list, the shell indicator colours, and new requirements for the SSH marker, the git status counts and the Python virtualenv segment.

## Impact

- `home/prompt/.config/starship.toml`, `tests/unit/test_starship_prompt.py`.
- All hosts with the `prompt` dotfile group (every context and device).
- Icons come from the Nerd Font already set for the terminals ("FiraCode Nerd Font Mono"); the markers are colour emoji.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/prompt-icons` on branch `prompt-icons`, because the Starship configuration is read by the host's shells directly from the live checkout.
