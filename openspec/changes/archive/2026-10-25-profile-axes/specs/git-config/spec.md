# Spec Delta

## MODIFIED Requirements

### Requirement: Host-local Git config
`~/.gitconfig.local` SHALL be host-local and not versioned. `machine setup` SHALL create it once from the context and device (default identity from the context, and `safe.directory` on work hosts and containers) when it does not exist, and nothing SHALL overwrite it afterwards. Git SHALL treat a missing file as empty, so a host without the file works.

#### Scenario: Update on an existing host
- **WHEN** `machine setup` or `machine update` runs and `~/.gitconfig.local` exists
- **THEN** the file is left unchanged

#### Scenario: Existing work host without the CA bundle key
- **WHEN** the dotfile apply runs on a work host whose `~/.gitconfig.local` has no `http.sslCAInfo`
- **THEN** only that key is appended (the user-space Git ignores the system CA store) and nothing else in the file changes

#### Scenario: First setup
- **WHEN** `machine setup` runs on a host without `~/.gitconfig.local`
- **THEN** the file is created with the identity of the context

#### Scenario: File missing later
- **WHEN** the file is deleted and Git runs before the next setup
- **THEN** Git reports no error

### Requirement: GitHub token variable per host type
For github.com, the credential helper SHALL read `GITHUB_PRIVATE_TOKEN` on hosts with the context `work` and `GITHUB_TOKEN` on all other hosts. The choice SHALL come from a file that `machine` writes on every dotfile apply and that `private.gitconfig` includes; a missing file SHALL leave github.com without a token helper and cause no error.

#### Scenario: Private laptop
- **WHEN** Git needs a github.com credential on a private host
- **THEN** `git-credential-env` serves `GITHUB_TOKEN`

#### Scenario: Work machine
- **WHEN** Git needs a credential for a private github.com repository on a work host
- **THEN** `git-credential-env` serves `GITHUB_PRIVATE_TOKEN` and never the work `GITHUB_TOKEN`

### Requirement: SSH remote for the checkout on private hosts
`machine setup` SHALL change the `origin` remote of the dotfiles checkout from an `https://github.com/` URL to the matching `git@github.com:` URL when the context is `private`, the device is not `container`, and `ssh -T git@github.com` authenticates. Otherwise the remote SHALL stay unchanged.

#### Scenario: SSH key registered with GitHub
- **WHEN** `machine setup` runs on a private host whose checkout uses `https://github.com/ditschi/dotfiles.git` and SSH to GitHub authenticates
- **THEN** `origin` becomes `git@github.com:ditschi/dotfiles.git`

#### Scenario: No SSH access
- **WHEN** SSH to GitHub does not authenticate
- **THEN** `origin` stays on HTTPS

#### Scenario: Work machine
- **WHEN** `machine setup` runs on a work host
- **THEN** `origin` is not changed
