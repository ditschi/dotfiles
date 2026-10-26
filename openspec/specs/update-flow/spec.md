# update-flow Specification

## Purpose
Defines how a user learns about dotfiles updates and how `machine update` applies them.

## Requirements

### Requirement: Update hint at shell start
Interactive zsh and bash SHALL show the update state as a persistent prompt segment: update available, updated and shell reload needed, or needs attention. The shell SHALL NOT run the update check itself, so that startup stays fast.

#### Scenario: Update available
- **WHEN** an update is pending and not applied automatically and a zsh starts
- **THEN** the prompt segment shows that an update is available and no text is printed at shell start

#### Scenario: Update available in bash
- **WHEN** an update is pending and not applied automatically and an interactive bash starts and stays in bash
- **THEN** the prompt segment shows that an update is available

#### Scenario: Shell older than the applied update
- **WHEN** an update was applied after the shell started
- **THEN** the prompt segment tells the user to reload the shell

#### Scenario: Needs attention
- **WHEN** the update needs manual checking
- **THEN** the prompt segment shows it and a one-line message is printed at shell start

#### Scenario: No update
- **WHEN** no update is pending and the shell is current
- **THEN** nothing is shown

#### Scenario: State changes in an open shell
- **WHEN** the update state changes while a shell is open
- **THEN** the prompt segment shows the new state after the next command

#### Scenario: Fresh shell shows nothing
- **WHEN** a shell is started after the update was applied
- **THEN** no segment is shown

#### Scenario: Message only for needs-attention
- **WHEN** a shell starts
- **THEN** a one-line message is printed only for needs-attention

#### Scenario: Segment follows state changes
- **WHEN** the state changes in an open shell
- **THEN** the segment is re-evaluated after each command without reloading the shell, as long as the prompt stays fast

### Requirement: Explicit update
`machine update` SHALL fast-forward the checkout, sync the host config and apply the setup, applying the dotfile groups and the user-space tools before Ansible. System changes and host-config changes SHALL stay explicit.

#### Scenario: Clean fast-forward
- **WHEN** a user runs `machine update` on a clean checkout that is behind its upstream
- **THEN** the checkout is fast-forwarded and the setup is applied

#### Scenario: Home-only change, clean checkout
- **WHEN** the background job finds only home-file changes and the checkout has no local changes
- **THEN** the changes are pulled and applied and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-config change
- **THEN** the background job fast-forwards to the upstream tip, applies the dotfile groups and the user-space tools, does not run Ansible or apply the host config, and the state shows that a system update is available when the changes apply to this host

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host config
- **THEN** the background job treats all incoming changes together as in "System change pending"; it does not stop before that commit

#### Scenario: Blocked automatic update
- **WHEN** local changes remain that block the fast-forward
- **THEN** nothing is applied and the state is needs-attention with the reason

#### Scenario: System changes are not applied implicitly
- **WHEN** system or host-config changes are pending
- **THEN** they are not applied without the user running the command

#### Scenario: Background job limits
- **WHEN** the background job runs on a clean checkout
- **THEN** it MAY fast-forward to the upstream tip and apply the dotfile groups and user-space tools, and it SHALL only report pending system changes that apply to this host (see "Relevant system changes only")

### Requirement: Update never discards local work
`machine update` SHALL first remove text that the local-overrides helper already knows from shared files, then fast-forward without touching local changes. It SHALL stop and report why only when a locally changed file is also changed upstream or the history diverged. Other local changes SHALL be a notice. `--force` overrides a stop.

#### Scenario: Only expected local changes
- **WHEN** the only local changes are blocks that are already stored in a `.local` file
- **THEN** they are removed from the shared file and the update continues

#### Scenario: New local text
- **WHEN** a shared file contains local text that the helper does not know yet and the update does not change that file
- **THEN** the text is left in place and not reported; a manual update may offer the helper

#### Scenario: New local text in a file the update changes
- **WHEN** a shared file with unknown local text is also changed by the incoming commits
- **THEN** the update records a conflict and does not overwrite the text

#### Scenario: Dirty checkout
- **WHEN** a locally changed file is also changed by the incoming commits
- **THEN** the files are listed, the reason is reported and the update stops

#### Scenario: Unrelated local change
- **WHEN** a local change remains that the incoming commits do not touch
- **THEN** the update runs, the local change is kept and reported as a notice

#### Scenario: Diverged history
- **WHEN** a fast-forward is not possible
- **THEN** the update stops and nothing is overwritten

### Requirement: Shell helpers
`dotfiles-update` and `update-dotfiles` SHALL delegate to `machine update`. `dotfiles-setup` and `machine-setup` SHALL run `./bootstrap`.

#### Scenario: Running the helper
- **WHEN** a user runs `update-dotfiles`
- **THEN** `machine update` runs

### Requirement: No layout migration
`machine setup` and `machine update` SHALL NOT check for or migrate the old root layout, and the `machine` CLI SHALL NOT provide `migrate` or `rollback` subcommands.

#### Scenario: Update on a migrated host
- **WHEN** a user runs `machine update` on a host with the chezmoi layout
- **THEN** the update runs without any layout check

#### Scenario: Removed subcommands
- **WHEN** a user runs `machine migrate` or `machine rollback`
- **THEN** the CLI reports an unknown command

### Requirement: Targeted update
`machine update` SHALL determine from the files that differ between the current and the target revision which steps are needed and run only those.

#### Scenario: Only a shell file changed
- **WHEN** the incoming changes touch only the content of existing shell configuration files
- **THEN** neither the dotfile apply, the tool install nor the system (Ansible) step runs

#### Scenario: Tool lockfile changed
- **WHEN** the incoming changes touch the lockfile
- **THEN** the tool install runs and the system step does not

#### Scenario: Several commits
- **WHEN** the target revision is several commits ahead
- **THEN** the steps are decided from the file difference to the target and not from each commit

#### Scenario: Step per kind of change
- **WHEN** files differ between the revisions
- **THEN** added, removed or renamed group files and group selection changes need the dotfile apply; a changed tool fragment or lockfile needs the tool install; changed content of existing home files needs only a shell refresh; `ansible/**` or package changes need the system step; a changed host profile needs the profile apply; `machine_cli/` changes need nothing extra

### Requirement: Read-only update check
`machine update --check` SHALL show the changed areas, the steps that would run, the local changes and the blockers without changing anything, and SHALL offer `--json` for the background job. `machine status` SHALL use the same result.

#### Scenario: Checking before updating
- **WHEN** a user runs `machine update --check`
- **THEN** nothing is changed and the needed steps and blockers are shown

### Requirement: One update at a time
Background and manual updates SHALL share a lock so that they cannot run at once, and `machine setup` and `machine update` SHALL ensure that the update-check timer is enabled and, where `loginctl` is available and the host is not a container, that user linger is enabled so the timer also runs without a login session. Enabling linger SHALL be best effort: a failure SHALL be reported with the manual command and SHALL NOT stop setup or update.

#### Scenario: Manual update during a background update
- **WHEN** a manual update starts while a background update runs
- **THEN** it waits or reports that an update is already running

#### Scenario: Linger enabled by setup or update
- **WHEN** `machine setup` or `machine update` runs on a host where linger is off
- **THEN** linger is enabled for the user

#### Scenario: Linger cannot be enabled
- **WHEN** enabling linger fails, for example without admin rights
- **THEN** the command continues and reports how to enable it manually

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

### Requirement: Failed apply restores the host config
When a local `machine apply` or the apply step of `machine update` fails, including a failing post-apply health check, the previously applied host config SHALL be restored. If the host config had changed, the setup SHALL run once more with the restored one. The post-apply health check SHALL be able to fail and SHALL use only checks that work without root privileges and without cached sudo credentials. Remote applies (`--limit`) SHALL NOT revert.

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

### Requirement: Relevant system changes only
The update SHALL report a pending system update only when the files changed since the last successful Ansible run apply to this host, decided without root.

#### Scenario: Always-relevant paths
- **WHEN** playbooks, `ansible/tasks/`, `ansible/group_vars/` or the host config changed
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
- **WHEN** a host config sets `ansible: false`, or the host has never run Ansible
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
`machine update` SHALL end with a converge check, also when nothing was incoming: the user-space tools declared in the `mise` configuration are installed (missing ones are added), the dotfile groups of the host are applied (missing links created, removed ones pruned), `~/.local/bin/machine` is a symlink to the CLI script of the checkout that runs, and, when the command runs in an interactive shell, that shell is replaced by a fresh one so the result is live without opening a new terminal. The checks SHALL be idempotent and cheap when nothing is missing. A host that is not set up (no `mise` or no `~/.config/mise/config.local.toml`) SHALL NOT end silently: `machine update` warns, names `bootstrap` of the checkout and marks the update as needs-attention; in an interactive terminal it offers to run `bootstrap`, and `machine update --auto` never does.

#### Scenario: Nothing incoming but a tool is missing
- **WHEN** a user runs `machine update`, no commits are incoming and a declared tool is not installed
- **THEN** the tool is installed

#### Scenario: Link missing
- **WHEN** a user runs `machine update` and a dotfile link of the host's groups is missing
- **THEN** the link is created

#### Scenario: Entry point of the earlier layout
- **WHEN** `~/.local/bin/machine` is a regular file and a user runs `~/dotfiles/machine_cli/machine update`
- **THEN** it is replaced by a symlink to `machine_cli/machine` in the checkout and `machine` starts again

#### Scenario: Fresh shell after the update
- **WHEN** `machine update` finishes successfully in an interactive shell
- **THEN** that shell is replaced by a freshly loaded one; a failed update leaves the shell untouched

#### Scenario: Host not set up, no terminal
- **WHEN** `machine update` runs without a terminal and `mise` or `~/.config/mise/config.local.toml` is missing
- **THEN** it warns that the host is not set up and names `bootstrap` in the checkout, sets the update state to needs-attention and does not run `bootstrap`

#### Scenario: Host not set up, interactive
- **WHEN** a user runs `machine update` in a terminal on a host that is not set up and confirms
- **THEN** `bootstrap` of the checkout runs; declining leaves the warning and the needs-attention state
