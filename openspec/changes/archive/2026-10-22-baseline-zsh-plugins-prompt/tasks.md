# Tasks

This change adds planning artifacts only; no project code changes.

## 1. Baseline review

- [x] 1.1 Ask the owner to confirm each point; verified: confirmed points are in the specs and the rest are investigations in design.md.
- [x] 1.2 Check the specs against `home/dot_zshrc`, `02_plugins.zsh`, `03_theme.zsh` and `home/.chezmoiignore`; verify every scenario matches current behaviour.

## 2. Decision record retirement (temporary)

- [x] 2.1 (temporary, drop once `docs/decisions/` is retired) Update `docs/decisions/0003-zsh-plugins-and-prompt.md` (What, Last verified, tagged Why) to point at this change; verify it no longer contradicts the specs.

## 3. Validation

- [x] 3.1 Run `openspec validate baseline-zsh-plugins-prompt --strict`; verify it passes.

## Workflow follow-up

- Archive the change once the owner has confirmed the open items.
