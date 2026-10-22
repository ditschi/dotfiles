# Tasks

This change adds planning artifacts only; no project code changes.

## 1. Baseline review

- [x] 1.1 Ask the owner to confirm each point; verified: confirmed points are in the specs and the rest are investigations in design.md.
- [x] 1.2 Compare the specs against `commands.py` (`cmd_update`), `00_alias.zsh` and `home/dot_zshrc`; verify every scenario matches current behaviour.

## 2. Decision record retirement (temporary)

- [x] 2.1 (temporary, drop once `docs/decisions/` is retired) Update `docs/decisions/0007-*.md` (What note, Last verified) to point at this change; verify it no longer contradicts the specs.

## 3. Validation

- [x] 3.1 Run `openspec validate baseline-update-mechanism --strict`; verify it passes.

## Workflow follow-up

- Archive the change once review is complete.
