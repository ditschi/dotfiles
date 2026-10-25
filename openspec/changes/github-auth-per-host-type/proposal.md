# Proposal

## Why

On a private laptop the dotfiles checkout should use the SSH key that is already registered with GitHub, so pushing needs no token. Where a token is needed on private hosts, it is `GITHUB_TOKEN`. `GITHUB_PRIVATE_TOKEN` is only needed on work machines, where `GITHUB_TOKEN` is the work token by default. Today every host asks for `GITHUB_PRIVATE_TOKEN` for github.com, and the checkout is cloned over HTTPS, so a private laptop without that variable cannot push.

## What Changes

- `machine setup` switches the `origin` remote of the checkout from `https://github.com/<owner>/<repo>` to `git@github.com:<owner>/<repo>.git` on non-work profiles, when `ssh -T git@github.com` authenticates. Work machines and containers keep HTTPS.
- The token variable for github.com comes from a small machine-written file, `~/.config/git/github-token.gitconfig`, included by `private.gitconfig`: `GITHUB_TOKEN` on private profiles, `GITHUB_PRIVATE_TOKEN` on `work-machine`. The file is rewritten on every dotfile apply.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `git-config`: token variable per host type; SSH remote for the checkout on private hosts.

Affected profiles: all. Work machines keep their behaviour (`GITHUB_PRIVATE_TOKEN`, HTTPS).

## Impact

- `home/core/.config/git/private.gitconfig`, `machine_cli/dotfiles.py` (token file), `machine_cli/commands.py` (SSH remote in setup), tests, Readme.
