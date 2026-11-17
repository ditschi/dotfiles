# Design

## Context

See proposal.md for the motivation and the specs for the behaviour.

Current state:
- `machine env pull` (`machine_cli/env_pull.py`) generates `~/.env` and `~/.env.host` from `env/groups/<group>` and `env/hosts/<hostname>`, resolves `{{bw:<item>/<target>}}` references (`resolve_reference`, `bw_items_named`), backs up changed files under `~/.local/share/machine/env-backup/`, stores the last generated content per file under `~/.local/share/machine/env-generated/`, and protects unpushed local edits. `machine env push` (`machine_cli/env_push.py`) writes edits back to the item notes or to the referenced item.
- The groups per context come from `ENV_GROUPS` in `machine_cli/core.py` (`work` -> `work`, `private` -> `private`, no context -> none).
- `~/.netrc` is not managed. The owner keeps one by hand with a multi-line block per host (`machine <host>`, then `login …`, then `password …`); the hosts are internal Artifactory, source code and Azure DevOps servers.
- `machine env pull` is run by `machine setup` and `machine update`.
- `docs/git.md` notes that a `~/.netrc` entry for a host makes curl send credentials up front, so git credential helpers never run for it.

## Goals / Non-Goals

**Goals:**
- `~/.netrc` generated from Bitwarden with the same references as the env files, so a token is kept once.
- Same safety as the env sync: backup, no silent loss of local edits, no secret values in messages.

**Non-Goals:**
- Changes to the env sync or to `get-password`, `kinit-pw`, `work-net`.
- Other credential files (`~/.git-credentials`, `~/.pypirc`, `~/.npmrc`).
- Per-device items (`netrc/groups/<group>-<device>`).
- Keeping hand-written entries next to generated ones (there is no `~/.netrc.local`); Bitwarden is the truth (owner decision, 2026-11-16).

## Decisions

**Items and layout** (owner decisions, 2026-11-16). The templates are the notes of `netrc/groups/<group>` and `netrc/hosts/<hostname>`, written as in a real `~/.netrc`: one block per host, with `login` and `password` on their own lines. Values are literal or references; the reference syntax is that of the env files.

**Part of the env pull and push** (owner decision, 2026-11-16). `cmd_env_pull` also writes `~/.netrc`, so `machine setup` and `machine update` do it without a new step; `cmd_env_push` also pushes `~/.netrc` (`--host` selects `netrc/hosts/<hostname>`). There is no `machine netrc` command. The netrc part runs after the env files, and a failure in it does not stop the env sync.

**Both contexts** (owner decision). `work` reads `netrc/groups/work`, `private` reads `netrc/groups/private`; a context whose item is missing writes nothing. The group names reuse `ENV_GROUPS`.

**Pull and push work like the env sync** (owner decision). Backup, last generated content, push, discard or skip with skip preselected, and the push rules (confirmation, references checked first, removals and conflicts default to "no", no push without last generated content) are the ones of the env files; the unit is a host block instead of a key.

**An existing `~/.netrc` is replaced** (owner decision). The first pull after the change replaces a hand-written file after a backup; the owner moves the wanted hosts into Bitwarden first.

**Reference tokens are matched before splitting.** A netrc is split by whitespace, but item names contain spaces (`Bosch User -- DCI2LR`). The parser therefore reads a `{{bw:…}}` reference as one token and the rest by whitespace. `login`, `password` and `account` values may be references; `machine` and `default` may not.

**Blocks are the unit.** The parser cuts the notes at each `machine <host>` or `default` token. A block is written only when all its references resolve; otherwise it is skipped as a whole, because a block without its password would send the login alone.

**Resolved values stay literal and must be netrc-safe** (owner decision, 2026-11-16). `~/.netrc` has no shell syntax. A resolved value with whitespace, a quote, a backslash or a line break would be read differently by curl, git and Python, so it counts as unresolved (the block is skipped).

**Comments stay as in Bitwarden** (owner decision, 2026-11-16). Comment lines of the notes are written to `~/.netrc` unchanged.

**Skipped blocks are reported twice** (owner decision). A skipped block gets a notice and an attention item, as an unresolved env reference does.

**No usable item list, no write** (owner decision). When `bw` cannot list the items, `~/.netrc` stays unchanged instead of being emptied.

**`github.com` is warned about, and written** (owner decision). A block for `github.com` is written as given, with a warning that curl then skips the git credential helpers for it (see `docs/git.md`). Other hosts, such as `github.boschdevcloud.com`, get no warning.

**Pushed blocks go back to their item.** The pull records which item each written block came from, and which block of that item for a repeated machine (`netrc-generated/origins.json` in the state directory). A changed or removed block is edited in that item, so a block of the host item is not copied into the group item; only a new block goes to `netrc/groups/<group>`, or with `--host` to `netrc/hosts/<hostname>`. A changed value is matched to the item's tokens by position: a token that is a reference changes the referenced item's target, a literal changes the note, and a block whose token layout changed is rewritten as written locally.

**One file, host item first, content as in Bitwarden** (owner decision, 2026-11-16). A netrc has no include directive (curl and the other readers know only `machine`, `default`, `login`, `password`, `account`, `macdef`), so the two items are combined into one `~/.netrc`: the host item first, then the group item. The notes are written as they are, with only the references replaced. The pull does not merge, drop or reorder blocks, also not a machine that both items hold or a `default` block; how a repeated machine or `default` is treated is up to the tools that read the file. Because a machine may appear twice, a block is identified by its machine and, for a repeated machine, by its position (`host`, `host#2`).

**No usable block, no write** (owner decision). If no block can be written, `~/.netrc` stays unchanged instead of being emptied.

**Comments with references** (owner decision). A comment line that contains a reference is left out, so reference text is never written.

**Encoding** (owner delegated the choice, 2026-11-16). A `~/.netrc` that is not valid UTF-8 is read and written back byte for byte, so a pull or a backup never fails on it.

**Reuse, not copy.** The netrc module (a mixin like `EnvPullMixin`) calls `resolve_reference`, `bw_items_named`, `bw_edit_item`, `write_private` and the attention helpers. State is kept beside the env state: last generated content in `~/.local/share/machine/netrc-generated/`, backups in `env-backup/` as `netrc.<digest>`.

**Alternatives considered and rejected:**
- A separate `machine netrc pull|push` command: the owner chose to run it inside the env pull, so it follows the update flow without a new step.
- `KEY=value` lines mapped to hosts by the repository: the owner wants the same layout as the local `~/.netrc`.
- Keeping hand-written blocks beside generated ones: the owner wants Bitwarden to hold the truth.

## Risks / Trade-offs

- [A host listed for curl in `~/.netrc` overrides credential helpers for that host] → the owner decides which hosts go in; `github.com` gets a warning.
- [Curl before 7.84 does not read `#` comment lines] → the owner chose to keep comments; the owner removes them from the notes if a tool on a host misreads them.
- [A replaced hand-written `~/.netrc` loses a host] → the backup holds it and the pull names the backup; the owner adds the host to Bitwarden.
- [The stored last generated content holds secrets] → mode 600 in the owner-only state directory, like the env backups.
- [Skipping a block removes its access until the secret exists again] → the notice and the attention item name the host and the reason, never values.
- [Parsing netrc by hand misreads exotic input (`macdef`, quoted values)] → tokens the parser does not know are kept as written; the unit tests cover the owner's real layout.

## Migration Plan

1. The owner creates `netrc/groups/work` (and `netrc/groups/private` where wanted) in Bitwarden with the host blocks, using references to the work user item and its custom fields.
2. The change lands through `machine update`; the first `machine env pull` backs up the old `~/.netrc` and replaces it.
3. Rollback: revert the commit and restore `~/.netrc` from `~/.local/share/machine/env-backup/`.
