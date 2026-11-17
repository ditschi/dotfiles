# Tasks

Work only in the worktree `$(machine repo)/.worktrees/netrc-from-bitwarden` (see proposal.md).

## 1. Owner decisions

- [x] 1.1 Get the owner's answer to Assumption A4 in design.md; move it into Decisions and adjust the spec and the tasks below if the answer differs from the assumption; verify that Assumptions lists nothing unconfirmed that changes behaviour and `openspec validate netrc-from-bitwarden --strict` passes.

## 2. Pull

- [x] 2.1 Parse netrc notes into host blocks (reference tokens with spaces read as one token, `machine` and `default` as block starts, comment lines kept) in a new `machine_cli/netrc_sync.py`; verify with unit tests on the owner's multi-line layout, an item name with spaces and a `default` block.
- [x] 2.2 Generate `~/.netrc` from `netrc/groups/<group>` and `netrc/hosts/<hostname>` with the env reference resolver: host block of the host item wins, blocks with unresolved or non-netrc-safe values are skipped, nothing is written without a usable item list, mode 600, backup of the previous file, last generated content stored; verify with unit tests using a stubbed `bw` (password, username, field, missing field, ambiguous name, value with a space, host item override, no items, locked vault, `github.com` warning without a warning for an enterprise host).
- [x] 2.3 Call the netrc part from `cmd_env_pull` after the env files (a failure there does not stop the env sync) and add attention items for skipped blocks in `machine_cli/attention.py`; verify with unit tests that the existing env pull tests still pass, that the attention item and all messages contain no values and that an unattended run with a locked vault exits 0.
- [x] 2.4 Protect unpushed local edits (changed, removed, added blocks): ask push, discard or skip with skip preselected in a terminal, leave the file unchanged with an attention item otherwise; verify with unit tests for each choice and the unattended run.

## 3. Push

- [x] 3.1 Push `~/.netrc` from `cmd_env_push` (`--host` selects the host item): compare with the last generated content, list blocks by machine name (never values), skip the file without last generated content, confirm, append and replace block text in the item notes, then pull; verify with unit tests for a new block, a changed literal value, a declined confirmation and a push before any pull.
- [x] 3.2 Write a changed value of a referenced `login` or `password` into the referenced item's target and keep the reference in the notes; check all references before any write; verify with unit tests, including a reference typo that writes nothing.
- [x] 3.3 Offer removals and conflicts with "no" preselected; verify with unit tests that Enter keeps the item unchanged, that the same new value on both sides is no conflict and that a block changed only in Bitwarden is not written back.
- [x] 3.4 Confirm that no new subcommand is added, so the `machine env` completion needs no change; verify with the existing completion tests.

## 4. Documentation

- [x] 4.1 Document `netrc/groups/<group>`, `netrc/hosts/<hostname>`, the block layout with references, skipped blocks, local edits and the push through `machine env push` in `docs/secrets.md`, and update the `~/.netrc` note in `docs/git.md`; verify the wording matches the spec.

## 5. Validation

- [x] 5.1 Run `pytest tests/unit/test_netrc_sync.py tests/unit/test_update_and_env.py -q`, then `pytest tests/unit -q`, because attention items and the machine command are shared infrastructure; verify all pass.
- [x] 5.2 Run `pre-commit run --files <changed paths>` including untracked additions; verify all hooks pass.
- [x] 5.3 Run `openspec validate netrc-from-bitwarden --strict`; verify the change is valid.
- [x] 5.4 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the update flow and attention items and writes to the vault; fix the findings and rerun 5.1 to 5.3 after relevant edits.

## Workflow follow-up

- Owner: create `netrc/groups/work` (and `netrc/groups/private`) in Bitwarden with the host blocks and references, run `machine env pull` on a work host, and check that curl and git still authenticate to the listed hosts.
- Archive with `/opsx-archive` following the archive guidance in `openspec/config.yaml`.
