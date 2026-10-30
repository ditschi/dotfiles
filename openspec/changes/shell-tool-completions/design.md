# Design

## Context

See proposal.md for the motivation. Bash sources distribution `bash-completion` when available and registers `machine` directly. Zsh runs one cached `compinit` in its deferred initialization, registers `machine` after that, and then loads `fzf-tab`. Shell modules are explicitly loaded, and generated state belongs under the user cache rather than beside repository-linked files.

## Goals / Non-Goals

**Goals:**
- Enable native Bash and Zsh completions for the installed CLIs that provide them, including tools selected through features.
- Preserve optional-tool behavior, offline startup, and the existing prompt/deferred-load performance contracts.
- Keep generated files out of the repository and refresh them when the installed CLI changes.

**Non-Goals:**
- Add Fish support or a new completion manager.
- Install a system completion package or require root.
- Vendor upstream-only static completion scripts that are not already supplied by a configured provider.
- Change key bindings, tool versions, or which tools are selected by each profile.

## Decisions

### Keep completion integration in the shell owners

Use the existing explicit Bash and Zsh shell modules to load completions. Tool fragments remain responsible for installing tools; shell modules own shell-specific registration and ordering. Bash completion setup follows the existing base `bash-completion` load when present. Zsh tool registrations run after `compinit` and before `fzf-tab`, without adding a general-purpose after-compinit registry.

### Prefer tool-generated scripts and cache them

Use the CLI's own completion generator when available, including the already-identified generators for Copilot CLI, Zellij, GitHub CLI, OpenCode, uv and mise. Use static definitions already supplied by configured system or Zsh providers. Audit all core and feature tool declarations for additional generators and provider coverage. Document upstream-only static scripts but do not vendor them in this change. Store generated scripts under `${XDG_CACHE_HOME:-$HOME/.cache}` and refresh them when the corresponding executable is newer than the cache. Guard generation and sourcing on the command being installed; do not download completion data at shell startup. GitHub CLI and Git LFS Bash scripts depend on `_get_comp_words_by_ref` from `bash-completion`, so register their native scripts only when that helper is available; do not make the OS package mandatory.

### Support only the configured interactive shells

Generate or load Bash and Zsh definitions only. Fish may be supported by some upstream tools, but this repository does not configure Fish. Keep each shell's generated script separate because the formats and registration APIs differ.

### Preserve startup validation

Extend the existing shell-focused checks to prove that the generated definitions load in Bash and Zsh, appear after the required completion initialization, and remain absent without errors when an optional CLI is missing. Continue exercising the Zsh deferred/check-mode path and the plain Bash fallback.

### Keep the future-tool check visible during planning

Put the tool-completion reminder in the global OpenSpec `context`, so it is present while agents propose and plan future features, not only while changing shell code. Keep the `user-tools` requirement as the behavior contract; the config reminder tells contributors to account for that requirement when a new CLI is introduced.

No alternative completion manager or system package was identified by the owner; this design follows the existing per-shell completion lifecycle.

## Risks / Trade-offs

- [A completion generator may be slow or emit errors] -> Run it only when its cache is missing or stale, guard it by command availability, and keep it offline.
- [Tool updates leave stale generated definitions] -> Regenerate when the installed executable is newer than the cached script and test cache refresh behavior.
- [A completion is registered too early for Zsh] -> Load it after `compinit` and before `fzf-tab`; cover deferred startup and check mode.
- [Bash lacks the distribution completion package] -> Load self-contained native CLI completions independently of the optional system provider and skip GitHub CLI and Git LFS native Bash completions, which require a helper from that package.
- [Some tools publish static scripts not present in configured providers] -> Document those gaps rather than downloading or vendoring files as part of this change.

## Migration Plan

No user data or tool selection changes. On the next shell start, missing or stale completion scripts are generated in the user cache and loaded. Rollback is a dotfiles update; unused cached completion files can remain harmlessly in the cache.
