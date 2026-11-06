# editor-command Specification

## Purpose
Lets the owner open the place a coding agent is working in, the repository or worktree, in the preferred editor for that repository, optionally together with the files the conversation is about, through one `/editor` command in Claude Code, GitHub Copilot and opencode.

## Requirements

### Requirement: Open the work root in the preferred editor
`open-in-editor` SHALL open the work root in the preferred editor and return without waiting for the editor to close. The work root SHALL be the top level of the Git worktree containing the current directory, or the current directory when it is not inside a Git worktree.

#### Scenario: Inside a linked worktree
- **WHEN** `open-in-editor` runs in a subdirectory of the worktree `.worktrees/x` of a repository
- **THEN** the editor is started with the top level of `.worktrees/x`, not the main checkout

#### Scenario: Outside Git
- **WHEN** `open-in-editor` runs in a directory that is not inside a Git worktree
- **THEN** the editor is started with that directory

#### Scenario: Editor keeps running
- **WHEN** the editor process is still running after the start
- **THEN** `open-in-editor` has already returned with exit status 0

### Requirement: Preferred editor from the Git configuration
The preferred editor SHALL be the command in the Git configuration key `editor.open` as Git resolves it for the work root, so a repository value wins over the global one. When the key is unset, the editor SHALL be `code`. The value SHALL be a command name, optionally followed by arguments.

#### Scenario: Repository value
- **WHEN** the repository sets `editor.open` to `cursor` and the global configuration sets `code`
- **THEN** `cursor` is started

#### Scenario: Nothing set
- **WHEN** `editor.open` is set nowhere
- **THEN** `code` is started

#### Scenario: Value with an argument
- **WHEN** `editor.open` is `code --new-window`
- **THEN** `code` is started with `--new-window` before the work root

### Requirement: Missing editor is reported
When the preferred editor command is not found, `open-in-editor` SHALL exit with a non-zero status and a message that names the command and the key `editor.open`, and SHALL NOT start another editor.

#### Scenario: Configured editor not installed
- **WHEN** `editor.open` is `zed` and no `zed` is on `PATH`
- **THEN** the exit status is non-zero, the message names `zed` and `editor.open`, and no editor is started

### Requirement: Open given files with the work root
Files passed to `open-in-editor` SHALL be opened in the same editor window as the work root. Relative paths SHALL be resolved against the current directory. A path that does not exist SHALL be reported and left out, and the work root and the other files SHALL still be opened.

#### Scenario: Two files
- **WHEN** `open-in-editor docs/a.md b.txt` runs and both exist
- **THEN** the editor is started with the work root, then both files as absolute paths

#### Scenario: Missing file
- **WHEN** one of the given files does not exist
- **THEN** a message names it, the work root and the existing files are opened, and the exit status is non-zero

### Requirement: Open the planning files of an OpenSpec change
`open-in-editor --change [NAME]` SHALL open the work root with the files `proposal.md`, `design.md` and `tasks.md` that exist in `openspec/changes/<change>/` of the work root, in that order, followed by the change's delta specs `specs/**/spec.md` sorted by path.

#### Scenario: Named change
- **WHEN** `open-in-editor --change foo` runs and the change `foo` has a proposal, tasks, the delta specs `specs/b/spec.md` and `specs/a/spec.md`, and no design
- **THEN** the work root, `proposal.md`, `tasks.md`, `specs/a/spec.md` and `specs/b/spec.md` of `foo` are opened in that order

#### Scenario: Unknown change
- **WHEN** the named change does not exist under `openspec/changes/`
- **THEN** nothing is opened, the exit status is non-zero and the active changes are listed

### Requirement: Find the current OpenSpec change
Without a name, `--change` SHALL choose the change named like the current Git branch, otherwise the only active change. Archived changes SHALL NOT count. When neither applies, nothing SHALL be opened, the active changes SHALL be listed one per line and the exit status SHALL be 2.

#### Scenario: Branch names the change
- **WHEN** the branch is `editor-command` and `openspec/changes/editor-command/` exists among other active changes
- **THEN** the files of `editor-command` are opened

#### Scenario: Several changes, none matches the branch
- **WHEN** the branch is `main` and two changes are active
- **THEN** both names are printed, nothing is opened and the exit status is 2

### Requirement: The /editor command in the agents
Claude Code, Copilot CLI, VS Code Copilot Chat and opencode SHALL offer a user-invoked command `/editor` that runs `open-in-editor` in the agent's current directory. The command SHALL only open files and SHALL NOT change any file. Its instructions SHALL be kept in one place in the repository.

#### Scenario: No argument
- **WHEN** the user runs `/editor` in an agent session working in a worktree
- **THEN** the worktree's root opens in the preferred editor

#### Scenario: Agent does not invoke it on its own
- **WHEN** the conversation mentions opening a file but the user does not run `/editor`
- **THEN** the agent does not run the command by itself

### Requirement: /editor resolves a hint to files
For `/editor <hint>` the agent SHALL pick the files the user most probably means, from the hint, the files named in the conversation and a search in the work root. It SHALL ask the user, with numbered options, when several files fit equally well or none fits, and SHALL then open the work root with the chosen files.

#### Scenario: Unique match
- **WHEN** the user runs `/editor editor.md` and one file named `editor.md` exists in the work root
- **THEN** the work root opens with that file

#### Scenario: Ambiguous hint
- **WHEN** the hint fits `docs/tools.md` and `home/core/tools.md` equally well
- **THEN** the agent lists both as numbered options and opens only the file the user picks

### Requirement: /editor change opens the change files
`/editor change [NAME]` SHALL open the planning files of the named or current OpenSpec change. When the current change cannot be found, the agent SHALL offer the listed active changes as numbered options and open the one the user picks.

#### Scenario: Current change found
- **WHEN** the user runs `/editor change` in the worktree of the change `foo`
- **THEN** the work root opens with `proposal.md`, `design.md`, `tasks.md` and the delta specs of `foo`

#### Scenario: Current change not found
- **WHEN** the user runs `/editor change` on `main` with two active changes
- **THEN** the agent asks which of the two to open
