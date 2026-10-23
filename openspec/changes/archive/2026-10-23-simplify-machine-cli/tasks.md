# Tasks

## 0. Event log

- [x] 0.1 Add an `events` module that appends JSON Lines to `events.jsonl` in `MACHINE_STATE_DIR`, never raises, drops the oldest lines above a 5 MiB cap and stores no secrets or paths. Verify unit tests for append, size cap, unwritable directory and field whitelist.
- [x] 0.2 Record the automatic update outcome (including the revert and its reason), manual update and `--force`, subcommand usage and `env`/`ssh` failures. Verify a unit test per event and that the `update-flow` safety-net tests still pass.

## 1. CLI toolkit and prompts

- [x] 1.1 Compare `cyclopts` and `click` with `argcomplete` on bash and zsh completion for every subcommand, option and the `--limit` host names; record the choice and reasons in `design.md`. Verify `machine completion bash|zsh` output sources without errors in both shells.
- [x] 1.2 Port the `machine` script to the chosen toolkit, remove the private `typer` imports, the completion patches and the exact pin. Verify `grep -rn "_completion" machine_cli/machine` finds nothing and `pytest tests/unit/test_machine_cli.py -q` passes.
- [x] 1.3 Replace `choose`, `choose_many` and `prompt_yes_no` in `machine_cli/system.py` with the toolkit's prompts, or remove `questionary` if no longer needed. Verify the prompt-related unit tests pass and no unused dependency remains in the script's inline metadata.

## 2. Bitwarden split

- [x] 2.1 Extract a small `bw` client (status, unlock, get item, list, upsert item) from `machine_cli/bitwarden.py`. Verify existing tests in `tests/unit/test_bw_and_answers.py` pass against the client with stubbed `bw`.
- [x] 2.2 Move `env pull` and the SSH-key functions into their own modules that use the client; delete setup, status and settings-saving code that no command reaches, after checking each with `grep` and the tests. Verify `machine env pull`, `machine env status` and `machine ssh publish|restore` behave as before in the unit tests, and `BW_SESSION` storage stays opt-in (`secret-tools` scenarios).
- [x] 2.3 Verify no module in `machine_cli/` references the removed functions and `pytest tests/unit -q` passes.

## 3. Local-overrides helper

- [x] 3.1 Implement the helper for shared files: list lines that differ from the repository version, let the user select, store selected text between marker comments in the `.local` file with a backup, then remove it from the shared file. Verify with unit tests for the `local-overrides` scenarios (new addition, nothing selected, first move, interrupted move).
- [x] 3.2 Implement removal of known text and the conflict report for diverging text, including Git keys with a different value (equal value is moved). Verify unit tests for "tooling adds the same block again" and "block changed by tooling".
- [x] 3.3 Move `.bashrc` externally managed block handling onto the helper and delete `relocate_managed_blocks` and its callers. Verify the existing `.bashrc` relocation tests pass against the helper and `~/.bashrc` still starts without `~/.bashrc-local`.
- [x] 3.4 Move host-only Git key handling onto the helper, replace `machine/gitconfig.py` in `.pre-commit-config.yaml` and `.github/workflows/verify.yml`. Verify `tests/unit/test_gitconfig.py` cases pass for the helper, `pre-commit run --all-files` passes and CI fails when a host-only key is added to `home/dot_gitconfig`.
- [x] 3.5 Update `Readme.md` and the `home/` comments that mention the old resolvers. Verify no document refers to `machine/gitconfig.py` or the resolvers.

## 4. Final checks

- [x] 4.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and, for the Docker tests listed in the Readme "Tests" section, the CLI-related ones. Verify all pass.
- [x] 4.2 Run `openspec validate simplify-machine-cli --strict` and verify it passes.

## Workflow follow-up

- Archive this change before `adopt-mise`, which builds on the toolkit and the local-overrides helper and holds the update-flow simplification and `machine attention`.
- Use the `events.jsonl` data to decide whether the automatic revert is still needed (separate follow-up, not part of this change).
- Archive the change after review.
