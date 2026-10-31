# Spec Delta

## MODIFIED Requirements

### Requirement: Failed apply restores the host config
When a local `machine apply` or the apply step of `machine update` fails, including a failing post-apply health check, the previously applied host config SHALL be restored. If the host config had changed, the setup SHALL run once more with the restored one. The post-apply health check SHALL be able to fail and SHALL use only checks that work without root privileges and without cached sudo credentials. Remote applies (`--limit`) SHALL NOT revert. The failure message SHALL name the step that failed (Ansible or the health check) with its reason; hints about Ansible or sudo SHALL appear only when Ansible failed.

#### Scenario: Ansible fails after a profile change during update
- **WHEN** `machine update` syncs a changed host config and the Ansible run fails
- **THEN** the previously applied host config is restored and the setup runs again with it

#### Scenario: Health check fails
- **WHEN** the post-apply health check reports a failure
- **THEN** the previously applied host config is restored as for a failed Ansible run

#### Scenario: Unchanged profile
- **WHEN** the apply fails and the host config did not change
- **THEN** the applied host config is kept and the setup is not retried

#### Scenario: Remote apply
- **WHEN** an apply with `--limit` fails
- **THEN** nothing is reverted

#### Scenario: Health check names itself
- **WHEN** Ansible succeeds and the post-apply health check fails because zsh prints an error on startup
- **THEN** the output says that the health check failed, shows the zsh output and does not mention Ansible's error or sudo restrictions

#### Scenario: Missing mise tools are installed once
- **WHEN** the only health-check failure is zsh reporting missing mise tools (`mise WARN missing: …`)
- **THEN** `machine` logs that it runs `mise install`, runs it once and repeats the health check; the apply succeeds if the check now passes

#### Scenario: Missing mise tools stay missing
- **WHEN** the health check still reports missing mise tools after that `mise install`
- **THEN** the apply fails as for any health-check failure and the message names `mise install` as the next step

### Requirement: Conflict choices
When local changes conflict with the incoming changes, an interactive `machine update` SHALL show a colored diff of the conflicting local changes and the incoming commits that touch them, then offer: resolve manually (default) or put the conflicting local changes into the stash and update. The reason SHALL be the last line of output. This SHALL also apply when the history diverged and uncommitted changes conflict with the incoming commits; the stash choice then rebases the local commits after stashing.

#### Scenario: Default is manual
- **WHEN** a user runs `machine update` in a terminal, a local change conflicts and the user presses Enter
- **THEN** the commands for resolving the conflict outside `machine` are shown, nothing is changed and the state is needs-attention with the reason

#### Scenario: Stash and update
- **WHEN** the user chooses to put the conflicting changes into the stash
- **THEN** only the conflicting local changes go into a named stash entry, cleanly merging local changes are kept, the update runs, and an attention item for the stash entry is recorded

#### Scenario: Non-interactive conflict
- **WHEN** `machine update` runs without a terminal and a local change conflicts
- **THEN** no diff is paged, nothing is changed, the reason is printed last and the state is needs-attention

#### Scenario: Diverged history with a conflicting uncommitted change
- **WHEN** a user runs `machine update` in a terminal, two unpushed local commits must be rebased and an uncommitted change to `home/core/.config/mise/mise.lock` conflicts with an incoming commit, and the user chooses the stash
- **THEN** the diff of `mise.lock` was shown, only that change goes into a named stash entry with an attention item, the local commits are rebased onto the upstream, other uncommitted changes are kept and the update continues

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
