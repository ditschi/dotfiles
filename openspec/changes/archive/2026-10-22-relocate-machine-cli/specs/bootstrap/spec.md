## ADDED Requirements

### Requirement: Bootstrap runs from a checkout or piped
`./bootstrap` SHALL detect whether it runs from a checkout of the repository or piped from the network (`curl | bash`). When piped, it SHALL clone the repository over HTTPS to `~/dotfiles`, or to the path in `DOTFILES_DIR` when set, and continue from that clone. The repository is assumed to be public; piped bootstrap does not work for a non-public repository.

#### Scenario: Run from a checkout
- **WHEN** a user runs `./bootstrap` inside a checkout
- **THEN** that checkout is used and nothing is cloned

#### Scenario: Piped run on a new host
- **WHEN** bootstrap is piped from the network and no clone exists at the target path
- **THEN** the repository is cloned to `~/dotfiles` (or `DOTFILES_DIR`) and setup continues from the clone

### Requirement: Bootstrap does not update an existing clone
When the clone target already exists, bootstrap SHALL use it without pulling and run `machine setup`. Updating the checkout SHALL stay the job of `machine update`.

#### Scenario: Piped run with an existing clone
- **WHEN** bootstrap is piped and the target path already holds a clone
- **THEN** the clone is left as it is and `machine setup` runs from it

### Requirement: Bootstrap links the machine command
Bootstrap SHALL create or replace `~/.local/bin/machine` as a symlink to the CLI script in the checkout it uses, replacing a regular file left by an earlier layout.

#### Scenario: Host with the earlier copied entry point
- **WHEN** bootstrap runs on a host where `~/.local/bin/machine` is a regular file
- **THEN** it is replaced by a symlink into the checkout and `machine` runs from the checkout
