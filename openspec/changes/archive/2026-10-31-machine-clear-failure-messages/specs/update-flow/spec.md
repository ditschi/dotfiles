# Spec Delta

## MODIFIED Requirements

### Requirement: Force update
`machine update --force` SHALL do what the stash choice of "Conflict choices" does, without asking: update to the upstream, keep the local changes that merge cleanly and put only the conflicting ones into a named stash entry with an attention item. In a diverged history it SHALL rebase the local commits after stashing.

#### Scenario: Forced update with a conflict
- **WHEN** a user runs `machine update --force` and one of two locally changed files conflicts
- **THEN** the checkout is at the upstream, the cleanly merging file keeps its local change, the conflicting change is in a named stash entry and `machine attention` lists it

#### Scenario: Forced update with diverged history
- **WHEN** a user runs `machine update --force`, local commits must be rebased and an uncommitted change conflicts with an incoming commit
- **THEN** the conflicting change is in a named stash entry, the local commits are rebased onto the upstream and `machine attention` lists the entry

### Requirement: Concrete attention reason
The needs-attention reason for a blocked update SHALL name the number of incoming commits and the conflicting files, and SHALL say what the user runs next. The named next step SHALL be one that can succeed in the current state.

#### Scenario: Reason for a conflict
- **WHEN** two incoming commits conflict with a local change in `Readme.md`
- **THEN** the reason names `Readme.md`, says that 2 commits are incoming and names `machine` as the next command

#### Scenario: Reason for diverged history with a conflicting uncommitted change
- **WHEN** `machine update` runs without a terminal, the history diverged and an uncommitted change to `home/core/.config/mise/mise.lock` conflicts with the incoming commits
- **THEN** the reason names `home/core/.config/mise/mise.lock`, the number of local and incoming commits, says to commit, stash or discard the change and then run `machine update`, and does not recommend `git pull --rebase`

### Requirement: Update reports a host that is not set up
A host that is not set up (no `mise` or no `~/.config/mise/config.local.toml`) SHALL NOT end silently: `machine update` warns, names `bootstrap` of the checkout and marks the update as needs-attention; in an interactive terminal it offers to run `bootstrap`, and `machine update --auto` never does. `machine` SHALL add `~/.local/bin` to the front of `PATH` when it is missing, so that tools installed there are found without a login shell.

#### Scenario: Host not set up, no terminal
- **WHEN** `machine update` runs without a terminal and `mise` or `~/.config/mise/config.local.toml` is missing
- **THEN** it warns that the host is not set up and names `bootstrap` in the checkout, sets the update state to needs-attention and does not run `bootstrap`

#### Scenario: Host not set up, interactive
- **WHEN** a user runs `machine update` in a terminal on a host that is not set up and confirms
- **THEN** `bootstrap` of the checkout runs; declining leaves the warning and the needs-attention state

#### Scenario: Run over SSH without a login shell
- **WHEN** a user runs `ssh host '~/.local/bin/machine update'` on a set-up host whose `PATH` lacks `~/.local/bin`
- **THEN** `mise` in `~/.local/bin` is found, the host is not reported as not set up and no `bootstrap` is offered

## ADDED Requirements

### Requirement: Apply failure names the failing step
When a local `machine apply` or the apply step of `machine update` fails, the message SHALL name the step that failed (Ansible or the post-apply health check) with its reason. Hints about Ansible or sudo restrictions SHALL appear only when Ansible failed.

#### Scenario: Health check names itself
- **WHEN** Ansible succeeds and the post-apply health check fails because zsh prints an error on startup
- **THEN** the output says that the health check failed, shows the zsh output and does not mention Ansible's error or sudo restrictions

#### Scenario: Ansible failure keeps its hint
- **WHEN** the Ansible run of `machine apply` fails and the host config did not change
- **THEN** the output says to review Ansible's error and that sudo command restrictions need administrator approval

### Requirement: Missing mise tools are installed once
When the post-apply health check fails because zsh reports a missing mise tool (`mise WARN missing: …`), `machine` SHALL log that it installs the missing tools, run `mise install` once and repeat the health check before it restores anything.

#### Scenario: Missing mise tools are installed once
- **WHEN** the zsh health check reports `mise WARN missing: npm:@anthropic-ai/claude-code@2.1.308`
- **THEN** `machine` logs that it runs `mise install`, runs it once and repeats the health check; the apply succeeds if the check now passes

#### Scenario: Missing mise tools stay missing
- **WHEN** the health check still reports missing mise tools after that `mise install`
- **THEN** the apply fails as for any health-check failure and the message names `mise install` as the next step

#### Scenario: Other zsh errors
- **WHEN** the zsh health check fails with any other error
- **THEN** `mise install` is not run

### Requirement: Conflict choices for a diverged history
When the history diverged and the only obstacle to rebasing the local commits is an uncommitted change that conflicts with the incoming commits, `machine update` SHALL treat it as in "Conflict choices"; the stash choice SHALL stash only the conflicting files and then rebase the local commits.

#### Scenario: Diverged history with a conflicting uncommitted change
- **WHEN** a user runs `machine update` in a terminal, an unpushed local commit must be rebased and an uncommitted change to `home/core/.config/mise/mise.lock` conflicts with an incoming commit, and the user chooses the stash
- **THEN** the diff of `mise.lock` was shown, only that change goes into a named stash entry with an attention item, the local commits are rebased onto the upstream, other uncommitted changes are kept and the update continues

#### Scenario: Resolving manually
- **WHEN** the user presses Enter at that choice
- **THEN** nothing is changed, the commands shown rebase onto the upstream instead of fast-forwarding, and the state is needs-attention with the reason
