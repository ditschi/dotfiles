## MODIFIED Requirements

### Requirement: Identity by remote owner
Git SHALL choose the work or private identity from the remote URL through
`includeIf "hasconfig:remote.*.url:..."` rules: any github.com remote selects
`private.gitconfig`, and github.com owners matching `bosch-*`, `bosch_*`, or
`*_bosch`, GHES and Bitbucket `sourcecode*` remotes select `work.gitconfig`.
GitHub owner rules SHALL apply to HTTPS and SCP-style SSH URLs. The rules SHALL
NOT depend on the clone path. This needs Git 2.36 or newer.

#### Scenario: Private GitHub repository
- **WHEN** a repository has a github.com remote of another owner
- **THEN** the private identity is active

#### Scenario: Work remote
- **WHEN** a repository has a GHES or Bitbucket `sourcecode*` remote
- **THEN** the work identity is active

#### Scenario: Work GitHub owner suffix
- **WHEN** a GitHub remote uses HTTPS or SCP-style SSH and its owner ends in `_bosch`
- **THEN** the work identity and work GitHub credential configuration are active

#### Scenario: Suffix belongs to the repository name
- **WHEN** a private GitHub owner has a repository name ending in `_bosch`
- **THEN** the private identity remains active

#### Scenario: Owner contains but does not end in suffix
- **WHEN** an otherwise private GitHub owner contains `_bosch` but does not end with it
- **THEN** the private identity remains active
