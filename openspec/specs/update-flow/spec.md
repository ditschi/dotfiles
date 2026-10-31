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

#### Scenario: Home-only change, local changes merge cleanly
- **WHEN** the background job finds only home-file changes and the local changes merge cleanly with them
- **THEN** the changes are pulled and applied, the local changes are kept, and the state tells the user to reload the shell

#### Scenario: System change pending
- **WHEN** the incoming changes include a system or host-config change
- **THEN** the background job fast-forwards to the upstream tip, applies the dotfile groups and the user-space tools, does not run Ansible or apply the host config, and the state shows that a system update is available when the changes apply to this host

#### Scenario: Home changes before a system change
- **WHEN** the incoming commits are home-only up to a commit that touches `ansible/**`, packages or the host config
- **THEN** the background job treats all incoming changes together as in "System change pending"; it does not stop before that commit

#### Scenario: Blocked automatic update
- **WHEN** local changes conflict with the incoming changes or the history diverged
- **THEN** nothing is applied and the state is needs-attention with the reason

#### Scenario: System changes are not applied implicitly
- **WHEN** system or host-config changes are pending
- **THEN** they are not applied without the user running the command

#### Scenario: Background job limits
- **WHEN** the background job runs on a checkout whose local changes, if any, merge cleanly with the incoming changes
- **THEN** it MAY fast-forward to the upstream tip and apply the dotfile groups and user-space tools, and it SHALL only report pending system changes that apply to this host (see "Relevant system changes only")

### Requirement: Update never discards local work
`machine update` and the background job SHALL first remove text that the local-overrides helper already knows from shared files, then update while keeping all local changes. They SHALL stop and report why only when local changes conflict with the incoming changes or the history diverged. Local changes that merge cleanly SHALL be kept and reported as a notice. Local changes SHALL be put aside only when the user chooses it (see "Conflict choices" and "Force update").

#### Scenario: Only expected local changes
- **WHEN** the only local changes are blocks that are already stored in a `.local` file
- **THEN** they are removed from the shared file and the update continues

#### Scenario: New local text
- **WHEN** a shared file contains local text that the helper does not know yet and the update does not change that file
- **THEN** the text is left in place and not reported; a manual update may offer the helper

#### Scenario: New local text in a file the update changes
- **WHEN** a shared file with unknown local text is also changed by the incoming commits
- **THEN** the text is kept; the update continues if it merges cleanly and stops with a conflict otherwise

#### Scenario: Same file changed, merges cleanly
- **WHEN** a locally changed file is also changed by the incoming commits and both changes merge without a conflict
- **THEN** the update continues, the file contains both changes afterwards and the file is reported as merged

#### Scenario: Dirty checkout
- **WHEN** a locally changed file is also changed by the incoming commits and the changes conflict
- **THEN** the conflicting files are listed, the reason is reported, nothing is changed and the update stops

#### Scenario: Untracked file added upstream
- **WHEN** an untracked local file has the same path as a file the incoming commits add
- **THEN** it counts as a conflict

#### Scenario: Unrelated local change
- **WHEN** a local change remains that the incoming commits do not touch
- **THEN** the update runs, the local change is kept and reported as a notice

#### Scenario: Diverged history
- **WHEN** a fast-forward is not possible and the local commits cannot be rebased automatically (see "Clean rebase of local commits")
- **THEN** the update stops, nothing is overwritten, and the reason names the number of local and incoming commits and the command to rebase

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
`machine update --check` SHALL show the changed areas, the steps that would run, the local changes, the files that merge cleanly, the files that conflict and the blockers without changing anything, and SHALL offer `--json` for the background job. `machine status` SHALL use the same result.

#### Scenario: Checking before updating
- **WHEN** a user runs `machine update --check`
- **THEN** nothing is changed and the needed steps and blockers are shown

#### Scenario: Overlapping files are classified
- **WHEN** locally changed files are also changed upstream
- **THEN** the check lists which of them merge cleanly and which conflict, and only conflicts are blockers

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

#### Scenario: Revert keeps local changes
- **WHEN** an automatic update that kept local changes is reverted
- **THEN** the local changes are present again after the reset to the previous revision

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
The update SHALL report a pending system update only when the files changed since the last successful Ansible run apply to this host, decided without root. A change to the feature table SHALL count only when it changes what Ansible reads.

#### Scenario: Always-relevant paths
- **WHEN** playbooks, `ansible/tasks/`, `ansible/group_vars/` or the host config changed
- **THEN** the change applies

#### Scenario: Feature table changed only for the CLI
- **WHEN** the only change to `ansible/group_vars/all/features.yml` is in keys that only the CLI reads (a feature's help text or dotfile groups)
- **THEN** no system update is reported and no Ansible run starts

#### Scenario: Feature table changed for Ansible
- **WHEN** a change to `ansible/group_vars/all/features.yml` changes what Ansible reads, for example where a feature is excluded
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
`machine attention`, also run by `machine` without arguments, SHALL list every open item that needs manual action (pending system update, conflicts, diverging values, new local text in a conflicting file, failed update, Telegraf not working on a host with `monitoring`, a filesystem low on space or inodes, local-only keys or shell code in an env file) and guide the user through each with prompts. Background runs SHALL only record items and SHALL NOT prompt.

#### Scenario: Open items exist
- **WHEN** a user runs `machine attention` and items are open
- **THEN** each item is shown with its choices, and resolved items are removed from the list

#### Scenario: Nothing to do
- **WHEN** no item is open
- **THEN** the command says so and exits successfully

#### Scenario: Non-interactive run
- **WHEN** the command runs without a terminal
- **THEN** it lists the items without prompting

#### Scenario: Blocked update with a conflict
- **WHEN** the update item is open because local changes conflict with the incoming changes
- **THEN** the item offers the conflict choices of an interactive update (see "Conflict choices") and stays open until the conflict is resolved

#### Scenario: System item while the update is blocked
- **WHEN** a system update is pending and the update item is open
- **THEN** the update item is listed first and the system item does not offer `machine apply` on the old checkout; the system step runs as part of the update once it is unblocked

#### Scenario: Stashed local changes
- **WHEN** local changes were put into the stash by `machine` and are not restored yet
- **THEN** an item names the stash entry, shows what it contains and offers to restore it, drop it or keep it for later (default: keep); if restoring conflicts, the files keep the conflict markers, the entry is kept and the commands to finish by hand are shown

#### Scenario: Reverted automatic update
- **WHEN** the update item is open because an automatic update was reverted
- **THEN** the item shows the output of the failed check or step before it offers the update

#### Scenario: Blocked update no longer conflicts
- **WHEN** the update item is open and the local changes now merge cleanly, for example after the user resolved the conflict
- **THEN** the item offers to run the update, which runs the full update including the system step when it is pending

#### Scenario: Telegraf not installed
- **WHEN** the host has `monitoring` and `telegraf` is not installed
- **THEN** a monitoring item says so and offers `machine apply`

#### Scenario: Telegraf without output
- **WHEN** the host has `monitoring`, `telegraf` is installed, no output file exists and the last apply left `telegraf` disabled for lack of an output
- **THEN** a monitoring item names the missing Bitwarden item `influxdb-telegraf-write` and offers `machine apply` once the item exists

#### Scenario: Telegraf not active
- **WHEN** the host has `monitoring`, an output exists and `telegraf` is not active
- **THEN** a monitoring item shows the last lines of the Telegraf journal and offers to restart the service

#### Scenario: Telegraf working
- **WHEN** the host has `monitoring` and `telegraf` is active with an output, or the host does not have `monitoring`
- **THEN** no monitoring item is listed

#### Scenario: Low disk space
- **WHEN** a watched filesystem is low on space or inodes (see the capability `disk-space`)
- **THEN** a disk item names the mount point and its usage and offers the guided cleanup

#### Scenario: Local-only env keys
- **WHEN** `~/.env` or `~/.env.host` has a local-only section, or was left unchanged because it holds shell code (see the capability `env-files`)
- **THEN** an env item names the file and its keys and offers the choices of "Choices for a local-only key" for each key, and the item disappears once no key is left unresolved

### Requirement: Update ends converged
`machine update` SHALL end with a converge check, also when nothing was incoming: the user-space tools declared in the `mise` configuration are installed (missing ones are added) and the dotfile groups of the host are applied (missing links created, removed ones pruned). The checks SHALL be idempotent and cheap when nothing is missing.

#### Scenario: Nothing incoming but a tool is missing
- **WHEN** a user runs `machine update`, no commits are incoming and a declared tool is not installed
- **THEN** the tool is installed

#### Scenario: Link missing
- **WHEN** a user runs `machine update` and a dotfile link of the host's groups is missing
- **THEN** the link is created

#### Scenario: Feature table gives a feature a new group
- **WHEN** an incoming change adds a dotfile group to a feature the host has and the host config itself is unchanged
- **THEN** the host's group list is rewritten, the group's files are linked and its tools are installed

### Requirement: Update keeps the entry point and shell current
`machine update` SHALL make `~/.local/bin/machine` a symlink to the CLI script of the checkout that runs and, when the command runs in an interactive shell, replace that shell by a fresh one so the result is live without opening a new terminal.

#### Scenario: Entry point of the earlier layout
- **WHEN** `~/.local/bin/machine` is a regular file and a user runs `~/dotfiles/machine_cli/machine update`
- **THEN** it is replaced by a symlink to `machine_cli/machine` in the checkout and `machine` starts again

#### Scenario: Fresh shell after the update
- **WHEN** `machine update` finishes successfully in an interactive shell
- **THEN** that shell is replaced by a freshly loaded one; a failed update leaves the shell untouched

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

### Requirement: Conflict choices
When local changes conflict with the incoming changes, an interactive `machine update` SHALL show a colored diff of the conflicting local changes and the incoming commits that touch them, then offer: resolve manually (default) or put the conflicting local changes into the stash and update. The reason SHALL be the last line of output.

#### Scenario: Default is manual
- **WHEN** a user runs `machine update` in a terminal, a local change conflicts and the user presses Enter
- **THEN** the commands for resolving the conflict outside `machine` are shown, nothing is changed and the state is needs-attention with the reason

#### Scenario: Stash and update
- **WHEN** the user chooses to put the conflicting changes into the stash
- **THEN** only the conflicting local changes go into a named stash entry, cleanly merging local changes are kept, the update runs, and an attention item for the stash entry is recorded

#### Scenario: Non-interactive conflict
- **WHEN** `machine update` runs without a terminal and a local change conflicts
- **THEN** no diff is paged, nothing is changed, the reason is printed last and the state is needs-attention

### Requirement: Force update
`machine update --force` SHALL do what the stash choice of "Conflict choices" does, without asking: update to the upstream, keep the local changes that merge cleanly and put only the conflicting ones into a named stash entry with an attention item. In a diverged history it SHALL rebase the local commits after stashing.

#### Scenario: Forced update with a conflict
- **WHEN** a user runs `machine update --force` and one of two locally changed files conflicts
- **THEN** the checkout is at the upstream, the cleanly merging file keeps its local change, the conflicting change is in a named stash entry and `machine attention` lists it

#### Scenario: Forced update with diverged history
- **WHEN** a user runs `machine update --force`, local commits must be rebased and an uncommitted change conflicts with an incoming commit
- **THEN** the conflicting change is in a named stash entry, the local commits are rebased onto the upstream and `machine attention` lists the entry

### Requirement: Stashed local changes are never lost
Every stash entry that `machine` creates SHALL either be re-applied completely or stay in the stash under a name that says when and why it was created, with an attention item until the user restores or drops it.

#### Scenario: Re-apply fails
- **WHEN** `machine` re-applies local changes it stashed and the re-apply conflicts or fails
- **THEN** the stash entry is kept, the state is needs-attention naming the entry, and nothing is dropped

#### Scenario: Restored
- **WHEN** the user restores the stash entry through the attention item and no conflict is left
- **THEN** the entry is dropped and the item is removed

### Requirement: Manual update checks zsh
After a manual update has applied home-file changes, `machine update` SHALL run the same zsh health check as the background job. On a failure it SHALL show the check output and set the state to needs-attention; it SHALL NOT revert, because the user is present.

#### Scenario: Zsh broken after a manual update
- **WHEN** the zsh health check fails at the end of a manual update
- **THEN** the check output is shown, the shell is not replaced and the state is needs-attention with the reason

### Requirement: Clean rebase of local commits
When the history diverged, a manual `machine update` SHALL rebase the local commits onto the upstream without asking if a trial rebase without changes to the checkout is clean, none of the local commits is on a remote branch, the local commits contain no merge commit, commit signing is off and no rebase, merge or cherry-pick is in progress. Otherwise it SHALL stop as for a diverged history. The background job SHALL NOT rebase; it SHALL record needs-attention.

#### Scenario: Clean rebase
- **WHEN** a user runs `machine update`, one unpushed local commit and three incoming commits do not conflict
- **THEN** the local commit is rebased onto the upstream, local uncommitted changes are kept and the update continues

#### Scenario: Rebase would conflict
- **WHEN** the trial rebase conflicts
- **THEN** nothing is changed and the update stops with the reason

#### Scenario: Local commit already pushed elsewhere
- **WHEN** a local commit is also on a remote branch
- **THEN** nothing is rebased and the update stops with the reason

#### Scenario: Background job and diverged history
- **WHEN** the background job finds a diverged history
- **THEN** it does not rebase and the state is needs-attention; the next manual `machine update` rebases if the conditions hold

### Requirement: Concrete attention reason
The needs-attention reason for a blocked update SHALL name the number of incoming commits and the conflicting files, and SHALL say what the user runs next. The named next step SHALL be one that can succeed in the current state.

#### Scenario: Reason for a conflict
- **WHEN** two incoming commits conflict with a local change in `Readme.md`
- **THEN** the reason names `Readme.md`, says that 2 commits are incoming and names `machine` as the next command

#### Scenario: Reason for diverged history with a conflicting uncommitted change
- **WHEN** `machine update` runs without a terminal, the history diverged and an uncommitted change to `home/core/.config/mise/mise.lock` conflicts with the incoming commits
- **THEN** the reason names `home/core/.config/mise/mise.lock`, the number of local and incoming commits, says to commit, stash or discard the change and then run `machine update`, and does not recommend `git pull --rebase`

### Requirement: Consistent update status
`machine status` SHALL derive whether the checkout is behind and whether an update is pending from the same live check as `machine update --check`, so that no two lines of the status contradict each other.

#### Scenario: Blocked manual update
- **WHEN** a manual update stopped on a conflict and the checkout is behind
- **THEN** the status shows the checkout as behind with an update pending and names the conflict

### Requirement: Compact status
`machine status` SHALL show a short overview with one line per topic and the features in columns. It SHALL use colors only on a terminal and honor `NO_COLOR`. `machine status -v` SHALL also show the full host config, the dotfile groups configuration and the file lists.

#### Scenario: Default status
- **WHEN** a user runs `machine status` in a terminal
- **THEN** it shows the branch and how far it is behind, the time of the last check, the attention reason with the next command, the incoming change count with the steps, counts of local changes, one host line (name, context, device, host config in sync), the features in columns and the dotfile groups on one line, and does not print the host config or the dotfile groups configuration in full

#### Scenario: Verbose status
- **WHEN** a user runs `machine status -v`
- **THEN** the full host config, the dotfile groups configuration and the lists of local and incoming files are shown as well

#### Scenario: Stash entries put aside by machine
- **WHEN** the stash holds entries that `machine` created, recorded in the update state or recognised by their name `machine update <date>: <why>`
- **THEN** the status shows how many there are and that the user decides in `machine attention` whether to restore or drop them; `-v` lists them; stash entries the user made are not counted

#### Scenario: Piped status
- **WHEN** the output of `machine status` is not a terminal or `NO_COLOR` is set
- **THEN** no color codes are written

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
