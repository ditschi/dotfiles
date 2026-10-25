# Spec Delta

## ADDED Requirements

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
