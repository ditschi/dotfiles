# Proposal

## Why

Three `machine` messages sent the user in the wrong direction on 2026-10-30: a failed health check was reported as an Ansible error, a blocked update recommended a command that cannot work and named no file, and an SSH run reported mise as missing and offered bootstrap. Each message should name what actually failed and a next step that works.

## What Changes

- **Apply failure names the failing step.** When the post-apply health check fails, `machine apply` and the apply step of `machine update` say that the health check failed and show its reason. The hint about Ansible and sudo restrictions appears only when Ansible itself failed.
- **Missing mise tools are installed once.** When the only health-check failure is zsh reporting missing mise tools (`mise WARN missing: …`), `machine` runs `mise install` once, logs it and checks again. Only if the check still fails is the apply rolled back, with `run: mise install` as the next step.
- **Diverged history with conflicting uncommitted changes gets the conflict choices.** When local commits must be rebased and uncommitted changes conflict with the incoming commits, an interactive `machine update` shows the conflicting files and their diff, then offers the existing choices: resolve manually (default) or put only the conflicting changes into a named stash, rebase and update. `--force` takes the stash choice without asking. Without a terminal the reason names the files and says to commit, stash or discard them, then run `machine update`; it no longer recommends `git pull --rebase`, which fails in this case.
- **`machine` finds user tools without a login `PATH`.** When `~/.local/bin` is not in `PATH` (for example `ssh host '~/.local/bin/machine update'`), `machine` adds it at the front before doing anything else, so `mise`, `bw` and `ansible` are found and a set-up host is not reported as "not set up".

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `update-flow`: "Failed apply restores the host config" (failing step named; one `mise install` retry), "Conflict choices", "Force update" and "Concrete attention reason" (diverged history with conflicting uncommitted changes), "Update reports a host that is not set up" (`~/.local/bin` without a login `PATH`).

Affected profiles: all contexts and devices that run `machine` (private and work; containers only for the `PATH` part).

## Impact

- Code: `machine_cli/commands.py` (`cmd_apply` failure messages), `machine_cli/tools.py` (`health_check_after_apply`, mise retry), `machine_cli/local_work.py` (`rebase_blocker` returns the conflicting files), `machine_cli/updates.py` (`_update_locked`, `blocked_reason`, `resolve_conflicts` for the diverged case), `machine_cli/machine` (`PATH` at start).
- Tests: `tests/unit/test_host_profiles.py` (apply/health check), `tests/unit/test_update_and_env.py` (diverged history, not-set-up host).
- Docs: Readme update section where it describes diverged history and the health check.
- Where: git worktree `.worktrees/machine-clear-failure-messages` on branch `machine-clear-failure-messages`, because the change touches `machine_cli/`, which the host runs live from the main clone.
