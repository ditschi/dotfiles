# Spec Delta

## MODIFIED Requirements

### Requirement: Credential helper before netrc for github.com
When the github.com token variable is set at dotfile apply time (environment or `~/.env*`), Git SHALL ask its credential helper for github.com before the first request (`http.https://github.com/.proactiveAuth = basic`, written by `machine` into `github-token.gitconfig`), so that a `github.com` entry in `~/.netrc` does not replace the configured credential. Work owners SHALL keep the credential helper of `work.gitconfig`. Git versions that do not know the key SHALL behave as before.

#### Scenario: Personal repository with a work netrc entry
- **WHEN** the token is set, `~/.netrc` has a `machine github.com` entry for another login and a repository has the remote `https://github.com/ditschi/dotfiles.git`
- **THEN** Git pushes with the personal token from its credential helper and not with the netrc credentials

#### Scenario: Work owner
- **WHEN** a repository has the remote `https://github.com/bosch-example/repo.git`
- **THEN** the credential helper of `work.gitconfig` is the effective helper and the identity is the work identity

#### Scenario: Any other owner
- **WHEN** the token is set and a repository has a github.com remote of an owner that does not match a work rule
- **THEN** the rule is active through `private.gitconfig` without naming the owner

#### Scenario: Remote unchanged
- **WHEN** a user runs `git remote -v`
- **THEN** the remotes show the URLs as configured

#### Scenario: Git without the key
- **WHEN** Git is older than 2.46
- **THEN** it ignores the key and reports no error

## ADDED Requirements

### Requirement: Anonymous github.com access without a token
When the github.com token variable is not set at dotfile apply time, `github-token.gitconfig` SHALL NOT enable proactive auth, so Git clones and fetches public github.com repositories anonymously and runs the credential helper only when GitHub asks for a credential.

#### Scenario: Fresh container clones zsh plugins
- **WHEN** a host without the token starts zsh for the first time and the plugin manager clones from `https://github.com/`
- **THEN** the clones succeed and the credential helper prints nothing

#### Scenario: Private repository without a token
- **WHEN** a host without the token fetches a repository for which GitHub answers 401
- **THEN** the credential helper reports that the token variable is not set
