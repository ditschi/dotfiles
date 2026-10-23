# Spec Delta

## MODIFIED Requirements

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host profile and apply the setup, applying the dotfile groups and the user-space tools before Ansible. System changes and host-profile changes SHALL stay explicit: they are not applied without the user running the command. The background job MAY fast-forward a clean checkout to the upstream tip and apply the dotfile groups and the user-space tools; it SHALL only report pending system changes, and only when the changed files apply to this host (see "Relevant system changes only").

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

#### Scenario: Home-only change, clean checkout
- **WHEN** the background job finds only home-file changes and the checkout has no local changes
- **THEN** the changes are pulled and applied and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-profile change
- **THEN** the background job fast-forwards to the upstream tip, applies the dotfile groups and the user-space tools, does not run Ansible or apply the host profile, and the state shows that a system update is available when the changes apply to this host

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host profile
- **THEN** the background job treats all incoming changes together as in "System change pending"; it does not stop before that commit

#### Scenario: Blocked automatic update
- **WHEN** local changes remain that block the fast-forward
- **THEN** nothing is applied and the state is needs-attention with the reason

### Requirement: Targeted update
`machine update` SHALL determine from the files that differ between the current and the target revision which steps are needed and run only those: added, removed or renamed files in a group and changes to the group selection need the dotfile apply; a changed tool fragment or lockfile needs the tool install; changes to the content of existing home files need only a shell refresh; changes to `ansible/**` or packages need the system step; a changed host profile needs the profile apply; changes to `machine_cli/` need nothing extra.

#### Scenario: Only a shell file changed
- **WHEN** the incoming changes touch only the content of existing shell configuration files
- **THEN** neither the dotfile apply, the tool install nor the system (Ansible) step runs

#### Scenario: Tool lockfile changed
- **WHEN** the incoming changes touch the lockfile
- **THEN** the tool install runs and the system step does not

#### Scenario: Several commits
- **WHEN** the target revision is several commits ahead
- **THEN** the steps are decided from the file difference to the target and not from each commit

### Requirement: Automatic update safety net
After an automatic update the background job SHALL verify that the shell still works. If the dotfile apply or the tool install fails or the zsh health check fails, the job SHALL reset the checkout to the previous revision, re-apply the dotfile groups, not retry the failed revision until a manual `machine update` succeeds, and set the state to needs-attention with the reason.

#### Scenario: Zsh breaks after an automatic update
- **WHEN** the zsh health check fails after an automatic update
- **THEN** the checkout is reset to the previous revision, the dotfile groups are re-applied and the state is needs-attention with the reason

#### Scenario: Tool download fails
- **WHEN** the tool install fails in the background job, for example without network
- **THEN** the checkout is reset to the previous revision, the state is needs-attention with the reason, and nothing is retried until the network or a manual `machine update` succeeds

#### Scenario: Failed revision is not retried
- **WHEN** the background job runs again and the target revision is the one that was reverted
- **THEN** nothing is applied and the state stays needs-attention until a manual `machine update` succeeds

#### Scenario: Manual update clears the failure
- **WHEN** a manual `machine update` succeeds after a reverted automatic update
- **THEN** the failed revision is forgotten and the background job may update again

## ADDED Requirements

### Requirement: Relevant system changes only
The update SHALL report a pending system update only when the files changed since the last successful Ansible run apply to this host, decided without root.

#### Scenario: Always-relevant paths
- **WHEN** playbooks, `ansible/tasks/`, `ansible/group_vars/` or the host profile changed
- **THEN** the change applies

#### Scenario: Ignored paths
- **WHEN** only documentation, `dump_*.yml` or the inventory changed
- **THEN** no system update is reported

#### Scenario: Role not enabled on this host
- **WHEN** the incoming change touches only a role that is not enabled for this host
- **THEN** no system update is reported

#### Scenario: Enabled role changed
- **WHEN** the incoming change touches a role that is enabled for this host
- **THEN** the state shows that a system update is available

#### Scenario: Unknown condition
- **WHEN** the enabling condition of a changed role cannot be evaluated
- **THEN** the change counts as applicable

#### Scenario: Host without root
- **WHEN** a host cannot become root and has never run Ansible
- **THEN** no system update is reported for it

### Requirement: Attention entry point
`machine attention`, also run by `machine` without arguments, SHALL list every open item that needs manual action (pending system update, conflicts, diverging values, new local text in a conflicting file, failed update) and guide the user through each with prompts. Background runs SHALL only record items and SHALL NOT prompt.

#### Scenario: Open items exist
- **WHEN** a user runs `machine attention` and items are open
- **THEN** each item is shown with its choices, and resolved items are removed from the list

#### Scenario: Nothing to do
- **WHEN** no item is open
- **THEN** the command says so and exits successfully

#### Scenario: Non-interactive run
- **WHEN** the command runs without a terminal
- **THEN** it lists the items without prompting

### Requirement: Update ends converged
`machine update` SHALL end with a converge check, also when nothing was incoming: the user-space tools declared in the `mise` configuration are installed (missing ones are added), the dotfile groups of the host are applied (missing links created, removed ones pruned), and, when the command runs in an interactive shell, that shell is replaced by a fresh one so the result is live without opening a new terminal. The checks SHALL be idempotent and cheap when nothing is missing.

#### Scenario: Nothing incoming but a tool is missing
- **WHEN** a user runs `machine update`, no commits are incoming and a declared tool is not installed
- **THEN** the tool is installed

#### Scenario: Link missing
- **WHEN** a user runs `machine update` and a dotfile link of the host's groups is missing
- **THEN** the link is created

#### Scenario: Fresh shell after the update
- **WHEN** `machine update` finishes successfully in an interactive shell
- **THEN** that shell is replaced by a freshly loaded one; a failed update leaves the shell untouched
