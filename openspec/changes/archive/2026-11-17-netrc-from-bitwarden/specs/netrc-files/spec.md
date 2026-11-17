# Spec Delta

## Purpose

Defines how `~/.netrc` is generated from Bitwarden items, how references to other items are resolved, and how local edits are protected and written back.

## ADDED Requirements

### Requirement: ~/.netrc is generated from Bitwarden
`machine env pull` SHALL also write `~/.netrc` from the notes of the Bitwarden items `netrc/groups/<group>` (the group of the host's context, `work` or `private`) and `netrc/hosts/<hostname>`, with mode `600`, and SHALL back up the previous content first. Bitwarden is the source of truth: the file is replaced as a whole. `machine setup` and `machine update` write it through `machine env pull`.

#### Scenario: Pulling
- **WHEN** a user runs `machine env pull` on a `work` host and `netrc/groups/work` holds host blocks
- **THEN** `~/.netrc` has mode `600` and holds those host blocks, and the previous file is in the backup directory

#### Scenario: Hand-written entries
- **WHEN** an existing `~/.netrc` holds a machine that no item holds and the file was not written by the last pull
- **THEN** the pull replaces the file after the backup, and the backup holds that machine

### Requirement: Host item first, blocks as in Bitwarden
The generated file SHALL hold the blocks of `netrc/hosts/<hostname>` first and then those of `netrc/groups/<group>`, each in the order of its notes. Blocks SHALL NOT be merged, dropped or reordered, also not for a repeated machine or a `default` block; the tools that read the file decide which block applies.

#### Scenario: Host item adds to the group item
- **WHEN** `netrc/hosts/<hostname>` holds a block for a machine that `netrc/groups/work` does not
- **THEN** `~/.netrc` holds the blocks of the host item, then those of the group item

#### Scenario: Same machine in both items
- **WHEN** both items hold a block for the same machine
- **THEN** `~/.netrc` holds both blocks, the one of the host item first

#### Scenario: Default block
- **WHEN** an item holds a `default` block before another block
- **THEN** `~/.netrc` keeps that order

### Requirement: Host blocks keep their layout
The generated file SHALL keep the host blocks of the notes as written (`machine`, `login`, `password` and other netrc tokens, on one or several lines, and comment lines), except that references are replaced by their values.

#### Scenario: Multi-line block
- **WHEN** the notes hold `machine host.example`, `login alice` and `password {{bw:Work login/password}}` on three lines
- **THEN** `~/.netrc` holds the same three lines with the password in place of the reference

#### Scenario: Comment
- **WHEN** the notes hold a line `# artifactory token, rotated yearly` above a block
- **THEN** `~/.netrc` holds that line unchanged

### Requirement: References in netrc values
A `login` or `password` value of the form `{{bw:<item name>/<target>}}`, with `<target>` `password`, `username` or `field:<NAME>` and the item name matched exactly, SHALL be a reference. The pull SHALL write the referenced value and SHALL never write the reference text.

#### Scenario: Item name with spaces
- **WHEN** a block holds `login {{bw:Work login/username}}` and `password {{bw:Work login/field:artifactory-token}}` and the item `Work login` has both
- **THEN** `~/.netrc` holds the login name of the item and the value of its field `artifactory-token`

### Requirement: Unresolvable host blocks are skipped
A host block with a reference that cannot be resolved (item missing or ambiguous, target missing or empty) or whose value cannot be written unchanged into a netrc (it contains whitespace, a quote, a backslash or a line break) SHALL be left out of `~/.netrc`; the other blocks SHALL still be written. The pull SHALL name the host and the reason without values and record an attention item.

#### Scenario: Missing field
- **WHEN** a block references `field:artifactory-token` and the item has no such field
- **THEN** `~/.netrc` holds no block for that machine, holds the other blocks, and a notice names the machine and the missing field

#### Scenario: No value in messages
- **WHEN** a block is skipped
- **THEN** neither the notice nor the attention item contains a secret value or the reference text of another block

#### Scenario: Every block skipped
- **WHEN** no block of the items can be written
- **THEN** `~/.netrc` is unchanged and the skipped blocks are named in the notice and the attention items

### Requirement: Nothing is written when Bitwarden is not usable
When there is no context, `bw` is missing, Bitwarden is locked, Bitwarden items cannot be listed, or neither `netrc/` item exists, `machine env pull` SHALL leave `~/.netrc` unchanged. A locked or missing Bitwarden SHALL NOT make an unattended run fail.

#### Scenario: Locked vault
- **WHEN** Bitwarden is locked and the pull runs without a terminal
- **THEN** `~/.netrc` is unchanged and the run does not fail

#### Scenario: No netrc items
- **WHEN** neither `netrc/groups/<group>` nor `netrc/hosts/<hostname>` exists
- **THEN** `~/.netrc` is unchanged

### Requirement: Unpushed local edits are kept
The pull SHALL remember the content it last wrote. A host block in `~/.netrc` that was changed, removed or added since then is an unpushed local edit. In a terminal the pull SHALL ask push, discard or skip with skip preselected; without a terminal it SHALL leave `~/.netrc` unchanged and record an attention item.

#### Scenario: Edited block in a terminal
- **WHEN** the user changed the login of a block and runs `machine env pull` in a terminal
- **THEN** the pull names the machine, offers push, discard and skip, and skip is preselected

#### Scenario: Discard
- **WHEN** the user picks discard
- **THEN** `~/.netrc` is regenerated from Bitwarden and the backup holds the edited file

#### Scenario: Background update
- **WHEN** an unattended pull finds an unpushed edit
- **THEN** `~/.netrc` is unchanged and an attention item names the machine

### Requirement: Push writes local edits to Bitwarden
`machine env push [--host]` SHALL also push `~/.netrc`: compare it with the last pulled content, list the added, changed and removed host blocks by machine name (never values), ask for confirmation, write the changes into the notes of the item that holds the block (a new block goes into `netrc/groups/<group>`, with `--host` into `netrc/hosts/<hostname>`), and then pull. It SHALL leave `~/.netrc` alone when there is no last pulled content.

#### Scenario: New block
- **WHEN** the user added a host block with a literal password to `~/.netrc` and runs `machine env push`
- **THEN** the machine name is listed without the password, and after confirmation the block is appended to the notes of the item

#### Scenario: Declined
- **WHEN** the user declines the confirmation
- **THEN** Bitwarden and `~/.netrc` are unchanged

#### Scenario: No last pulled content
- **WHEN** the push runs before any pull wrote `~/.netrc` and there is nothing else to push
- **THEN** it writes nothing for `~/.netrc` and names `machine env pull` as the next command

### Requirement: Push of a referenced value
A new value for a `login` or `password` that the notes give as a reference SHALL be written into the referenced item's target, and the notes SHALL keep the reference. All references SHALL be checked before anything is written.

#### Scenario: Changed token
- **WHEN** the password of a block comes from `{{bw:Work login/field:artifactory-token}}`, the user changes it in `~/.netrc` and pushes
- **THEN** the field `artifactory-token` of `Work login` has the new value and the notes still hold the reference

#### Scenario: Reference typo
- **WHEN** a pushed reference names an item that does not exist
- **THEN** nothing is written to Bitwarden

### Requirement: Removals and conflicts default to no
The push SHALL offer removing a host block from the notes, and writing a block that Bitwarden changed to a different value since the last pull, each with "no" preselected. A block changed only in Bitwarden SHALL NOT be written back.

#### Scenario: Removed block
- **WHEN** the user deleted a block from `~/.netrc` and presses Enter at the removal question
- **THEN** the notes still hold the block

### Requirement: Warning for github.com
A host block for `github.com` SHALL be written as given, and the pull SHALL warn that curl then sends these credentials up front, so git credential helpers do not run for that host. Other hosts, including GitHub Enterprise hosts, SHALL get no warning.

#### Scenario: github.com block
- **WHEN** the notes hold a block for `machine github.com`
- **THEN** `~/.netrc` holds the block and the pull prints one warning naming `github.com`

#### Scenario: Enterprise host
- **WHEN** the notes hold a block for `machine github.boschdevcloud.com`
- **THEN** `~/.netrc` holds the block and no warning is printed
