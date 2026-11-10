# Tasks

## 1. Device group items

- [x] 1.1 In `env_item_names()` (`machine_cli/profile.py`), append `env/groups/<group>-<device>` after the group item when `current_device()` is `desktop` or `server`; keep `ENV_GROUPS` (`machine_cli/core.py`) and the assertions in `tests/unit/test_machine_cli.py` valid; verify with unit tests of the item list for private desktop, private server, private container, work desktop, work server and no context.
- [x] 1.2 Verify with tests in `tests/unit/test_update_and_env.py` the scenarios "Pull on a private desktop", "Pull on a private server" and "Pull on a work server" (desktop item never requested from the fake `bw`), "Server item" and "Device item missing", and that "add to Bitwarden" from `~/.env` still targets the shared group item.
- [x] 1.3 Verify with a test that `machine env push` on a private desktop writes a changed `GITHUB_TOKEN` to `env/groups/private-desktop` ("Change the token on a desktop"); fix `env_push.py` only if the test fails.
- [x] 1.4 Document in `docs/secrets.md` the group and device items (item table, group paragraph after `ENV_GROUPS`), the order of moving a key (create the device item first, then remove it from the shared item), and that private servers do not get `GITHUB_TOKEN` while work hosts keep it; verify the text matches the spec delta.

## 2. Env sync follows Bitwarden

- [x] 2.1 In `env_local_only()` (`machine_cli/env_pull.py`), leave out keys that the last pull (`env_state_path`) wrote from a Bitwarden item and the current file holds unchanged, on every host, and log `removed <KEY> from <file> (no longer in Bitwarden)`; keys with a `# was in` origin in the local-only section and files without a last-pull record keep today's handling. Verify with tests for "Key moved in Bitwarden" (desktop keeps it, server drops it, `env_attention()` empty, no value in captured output), "Key deleted in Bitwarden on a desktop", a carried-over `# was in` key and a missing last-pull record; adjust existing tests such as `test_env_pull_remembers_keys_deleted_in_the_vault` to the modified "Skip is preselected" scenario.
- [x] 2.2 Verify with tests that "Edited locally, deleted in Bitwarden" leaves `~/.env` unchanged with an attention item, and that "Removed locally" makes `machine env push` offer the removal; fix `env_pull.py` or `env_push.py` only if a test fails.
- [x] 2.3 Write the backup of a pull without the lines removed because Bitwarden no longer sets them; verify with a test for "Backup after the token moved" (new backup has no `GITHUB_TOKEN=`).
- [x] 2.4 Update the local-only paragraph in `docs/secrets.md`: deleted in Bitwarden and unchanged locally → removed; edited locally → conflict; removed locally → `machine env push`; verify it matches the spec delta.

## 3. Validation

- [x] 3.1 Run `pytest tests/unit/test_update_and_env.py tests/unit/test_machine_cli.py tests/unit/test_dotfiles.py -q` (env pull/push, item names and the `GITHUB_TOKEN` credential helper consumer) and confirm they pass.
- [x] 3.2 Run `pre-commit run --files <changed paths>` including the change directory and confirm it passes.
- [x] 3.3 Run `openspec validate servers-without-github-token --strict` and confirm it passes.

## Workflow follow-up

- Owner, in Bitwarden: create `env/groups/private-desktop` with `GITHUB_TOKEN`, then remove the key from `env/groups/private` (after the servers run the new code).
- Run `machine update` on privatecloud, contabo, homeserver and netmaster and check `grep -c '^GITHUB_TOKEN=' ~/.env` prints 0 (key name only, no value).
- Archive the change.
