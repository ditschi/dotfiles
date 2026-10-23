# zsh-plugins Specification

## Purpose
Defines how zsh plugins and helper programs are managed with antidote, so that the prompt appears before the plugins load, the plugin set is installed without manual steps and the list stays easy to edit.

## Requirements

### Requirement: Configured plugin set
zsh SHALL load these plugins from the plugin list:
- zsh-completions
- LS_COLORS
- fzf-tab
- zsh-history-substring-search
- zsh-autosuggestions
- fast-syntax-highlighting

It SHALL also provide the commands git-open, git-recent and git-recall from their plugin checkouts. Directory jumping (`z`) SHALL come from zoxide when it is installed. zsh-z, z.lua, undollar, zsh-sudo and zsh-syntax-highlighting SHALL NOT be loaded.

#### Scenario: Plugins active after loading
- **WHEN** the deferred part of an interactive zsh has finished
- **THEN** autosuggestions, syntax highlighting, substring history search on Up/Down and fzf-tab completion are active

#### Scenario: Git helper commands
- **WHEN** the user runs `git open`, `git recent` or `git recall`
- **THEN** the command is found

#### Scenario: zoxide available
- **WHEN** zoxide is installed
- **THEN** `z <dir>` jumps to a matching directory, in zsh and in bash

#### Scenario: Lua available
- **WHEN** lua or luajit is installed
- **THEN** z.lua is still not loaded, and `z` comes from zoxide only

#### Scenario: Lua not available
- **WHEN** neither lua nor luajit is installed
- **THEN** startup continues without error, and `z` is available when zoxide is installed

### Requirement: antidote is the plugin manager
zsh plugins SHALL be managed by antidote with zsh-defer. On the first interactive start, antidote installs itself and the listed plugins into the user's data and cache directories, without root. Later starts SHALL load the generated plugin file and SHALL NOT fetch anything. The plugin list is one file in the repository, with one line per plugin.

#### Scenario: Fresh host
- **WHEN** the first interactive zsh starts and antidote is not installed
- **THEN** antidote and the listed plugins are cloned and loaded in the same start

#### Scenario: Established host
- **WHEN** an interactive zsh starts, antidote is installed, and the plugin list is unchanged
- **THEN** the generated plugin file is loaded without network access

#### Scenario: Plugin list changed
- **WHEN** the plugin list in the repository is newer than the generated plugin file
- **THEN** the generated plugin file is rebuilt on the next start, and missing plugins are cloned

#### Scenario: No network on a fresh host
- **WHEN** the first interactive zsh starts without network access
- **THEN** zsh still shows a working prompt, with the built-in key bindings and without the plugins

### Requirement: Prompt before plugins
Interactive zsh SHALL show the prompt before the deferred plugins are loaded, and SHALL load them in the background in a fixed order. The order is:
1. completion system
2. fzf-tab
3. history-substring-search
4. autosuggestions
5. fast-syntax-highlighting

The deferred loading SHALL NOT redraw the prompt or run prompt hooks after each step.

#### Scenario: Typing right after start
- **WHEN** an interactive zsh shows its first prompt
- **THEN** input typed before the deferred plugins finish is kept and handled once they are loaded

#### Scenario: Startup time on the reference host
- **WHEN** zsh-bench runs on the owner's workstation
- **THEN** the first prompt appears in under 50 ms and the shell is fully loaded in under 300 ms

### Requirement: One completion initialisation
The completion system SHALL be initialised exactly once per start, from a cached dump, before fzf-tab. It SHALL be initialised before any module that registers completions with `compdef`, including the `machine` completion.

#### Scenario: machine completion with deferred compinit
- **WHEN** zsh finishes loading the deferred part
- **THEN** `machine <Tab>` offers the subcommands

#### Scenario: Distribution compinit
- **WHEN** the distribution's global zshrc would run compinit
- **THEN** it is skipped, and the dotfiles run compinit once

### Requirement: Optional tools are skipped silently
Tool integrations (fzf, zoxide, eza preview, starship) SHALL be enabled only when the tool is on `PATH`. A missing tool SHALL NOT print errors or trigger downloads.

#### Scenario: Host without fzf and zoxide
- **WHEN** an interactive zsh starts on a host where fzf and zoxide are missing
- **THEN** zsh starts without error output, `z` and the fzf key bindings are absent, and the other plugins work

#### Scenario: Tool installed later
- **WHEN** a tool is installed or updated after its init output was cached
- **THEN** the next start regenerates the cached init output

### Requirement: Paste and sudo helpers
A line that starts with `$ ` or `❯ ` SHALL run the rest of the line as a command, so that pasted examples work. Pressing Esc twice SHALL put `sudo ` in front of the current line, or toggle it off if it is already there.

#### Scenario: Pasting a command with a prompt character
- **WHEN** the user runs `$ echo hi` or `❯ echo hi`
- **THEN** `hi` is printed

#### Scenario: Prepending sudo
- **WHEN** the user presses Esc twice on the line `apt update`
- **THEN** the line becomes `sudo apt update`

### Requirement: Spelling correction
zsh SHALL offer to correct misspelt command names.

#### Scenario: Misspelt command
- **WHEN** the user types `gti status`
- **THEN** zsh asks whether `git status` was meant
