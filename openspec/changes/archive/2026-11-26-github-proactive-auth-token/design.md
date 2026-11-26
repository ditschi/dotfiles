# Design

## Context

See proposal.md for the motivation.

Current state:
- `private.gitconfig` is included for every github.com remote (`includeIf hasconfig:remote.*.url`). It sets `credential.https://github.com.username = ditschi`, resets the helpers, includes the machine-written `github-token.gitconfig` (helper `git-credential-env GITHUB_TOKEN`, or `GITHUB_PRIVATE_TOKEN` on work hosts) and sets `http.https://github.com/.proactiveAuth = basic` (change `private-github-url-user`, 2026-11-17), so a `github.com` entry in `~/.netrc` does not replace the personal token.
- Checked on this host (2026-11-26, Git 2.56) with the repository's Git config files in a temporary HOME and no token: `git clone --depth 1 https://github.com/zsh-users/zsh-autosuggestions` runs the helper (the `hasconfig` rule is already active during a clone, contrary to the note in the earlier design), the helper prints its hint, Git asks for a password and exits 128 (`terminal prompts disabled`).
- With proactive auth Git passes `wwwauth[]=Basic` to the helper just as after a real 401, so the helper cannot tell the two cases apart.
- GitHub answers 401 to empty or wrong Basic credentials also for public repositories (anonymous: 200), so no placeholder credential can stand in for a missing token.
- The zsh plugin manager (antidote, `home/core/.shell/zsh/plugins.zsh`) clones antidote and the plugins from `https://github.com/...` at the first shell start and retries the bundle at every start while it fails. The `machine apply` health check runs `zsh -i` and fails on its stderr (CI run 44610448518, commit 0a3d695).
- Hosts: every host and container without a token in its environment or `~/.env*` is affected; hosts with the token behave as before.

## Goals / Non-Goals

**Goals:**
- Public github.com clones and fetches work without the token.
- Hosts with the token keep the personal token in front of a `github.com` netrc entry.

**Non-Goals:**
- Silencing the helper's hint: when GitHub asks for a credential and none is set, the hint is correct.
- A change to the health check: the errors were real.

## Decisions

**Proactive auth only with an available token** (owner decision, 2026-11-26). `machine` writes `[http "https://github.com/"] proactiveAuth = basic` into `github-token.gitconfig` when the token variable that the file names resolves to a non-empty value at apply time, in the same way the helper resolves it: the `machine` environment first, else the checkout's `home/core/.shell/common/environment.sh` sourced in Bash (it reads `~/.env*`). The checkout's loader is used because the first apply writes the file before `$HOME` is linked. Git config cannot depend on an environment variable at run time, so the decision is made at apply time. `machine update` pulls the env files before the dotfile apply, so a host that gets its token is covered on its next update. The setting moves out of `private.gitconfig`; because that file includes `github-token.gitconfig`, the setting still applies to every github.com remote, also to work owners, as before.

**Alternatives considered and rejected:**
- Making the helper quiet without a token: Git still asks for a password and the clone still fails.
- Proactive auth only with a `github.com` netrc entry (and the token): more conditions to keep correct for no practical gain; with the token proactive auth is harmless.
- Proactive auth per repository (e.g. `git user-private` or the dotfiles checkout): gives up the rule for every github.com remote.

## Risks / Trade-offs

- [A host gets its token after the apply] → proactive auth is off until the next apply; until then a `github.com` netrc entry wins for personal pushes, as before the earlier change.
- [A work host without `GITHUB_PRIVATE_TOKEN` but with the work netrc entry] → work-owner and public requests use the netrc credential; personal pushes fail as they would without a token anyway.
- [The token is removed after the apply] → proactive auth stays on until the next apply and public clones fail as today; the next apply drops it.

## Migration Plan

None: the next dotfile apply rewrites `github-token.gitconfig`.
