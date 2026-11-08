# Tasks

Work only in the worktree `$(machine repo)/.worktrees/env-bitwarden-references` (see proposal.md).

## 1. Owner decisions

- [x] 1.1 Confirm the assumptions in design.md (conflict default "no", push refuses without last-generated content) with the owner and move them to Decisions or revise the spec; verify that Assumptions lists nothing unconfirmed that changes behaviour.

## 2. Resolving references in the pull

- [ ] 2.1 Parse `{{bw:<item>/<target>}}` in note lines and custom field values in `machine_cli/env_pull.py`, resolve `password`, `username` and `field:<NAME>` by exact item name through `machine_cli/bw_client.py`, and write the quoted value after the `# KEY from Bitwarden …` comment; verify with unit tests using a stubbed `bw` (password, username, custom field, similar names, value with quotes and spaces).
- [ ] 2.2 Handle unresolved references (missing, ambiguous, missing or empty target): keep the previous value or leave the key out, warn without values, add an attention item in `machine_cli/attention.py`; verify with unit tests, including that stderr and the file never contain the reference text or another key's value.
- [ ] 2.3 Add the syntax hint to the generated header; verify with a unit test on the header and the existing header tests.

## 3. Protecting unpushed local edits

- [ ] 3.1 Store the last generated content per file (mode 600, owner-only state directory) and detect unpushed local edits (changed or missing keys from an item; added keys stay local-only); verify with unit tests for changed, removed and added keys.
- [ ] 3.2 Ask push / discard / skip (skip preselected) in a terminal, leave the file unchanged and record an attention item without a terminal or with `--yes`, and still generate the other file; verify with unit tests for each choice and for the non-interactive run.

## 4. machine env push

- [ ] 4.1 Add `push [--host]` to `machine env` in `machine_cli/machine`: sync, take the keys edited since the last pull, list them by name (references in clear, never values), refuse files with shell code and runs without last-generated content, confirm, write, then pull; verify with unit tests for add, change, declined confirmation and shell code.
- [ ] 4.2 Write changes into the item: append and replace note lines, update custom fields that set a key, and write a new value of a referenced key into the referenced item's target field; check all references before any write; verify with unit tests, including a reference typo that writes nothing.
- [ ] 4.3 Offer removals and conflicts with "no" preselected; verify with unit tests that Enter keeps the item unchanged, that the same new value on both sides is no conflict, and that keys changed only in Bitwarden are not written back.
- [ ] 4.4 Add shell completion for the new subcommand if `machine env` completion lists subcommands; verify with the existing completion tests, or note that none applies.

## 5. Documentation

- [ ] 5.1 Update `docs/secrets.md`: reference syntax, resolution and failure, the header hint, `machine env push`, unpushed local edits; remove "does not resolve references"; verify the wording matches the delta spec.

## 6. Validation

- [ ] 6.1 Run the env pull and attention unit tests touched in groups 2 to 4 and `pytest tests/unit -q`, because the update flow and attention items are shared infrastructure; verify all pass.
- [ ] 6.2 Run `pre-commit run --files <changed paths>` including untracked additions; verify all hooks pass.
- [ ] 6.3 Run `openspec validate env-bitwarden-references --strict`; verify the change is valid.
- [ ] 6.4 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the update flow and writes to the vault; fix the findings and rerun 6.1 to 6.3 after relevant edits.

## 7. Single work password in Bitwarden

- [ ] 7.1 On a work host, with `PASSWORD` referencing the Microsoft login item, try candidate (a) of investigation I1 (one login item with a `loginfmt` custom field) and record the owner's outcome in design.md; if the items are merged, change the reference with `machine env push`; verify that I1 has a recorded outcome, `get-password` returns the password and `openspec validate env-bitwarden-references --strict` passes.

## Workflow follow-up

- Owner: replace the literal `PASSWORD` in `env/groups/work` with a reference to the Microsoft login item, remove the temporary syntax hint from its notes, then run `machine env pull` on the work host and check that `get-password` and `work-net kerberos kinit` still work.
- Archive with `/opsx-archive` following the archive guidance in `openspec/config.yaml`.
