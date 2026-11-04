# Spec Delta

## ADDED Requirements

### Requirement: Shared ignore rules per folder
Each shared Syncthing folder SHALL hold its shared ignore rules in a synced file `.stglobalignore` at the folder root. Build output and dependency caches SHALL be ignored by default, and an exception SHALL be a `!<path>` line above the rules in that file, so that it applies on every device of the folder.

#### Scenario: Rust build output
- **WHEN** a project inside a shared folder is built and creates `target/`
- **THEN** `target/` is not synced to the other devices

#### Scenario: Opt-in exception
- **WHEN** `.stglobalignore` of a folder has `!DIY/sbx/demo/node_modules` above the rules
- **THEN** that directory is synced on every device, and every other `node_modules` stays ignored

### Requirement: Local ignore file loads the shared rules first
On a host with the feature `syncthing`, `machine` SHALL make sure that the `.stignore` of every folder in the local Syncthing configuration has `#include .stglobalignore` as its first line, exactly once. Every other line SHALL keep its content and order.

#### Scenario: Local lines present
- **WHEN** a folder's `.stignore` holds device-specific lines without the include line
- **THEN** the include line is added as the first line and the device-specific lines follow unchanged

#### Scenario: Include line further down
- **WHEN** the include line is present but not first
- **THEN** it is moved to the top and appears only once

#### Scenario: Already in place
- **WHEN** the include line is already the first line
- **THEN** `.stignore` is not rewritten

### Requirement: Shared rules are never written by the dotfiles
The dotfiles SHALL NOT write or overwrite an existing `.stglobalignore`; its content comes only from the synced folder.

#### Scenario: Different dotfiles versions
- **WHEN** two laptops with different dotfiles versions run `machine update`
- **THEN** neither changes `.stglobalignore`, and Syncthing creates no conflict file for it

### Requirement: New folders start with the shared rules
On a host with the feature `syncthing`, `machine` SHALL set Syncthing's default ignore patterns to the shared rules kept in the repository, so that a folder added or accepted later ignores build output from the start.

#### Scenario: Newly accepted folder
- **WHEN** the host accepts a new shared folder after `machine` has run
- **THEN** the folder's ignore patterns contain the shared rules before its first sync

### Requirement: Only hosts with the feature
`machine` SHALL read or change Syncthing ignore files and settings only on hosts whose features include `syncthing`. Without a local Syncthing configuration, the step SHALL do nothing and report nothing.

#### Scenario: Work host
- **WHEN** `machine update` runs on a work host, where `syncthing` is excluded
- **THEN** no `.stignore` and no Syncthing setting is read or changed

#### Scenario: Feature selected, Syncthing never started
- **WHEN** the host has the feature but no Syncthing configuration exists yet
- **THEN** the step finishes without a change or a message
