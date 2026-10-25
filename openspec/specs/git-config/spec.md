# git-config Specification

## Purpose
Defines the layers of Git configuration, how the identity is chosen and which settings stay host-local.

## Requirements

### Requirement: Shared Git config
`~/.gitconfig` SHALL be a symlink into the repository and identical on all hosts. It SHALL hold the shared defaults (`push.default=current`, `pull.rebase`, `fetch.prune`, rerere, `init.defaultBranch=main`, meld, delta as diff pager and LFS) and the aliases, so that `git config --global alias...` changes the shared file.

#### Scenario: Adding a global alias
- **WHEN** a user runs `git config --global alias.x ...`
- **THEN** the change lands in the repository file and syncs to other hosts with the dotfiles

#### Scenario: delta installed
- **WHEN** a user runs `git diff` or `git show` and delta is installed
- **THEN** the output is shown through delta

#### Scenario: delta not installed
- **WHEN** a user runs `git diff` on a host without delta
- **THEN** the output is shown through `less` (or printed plainly without `less`) and no error appears

### Requirement: Host-local Git config
`~/.gitconfig.local` SHALL be host-local and not versioned. `machine setup` SHALL create it once from the profile (default identity from the profile, and `safe.directory` on work and container profiles) when it does not exist, and nothing SHALL overwrite it afterwards. Git SHALL treat a missing file as empty, so a host without the file works.

#### Scenario: Update on an existing host
- **WHEN** `machine setup` or `machine update` runs and `~/.gitconfig.local` exists
- **THEN** the file is left unchanged

#### Scenario: Existing work host without the CA bundle key
- **WHEN** the dotfile apply runs on a work host whose `~/.gitconfig.local` has no `http.sslCAInfo`
- **THEN** only that key is appended (the user-space Git ignores the system CA store) and nothing else in the file changes

#### Scenario: First setup
- **WHEN** `machine setup` runs on a host without `~/.gitconfig.local`
- **THEN** the file is created with the identity of the profile

#### Scenario: File missing later
- **WHEN** the file is deleted and Git runs before the next setup
- **THEN** Git reports no error

### Requirement: Identity by remote owner
Git SHALL choose the work or private identity from the remote URL through `includeIf "hasconfig:remote.*.url:..."` rules: any github.com remote selects `private.gitconfig`, and github.com `bosch-*` or `bosch_*` owners, GHES and Bitbucket `sourcecode*` remotes select `work.gitconfig`. The rules SHALL NOT depend on the clone path. This needs Git 2.36 or newer.

#### Scenario: Private GitHub repository
- **WHEN** a repository has a github.com remote of another owner
- **THEN** the private identity is active

#### Scenario: Work remote
- **WHEN** a repository has a GHES or Bitbucket `sourcecode*` remote
- **THEN** the work identity is active

### Requirement: Per-repository override
A user SHALL be able to override the identity in one repository with `git user-work` or `git user-private`, undo it with `git user-unset-local`, and show the identities with `git user-show`.

#### Scenario: Forcing the work identity
- **WHEN** a user runs `git user-work` in a repository
- **THEN** the repository-local include selects the work identity and wins over the owner rules

### Requirement: Host-only keys stay out of the shared file
Host-only keys (identity, signing, `safe.*`, `credential.*`, `http(s).*`, `core.sshCommand`) SHALL be kept out of the shared file. `machine update`, `machine commit` and a pre-commit hook SHALL move them to `~/.gitconfig.local` through the local-overrides helper.

#### Scenario: Host-only key in the shared file
- **WHEN** a host-only key appears in the shared file
- **THEN** the check fails and the tooling moves it to `~/.gitconfig.local`

#### Scenario: Key re-added with the same value
- **WHEN** a host-only key reappears in the shared file with the value already in `~/.gitconfig.local`
- **THEN** it is removed from the shared file without asking

#### Scenario: Key re-added with a different value
- **WHEN** a host-only key reappears in the shared file with a value that differs from `~/.gitconfig.local`
- **THEN** the local value is kept, a conflict is recorded and the user chooses which value to keep

#### Scenario: Equal or absent value is moved
- **WHEN** a host-only key in the shared file has a value equal to or absent from the local file
- **THEN** the helper moves it to `~/.gitconfig.local`

#### Scenario: Different local value is a conflict
- **WHEN** a host-only key has a different value in the local file
- **THEN** the user resolves it interactively with the helper and the local value is never overwritten silently

#### Scenario: CI guards the shared file
- **WHEN** a host-only key is in the shared file
- **THEN** CI fails

### Requirement: GitHub token variable per host type
For github.com, the credential helper SHALL read `GITHUB_PRIVATE_TOKEN` on `work-machine` hosts and `GITHUB_TOKEN` on all other profiles. The choice SHALL come from a file that `machine` writes on every dotfile apply and that `private.gitconfig` includes; a missing file SHALL leave github.com without a token helper and cause no error.

#### Scenario: Private laptop
- **WHEN** Git needs a github.com credential on a `home-laptop` host
- **THEN** `git-credential-env` serves `GITHUB_TOKEN`

#### Scenario: Work machine
- **WHEN** Git needs a credential for a private github.com repository on a `work-machine` host
- **THEN** `git-credential-env` serves `GITHUB_PRIVATE_TOKEN` and never the work `GITHUB_TOKEN`

### Requirement: SSH remote for the checkout on private hosts
`machine setup` SHALL change the `origin` remote of the dotfiles checkout from an `https://github.com/` URL to the matching `git@github.com:` URL when the profile is neither `work-machine` nor `container` and `ssh -T git@github.com` authenticates. Otherwise the remote SHALL stay unchanged.

#### Scenario: SSH key registered with GitHub
- **WHEN** `machine setup` runs on a private host whose checkout uses `https://github.com/ditschi/dotfiles.git` and SSH to GitHub authenticates
- **THEN** `origin` becomes `git@github.com:ditschi/dotfiles.git`

#### Scenario: No SSH access
- **WHEN** SSH to GitHub does not authenticate
- **THEN** `origin` stays on HTTPS

#### Scenario: Work machine
- **WHEN** `machine setup` runs on a `work-machine` host
- **THEN** `origin` is not changed
