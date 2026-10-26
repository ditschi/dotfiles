## MODIFIED Requirements

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

### Requirement: Read-only update check
`machine update --check` SHALL show the changed areas, the steps that would run, the local changes, the files that merge cleanly, the files that conflict and the blockers without changing anything, and SHALL offer `--json` for the background job. `machine status` SHALL use the same result.

#### Scenario: Checking before updating
- **WHEN** a user runs `machine update --check`
- **THEN** nothing is changed and the needed steps and blockers are shown

#### Scenario: Overlapping files are classified
- **WHEN** locally changed files are also changed upstream
- **THEN** the check lists which of them merge cleanly and which conflict, and only conflicts are blockers

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

### Requirement: Update ends converged
`machine update` SHALL end with a converge check, also when nothing was incoming: the user-space tools declared in the `mise` configuration are installed (missing ones are added) and the dotfile groups of the host are applied (missing links created, removed ones pruned). The checks SHALL be idempotent and cheap when nothing is missing.

#### Scenario: Nothing incoming but a tool is missing
- **WHEN** a user runs `machine update`, no commits are incoming and a declared tool is not installed
- **THEN** the tool is installed

#### Scenario: Link missing
- **WHEN** a user runs `machine update` and a dotfile link of the host's groups is missing
- **THEN** the link is created

## ADDED Requirements

#### Scenario: Feature table gives a feature a new group
- **WHEN** an incoming change adds a dotfile group to a feature the host has and the host config itself is unchanged
- **THEN** the host's group list is rewritten, the group's files are linked and its tools are installed

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
`machine update --force` SHALL do what the stash choice of "Conflict choices" does, without asking: update to the upstream, keep the local changes that merge cleanly and put only the conflicting ones into a named stash entry with an attention item.

#### Scenario: Forced update with a conflict
- **WHEN** a user runs `machine update --force` and one of two locally changed files conflicts
- **THEN** the checkout is at the upstream, the cleanly merging file keeps its local change, the conflicting change is in a named stash entry and `machine attention` lists it

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
The needs-attention reason for a blocked update SHALL name the number of incoming commits and the conflicting files, and SHALL say what the user runs next.

#### Scenario: Reason for a conflict
- **WHEN** two incoming commits conflict with a local change in `Readme.md`
- **THEN** the reason names `Readme.md`, says that 2 commits are incoming and names `machine` as the next command

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
