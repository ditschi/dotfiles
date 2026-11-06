# Proposal

## Why

The owner wants one command in the coding agents (Claude Code, GitHub Copilot and opencode) that opens the place the agent is working in, the repository or worktree, in the owner's preferred editor for that repository. VS Code is the default. Optionally, the command also opens the files the conversation is about, for example a file named in a short hint, or the planning files of the current OpenSpec change. The command should come with the dotfiles as a feature, so that every host that selects it gets it the same way, for all repositories.

## What Changes

- A new feature `editor-command` in the feature table. It is preselected on private and work desktops, optional on servers and excluded in containers. It selects a new dotfile group `editor-command`.
- The group holds a helper script `open-in-editor` in `~/.local/bin`. It opens the root of the current work (the root of the Git worktree, or the current directory outside Git) in the preferred editor, together with any files it is given. With `--change [NAME]` it opens the planning files and delta specs of an OpenSpec change.
- The preferred editor is read from the Git configuration key `editor.open`. The repository's own value wins over the user's global value (for example in `~/.gitconfig.local`), and `code` (VS Code) is used when neither is set.
- The group holds one agent command `/editor`: a skill named `editor` for Claude Code (`~/.claude/skills/editor/`), Copilot CLI and VS Code Copilot Chat (`~/.copilot/skills/editor/`), and a command for opencode (`~/.config/opencode/commands/editor.md`). The instructions are kept in one place in the repository.
  - `/editor` opens the work root.
  - `/editor <hint>`: the agent picks the file or files the user most probably means, from the hint, the conversation and a file search. It asks when unsure, then opens the work root with those files.
  - `/editor change [NAME]` opens `proposal.md`, `design.md`, `tasks.md` and the delta specs of the current or named OpenSpec change. The script finds the current change. When it cannot, the agent asks the user.
- The skill only opens files. It never edits them.
- Docs: a section in `docs/tools.md` on `/editor`, the `editor.open` key and how to pick an editor per repository.
- Unchanged: the features `claude-code`, `copilot-cli` and `opencode` and their groups, and the shell's `$EDITOR` (`nano`), which stays the terminal editor for Git and other command-line tools.

## Capabilities

### New Capabilities

- `editor-command`: the `/editor` command for Claude Code, Copilot and opencode, and the `open-in-editor` script. Covers how the work root is found, how the preferred editor is chosen, which files are opened for a hint or for an OpenSpec change, and how failures are reported.

### Modified Capabilities

- `feature-selection`: adds the values of the feature `editor-command` for each context and device, and its dotfile group.

Affected profiles: private and work desktops (preselected), servers (optional), containers (not offered).

## Where the change is made

The change is made in the worktree `$(machine repo)/.worktrees/editor-command`. It adds a dotfile group that links files into `$HOME` (`~/.local/bin`, `~/.claude/skills`, `~/.copilot/skills`, `~/.config/opencode/commands`) and changes the feature table. Both would affect the host's tools in the live checkout.

## Impact

- `ansible/group_vars/all/features.yml`: new row `editor-command`. No Ansible role or package; the editors themselves (`code`, `cursor`, ...) are installed by other means and not by this feature.
- New group `home/editor-command/` with the script, the skill and the opencode command.
- Host configs that list features explicitly (`machine/hosts/*.yml`, `tests/hosts/*.yml`) get the feature where it should apply.
- Tests: `tests/unit/test_features.py`, a new `tests/unit/test_open_in_editor.py`, and a test for the skill files of the group.
- Docs: `docs/tools.md`.
