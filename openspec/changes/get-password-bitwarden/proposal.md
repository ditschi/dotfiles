# Proposal

## Why

`get-password` knows only the env files (`PASSWORD`) and the GNOME keyring. The owner wants it to use Bitwarden when Bitwarden is set up on the host, as recorded in investigation 5 of the archived change `baseline-env-secrets`. The passwords it serves get fixed Bitwarden item names, so that every host finds them the same way.

## What Changes

- `home/core/.local/bin/get-password [USERNAME]` gains Bitwarden as a password source, next to the env files and the GNOME keyring.
- Two Bitwarden item names are defined, both Bitwarden Login items with the password in the login password field:
  - `login/work/<user>`: the work account password (username = the user, `id -un` by default). Callers: Kerberos through `kinit-pw` and `work-net`, the VPN connect of `work-net`, `sudo` on work machines.
  - `login/home/hosts/<hostname>`: the local `sudo` password of a private host. Caller: the `update-system` alias in `home/core/.shell/common/aliases.sh`, which pipes `get-password` into `sudo -S`.
- `get-password` keeps its existing guarantees: no prompt, no unlock dialog, no blocking on a locked keyring; it now also never prompts for or unlocks Bitwarden.
- `docs/secrets.md` (item table) and `docs/features.md` (password line) describe the new source and items.
- The source order, keyring caching of a Bitwarden hit, how the item is chosen (work or home) and whether `bw` runs without `BW_SESSION` are open; see design.md "Open Questions". The delta specs are written so that they hold for any of the proposed answers, and are tightened once the owner decides.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kerberos-tokens`: "Password lookup" names Bitwarden as a further source after the env files; a new requirement defines how `get-password` reads Bitwarden without prompting or unlocking.
- `secret-tools`: a new requirement defines the Bitwarden item names and layout for the passwords `get-password` serves.

Affected contexts: `work` (work account password for Kerberos, VPN and `sudo`) and `private` (local `sudo` password for `update-system`). Devices: desktop and server; a container has no context, so whether it reads an item depends on the open question about choosing the item.

## Impact

- Code: `home/core/.local/bin/get-password`; possibly `home/work/.local/bin/work-net` (`keyring_sync`), depending on the caching question.
- Tests: `tests/unit/test_work_net.py` (the `get-password` tests) gets cases with stubbed `bw` and `secret-tool`.
- Docs: `docs/secrets.md`, `docs/features.md`.
- Dependencies: `bw` from the `core` mise group (spec `secret-tools`); no new tool, so no new shell completion.
- Bitwarden vault: the owner creates the items `login/work/<user>` and `login/home/hosts/<hostname>`.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/get-password-bitwarden` on branch `get-password-bitwarden`, because the change edits `get-password`, a script on `PATH` through the `$HOME` symlinks, which the host's shells, `kinit-pw`, `work-net` and the user timers call.
