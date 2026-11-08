# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Permission warning does not block loading`
- TO: `### Requirement: Loader fixes too-open env files`

## MODIFIED Requirements

### Requirement: Loader fixes too-open env files
When an env file grants any permission to group or others, the loader SHALL change its mode to `600`, SHALL print one line on stderr naming the file and the old mode, and SHALL load the file. When the mode cannot be changed, the loader SHALL print a warning with the `chmod 600` hint and SHALL still load the file. A mode without group or other bits SHALL be left unchanged.

#### Scenario: Open permissions
- **WHEN** an env file has mode `644`
- **THEN** the file has mode `600` afterwards, a line naming the file and `644` is printed on stderr, and the file is loaded

#### Scenario: Group or other bits only
- **WHEN** an env file has mode `044` or `604`
- **THEN** the file has mode `600` afterwards and is loaded

#### Scenario: Stricter mode
- **WHEN** an env file has mode `400`
- **THEN** its mode is unchanged and nothing is printed

#### Scenario: Mode cannot be changed
- **WHEN** an env file has mode `644` and changing the mode fails, for example because another user owns it
- **THEN** a warning with the `chmod 600` hint is printed and the file is loaded

## ADDED Requirements

### Requirement: Health check run leaves env file permissions alone
During the zsh health check run, the loader SHALL NOT change the mode of an env file and SHALL NOT print a permission message, so an open env file does not make the check fail.

#### Scenario: Open env file during the check
- **WHEN** the zsh health check runs and `~/.env` has mode `644`
- **THEN** the check passes, and `~/.env` still has mode `644` until the next real shell start

### Requirement: machine fixes too-open env files
`machine env pull`, and `machine setup` and `machine update` through it, SHALL change the mode of `~/.env`, `~/.env.host` and `~/.env.local` to `600` when group or other bits are set, and SHALL log each change with the file and the old mode. This SHALL also happen when Bitwarden is locked, `bw` is missing or the host has no context.

#### Scenario: Open file during an update
- **WHEN** `~/.env.local` has mode `664` and `machine update` runs with Bitwarden locked
- **THEN** `~/.env.local` has mode `600` afterwards and the output names it and `664`

#### Scenario: Nothing to fix
- **WHEN** all env files have mode `600`
- **THEN** `machine env pull` logs no permission change
