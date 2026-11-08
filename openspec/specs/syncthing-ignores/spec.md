# syncthing-ignores Specification

## Purpose
Defines the shared Syncthing ignore rules: one synced `.stglobalignore` per folder, the lines `machine` keeps at the top of each local `.stignore`, and the default ignore patterns for new folders, on hosts with the feature `syncthing`.

## Requirements

### Requirement: Shared ignore rules per folder
Each shared Syncthing folder SHALL hold its shared ignore rules in a synced file `.stglobalignore` at the folder root. Build output, dependency caches, `.claude/worktrees` and the Synology folders `@eaDir`, `#recycle` and `#snapshot` SHALL be ignored by default, and an exception SHALL be a `!<path>` line above the rules in that file, so that it applies on every device of the folder.

#### Scenario: Rust build output
- **WHEN** a project inside a shared folder is built and creates `target/`
- **THEN** `target/` is not synced to the other devices

#### Scenario: Opt-in exception
- **WHEN** `.stglobalignore` of a folder has `!DIY/sbx/demo/node_modules` above the rules
- **THEN** that directory is synced on every device, and every other `node_modules` stays ignored

### Requirement: Local ignore file loads the shared rules first
On a host with the feature `syncthing`, `machine` SHALL make sure that the `.stignore` of every folder in the local Syncthing configuration starts with `#include .stglobalignore` (only when that file exists) followed by `!/.stglobalignore`, each exactly once. Every other line SHALL keep its content and order. A folder without `.stglobalignore` SHALL NOT have the include line; an existing one SHALL be removed.

#### Scenario: Local lines present
- **WHEN** a folder's `.stignore` holds device-specific lines without the include line
- **THEN** the include line and `!/.stglobalignore` are added on top and the device-specific lines follow unchanged

#### Scenario: Allow-list folder
- **WHEN** a folder's `.stignore` ends with `(?d)*` and only lets listed paths through
- **THEN** `!/.stglobalignore` near the top keeps `.stglobalignore` itself synced in both directions

#### Scenario: Include line further down
- **WHEN** the include line is present further down, also with other spacing or as `#include ./.stglobalignore`
- **THEN** one include line is on top and no other include of the file remains

#### Scenario: Shared file not there yet
- **WHEN** a folder has no `.stglobalignore` and a peer has announced one that has not arrived yet
- **THEN** the folder's `.stignore` gets `!/.stglobalignore` but no include line, the folder shows no error, and `machine` reports it as waiting

#### Scenario: Already in place
- **WHEN** the two lines are already on top
- **THEN** `.stignore` is not rewritten

### Requirement: Shared rules created only where no device has them
The dotfiles SHALL NOT overwrite an existing `.stglobalignore`; its content comes from the synced folder. When a folder has no `.stglobalignore` and no device known to Syncthing has announced one, `machine` SHALL create it from the rule list in the repository and then add the include line. When Syncthing cannot tell or the folder is paused, `machine` SHALL NOT create it; when it was deleted on another device, `machine` SHALL NOT recreate it.

#### Scenario: Different dotfiles versions
- **WHEN** two laptops with different dotfiles versions run `machine update` on a folder that has `.stglobalignore`
- **THEN** neither changes `.stglobalignore`, and Syncthing creates no conflict file for it

#### Scenario: Folder without shared rules anywhere
- **WHEN** a folder has no `.stglobalignore` and no known device has one
- **THEN** `machine` creates it from the repository rule list, its `.stignore` starts with the include line, and the file is synced to the other devices

#### Scenario: Accepting an existing folder
- **WHEN** a device accepts a folder whose `.stglobalignore` exists on the offering device but has not arrived yet
- **THEN** `machine` does not create it and reports the folder as waiting until it has arrived

#### Scenario: Syncthing not running
- **WHEN** a folder has no `.stglobalignore` and the local Syncthing does not answer
- **THEN** nothing is created, and the next run tries again

### Requirement: Conflict copies of the shared rules
On a host with the feature `syncthing`, `machine` SHALL delete a Syncthing conflict copy of `.stglobalignore` only when its content equals `.stglobalignore`, and SHALL keep and report any other conflict copy.

#### Scenario: Identical conflict copy
- **WHEN** a folder holds a conflict copy of `.stglobalignore` with the same content
- **THEN** `machine` deletes it

#### Scenario: Different conflict copy
- **WHEN** a folder holds a conflict copy of `.stglobalignore` with other rules
- **THEN** the copy is kept and `machine` names it in its output

### Requirement: New folders start with the shared rules
On a host with the feature `syncthing`, `machine` SHALL set Syncthing's default ignore patterns to the shared rules kept in the repository, without an include line, followed by the host's existing default lines that are not among them, so that a folder added or accepted later ignores build output from the start.

#### Scenario: Newly accepted folder
- **WHEN** the host accepts a new shared folder after `machine` has run
- **THEN** the folder's ignore patterns contain the shared rules before its first sync, and the folder shows no error

#### Scenario: Own default lines
- **WHEN** the default ignore patterns hold `__*` and `(?d)@eaDir` before `machine` runs
- **THEN** they hold the shared rules followed by `__*`, and `(?d)@eaDir` appears once

### Requirement: Only hosts with the feature
`machine` SHALL read or change Syncthing ignore files and settings only on hosts whose features include `syncthing`. Without a local Syncthing configuration, the step SHALL do nothing and report nothing.

#### Scenario: Work host
- **WHEN** `machine update` runs on a work host, where `syncthing` is excluded, or on a server without the feature
- **THEN** no `.stignore` and no Syncthing setting is read or changed

#### Scenario: Feature selected, Syncthing never started
- **WHEN** the host has the feature but no Syncthing configuration exists yet
- **THEN** the step finishes without a change or a message
