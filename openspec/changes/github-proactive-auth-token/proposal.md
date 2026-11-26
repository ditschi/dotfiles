# Proposal

## Why

On a host without the GitHub token (a fresh container, the APT integration tests in CI, a host before its first `machine env pull`), Git cannot reach public github.com repositories over HTTPS. `private.gitconfig` sets `http.https://github.com/.proactiveAuth = basic` for every github.com remote, so Git demands a credential before the first request; the helper has none, Git asks for a password and fails without a terminal. The zsh plugin manager clones its plugins from github.com at the first shell start, so the shell start prints `git-credential-env: GITHUB_TOKEN is not set` and Git errors, the plugins stay missing, and the `machine apply` health check fails (CI jobs `apt-rpi-zero (26.04)` and `apt-home-laptop`). A missing token must not break public clones; it should only matter when GitHub actually asks for a credential.

## What Changes

- `machine` writes `http.https://github.com/.proactiveAuth = basic` into the generated `~/.config/git/github-token.gitconfig` only when the host's GitHub token variable is set at apply time (environment, or `~/.env*` through the shell environment loader of the checkout).
- `private.gitconfig` no longer sets `proactiveAuth` itself.
- Without the token, Git clones and fetches public github.com repositories anonymously and asks the credential helper only after GitHub answers 401; the helper's hint about the missing variable stays for that case.
- `docs/git.md` describes the condition.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `git-config`: the requirement "Credential helper before netrc for github.com" applies only when the token is available; a new requirement covers anonymous access without the token.

Affected contexts: `private` and `work`, all devices; in practice hosts without the token (containers, fresh hosts, CI).

## Impact

- Code: `machine_cli/dotfiles.py` (token config rendering), `home/core/.config/git/private.gitconfig`.
- Tests: `tests/unit/test_dotfiles.py`, `tests/unit/test_gitconfig.py`; the APT host-yaml integration test covers the clean install.
- Docs: `docs/git.md`.
- Hosts: the next dotfile apply rewrites `github-token.gitconfig`. A host that gets its token later gets proactive auth on the next apply (`machine update` pulls the env files before it applies the dotfiles).

## Where the change is made

In the worktree `$(machine repo)/.worktrees/github-proactive-auth-token` on branch `github-proactive-auth-token`, because the change edits Git configuration that every shell and tool on the host reads.
