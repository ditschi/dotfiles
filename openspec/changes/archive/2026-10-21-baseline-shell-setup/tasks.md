# Tasks

This change adds planning artifacts only; no project code changes.

## 1. Baseline review

- [x] 1.1 Compare each requirement in `shell-handoff` against `home/dot_bashrc` and `~/.preferred-shell` handling; verify every scenario matches current behaviour and the Docker and `bash -c` guards are not claimed.
- [x] 1.2 Compare `zsh-config-loading` and `bash-shared-config` against `home/dot_zsh/config/00_LOADER.zsh` and the bash module list in `home/dot_bashrc`; verify the module names and the `WORK_SETUP` condition are accurate.
- [x] 1.3 Verify the managed blocks named in the spec exist (`ANSIBLE MANAGED BLOCK` in the profile, `OSD-PROXY-PACKAGE` in the work module) with `grep`.
- [x] 1.4 Ask the owner to confirm each spec and each investigation in design.md; verify that anything not confirmed is moved to Open Questions rather than left as a requirement.

## 2. Decision record retirement (temporary)

- [x] 2.1 (temporary, drop once `docs/decisions/` is retired) Update `docs/decisions/0002-shell-setup.md` (What, Last verified, tagged Why) to point at the baseline specs; verify the record no longer contradicts them.

## 3. Validation

- [x] 3.1 Run `openspec validate baseline-shell-setup --strict` and `pre-commit run --all-files`; verify both pass.

## Workflow follow-up

- Archive this change before reworking `add-zsh-startup-check` so that `shell-handoff` exists in the main specs.
