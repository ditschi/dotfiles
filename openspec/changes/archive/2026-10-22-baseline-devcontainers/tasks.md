# Tasks

This change adds planning artifacts only; no project code changes.

## 1. Baseline review

- [x] 1.1 Ask the owner to confirm each point; verified: all points are confirmed and in the specs.
- [x] 1.2 Compare the specs against `home/dot_zsh/config/01_work.zsh` and `home/dot_local/bin/executable_sde`; verify every scenario matches current behaviour.

## 2. Decision record retirement (temporary)

- [x] 2.1 (temporary, drop once `docs/decisions/` is retired) Update `docs/decisions/0008-*.md` (What note, Last verified) to point at this change; verify it no longer contradicts the specs.

## 3. Validation

- [x] 3.1 Run `openspec validate baseline-devcontainers --strict`; verify it passes.

## Workflow follow-up

- Archive the change once review is complete.
