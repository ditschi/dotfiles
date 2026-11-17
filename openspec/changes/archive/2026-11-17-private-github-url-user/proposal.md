# Proposal

## Why

The owner needs a `machine github.com` entry in `~/.netrc` on work hosts, because the work devcontainer setup reads it. Curl sends a netrc entry for a host up front, so Git never asks its credential helper for that host: an HTTPS push to a personal repository (`ditschi/dotfiles`) then goes out with the work token and GitHub answers `403 … denied to dci2lr_bosch`. The owner wants both to work, the netrc entry for the devcontainers and the personal token for personal repositories.

## What Changes

- `private.gitconfig` sets `http.https://github.com/.proactiveAuth = basic`, so Git runs its credential helper before the first request and curl sends the helper's credentials instead of the `github.com` netrc entry. The helper serves the personal token (`GITHUB_PRIVATE_TOKEN` on work hosts, `GITHUB_TOKEN` otherwise) for personal owners and the work token for work owners, because the work owner rules include `work.gitconfig` after `private.gitconfig` as today.
- No owner is named: the rule follows the existing pattern "private unless it matches work".
- `docs/git.md` describes the rule next to the `~/.netrc` note.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `git-config`: Git asks the credential helper first for github.com, so a `github.com` netrc entry does not replace the configured credential.

Affected contexts: `work` (the problem occurs there with the netrc entry) and `private` (the rule is harmless and keeps one behaviour); all devices that use Git over HTTPS.

## Impact

- Code: `home/core/.config/git/private.gitconfig`.
- Tests: `tests/unit/` Git config tests (effective config for personal and work remotes).
- Docs: `docs/git.md`.
- Hosts: the next dotfile apply links the changed file; Git 2.46 or newer is needed for the key to take effect, older Git ignores it.

## Where the change is made

In the worktree `$(machine repo)/.worktrees/private-github-url-user` on branch `private-github-url-user`, because the change edits Git configuration that every shell and tool on the host reads.
