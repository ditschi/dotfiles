## Purpose

Defines the layers of Git configuration, how the identity is chosen and which settings stay host-local.

## ADDED Requirements

### Requirement: Shared Git config
`~/.gitconfig` SHALL be a symlink into the repository and identical on all hosts. It SHALL hold the shared defaults (`push.default=current`, `pull.rebase`, `fetch.prune`, rerere, `init.defaultBranch=main`, meld, diff-so-fancy and LFS) and the aliases, so that `git config --global alias...` changes the shared file.

#### Scenario: Adding a global alias
- **WHEN** a user runs `git config --global alias.x ...`
- **THEN** the change lands in the repository file and syncs to other hosts with the dotfiles

### Requirement: Host-local Git config
`~/.gitconfig.local` SHALL be host-local and not versioned. Chezmoi SHALL create it once from the profile (default identity from the profile, and `safe.directory` on work and container profiles) and SHALL never overwrite it.

#### Scenario: Update on an existing host
- **WHEN** chezmoi applies and `~/.gitconfig.local` exists
- **THEN** the file is left unchanged

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
Host-only keys (identity, signing, `safe.*`, `credential.*`, `http(s).*`, `core.sshCommand`) SHALL be kept out of the shared file. `machine update`, `machine commit` and a pre-commit hook SHALL move them to `~/.gitconfig.local`, and CI SHALL run `machine/gitconfig.py --check`.

#### Scenario: Host-only key in the shared file
- **WHEN** a host-only key appears in the shared file
- **THEN** the check fails and the tooling moves it to `~/.gitconfig.local`
