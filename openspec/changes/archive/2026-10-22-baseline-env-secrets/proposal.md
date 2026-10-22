# Proposal

## Why

Env files and secret handling are the fifth area moved from the temporary decision log into OpenSpec.

Motivation confirmed by the owner:

- Bitwarden, self-hosted, manages passwords and tokens centrally across machines.
- Secrets stay out of the repository.
- Environment variables also make selected tools and credentials available to container workflows, with work and private groups kept separate.

## What Changes

- Describe the confirmed behaviour as baseline requirements: the three env files and their load order, how the generated files are produced from Bitwarden, the loader formats, the permission warning, Bitwarden CLI and session handling, and the Ansible Vault password.
- Points the owner marked unclear or as gaps stay out of the specs and become investigations in design.md: the load order and more flexible file locations, the permission handling, the `git-credential-env` helper, and the `get-password` design.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

- `env-files`: which env files the shell loads, how they are generated and parsed.
- `secret-tools`: Bitwarden CLI and session handling, and the Ansible Vault password.

### Modified Capabilities

None.

## Open Questions

See design.md for the investigations.

## Impact

- Decision records: 0005 (env files and secrets) (to be retired once its content lives in specs and design).
- Code: none. This change only adds planning artifacts.
