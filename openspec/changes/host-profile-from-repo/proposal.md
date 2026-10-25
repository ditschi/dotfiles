# Proposal

## Why

The profile of a host lives in two places: the versioned `machine/hosts/<hostname>.yml` and the local `~/.config/machine/profile.yml`. Today the repository file silently wins on every update, while `machine setup` only asks whether to copy a changed selection into the repository; with `--yes` or a "no" the change stays local and the next update silently reverts it. The repository file shall be the only source of a host's profile, so that a profile can also be changed from another host and the next update brings new features to the machine as intended, with a visible notice instead of a question.

## What Changes

- `machine setup` writes the chosen profile, features and `ssh_allow_from` directly into `machine/hosts/<hostname>.yml` (no question, also with `--yes`) and offers to commit it, as before.
- `machine update` and `machine apply` take the repository file over the local copy without asking and print what changed (profile, added and removed features, `ssh_allow_from`).
- `machine update --check` lists an incoming change of the host's profile before anything is applied.
- `~/.config/machine/profile.yml` stays as the copy `machine` writes from the repository: it is the applied state that a failed apply reverts to, and the profile of hosts without a repository file (containers, a new host before its first commit).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `machine-profiles`: the repository host file is the only source; changes are applied with a notice.

Affected profiles: all except `container` (no repository file is written in containers).

## Impact

- `machine_cli/profile.py` (setup persists, sync notice), `machine_cli/updates.py` (check output), tests, Readme.
