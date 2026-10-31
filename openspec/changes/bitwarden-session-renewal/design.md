# Design

## Context

`unlock_bitwarden` already re-unlocks an invalid saved session on a terminal, but it asks "Log in now?" when logged out, and the paths that must not prompt (`bitwarden_session_ready`, used by the SSH key check, the SSH host list and the setup offer) give up with a warning. The background update calls no `bw` at all, so an expired session stays unnoticed until the user runs something by hand.

## Goals / Non-Goals

**Goals:** one notion of "Bitwarden expected", renewal without a yes/no question in a terminal, a visible needs-attention signal without a terminal.

**Non-Goals:** installing `bw` where it is missing (aarch64, separate change); storing a session for hosts that never opted in.

## Decisions

**Expected = a `BW_SESSION` in the environment or in `~/.env.local` (owner decision).** A user who saved or exported a session has set Bitwarden up and expects it to be used. Hosts without one are not nagged.

**Renew at once in a terminal (owner decision).** No yes/no question: the master-password prompt of `bw unlock` (or the login when logged out) starts directly; Ctrl-C or a failed unlock lets the run go on without Bitwarden. Rejected: a "log in now? [Y/n]" question first - one more key press for the common case.

**`bw status` in the background update (owner decision).** It is local, changes nothing in the vault and is called only on hosts that expect Bitwarden. It relaxes "the background update does not call `bw`" to exactly this call. Rejected: noticing it only in manual runs without a terminal - the background update is the run that happens regularly.

**Separate state file and prompt segment.** The update state (`~/.dotfiles-update-state`) is rewritten by every update step, so a Bitwarden notice there would be overwritten or would block updates. Like the disk segment, `machine` writes `bitwarden-state` (`segment=...`) in the state directory and the shell reads it with builtins only; Starship shows it next to the disk segment.

**Renewed session replaces the saved one.** Opt-in already happened when the session was saved; asking again on every renewal would defeat the purpose.

## Risks / Trade-offs

- [A wrong master password in an interactive run] → the run continues without Bitwarden and the item is recorded, as before.
- [`bw status` hangs without network] → it reads local data only; no timeout is added.
