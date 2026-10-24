# Tasks

## 1. opencode

- [x] 1.1 Add `opencode = "latest"` to `home/core/.config/mise/conf.d/30-llm.toml` and add its entry to the lockfile. Verify `python3 -m machine_cli.mise_check` passes and the lock pins `npm:@opencode/cli` for linux-x64 and linux-arm64.
- [x] 1.2 Name opencode in the Readme tool list. Verify no PATH export for `~/.opencode/bin` or `~/.npm-global/bin` is in the repository.

## 2. Checks

- [x] 2.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate opencode-via-mise --strict`. Verify all pass.
