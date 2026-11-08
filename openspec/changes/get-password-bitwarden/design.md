# Design

## Context

See proposal.md for the motivation and scope.

Current state:
- `home/core/.local/bin/get-password [USERNAME]` (bash) prints `$PASSWORD` when set; otherwise it loads the env files through `home/core/.shell/common/envfiles.sh` and prints `PASSWORD` from them. Without an env password it reads `secret-tool lookup password <user>`, but only when the default keyring collection reports `Locked = false` over D-Bus, each call bounded by `GET_PASSWORD_KEYRING_TIMEOUT` (default 5 s). Otherwise it exits 1. It never calls `bw`.
- Spec `kerberos-tokens` "Password lookup" requires env first, then keyring, no prompt, no unlock dialog, no blocking on a locked keyring.
- Callers: `kinit-pw` (also from the Kerberos user timer), `work-net` (`kerberos kinit`, `vpn connect`, `keyring sync`; it runs `get-password` with a timeout of `3 * KEYRING_TIMEOUT` = 15 s), and the alias `update-system` in `home/core/.shell/common/aliases.sh`, which pipes `get-password` into `sudo -S`.
- `work-net keyring_sync` (`home/work/.local/bin/work-net`) writes the output of `get-password` into the keyring entry `password <user>` when the keyring is unlocked (spec `kerberos-tokens`, "Keyring follows the env password").
- Bitwarden: `bw` comes from the `core` mise group; `BW_SESSION` is optional and saved in `~/.env.local` only on opt-in (spec `secret-tools`). Since `get-password` loads the env files, a saved `BW_SESSION` is visible to it, also in services. `machine_cli/bw_client.py` finds items by exact name (`bw list items --search <name>`, then a name filter). `machine env pull`, `machine update` and the SSH commands run `bw sync`; nothing syncs on its own.
- Host context: `home/core/.shell/common/machine-profile.sh` exports `MACHINE_CONTEXT` (`private`, `work`, unset in a container without context) from the applied host config.
- Related investigations: archived `baseline-env-secrets` investigation 5, archived `baseline-kerberos` investigation 4, and `openspec/investigations/env-and-update.md` A5.

## Goals / Non-Goals

**Goals:**
- Bitwarden as a password source of `get-password` with the item names in the specs, keeping all its non-interactive guarantees.
- An ordering test with stubbed `bw` and `secret-tool`.

**Non-Goals:**
- Changing how `update-system` hands the password to `sudo -S` (A5 flags the plaintext pipe for a separate review).
- Writing or rotating the Bitwarden items from `machine`; the owner creates them in the vault.
- Changing the keyring attribute (`password <user>`) or the env-file loader.

## Decisions

**Bitwarden is a source of `get-password`.** The script itself reads Bitwarden; callers keep calling `get-password` unchanged.

**Item names and layout.** The work account password is the Bitwarden Login item `login/work/<user>`, with the user as its username (default `id -un`, or the `USERNAME` argument) and the password in the login password field. It serves Kerberos (`kinit-pw`, `work-net`), the VPN connect and `sudo` on work machines. The local `sudo` password of a private host is the Login item `login/home/hosts/<hostname>`, password in the login password field; it serves `update-system`. Names are matched exactly, as `machine_cli/bw_client.py` does for the other items. The investigation's placeholder `passwords/<profile>/<user>` was not taken.

**The non-interactive guarantees cover Bitwarden too.** `get-password` never asks for the master password, never logs in and never unlocks the vault; a Bitwarden failure means "no password from this source", and the next source is tried. This keeps the existing requirement of spec `kerberos-tokens` intact for timers and services.

## Risks / Trade-offs

- [`bw` starts slowly (Node.js), and `work-net` gives `get-password` only 15 s] → bound the Bitwarden step with its own timeout (for example `GET_PASSWORD_BW_TIMEOUT`) well below the caller's limit, and pass `--nointeraction` so `bw` never waits for input.
- [`bw` reads its local cache, which may lag behind a rotated password until the next `bw sync`] → see open question 5; a stale password can trip the Kerberos failure guard.
- [A wrong password sent to the KDC counts as an authentication failure] → the item choice must never fall back to another class's password (see open question 3).
- [Error output could leak the password] → never print values; messages name only the item and the source.

## Migration Plan

1. The owner creates `login/work/<user>` on the work account and `login/home/hosts/<hostname>` per private host (suggested folders: `work` and `home`, as in `docs/secrets.md`).
2. The change lands through `machine update`; hosts without Bitwarden or without the items behave as before, because the env files and the keyring keep working.
3. Rollback: revert the commit; `get-password` returns to env and keyring only. The items can stay in the vault.

## Open Questions

These are not decided by the owner. The recommendations are proposals only. Questions 1 to 4 change the delta specs or the tasks and must be answered before `/opsx-apply`; the specs are written to hold for every option until then.

1. **Source order.** Options: (a) `$PASSWORD` → Bitwarden → keyring; (b) `$PASSWORD` → keyring → Bitwarden (keyring as a fast cache); (c) an order per caller context (archived `baseline-kerberos` investigation 4). Recommendation: (a). Bitwarden is then the source of truth whenever it is readable, so a rotated password is picked up without a stale keyring entry sending the old one to the KDC. The keyring stays the fallback when the vault is locked. With (b), `work-net keyring_sync` would read the keyring entry back through `get-password` and could never refresh it from Bitwarden.
2. **Cache a Bitwarden hit in the keyring.** Options: (a) `get-password` stores it itself; (b) no caching in `get-password`, but `work-net keyring_sync` stores whatever `get-password` returns, which already happens when the keyring is unlocked; (c) no caching. Recommendation: (b), with order 1(a). `get-password` stays read-only, and work hosts get the keyring as an offline copy through the existing sync. The spec "Keyring follows the env password" would then be widened to "follows the password from `get-password`". Private hosts would have no cache, because `work-net` runs only on work hosts.
3. **Choosing the item (work or home).** Options: (a) from the host context: `work` → `login/work/<user>`, `private` → `login/home/hosts/<hostname>`, no context (container) → no Bitwarden lookup; (b) from which item exists, for example work first, then home; (c) an explicit option or variable chosen by the caller. Recommendation: (a). It needs one `bw` call, is predictable, and never hands the home `sudo` password to Kerberos or the VPN. `get-password` has to read the context itself (by sourcing `machine-profile.sh` or the applied host config), because services do not have the shell environment.
4. **`bw` without `BW_SESSION`.** Options: (a) call `bw` only when `BW_SESSION` is set after loading the env files, otherwise skip without a call; (b) always call `bw` with `--nointeraction` and treat a locked vault as "no password". Recommendation: (a), plus `--nointeraction` and a timeout. It saves the slow `bw` start on hosts without a session, matches "Expected Bitwarden" in spec `secret-tools`, and rules out a master-password prompt in a terminal. A stale `BW_SESSION` then fails quietly and falls through.
5. **`bw sync` before reading.** Recommendation: no sync in `get-password` (network, slow, called by timers); rely on the syncs in `machine update` and `machine env pull`. To be confirmed, because a rotated password reaches the host only after such a sync.
6. **`USERNAME` argument for the home item.** `login/home/hosts/<hostname>` is per host, not per user. Recommendation: ignore the argument for the home item and do not check the item's username field.
7. **Several items with the same exact name.** Recommendation: skip Bitwarden and print a warning on stderr that names the item (never a value), as an ambiguous item cannot be trusted.
8. **Capability of `get-password`.** It now also serves private hosts, while its requirements live in `kerberos-tokens`. Recommendation: keep them there in this change; move them into an own capability only if more callers appear.
