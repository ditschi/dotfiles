# user-tools Specification

## Purpose
User tools can be installed without root, so that the dotfiles setup has every tool that its plugins and other functionality need. Dotfiles and the needed tools are then updated in one go, without manual user actions and without running Ansible.

## Requirements

### Requirement: User-space tools come from mise without root
Every tool that the shell configuration needs (for example `fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`) and the user-space developer tools (for example `gh`, `yazi`, Node) SHALL be installed by `mise` into the user's home, so that they are available on a host without root and without Ansible.

#### Scenario: Host without root
- **WHEN** `machine setup` runs on a host that cannot become root
- **THEN** all user-space tools of the selected groups are installed and the shell works with them

#### Scenario: Ansible not run
- **WHEN** a host has dotfiles and user-space tools applied but Ansible was never run
- **THEN** zsh and bash start without a missing-tool error for any tool of the selected groups

### Requirement: Tools are selected per group
Each dotfile group SHALL declare its tools in its own `mise` configuration fragment, and a host SHALL get the tools of exactly the groups its profile and features select. A tool name SHALL be declared in only one group; a duplicate across groups SHALL fail a repository check.

#### Scenario: Container profile
- **WHEN** a host with the `container` profile is set up
- **THEN** only the tools of the groups selected for that profile are installed

#### Scenario: Tool declared twice
- **WHEN** two groups declare the same tool
- **THEN** the repository check fails and names both groups

### Requirement: Versions are pinned by one lockfile
Tool versions and checksums SHALL be pinned in one lockfile kept in the repository and covering the platforms of the supported hosts, including arm64. Versions SHALL change only by a commit that updates the lockfile; `machine update --check` MAY report outdated tools but SHALL NOT change them.

#### Scenario: Update with an unchanged lockfile
- **WHEN** `machine update` runs and the lockfile did not change
- **THEN** no tool is upgraded

#### Scenario: Raspberry Pi
- **WHEN** a host with an arm64 CPU installs the tools
- **THEN** the lockfile provides the pinned arm64 builds

### Requirement: Tools of a removed group are removed
When a group is no longer selected for a host or its fragment is deleted, the tools only that group declared SHALL be removed from the host by the update, and tools of other groups SHALL stay.

#### Scenario: Group removed from the host
- **WHEN** a host drops a group and `machine update` runs
- **THEN** the tools that only this group declared are removed and the other tools stay installed

### Requirement: Tools are on the path of interactive shells
Interactive bash and zsh SHALL have the `mise` tools on `PATH` through `mise` activation, without a noticeable slowdown of shell start (the added time is expected to stay below 50 ms).

#### Scenario: New interactive shell
- **WHEN** an interactive bash or zsh starts after setup
- **THEN** the installed tools are found by name

### Requirement: No second installation source for a tool
A tool that `mise` installs SHALL NOT also be installed by Ansible on the same host.

#### Scenario: Tool in both places
- **WHEN** a tool is declared in a group fragment and in an Ansible package list
- **THEN** a repository check fails

### Requirement: Git is at least the version the shared config needs
The shared Git configuration needs Git 2.36 or newer. Every host SHALL get a user-space Git from `mise`, reachable by non-interactive callers (IDEs, hooks, `ssh` commands) through the `mise` shims directory on `PATH`. The first clone in `./bootstrap` MAY rely on a pre-installed system Git.

#### Scenario: Old system Git
- **WHEN** `machine setup` runs on a host whose Git is older than 2.36
- **THEN** a user-space Git is installed and `git` resolves to it in interactive and non-interactive shells

#### Scenario: Current system Git
- **WHEN** the system Git is 2.36 or newer
- **THEN** the user-space Git is still installed, so every host runs the same Git

### Requirement: Shell extras come with the shell configuration
Everything the shell configuration loads beyond the tools above (the Bash line editor extension `ble.sh`, shell fonts, plugin checkouts) SHALL be installed from pinned `mise` tools or Git checkouts by `machine`, without root and without Ansible, and `machine update` SHALL refresh them with the rest of the configuration.

#### Scenario: Bash host without zsh
- **WHEN** `machine setup` runs on a host that uses bash
- **THEN** the prompt, `zoxide`, `fzf` key bindings and completion work without Ansible

### Requirement: opencode comes from mise
opencode SHALL be installed by mise from the LLM fragment and pinned in the lockfile. The dotfiles SHALL NOT add `~/.opencode/bin` or `~/.npm-global/bin` to `PATH`.

#### Scenario: New interactive shell
- **WHEN** an interactive bash or zsh starts after `machine setup`
- **THEN** `opencode` is found through mise activation

#### Scenario: Leftover installer line
- **WHEN** an installer appended a PATH export to a shared shell file
- **THEN** the tool is added to a mise fragment instead and the line is not kept in the repository
