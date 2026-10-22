## ADDED Requirements

### Requirement: The machine CLI is not deployed by chezmoi
The `machine` CLI SHALL live in `machine_cli/` at the repository root, outside the chezmoi source tree, and `~/.local/bin/machine` SHALL be a symlink into the checkout. Chezmoi SHALL NOT deploy, copy or prompt about the CLI.

#### Scenario: Plain git pull adds a CLI module
- **WHEN** a user updates the checkout with `git pull` and the incoming commits add a module to the CLI
- **THEN** `machine` runs with the new module without running chezmoi

#### Scenario: Plain git pull changes the entry point
- **WHEN** a user updates the checkout with `git pull` and the incoming commits change the `machine` script
- **THEN** `machine` runs the new script and chezmoi does not ask to overwrite it

### Requirement: The checkout location is not fixed
The `machine` CLI SHALL find the repository by resolving the symlink `~/.local/bin/machine`, so the checkout MAY be at any path.

#### Scenario: Checkout outside the default location
- **WHEN** the repository is cloned to a path other than `~/dotfiles` and bootstrap has linked `machine`
- **THEN** `machine` operates on that checkout
