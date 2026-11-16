# Design

## Context

See proposal.md for the motivation. Observed state:

- The CI agents are one `Host` block in `~/.ssh/config.d/20-work`, generated from the Bitwarden note `ssh/work/config`, with `User ci-user-a` and `IdentityFile ~/.ssh/id_ed25519_ci-user-a`. A block for the second group of agents with `User ci-user-b` is to be added there with `machine ssh edit`. (Real user and vault names stay out of the repository; `ci-user-a` and `ci-user-b` stand for the two technical users.)
- `~/.env` is generated from `env/groups/work` (spec `env-files`); `machine` itself does not load it, so reading `AZKV_TECHUSERS` needs the process environment or a parse of the env files.
- OpenSSH reads the askpass program from `SSH_ASKPASS` and, since 8.4, honors `SSH_ASKPASS_REQUIRE`; the SSH config cannot set environment variables.
- `~/.local/bin` is prepended to `PATH` by `.profile` and `.zprofile`; `home/core/.shell/common/environment.sh` and `home/core/.shell/zsh/options.zsh` append it again, which does not move it behind an earlier entry.
- `machine` already has the pieces the sync needs: `bitwarden_session_ready`, `bw_items_named`, `bw_edit_item`, the `Steps` runner and `AttentionItem`.

## Goals / Non-Goals

**Goals:**
- Live password lookup for ssh, no password stored on disk or in the environment.
- Scoped to the technical users, also for `scp`, `rsync`, `git` and `ssh-copy-id`.
- Bitwarden items follow Key Vault.

**Non-Goals:**
- Installing the SSH key on the agents (use `ssh-copy-id`).
- Creating Bitwarden items, or syncing in the background update.
- Other Key Vault secrets, other users, other contexts than `work`.

## Decisions

**Wrapper instead of a global askpass (owner decision, 2026-11-13).** The `work` group links `~/.local/bin/ssh`. It finds the real `ssh` as the next `ssh` on `PATH` that is not itself, runs `ssh -G "$@"` (config resolution only, no connection), reads the `user` line, and compares it with `AZKV_TECHUSERS`. On a match it exports `SSH_ASKPASS`, `SSH_ASKPASS_REQUIRE=prefer` and `AZKV_ASKPASS_USER`, then `exec`s the real `ssh`; otherwise it unsets `AZKV_ASKPASS_USER` and `exec`s unchanged. Because `ssh -G` reflects the config, the scope is defined by the `User` of the host blocks, with no host list in the wrapper. Hops through `ProxyJump` start `ssh` through `PATH` again and so are evaluated on their own. A caller's own `SSH_ASKPASS` is never replaced, so editors that supply one keep working. If `-G` fails, the real `ssh` runs unchanged.

**The wrapper names the user; the helper does not parse the prompt.** Hosts may ask for the password by keyboard-interactive (`Password:`) instead of `user@host's password:`. Passing the user in `AZKV_ASKPASS_USER` makes the helper independent of the prompt wording. The helper answers a prompt only if it asks for a password and not a passphrase; anything else goes to the terminal with echo off for secrets and on for yes/no questions.

**Mapping in `env/groups/work` (owner decision, 2026-11-13).** `AZKV_TECHUSERS="<user>=<vault>/<secret> ..."`; the vault name expands to `https://<vault>.vault.azure.net`. The Bitwarden item that the sync updates is named like the user. Both consumers (helper at ssh time, sync) read the same key; `machine` reads the env files `~/.env`, `~/.env.host`, `~/.env.local` first, because the env pull has just written them, and the process environment only when no file sets the key. Nothing is executed. The vaults are in the public cloud (`<vault>.vault.azure.net`) and the existing `az` login reads both without a subscription option (owner decision, 2026-11-13).

**The helper answers only a prompt that names the resolved account.** `SSH_ASKPASS` and `AZKV_ASKPASS_USER` are inherited by child processes such as a `ProxyJump` hop. OpenSSH names the account in password prompts (`user@host's password:`, `(user@host) Password:`), so a prompt for another account, a password change, a passphrase or a confirmation goes to the terminal. A confirmation is reported through the exit status, an informational message is only shown.

**One password attempt.** The wrapper adds `-o NumberOfPasswordPrompts=1` for technical users, so a wrong Key Vault password is not sent three times (lockout risk). A mistyped terminal fallback password then needs a new `ssh` call.

**Quotes in the value are tolerated.** The shell loader exports plain `KEY=value` env files literally, quotes included, so the wrapper and the helper strip `"` and `'` from `AZKV_TECHUSERS`; the sync parses the file with `shlex`.

**Live lookup, nothing stored.** The helper runs `az keyvault secret show --id <url> --query value -o tsv` for each password prompt. It costs a second or two, and `ControlMaster` reuses the connection afterwards. The password goes from `az` to ssh through a pipe; no file, no argument, no environment variable holds it.

**Key Vault always wins, silently (owner decision, 2026-11-13).** The sync overwrites a differing Bitwarden password without asking. Bitwarden normally keeps the previous value in the item's password history, which would be the way back; this was not verified for `bw edit`.

**Existing items only.** The owner named the items after the two users (assumed to be login items that exist). Creating items would be a choice the owner has not made, so a missing item is reported.

**Manual update and explicit command only.** Specs `ssh-client-config` and `secret-tools` keep the background update away from Bitwarden; the sync follows that. A missing `az` login is an attention item, like an expired Bitwarden session.

**Sync before the env pull (owner decision, 2026-11-13).** Env items may reference the login items (`{{bw:<user>/password}}`), which the pull resolves. Fetching Key Vault into Bitwarden first makes the pulled value current in the same update, with no second pull. The mapping is read from the env files of the previous pull, so a user added to `AZKV_TECHUSERS` is synced from the update after the pull that brought the entry. In a terminal the sync logs in to or unlocks Bitwarden itself, so the pull finds the session.

**No key-install helper (owner decision, 2026-11-13).** `ssh-copy-id` tests which keys are accepted, falls back to the normal login (the password then comes from the wrapper) and appends the key to the account it logged in as. It is documented instead of wrapped.

**Alternatives offered and not chosen:**
- Global `SSH_ASKPASS` in the work environment with a tty fallback: would route every prompt of every connection through the script.
- A separate command (`ssh-ci`): would not cover `scp`, `rsync`, `git` and `ssh-copy-id`.
- Mapping in a Bitwarden note: the helper would need an unlocked `bw` when ssh runs.
- Asking for every differing password in the sync: not chosen; Key Vault is the truth.
- The password itself in `~/.env`: exported to every process, and stale like the Bitwarden copy.

## Risks / Trade-offs

- [The wrapper only works when `~/.local/bin` comes before the real `ssh` in `PATH`] → a task checks `command -v ssh` in bash and zsh login and non-login shells; the docs name the check.
- [A wrapper named `ssh` can recurse] → the real `ssh` is the next `ssh` on `PATH` that is not the wrapper (compared by resolved path), and the wrapper fails with a clear message if none exists.
- [Agents that ask for the password by another method than password or keyboard-interactive] → not answered; ssh falls back to the terminal. A probe of one agent showed `publickey,password` (owner-requested check, 2026-11-13), so the helper's `user@host's password:` case is the one in use; keyboard-interactive is handled in addition.
- [Key Vault firewall or private endpoint needs the corporate network or VPN] → the helper falls back to the terminal with a one-line reason; the sync skips and records an attention item.
- [`az` startup adds latency to each password login] → accepted; one call per password prompt.
- [A shared terminal or process listing could expose the password] → it never appears in argv or files; it is only on a pipe between helper and ssh.

## Open Questions

### Q3 Live check of the helper on an agent
The helper is covered by unit tests with a fake `az` and `ssh`. A real run needs the Key Vault password of an agent, so it is left to the owner.
1. (recommended) Owner runs `ssh <agent>` on an agent without the key authorized and confirms the password is not asked - then 3.1 is closed
2. Skip the live check

Answer:
