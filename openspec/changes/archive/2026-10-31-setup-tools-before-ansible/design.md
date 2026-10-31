# Design

## Context

See proposal.md for the motivation. Today `cmd_setup` runs, after writing the host config: Ansible, the SSH host key, the Tailscale login, then (unless `--skip-dotfiles`) `run_dotfiles_apply`, `run_tools_install`, `ensure_update_timer` and `cmd_env_pull`. `_update_locked` runs `run_dotfiles_apply` and `run_tools_install` (only when `mise` and the local mise config exist), then `cmd_env_pull`, then `cmd_apply` (Ansible). The background update (`update_auto`) applies dotfiles and tools only and never pulls env files.

Checked dependencies:
- The `mise` tools are prebuilt user-space binaries pinned by `mise.lock`; their prerequisites (git, curl, unzip, mise itself) come from `ensure_bootstrap_tools` and `./bootstrap`, not from Ansible.
- The env pull needs only `bw` (installed by `ensure_bitwarden_cli` into `~/.local/bin`, not by `mise`), an unlocked vault (setup unlocks it early in `setup_bitwarden`) and the context and hostname; it does not depend on the dotfile groups. `mise dot apply` manages no `~/.env*` file.
- `mise` does not see the pulled env files: `machine` passes its own process environment (`dotfiles_env`) and never loads `~/.env*`. So the order does not change which tokens `mise` uses.
- Ansible does not read `~/.env*`; the Influx credentials are read from Bitwarden by `run_ansible` itself.
- The GNOME extension step only uses `gnome-shell` and a system extension shipped by Ubuntu, not packages from Ansible.
- The Tailscale login needs the `tailscale` package, which Ansible installs.

## Goals / Non-Goals

**Goals:**
- One order for setup and update: env pull, dotfile groups, tools, then Ansible.
- All questions of the shell part (Bitwarden, features, local-only env keys) before the long tool install.
- A visible point at which the user can open a new terminal.
- One overall result: every independent step is tried, all failures are listed at the end.

**Non-Goals:**
- Running Ansible and `mise` in parallel.
- Loading the pulled env files into the environment of `mise`.
- Changing `machine apply`, the background update or the bootstrap script.
- Collecting failures in `machine update --auto`: nobody watches it, so reverting on the first failure stays right.
- Counting the SSH host key's own "not provisioned" result or the Tailscale login as failures; they keep their current messages.

## Decisions

1. **Env pull first.** `cmd_env_pull` runs before `run_dotfiles_apply` in both commands, so its questions about local-only keys come before `mise install`, which can take minutes on a fresh host. In update it runs before the "not set up" check, so it still runs on a host without `mise`, as it does today.
2. **Shell block before Ansible in setup.** Env pull, `run_dotfiles_apply` and `run_tools_install` move before `run_ansible_or_hint`, still guarded by `--skip-dotfiles` (all three) and `MACHINE_SKIP_TOOLS` (tools only).
3. **Ansible-dependent and background steps after Ansible.** The SSH host key and the Tailscale login stay after Ansible. `ensure_update_timer` moves to the end of setup: enabling the timer starts the background `machine update --auto`, which should not run while setup's Ansible run is still in progress.
4. **Ready line only when Ansible follows.** After the tools, setup logs that the shell is ready in a new terminal while Ansible continues. It is not printed when Ansible is skipped, `--skip-dotfiles` is set, or the dotfile apply or the tool install failed; a failed env pull does not suppress it, because the shell starts without the env files.
5. **Steps with explicit dependencies and a collected result.** Setup and the apply part of a manual update run a fixed list of steps. Each step ends as ok, failed (with reason) or skipped (with the failed step it needs). Dependencies: the tool install and the zsh health check need the dotfile apply; everything else is independent, because the checks above found no other dependency. A step counts as failed when it raises `subprocess.CalledProcessError`, `OSError` or `SystemExit` (from `die`), or when the env pull returns non-zero. `KeyboardInterrupt` is never caught. Catching `SystemExit` is limited to these step boundaries, so a `die` inside a step ends only that step.
6. **What still stops at once.** Updating the checkout (merge, rebase, conflicts, blockers) and the lock stay as they are: nothing is applied from a half-updated checkout. Missing prerequisites that are checked before the steps (`ensure_bootstrap_tools`, the not-set-up case of update) keep their behaviour.
7. **Ansible keeps its restore.** In update the apply step is `cmd_apply`, which restores the host config on failure and then calls `die`; the step boundary turns that into a failed step after the restore, so the restore logic is unchanged.
8. **Reporting.** At the end, failed and skipped steps are printed last, one line each with the reason. Setup and update exit non-zero. Update writes the state needs-attention with the names of the failed steps and the details into the update failure file (where the zsh health output already goes), so `machine attention` shows them; the zsh health failure becomes one of these results. The event of the run is recorded as failed. As before, a failed update does not replace the shell.
9. **Sequential, not parallel.** The owner chose a sequential order with the shell part first over running `mise` and Ansible at once. Running them in parallel would mix the `mise` progress output with Ansible's output, could hide Ansible's become-password prompt, and would complicate the restore logic after a failed apply, for little time saved.

## Risks / Trade-offs

- [Without network every step fails one after the other, so the user waits for several failures instead of one] → Each step reports its own reason, and the summary shows that all failed for the same cause.
- [Catching `SystemExit` at a step boundary could hide a `die` that was meant to end the whole run] → Only the listed steps are wrapped; prerequisites are checked before the steps, and the run still exits non-zero.
- [After a failed dotfile apply, Ansible still changes the system] → Ansible does not read the dotfile groups; the result names the failed apply, and the next run repeats it.
- [The become-password prompt of Ansible now appears after `mise install`, so an unattended first setup waits there longer] → The ready line comes right before the prompt, so the user sees both at once.
- [A tool step that later starts to need a package from Ansible would fail on a fresh host] → Tools must stay user-space (`system-provisioning` "Local roles"); a failing `mise install` names the tool.

## Migration Plan

No migration; the order applies to the next `machine setup` or `machine update`. Rollback is reverting the commit.
