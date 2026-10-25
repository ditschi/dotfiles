# Design

## Context

`private.gitconfig` is included for every github.com remote. It resets the credential helpers (so tokens never land in `~/.git-credentials`) and adds `git-credential-env GITHUB_PRIVATE_TOKEN`. That suits work machines, where `GITHUB_TOKEN` is the work token, but on private hosts the token is `GITHUB_TOKEN`. `~/.gitconfig.local` cannot carry the choice: it is included before the owner rules, so `private.gitconfig` would reset its helper. See proposal.md for the motivation.

## Decisions

- **SSH for the checkout on private hosts (owner request).** The checkout uses the SSH key already registered with GitHub; no token is needed to push. Work machines keep HTTPS, because SSH to github.com is often blocked there and the work setup relies on tokens.
- **`GITHUB_TOKEN` on private hosts, `GITHUB_PRIVATE_TOKEN` on work machines (owner request).** On work machines `GITHUB_TOKEN` is the work token by default, so it must never be sent to private repositories; there is no fallback from one variable to the other.
- **Machine-written include file.** `private.gitconfig` keeps the reset and includes `~/.config/git/github-token.gitconfig` after it. `machine` writes that file from the profile on every dotfile apply, so a profile change also changes the variable. A missing file only means no token helper.
- **Switch only when SSH works.** `ssh -T git@github.com` (batch mode, no prompt) must authenticate before `origin` is changed, so a host without a registered key keeps a working HTTPS remote.
