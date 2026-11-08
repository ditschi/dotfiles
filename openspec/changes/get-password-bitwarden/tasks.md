# Tasks

Work only in the worktree `$(machine repo)/.worktrees/get-password-bitwarden` (see proposal.md).

## 1. Owner decisions

- [ ] 1.1 Ask the owner open questions 1 to 4 of design.md (source order, keyring caching, item choice, `bw` without `BW_SESSION`) and write the answers into design.md Decisions; verify that no question that changes behaviour is left under Open Questions.
- [ ] 1.2 Tighten the delta specs to the answers (order in "Password lookup", item choice in "Bitwarden password source", and, if caching goes through `work-net`, a MODIFIED "Keyring follows the env password"); verify with `openspec validate get-password-bitwarden --strict`.
- [ ] 1.3 Ask the owner open questions 5 to 8 (`bw sync`, `USERNAME` for the home item, duplicate items, capability) and record the answers; verify that design.md lists only still deferrable questions.

## 2. Bitwarden source in get-password

- [ ] 2.1 Add the Bitwarden step to `home/core/.local/bin/get-password` in the decided order and item choice: exact-name lookup, login password field, `--nointeraction`, its own timeout below the 15 s that `work-net` allows, skip without error on missing `bw`, locked vault, missing item; verify by running it with a stubbed `bw` on `PATH`.
- [ ] 2.2 If decided in 1.1, adapt `work-net keyring_sync` (`home/work/.local/bin/work-net`) so the keyring follows the password from `get-password`; verify with its tests in `tests/unit/test_work_net.py`.
- [ ] 2.3 Add tests in `tests/unit/test_work_net.py` with stubbed `bw` and `secret-tool`: source order, env wins, locked vault without prompt, missing item, missing `bw`, item choice per context, no value in stderr; verify with `pytest tests/unit/test_work_net.py -q`.
- [ ] 2.4 Update the error message of `get-password` to name all sources it tried (never values); verify with the failure-case test.

## 3. Documentation

- [ ] 3.1 Add `login/work/<user>` and `login/home/hosts/<hostname>` (Login items, password field, folders) to the item table in `docs/secrets.md`; verify the names match the `secret-tools` delta spec.
- [ ] 3.2 Update the password line in `docs/features.md` with the Bitwarden source, its order and the no-prompt rule; verify it matches the `kerberos-tokens` delta spec.

## 4. Validation

- [ ] 4.1 Run `pytest tests/unit/test_work_net.py tests/unit/test_zsh_handoff.py tests/unit/test_dotfiles_repo_default.py -q` (get-password, work-net and the files that reference `kinit-pw` and the aliases); verify all pass.
- [ ] 4.2 Run `pre-commit run --files <changed paths>` including untracked additions; verify all hooks pass.
- [ ] 4.3 Run `openspec validate get-password-bitwarden --strict`; verify it reports the change as valid.
- [ ] 4.4 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change modifies two capabilities (`kerberos-tokens`, `secret-tools`); fix the findings and rerun 4.1 to 4.3 after relevant edits.

## Workflow follow-up

- Manual check on a work host and a private host with the items created: `get-password` prints the expected password with an unlocked vault and falls back without a prompt with a locked one.
- Archive with `/opsx-archive` following the archive guidance in `openspec/config.yaml`.
