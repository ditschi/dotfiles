# Spec Delta

## MODIFIED Requirements

### Requirement: Host-only keys stay out of the shared file
Host-only keys (identity, signing, `safe.*`, `credential.*`, `http(s).*`, `core.sshCommand`) SHALL be kept out of the shared file. `machine update`, `machine commit` and a pre-commit hook SHALL move them to `~/.gitconfig.local` through the local-overrides helper when the value is equal to or absent from the local file. A key with a different value in the local file SHALL be a conflict that the user resolves interactively with the helper; the local value is never overwritten silently. CI SHALL fail when a host-only key is in the shared file.

#### Scenario: Host-only key in the shared file
- **WHEN** a host-only key appears in the shared file
- **THEN** the check fails and the tooling moves it to `~/.gitconfig.local`

#### Scenario: Key re-added with the same value
- **WHEN** a host-only key reappears in the shared file with the value already in `~/.gitconfig.local`
- **THEN** it is removed from the shared file without asking

#### Scenario: Key re-added with a different value
- **WHEN** a host-only key reappears in the shared file with a value that differs from `~/.gitconfig.local`
- **THEN** the local value is kept, a conflict is recorded and the user chooses which value to keep
