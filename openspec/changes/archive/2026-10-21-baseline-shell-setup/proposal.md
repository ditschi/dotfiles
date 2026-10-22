# Proposal

## Why

The shell setup is the first area being moved from the temporary decision log into OpenSpec, so that later changes (starting with the zsh startup check) build on a written baseline instead of on history and guesswork.

Motivation confirmed by the owner:

- The shell should be fast and familiar across work and private machines.
- zsh is preferred whenever it is installed, unless the user explicitly configures another shell.
- Bash stays a guarded fallback: on machines where the account's login shell cannot be changed, and in containers where installing zsh is undesirable or impossible.

The login shell cannot be changed on work hosts because the accounts are centrally managed, so the handoff from bash is the way to reach zsh.

## What Changes

- Describe the confirmed current shell behaviour as baseline requirements: the bash-to-zsh handoff and the preferred-shell override, ordered module loading, host-local overrides, `machine` completion in both shells, the shared bash module subset, and preserved externally managed blocks.
- Points that the owner marked unclear stay out of the specs. They are recorded in design.md as investigations with a suggestion and its reason.
- Features only: no fixes or improvements are added to the baseline.

## Capabilities

### New Capabilities

Boundaries are a proposal and are settled together with the owner:

- `shell-handoff`: when and how an interactive bash session hands over to the preferred shell, including the override file and the cases that never hand over.
- `zsh-config-loading`: how zsh configuration is assembled from modules, with host-local overrides.
- `bash-shared-config`: which zsh modules bash reuses and the bash-compatibility constraint on them.

### Modified Capabilities

None. No specs exist yet.

## Open Questions

The investigations (Docker and `bash -c` guard, handoff mechanism, folder structure, loading scheme, edit aliases) are described in design.md.

## Assumptions

- The handoff has no direct test coverage today.
- A zsh startup health check with bash fallback is a separate change (`add-zsh-startup-check`) and is not part of this baseline.

## Impact

- Decision records: 0002-shell-setup (to be retired once its content lives in specs and design).
- Profiles: all (work-machine, home-laptop, home-server, rpi, rpi-zero, container).
- Code: none. This change only adds planning artifacts.
- Related change: `add-zsh-startup-check` should be reworked as a modification of the `shell-handoff` capability once this baseline exists.
