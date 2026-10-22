# Spec Delta

## Purpose

Defines how zsh plugins and helper programs are managed so that the shell stays fast and the plugin set is installed without manual steps.

## ADDED Requirements

### Requirement: zinit is the plugin manager
zsh plugins and programs SHALL be managed by zinit, which installs itself into the user's data directory on the first zsh start, and plugins SHALL be loaded lazily where possible to keep startup fast.

#### Scenario: Fresh host
- **WHEN** the first interactive zsh starts and zinit is not installed
- **THEN** zinit is installed automatically and the configured plugins are set up

#### Scenario: Established host
- **WHEN** an interactive zsh starts and zinit is installed
- **THEN** plugins are loaded without reinstalling, deferred where the configuration allows

### Requirement: Configured plugin set
zsh SHALL load the plugins and programs listed in the plugin configuration: sudo, undollar, zsh-z, git-open, fast-syntax-highlighting, zsh-autosuggestions, zsh-completions, fzf-tab, history-substring-search, z.lua (only when lua or luajit exists), LS_COLORS and zsh-syntax-highlighting, plus the programs git-recent, eza, git-recall, fd and diff-so-fancy.

#### Scenario: Lua available
- **WHEN** lua or luajit is installed
- **THEN** z.lua is loaded as well

#### Scenario: Lua not available
- **WHEN** neither lua nor luajit is installed
- **THEN** z.lua is not loaded and startup continues without error
