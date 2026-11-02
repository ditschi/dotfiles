# Spec Delta

## MODIFIED Requirements

### Requirement: The checkout location is not fixed
The `machine` CLI SHALL find the repository by resolving the symlink `~/.local/bin/machine`, so the checkout MAY be at any path.

#### Scenario: Checkout outside the default location
- **WHEN** the repository is cloned to a path other than `~/dotfiles` and bootstrap has linked `machine`
- **THEN** `machine` operates on that checkout

#### Scenario: Stale clone at the default location
- **WHEN** bootstrap has linked `machine` into a checkout outside `~/dotfiles`, another clone exists at `~/dotfiles` and `DOTFILES_REPO` is not set before the shell starts
- **THEN** the shell, `machine` and the background update check use the linked checkout, not `~/dotfiles`, and `machine` prints no warning about `DOTFILES_REPO`

#### Scenario: Explicit DOTFILES_REPO
- **WHEN** `DOTFILES_REPO` is set to a checkout before the shell starts
- **THEN** the shell keeps that value and `machine` operates on that checkout

#### Scenario: Background update check outside the default location
- **WHEN** the background update check runs without `DOTFILES_REPO` and `machine` links into a checkout outside `~/dotfiles`
- **THEN** it checks and updates that checkout

## ADDED Requirements

### Requirement: machine repo prints the live checkout
`machine repo` SHALL print the absolute path of the checkout that `~/.local/bin/machine` links into as a single line on stdout and nothing else, regardless of which copy of `machine` runs it and of `DOTFILES_REPO`. When the link is missing or does not point into a checkout, it SHALL print a reason on stderr and exit with status 1. It SHALL NOT write any state, event or file.

#### Scenario: Linked checkout
- **WHEN** `~/.local/bin/machine` links into `/home/u/src/dotfiles` and a user runs `machine repo`
- **THEN** stdout is exactly `/home/u/src/dotfiles` followed by a newline and the exit status is 0

#### Scenario: Run from another worktree
- **WHEN** `~/.local/bin/machine` links into `/home/u/dotfiles` and a user runs `./machine_cli/machine repo` inside `/home/u/dotfiles/.worktrees/x`
- **THEN** stdout is `/home/u/dotfiles`

#### Scenario: No link
- **WHEN** `~/.local/bin/machine` does not exist and a user runs `machine_cli/machine repo` from a checkout
- **THEN** stdout is empty, stderr names the missing link and the exit status is 1

#### Scenario: No side effects
- **WHEN** a user runs `machine repo`
- **THEN** no disk state, usage event or other file is written
