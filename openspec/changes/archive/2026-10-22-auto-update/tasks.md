## 1. Background job

- [x] 1.1 Extend `dotfiles-update-check-job` to run the resolvers, classify the incoming changes and decide: apply, pending, or needs-attention
- [x] 1.2 Apply home-only changes automatically (pull and chezmoi apply) and record the applied revision in the state
- [x] 1.3 Walk incoming commits in order and fast-forward only to just before the first commit touching `ansible/**`, packages or the host profile; leave the rest pending
- [x] 1.4 Decide and implement the safety net (health check and revert)

## 2. Units

- [x] 2.1 Review timer and service settings (interval, `Persistent`)

## 3. Validation

- [x] 3.1 Unit tests: clean home-only, system pending, home commits before a system commit, blocked by local changes, diverged history
- [x] 3.2 Update the Readme
- [x] 3.3 `pre-commit run --all-files` and `pytest tests/unit -q`
