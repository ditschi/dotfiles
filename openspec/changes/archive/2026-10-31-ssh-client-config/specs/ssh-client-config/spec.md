# Spec Delta

## Purpose

Defines the layers of the SSH client configuration (versioned base, host list per context from Bitwarden, host-only file) and the guided ways to add, edit, remove and pull hosts.

## ADDED Requirements

### Requirement: Versioned base config
The `core` dotfile group SHALL link `~/.ssh/config` to the versioned base config. It SHALL include `~/.ssh/config.local` first, then every file in `~/.ssh/config.d/`, and SHALL set its shared defaults under `Host *` after the includes, so that host-only and host-list settings win. A missing included file SHALL NOT cause an error.

#### Scenario: Fresh host without host list
- **WHEN** the dotfile groups are applied on a host without `~/.ssh/config.local` and without `~/.ssh/config.d/`
- **THEN** `ssh -G <any host>` succeeds and shows the shared defaults

#### Scenario: Host-only setting wins
- **WHEN** `~/.ssh/config.local` sets `User` for a host that the host list also sets
- **THEN** ssh uses the value from `~/.ssh/config.local`

### Requirement: Shared defaults
The base config SHALL set under `Host *`: keep-alive (`ServerAliveInterval 30`, `ServerAliveCountMax 4`), connection sharing (`ControlMaster auto`, `ControlPath ~/.ssh/cm/%C`, `ControlPersist 10m`), `IdentitiesOnly yes`, `HashKnownHosts no` and `UserKnownHostsFile ~/.ssh/known_hosts ~/.ssh/known_hosts.d/home`. It SHALL NOT set `ForwardAgent`, `AddKeysToAgent` or `StrictHostKeyChecking`. The repository SHALL NOT contain addresses, users, ports or other network details.

#### Scenario: Control socket directory
- **WHEN** the dotfile groups are applied
- **THEN** `~/.ssh/cm` exists with mode 700

#### Scenario: New ad-hoc host
- **WHEN** a user accepts the host key of a host that is not managed
- **THEN** ssh writes it to `~/.ssh/known_hosts`, not to the managed known-hosts file

### Requirement: Config file mode
`machine apply` SHALL make the versioned base config not writable for group and others, so that ssh accepts the linked file on every distribution.

#### Scenario: Checkout with umask 002
- **WHEN** the repository file has mode 664 and `machine apply` runs
- **THEN** the file has mode 644 afterwards and ssh reads it

### Requirement: Existing config is replaced once
When `~/.ssh/config` is a regular file and not the link, the apply SHALL move it aside as `~/.ssh/config.pre-dotfiles` (the general rule for replaced dotfiles) and link the base config in its place. It SHALL NOT move any content into the host list or `~/.ssh/config.local` without the user.

#### Scenario: Hand-written config
- **WHEN** the dotfile groups are applied on a host with a hand-written `~/.ssh/config`
- **THEN** the file is kept as `~/.ssh/config.pre-dotfiles`, `~/.ssh/config` is the link, and the log names the backup

### Requirement: Hosts of the replaced config stay usable
`machine apply`, also in the background update, SHALL write the sections of `~/.ssh/config.pre-dotfiles` whose host names neither the host list nor `~/.ssh/config.local` defines to `~/.ssh/config.d/90-legacy`, after the host list. While the file exists, `machine attention` SHALL list its hosts and offer for each: add to Bitwarden, move to `~/.ssh/config.local`, drop, or skip.

#### Scenario: Host without Bitwarden
- **WHEN** a host without `bw` gets the base config and its old config defines `nas`
- **THEN** `ssh nas` still uses the old settings

#### Scenario: Host now in the list
- **WHEN** the host list defines `nas` and the old config defines it too
- **THEN** `90-legacy` has no `nas` section and the list's settings apply

#### Scenario: Everything resolved
- **WHEN** every host of the old config was moved, added or dropped
- **THEN** `~/.ssh/config.pre-dotfiles` is moved to the machine state directory, `90-legacy` is removed and the item is closed

### Requirement: Host-only config file
`~/.ssh/config.local` SHALL be host-local, never versioned and never written by `machine` except when the user chose to move a host block into it.

#### Scenario: Update with a local file
- **WHEN** `machine update` runs on a host with `~/.ssh/config.local`
- **THEN** the file is unchanged

### Requirement: Host list per context from Bitwarden
The host list SHALL be a Bitwarden secure note per context whose notes hold ready `ssh_config` text: `ssh/home/config` for `private`, `ssh/work/config` for `work`. `machine setup`, the manual `machine update` and `machine ssh pull` SHALL write it to `~/.ssh/config.d/20-home` or `20-work` with mode 600. A container without context SHALL get no host list.

#### Scenario: Pull on a private host
- **WHEN** `machine ssh pull` runs on a private host with an unlocked Bitwarden session
- **THEN** `~/.ssh/config.d/20-home` holds the notes of `ssh/home/config` and no work list is queried

#### Scenario: Note does not exist yet
- **WHEN** the note of the context does not exist
- **THEN** no host list is written, nothing fails, and the log says how to create it with `machine ssh add`

### Requirement: Host list only with Bitwarden
The background update SHALL NOT read or write the host list. Without a Bitwarden session available without a prompt, the manual update SHALL keep the existing host list and log a warning that names the command to log in.

#### Scenario: Background update
- **WHEN** the background update runs
- **THEN** `~/.ssh/config.d/` is unchanged and `bw` is not called

#### Scenario: Manual update without session
- **WHEN** `machine update` runs without a Bitwarden session available without a prompt
- **THEN** the existing host list is kept and a warning says to log in with `machine env pull` in a terminal

### Requirement: Invalid host list is not written
Before writing a host list, `machine` SHALL check it with ssh. If ssh rejects it, the existing file SHALL be kept and the error reported.

#### Scenario: Syntax error in the note
- **WHEN** the note contains an option that ssh rejects
- **THEN** the existing `20-home` stays unchanged and the reported error names the note and the ssh message

### Requirement: Local host blocks are detected
A host block in the generated file that is not in the note, or that differs from it, SHALL be a local host block. Writing the host list SHALL carry each unresolved local host block over, unchanged, into a marked local-only section at the end of the file.

#### Scenario: Block added by hand
- **WHEN** a user added `Host test-vm` to `~/.ssh/config.d/20-home` and the host list is written
- **THEN** the file holds the current note and, in the local-only section, the `Host test-vm` block

### Requirement: Choices for a local host block
On a terminal and without `--yes`, `machine setup`, `machine update` and `machine ssh pull` SHALL ask for each local host block, by number: add to Bitwarden, move to `~/.ssh/config.local`, remove, or skip. Skip SHALL be preselected and SHALL record an attention item. Without a terminal or with `--yes` nothing SHALL be moved.

#### Scenario: Add to Bitwarden
- **WHEN** the user picks "add to Bitwarden" for a local host block
- **THEN** the block is appended to the note under a comment naming the host and the date, and the regenerated file has it outside the local-only section

#### Scenario: Move to the host-only file
- **WHEN** the user picks "move to config.local"
- **THEN** the block is in `~/.ssh/config.local` and no longer in the generated file

#### Scenario: Confirming the default
- **WHEN** the user presses Enter at the prompt
- **THEN** the block stays in the local-only section and an attention item is recorded

### Requirement: Safe writes to the note
Every write to the host-list note SHALL sync Bitwarden first and SHALL apply the change to the note as it is at write time. If the note changed after it was read, the change SHALL be applied to the new content. If the write fails, nothing local SHALL be removed and the failure SHALL be reported.

#### Scenario: Note changed on another host
- **WHEN** another host changed the note between reading and writing
- **THEN** both changes are in the note afterwards

#### Scenario: Write fails
- **WHEN** writing the note fails
- **THEN** the local host block stays where it was and an attention item is recorded

### Requirement: Adding a host interactively
`machine ssh add [alias]` SHALL ask for alias, address, user (default: current user) and port (default 22), and on a private host for the routes of a home host. It SHALL ask whether the host goes into the host list of the context (preselected) or into `~/.ssh/config.local`, show the resulting host block and write it only after confirmation.

#### Scenario: Work CI agent
- **WHEN** a user on a work host runs `machine ssh add ci-agent-07` and confirms the host list
- **THEN** the block is in `ssh/work/config` and in the regenerated `20-work`, and no host key file is written

#### Scenario: Alias already exists
- **WHEN** the alias is already defined in the host list or in `~/.ssh/config.local`
- **THEN** the command shows the existing block and asks whether to replace it, defaulting to no

### Requirement: Login test after adding
After writing a host, `machine ssh add` SHALL test a non-interactive login. When it fails, the command SHALL keep the entry and name the next step: install the user key on the target, or add this host to `ssh_allow_from` of a home host.

#### Scenario: Key not authorised
- **WHEN** the login test fails with a permission error
- **THEN** the entry is kept and the message names `ssh-copy-id <alias>` and `ssh_allow_from`

### Requirement: Editing the host list
`machine ssh edit` SHALL open the note of the context in the user's editor, check the result with ssh before saving, and on rejection offer to edit again or discard. After saving it SHALL regenerate the host list.

#### Scenario: Invalid edit
- **WHEN** the edited text is rejected by ssh
- **THEN** the note is unchanged and the user can edit again or discard

### Requirement: Removing a host
`machine ssh remove <alias>` SHALL remove the host block from the note or from `~/.ssh/config.local` after confirmation, and on a private host also the host key file of the alias, then regenerate the host list and the known-hosts file.

#### Scenario: Remove a home host
- **WHEN** a user confirms `machine ssh remove octoprint`
- **THEN** the block is gone from `ssh/home/config`, `machine/ssh_host_keys/octoprint.pub` is removed, and the removal is listed as not pushed yet

### Requirement: Setup offers to add the host itself
On a host with a context, `machine setup` SHALL offer to add the host to the host list of its context when its alias is not in it, with alias, address, user and port 22 prefilled from the host. Declining SHALL change nothing.

#### Scenario: New home server
- **WHEN** `machine setup` runs on a new private server whose hostname is not in `ssh/home/config` and the user accepts
- **THEN** a host block for the server is in the note, prefilled with its hostname, LAN address and the current user

#### Scenario: Host already listed
- **WHEN** the host's alias is already in the host list
- **THEN** setup does not ask
