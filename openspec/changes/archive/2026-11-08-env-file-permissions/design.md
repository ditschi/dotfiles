# Design

## Context

See proposal.md - Why. `dotfiles_load_envfiles` in `home/core/.shell/common/envfiles.sh` is sourced by `environment.sh` (bash and zsh start) and by `get-password`. It compares `stat -c %a` as a number with `600` (`$perms -gt 600`), so `044` or `060` pass unnoticed, while `700` warns. `machine env pull` writes `~/.env` and `~/.env.host` through `write_private` (`machine_cli/core.py`), but only when the content changes; it never writes `~/.env.local`. The zsh health check (`home/core/.shell/bash/zsh-health.bash`) starts `zsh -l -i` with `DOTFILES_ZSH_CHECK=1` and fails on any stderr output, so today every open env file makes the check fail and bash falls back.

## Goals / Non-Goals

**Goals:** an env file with group or other permissions becomes `600` on the next shell start or `machine` run, and the user is told once.

**Non-Goals:** changing the health check rules (separate topic: stderr tolerance); changing the owner's own bits (`700` is left as it is, because it exposes nothing to other users); other secret files (`~/.gitconfig.local`, SSH keys).

## Decisions

### Both the loader and `machine` fix the mode (owner decision 2026-11-08)
The loader covers files created by hand, such as `~/.env.local`, at the next shell start. `machine env pull` covers hosts where nobody opens a shell (servers, the background update job) and files that the pull leaves unchanged. Both use the same rule.

Alternatives considered: only the loader (headless hosts would keep an open file until someone logs in); only `machine` (the warning would stay on every shell start until `machine` ran).

### Check the permission bits, not the number
A file counts as too open when `mode & 077` is not zero. In the loader this is a test on `stat -c %a` without arithmetic on the decimal value (for example the last two digits are not `00`); in Python `stat.S_IMODE(st_mode) & 0o077`. The fix is `chmod 600`.

### The health check run skips the permission step
With `DOTFILES_ZSH_CHECK` set, the loader neither changes the mode nor prints. If the check run fixed the file, the message would go to the captured stderr, fail the check and never be seen; the real start afterwards would find nothing to report. Skipping keeps the message for the real start and keeps an open env file from sending the user to the bash fallback.

### `machine` fixes before any Bitwarden step
The fix runs first in `cmd_env_pull`, before the context, `bw` and unlock checks, so that it also happens in containers, without `bw` and with a locked vault. Each change is logged as `fixed permissions of ~/.env.local (664 -> 600)`.

## Risks / Trade-offs

- [The loader writes to a file during shell start] → only `chmod` on the user's own file in `$HOME`; a failure falls back to today's warning.
- [A user wants an env file group-readable on purpose] → not supported; the loader already warned on every start before this change.
- [Message on stderr in a non-interactive shell (`bash -c`, scripts using `get-password`)] → one line, only once per file, because the next start finds `600`.

## Migration Plan

None. The first shell start or `machine update` after the merge fixes existing files. Rollback: revert the commit; files stay at `600`.
