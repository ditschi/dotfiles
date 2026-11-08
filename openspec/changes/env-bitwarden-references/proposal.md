# Proposal

## Why

The work account password is kept several times in Bitwarden: in the login items used for browser autofill and as a literal `PASSWORD` in the notes of `env/groups/work`, from which `machine env pull` writes `~/.env`. After a password change every copy has to be updated by hand; a forgotten copy sends the old password to Kerberos and the VPN, and `work-net keyring sync` copies it into the keyring. The owner wants an env item to reference another Bitwarden item, so a secret is kept once, and wants to add or change such references, and other env values, from `~/.env` on the host instead of editing the notes in the Bitwarden web vault.

## What Changes

- An `env/…` item may hold, instead of a value, a reference to another Bitwarden item: `KEY={{bw:<item name>/password}}`, `…/username}}` or `…/field:<NAME>}}`. `machine env pull` resolves it and writes the value into `~/.env` or `~/.env.host`, with a comment naming the item. A reference that cannot be resolved keeps the previous value and records an attention item.
- The generated `~/.env` and `~/.env.host` start with a short comment that explains the reference syntax.
- New command `machine env push [--host]`: compares `~/.env` (or `~/.env.host`) with its Bitwarden item, shows added, changed and removed keys by name (references in clear, values never), checks every reference, and after confirmation writes the item's notes, then pulls. A new value for a referenced key is written into the referenced item's field. Removing keys is offered with "no" preselected.
- `machine env pull` no longer overwrites unpushed local edits: it remembers the last generated content, and when a file differs from it, it asks in a terminal (push, discard, skip) and otherwise leaves the file unchanged and records an attention item.
- `get-password`, `kinit-pw`, `work-net` and the keyring are unchanged; they keep reading `PASSWORD` from `~/.env`.
- This change replaces the earlier plan `get-password-bitwarden` (Bitwarden as a source of `get-password`), which the owner dropped (see design.md).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `env-files`: references in env items and their resolution, the syntax hint in the generated files, `machine env push`, and protection of unpushed local edits during the pull.

Affected contexts: `work` and `private` (both pull their group and host items); devices: desktop and server. A container without context pulls no env files and is unaffected.

## Impact

- Code: `machine_cli/env_pull.py` (resolution, header, last-generated state, push), `machine_cli/bw_client.py` (item field writes), the `machine env` command in `machine_cli/machine`, `machine_cli/attention.py` (new attention items).
- Tests: `tests/unit/` env pull tests with a stubbed `bw`.
- Docs: `docs/secrets.md` (reference syntax, push, local edits; drop "does not resolve references").
- Bitwarden vault: the owner replaces the literal `PASSWORD` in `env/groups/work` with a reference and removes the temporary syntax hint from its notes.
- Blocked by investigation I1 in design.md (store the work account password only once in Bitwarden).

## Where the change is made

In the worktree `$(machine repo)/.worktrees/env-bitwarden-references` on branch `env-bitwarden-references`, because the change edits `machine_cli`, which `machine update` and the host's background update run.
