# Investigation report: baseline-git-config

Read-only research for the four investigations in the archived change `2026-10-22-baseline-git-config` (design.md). Nothing was changed in code. Decisions stay with the owner.

## 1. Credential helper layout

**Findings**
- `private.gitconfig` and `work.gitconfig` set `credential.username` and a per-host helper `!$HOME/.local/bin/git-credential-env <VAR>` for `https://github.com` and, for work, `https://github.boschdevcloud.com`. An empty `helper =` comes first, so helpers inherited from earlier config (notably `store`) are dropped for those hosts.
- Token variables: private `GITHUB_PRIVATE_TOKEN`, work github.com `GITHUB_TOKEN`, GHES `BDC_GITHUB_TOKEN`.
- `git-credential-env` answers only `get`, never stores, and exits quietly with a message on stderr if the variable is empty. It validates the variable name. If the variable is not in the environment it loads `~/.zsh/config/01_env.zsh` in `bash -c`, which covers GUI-started tools.
- Fallback concern: this runs the user's own loader file, so it is the same trust level as the shell. The variable name comes from the git config, not from the remote.
- Tests: `tests/unit/test_gitconfig.py` covers the helper reading `~/.env` when the environment is empty, and checks that `~/.git-credentials` is not created.

**Bitbucket (owner info)**
- Bitbucket (`sourcecode*.bosch.com`) is on-premises and can use SSH. The identity rules already cover the `ssh://` form, so no token helper is needed; the missing credential block is not a gap.

**Suggestion:** keep the layout. Use SSH remotes for Bitbucket.

## 2. Local `credential.helper=store`

**Findings**
- `create_dot_gitconfig.local.tmpl` writes `[credential] helper = store` on every profile. The alias `git store` writes the same line to `~/.gitconfig.local`.
- GitHub (private and work) and GHES are overridden by the snippets, so they never use `store`.
- Remotes that rely on it: any HTTPS remote (Bitbucket over HTTPS, if used) not matched by a snippet (for example Gitea, GitLab, homelab; Bitbucket over SSH is unaffected).
- If removed: those HTTPS remotes would prompt on every operation. SSH remotes and the matched hosts are not affected.
- `store` keeps tokens in plain text in `~/.git-credentials`.

**Suggestion:** keep `store` as the fallback only for hosts without a snippet, and consider a keyring helper (for example `libsecret`) as the safer fallback. Check first which HTTPS remotes you really use.

## 3. `user.useConfigOnly`

**Findings**
- Set in the shared file. The Readme states it stays shared, and unit tests check that the relocation keeps it shared.
- Effect: Git never guesses an identity from user name and host. If no `user.name` or `user.email` is configured, commit fails with "Author identity unknown" (verified in a clean home).
- In practice `~/.gitconfig.local` sets a default identity from the profile on every host, so the setting only matters when that file is missing or a repository removes the identity (`git user-unset-local`).

**Suggestion:** keep it. It is harmless today and protects fresh hosts where the local file does not exist yet.

## 4. Suspected legacy settings (`workdir`)

**Findings**
- `workdir` appears only in a comment in `home/dot_p10k.zsh` (a Powerlevel10k option text). It is not a Git setting in this repository.
- No other setting was identified as unused. A full audit of every key in `dot_gitconfig` was not done.

**Suggestion:** close this investigation for `workdir` (nothing to remove). Audit `dot_gitconfig` keys only if you name a concrete suspect.
