# Proposal

## Why

The owner keeps tokens and passwords in Bitwarden (for example a work user item with custom fields for the Artifactory, GitHub and Azure DevOps tokens) and already reuses them in `~/.env` through references. `~/.netrc` holds the same credentials for tools that read it, but it is kept by hand on each host, so a token rotated in Bitwarden has to be changed again in every `~/.netrc`. The owner wants `~/.netrc` generated from Bitwarden, with the same reference syntax as the env files, so a secret is kept once and Bitwarden is the source of truth.

## What Changes

- `machine env pull` also writes `~/.netrc` (mode 600) from the notes of the Bitwarden items `netrc/groups/<group>` (group per context, as for `env/groups/<group>`) and `netrc/hosts/<hostname>`; `machine setup` and `machine update` do it through the env pull. The notes hold ordinary multi-line netrc host blocks; a `login` or `password` value may be a reference `{{bw:<item name>/password}}`, `…/username}}` or `…/field:<NAME>}}`, resolved by the pull.
- A host block whose reference cannot be resolved (item or target missing) is skipped, so a missing secret never produces a half-filled entry; the pull names the host and records an attention item.
- The pull replaces an existing `~/.netrc` after a backup; Bitwarden is the truth.
- Same protection as for the env files: the pull remembers what it last wrote and does not overwrite unpushed local edits (changed, removed or new host blocks): it asks in a terminal (push, discard, skip) and otherwise leaves the file unchanged and records an attention item.
- `machine env push [--host]` also writes local edits of `~/.netrc` back to the item notes, or to the referenced item for a changed value of a referenced field; removals and conflicts are offered with "no" preselected.

## Capabilities

### New Capabilities

- `netrc-files`: generation of `~/.netrc` from Bitwarden items with references, skipping of unresolved host blocks, protection of unpushed local edits, and its push.

### Modified Capabilities

None.

Affected contexts: `work` and `private` (both read their group item; a missing item is skipped); devices: desktop and server. A container without context writes no `~/.netrc`.

## Impact

- Code: a new netrc sync module in `machine_cli` (parsing of host blocks, generation, last-generated state, push) called from `cmd_env_pull` and `cmd_env_push`, reusing the reference resolver and the Bitwarden item helpers of the env sync; `machine_cli/attention.py` (new attention items).
- Tests: `tests/unit/` netrc tests with a stubbed `bw`.
- Docs: `docs/secrets.md` (netrc items, reference use, push), `docs/git.md` (the `~/.netrc` note).
- Bitwarden vault: the owner creates `netrc/groups/work` (and `netrc/groups/private` where wanted) with the host blocks, using references to the work user item.
- Hosts: an existing hand-written `~/.netrc` is replaced after a backup, so hosts the owner wants must be in Bitwarden first.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/netrc-from-bitwarden` on branch `netrc-from-bitwarden`, because the change edits `machine_cli`, which `machine update` and the host's background update run, and `~/.netrc` changes how curl and git authenticate on the host.
