# Design

## Context

See proposal.md for the motivation.

Current state:
- `~/.gitconfig` includes `private.gitconfig` for every github.com remote and, after it, `work.gitconfig` for work owners (`bosch-*`, `bosch_*`, `*_bosch`). Both are included for a work-owner repository; the later include wins.
- `private.gitconfig` sets `credential.https://github.com.username = ditschi`, drops inherited helpers and includes the machine-written token helper file.
- `~/.netrc` is generated from Bitwarden (spec `netrc-files`). An entry for `github.com` there makes curl send its credentials before Git runs a credential helper (see `docs/git.md`).
- Checked on the work host (2026-11-17, Git 2.56): `git push --dry-run` to `https://github.com/ditschi/dotfiles.git` gives `403 … denied to dci2lr_bosch`. The same push with `-c http.https://github.com/.proactiveAuth=basic` authenticates with the personal token, as does the `https://ditschi@github.com/ditschi/dotfiles.git` form.
- The pattern of the Git config is "private unless it matches work": every github.com remote includes `private.gitconfig`, the work owner rules include `work.gitconfig` after it, and the later include wins.

## Goals / Non-Goals

**Goals:**
- Personal HTTPS pushes work while `~/.netrc` has a `github.com` entry.

**Non-Goals:**
- Removing or changing the netrc entry (the owner needs it for the work devcontainers).
- A change to `work.gitconfig` (owner decision, 2026-11-17): work owners are covered by the rule in `private.gitconfig` and keep their own helper.
- A fix for a first `git clone` of a personal repository: no repository config exists yet, so the rule is not active and the netrc entry applies.

## Decisions

**`proactiveAuth = basic` in `private.gitconfig`** (owner decision, 2026-11-17). `[http "https://github.com/"] proactiveAuth = basic`. Git then runs the credential helper before the first request, so curl sends the helper's credentials and not the `github.com` netrc entry. The rule sits where the github.com credential configuration already is, so it follows the pattern "private unless it matches work" (owner decision): it applies to every github.com remote, and work owners use the work helper that `work.gitconfig` sets after it. No owner is named. Git before 2.46 ignores the key and behaves as before.

**Alternatives considered and rejected:**
- A URL rewrite (`insteadOf`) that puts the user `ditschi` into the URL: it also applies to work-owner repositories, a later include cannot undo it, and prefix matching cannot express the owner suffix `*_bosch`; scoped to one owner it would sit outside the pattern.
- Setting `origin` of one checkout to the user form: fixes only that checkout; the owner chose the general rule.
- Removing the `github.com` netrc entry: the work devcontainer setup needs it.
- Pushing over SSH: no key for personal GitHub on work hosts.

## Risks / Trade-offs

- [A host with Git before 2.46 does not get the fix] → the key is ignored there and pushes behave as today; hosts that need the netrc entry and personal pushes need a newer Git (the mise Git is 2.56).
- [Git asks the credential helper for every github.com request, also for public repositories] → the helper only reads an environment variable, so the cost is negligible; a host without a token fails as it would for a private repository.
- [A fresh `git clone https://github.com/...` is not covered] → no repository config exists yet; clone before the netrc entry exists, with `-c http.https://github.com/.proactiveAuth=basic`, or fetch afterwards; recorded as a non-goal.
