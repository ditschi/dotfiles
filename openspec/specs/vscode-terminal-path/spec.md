# vscode-terminal-path Specification

## Purpose
Keeps `PATH` entries that VS Code injects into terminals working on hosts whose home directory is reachable by more than one path, and makes such hosts visible in `machine status`.

## Requirements

### Requirement: Canonical Copilot CLI wrapper directory in PATH
When the shared shell environment is loaded, every `PATH` entry that ends in `/github.copilot-chat/copilotCli` and is an existing directory SHALL be replaced by its canonical path (all symlinks resolved). The position of the entry and all other `PATH` entries SHALL stay unchanged. Loading the environment again SHALL NOT change `PATH` further.

#### Scenario: Wrapper directory reached through a symlinked home
- **WHEN** `PATH` contains `/home/u/.vscode-server/data/User/globalStorage/github.copilot-chat/copilotCli` and `/home/u` is a symlink to `/mnt/data/home/u`
- **THEN** after loading the environment that entry reads `/mnt/data/home/u/.vscode-server/data/User/globalStorage/github.copilot-chat/copilotCli` at the same position

#### Scenario: Wrapper directory already canonical
- **WHEN** the wrapper directory entry has no symlink in its path
- **THEN** `PATH` is unchanged

#### Scenario: Other entries
- **WHEN** `PATH` contains other entries below a symlinked home, or a wrapper entry that does not exist
- **THEN** those entries are left as they are

#### Scenario: Bash and zsh
- **WHEN** the environment is loaded by Bash or by zsh
- **THEN** the result is the same

### Requirement: Report an aliased home in machine status
`machine status` SHALL add an informational note to the host row when `$HOME` differs from its canonical path, naming the canonical path. It SHALL NOT create an attention item or change the exit code.

#### Scenario: Symlinked home
- **WHEN** `$HOME` is `/home/u` and resolves to `/mnt/data/home/u`
- **THEN** the host row shows a note naming `/mnt/data/home/u`

#### Scenario: Canonical home
- **WHEN** `$HOME` equals its canonical path
- **THEN** the host row shows no such note
