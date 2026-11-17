# Spec Delta

## ADDED Requirements

### Requirement: Credential helper before netrc for github.com
Git SHALL ask its credential helper for github.com before the first request (`http.https://github.com/.proactiveAuth = basic` in `private.gitconfig`), so that a `github.com` entry in `~/.netrc` does not replace the configured credential. Work owners SHALL keep the credential helper of `work.gitconfig`. Git versions that do not know the key SHALL behave as before and report no error.

#### Scenario: Personal repository with a work netrc entry
- **WHEN** `~/.netrc` has a `machine github.com` entry for another login and a repository has the remote `https://github.com/ditschi/dotfiles.git`
- **THEN** Git pushes with the personal token from its credential helper and not with the netrc credentials

#### Scenario: Work owner
- **WHEN** a repository has the remote `https://github.com/bosch-example/repo.git`
- **THEN** the credential helper of `work.gitconfig` is the effective helper and the identity is the work identity

#### Scenario: Any other owner
- **WHEN** a repository has a github.com remote of an owner that does not match a work rule
- **THEN** the rule is active through `private.gitconfig` without naming the owner

#### Scenario: Remote unchanged
- **WHEN** a user runs `git remote -v`
- **THEN** the remotes show the URLs as configured

#### Scenario: Git without the key
- **WHEN** Git is older than 2.46
- **THEN** it ignores the key and reports no error
