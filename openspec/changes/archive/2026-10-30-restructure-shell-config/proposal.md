# Proposal

## Why

The Bash startup file has grown long, and shared Bash/zsh code is stored under `.zsh` alongside zsh-only modules. The owner wants an easy-to-maintain structure that makes it clear where each part is loaded and approved `.shell/{common,bash,zsh}` with explicit per-shell include lists.

This change consolidates the approved shell-layout investigation and implementation plan. Its design preserves the assessment, recommended directory tree, decisions and source references alongside the migration and acceptance criteria; no separate investigation change is needed.

## What Changes

- Move authored configuration into `home/core/.shell/common`, `.shell/bash` and `.shell/zsh`, using descriptive filenames and thin `.bashrc`/`.zshrc` entry points.
- Replace zsh's numeric-prefix glob loader with an explicit ordered source list. Give Bash its own explicit loader instead of embedding its fallback implementation in `.bashrc`.
- Separate shared aliases, environment and helper logic from interpreter-specific history, tool activation, prompt hooks and editor integration. Keep command-prefix matching shared and its Readline/ZLE integrations separate.
- Move work configuration into `home/work/.shell/work/{common,zsh}` while retaining existing group selection and runtime guards.
- Update the handoff loader checks and invalidation inputs, the `machine` post-update health-check caller, the credential helper, tests, lint coverage and documentation for the new paths.
- Preserve shell behavior, extension points, managed blocks, tool selection and generated cache/data locations. Migrate existing managed symlinks without deleting local files or reinstalling plugins.

## Capabilities

### New Capabilities

None. Existing shell capabilities own this behavior.

### Modified Capabilities

- `zsh-config-loading`: replace numeric/glob module discovery with explicit ordered loading from `.shell`, while retaining profile-first configuration, local overrides and deferred completion dependencies.
- `bash-shared-config`: load genuinely shared modules from `.shell/common` and shell-specific history/integration from `.shell/bash` through an explicit loader; retain work gating and final local overrides.
- `shell-handoff`: check the relocated zsh loader and invalidate health results for the relocated common, zsh and work startup inputs, including file removal/rename.

`shell-prompt`, `zsh-plugins`, `env-files`, `local-overrides`, `work-private-separation` and the command-prefix recovery requirements are regression constraints, not redesigned capabilities.

## Impact

Applies to private and work contexts on desktops, servers and containers. The `core` and `work` mise groups keep their current selection rules. No Ansible roles, system packages, new tools, secrets or authentication mechanisms are introduced.

Implementation touches shell entry points and modules under `home/core/` and `home/work/`, `git-credential-env`, `machine_cli/auto_update.py`, shell/deployment/credential/update tests, shell lint configuration where needed, and shell documentation. The existing update classifier and dotfile migration helpers must be verified for the new paths; change them only if focused tests show a gap.

The relocated authored files are internal paths, but direct consumers must be updated together. Keep `~/.bash_aliases`, `~/.bashrc-local`, `~/.zshrc-local`, `.profile` login behavior and minimal `.zshenv` behavior. Existing plugin checkouts and XDG caches remain usable; generated bundles that embed an old configuration path must be safely regenerated.

## Scope Boundary

This planning change does not apply the refactor. Implementation starts only through the apply workflow. Do not remove existing shell features or redesign handoff policy, history semantics, env-file parsing, prompt styling or plugin management as part of the migration.
