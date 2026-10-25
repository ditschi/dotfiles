# Tasks

## 1. Token per host type

- [x] 1.1 Write `~/.config/git/github-token.gitconfig` on every dotfile apply (`GITHUB_PRIVATE_TOKEN` on `work-machine`, `GITHUB_TOKEN` otherwise) and include it from `private.gitconfig` after the helper reset. Verify unit tests for both profiles and `git config --get-all credential.https://github.com.helper` in a checkout.

## 2. SSH remote

- [x] 2.1 In `machine setup`, switch `origin` from `https://github.com/<owner>/<repo>` to `git@github.com:<owner>/<repo>.git` on non-work, non-container profiles when `ssh -T -o BatchMode=yes git@github.com` authenticates. Verify unit tests for switch, no SSH access and work machine.

## 3. Docs and checks

- [x] 3.1 Update the Readme credential section. Verify the text matches the behaviour.
- [x] 3.2 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `openspec validate github-auth-per-host-type --strict`. Verify all pass.
