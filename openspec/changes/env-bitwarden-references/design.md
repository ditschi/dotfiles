# Design

## Context

See proposal.md for the motivation and scope.

Current state:
- `machine env pull` (`machine_cli/env_pull.py`) syncs Bitwarden, reads `env/groups/<group>` and `env/hosts/<hostname>`, turns each item into dotenv text (notes, then custom fields, which win) and writes `~/.env` and `~/.env.host` behind a generated header, one `# --- <item> ---` section per item. Changed files are backed up under `~/.local/share/machine/env-backup/`. Values are copied literally; `docs/secrets.md` says the pull does not resolve references to other items.
- The only write to Bitwarden is "add to Bitwarden" for a local-only key, which appends the line to the item's notes. Nothing replaces or removes a line, and there is no `machine env push`; `machine env` knows `pull` and `status`.
- A changed value of a key that an item sets is overwritten by the next pull, with a backup.
- `get-password` reads `PASSWORD` from the env files and falls back to the unlocked GNOME keyring; `work-net keyring sync` keeps the keyring equal to that password (spec `kerberos-tokens`).
- `machine_cli/bw_client.py` finds items by exact name and can create and edit items.

## Owner statements (2026-11-08)

- `get-password` is needed only on work machines, where `PASSWORD` already comes from Bitwarden through `machine env pull`, with the keyring as fallback. Reading Bitwarden in `get-password` brings no user-experience gain and risks extra logins (master password and second factor) after a session ends.
- The work account password is stored three times in Bitwarden: in the NT-user login item (needed by some work web sites), in a second login item for the Microsoft login (username = corporate e-mail address), and as a literal `PASSWORD` in the notes of `env/groups/work`. A custom field in the same item cannot replace the second item, because both logins need the same field names.
- `WAM_PASSWORD` is a different password of the same user that changes rarely; it is not a copy of the account password.

## Goals / Non-Goals

**Goals:**
- One place for a secret that an env item uses: a reference in the env item instead of a copy.
- Adding, changing and removing env values and references from the host, without the Bitwarden web vault.
- No local edit is lost silently by a pull.

**Non-Goals:**
- Any change to `get-password`, `kinit-pw`, `work-net` or the keyring sync.
- References in `~/.env.local`: the pull never rewrites it, so it stays literal.
- References that point to other references, and references to items of other vault accounts.
- Merging the two work login items; that is investigation I1.
- An editor command for item notes (`machine env edit`); see Open Questions.

## Decisions

**References are resolved by the pull, not at load time.** `~/.env` holds the resolved value; the shell, services and `get-password` never call `bw`. Bitwarden is read only in the pull, where the vault is unlocked anyway, so there is no additional login and an expired session keeps the last `~/.env` as today.

**Syntax.** `KEY={{bw:<item name>/<target>}}` with `<target>` = `password`, `username` or `field:<NAME>`, in note lines and custom field values. The owner accepted this syntax. Item names are matched exactly, as for the other items. The generated line is quoted and preceded by `# KEY from Bitwarden "<item>" (<target>)`; the comment is informational only, the pull acts on the value line.

**Unresolved reference: keep the previous value and record an attention item** (owner choice). A wrong or empty value never replaces a working one, and the shell never sees the reference text. Leaving the key out is used only when there is no previous value.

**Writing back is an explicit command, `machine env push [--host]`.** The owner preferred it over questions inside the pull: the pull stays one-directional apart from the existing local-only flow, and `machine update` asks nothing new. The push takes only the keys edited since the last pull (against the stored last-generated content), so a value changed in Bitwarden meanwhile is not written back; it shows keys and references but never values, checks every reference before writing anything, and pulls afterwards.

**A new value for a referenced key goes into the referenced item** (owner choice). Typing a new work password into `~/.env` and pushing changes the login item's password field, so browser autofill and `~/.env` stay on one value; the note keeps the reference.

**Removing keys is offered with "no" preselected** (owner choice), so an accidental Enter never deletes a key from Bitwarden.

**The pull protects unpushed local edits.** It stores the content it last wrote per file (owner-only, under `~/.local/share/machine/`). Changed or missing keys that this content set from an item are unpushed local edits. In a terminal the pull asks push / discard / skip, with skip preselected; without a terminal it leaves that file unchanged and records an attention item (owner choice), so a background update never discards an edit. Added keys keep the existing local-only flow, so a new reference can also go to Bitwarden through "add to Bitwarden"; the appended line is then resolved by the regeneration.

**Conflicts in the push** (owner choice). A key that both Bitwarden and the file changed since the last pull is a conflict only when the two new values differ; its question preselects "no", as for removals. The same new value on both sides needs no write.

**No push without a last-generated state** (owner choice). Before the first pull after the update the push refuses and names `machine env pull` as the next command.

**Syntax hint in the generated header.** Every generated file shows the syntax and names `machine env push`, so the owner can write a reference without looking it up. The temporary hint the owner placed in the notes of `env/groups/work` is removed when this change lands.

**Alternatives considered and rejected:**
- Bitwarden as a source of `get-password` (the earlier plan `get-password-bitwarden`): dropped by the owner; on work machines the env password always wins, so the source would never be used, and it would add a slow `bw` call and a session dependency.
- An encrypted `.env` in the repository with sops: the owner chose references after comparing both. A sops file keeps a second copy of the password next to the login items, so a password change would again need two edits.
- Questions about changed values inside every pull instead of a push command: replaced by `machine env push` (see above).

## Risks / Trade-offs

- [A reference in a local-only line without a terminal stays unresolved, so the shell sees the reference text] → the attention item and the pull notice name the key; `machine env pull` in a terminal resolves it.
- [The push writes into login items used for autofill] → only after confirmation, only the referenced field, and Bitwarden keeps the password history of login items.
- [The stored last-generated content holds secret values] → mode 600 in the owner-only state directory, like the env backups.
- [Concurrent edits on two hosts] → the push syncs first and writes only the keys edited locally since the last pull; a key changed on both sides is a conflict that needs its own confirmation (spec "Push conflicts").
- [Error output could leak a value] → messages name keys, items and targets only.

## Migration Plan

1. The change lands through `machine update`; items without references behave as before. The first pull after the update stores the last-generated content; until then no file has unpushed edits.
2. The owner replaces the literal `PASSWORD` in `env/groups/work` with a reference to the Microsoft login item and removes the temporary syntax hint from its notes. Until I1 is resolved, the NT-user login item keeps its own copy of the password.
3. Rollback: revert the commit. Items that contain references then reach `~/.env` as literal reference text, so the owner restores the literal values (the env backups hold them) before rolling back.

## Investigations

I1 does not block the implementation (owner decision): `PASSWORD` first references the Microsoft login item (e-mail address and password). If the two work login items are merged later, only the reference in `env/groups/work` changes, which `machine env push` does. I1 is the last task of this change and is tried on a work host.

I1. **Store the work account password only once in Bitwarden.** Bitwarden has no references between items (linked custom fields point only to fields of the same item), so the two work login items keep two copies. Candidates, none tested or decided:
   - (a) One login item for both accounts: username = NT user, password once, URIs of the NT sites and of the Microsoft login, plus a text custom field named `loginfmt` holding the e-mail address; the browser extension fills custom fields into inputs with the same `name`/`id`, and the Microsoft login's e-mail input is called `loginfmt`. To test: whether the extension fills the e-mail rather than the username into that input, and the limit that mobile autofill does not fill custom fields.
   - (b) Two login items kept equal by `machine`: the Microsoft item carries a marker field naming the source item, and `machine update` copies the password over with `bw edit`. Writes to the vault; the copies differ until the next update.
   - (c) Keep both items; only the `.env` copy goes away through references.
   Outcome needed: which candidate the owner takes. Candidate (b) needs its own change, because it adds a vault write to `machine update`.

## Open Questions

Deferrable; they change neither the specs nor the task breakdown.

1. `machine env edit [--host]`: open the item notes in `$EDITOR` through `bw`, check references on save, then pull. Useful for larger edits; a possible follow-up.
2. Whether company policy would have allowed an encrypted work `.env` in the private GitHub repository was not checked; it no longer affects this change.
