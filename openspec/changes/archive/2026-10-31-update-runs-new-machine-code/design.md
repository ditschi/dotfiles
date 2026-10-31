# Design

## Context

- `cmd_update` (`machine_cli/updates.py`) takes the update lock, runs `_update_locked`: local resolvers, `update_plan(fetch=True)`, conflict choices or rebase, `merge_upstream` (fast-forward keeping local changes), and then, in the same process, the host-config sync, env pull, dotfile apply, SSH host list, tool install, SSH key files, zsh health check and Ansible. The steps come from `plan["steps"]`, which was computed before the merge from `HEAD..upstream`.
- `_apply_auto` (`machine_cli/auto_update.py`) stores a stash copy of the local changes, fast-forwards to the safe target, then runs the dotfile apply, the tool install and the zsh health check in the same process. On the first failure `_revert_auto` resets to the previous revision, restores the stash copy, re-applies the dotfile groups and records needs-attention with `failed_revision`.
- Python has imported all of `machine_cli` before the merge. Whatever the merge changes in `machine_cli/` only takes effect in the next process. `run_dotfiles_apply` of the old code does not know steps that the incoming commits add (for example `apply_ssh_client` from `ssh-client-config`).
- `machine_cli/machine` is a `uv run --script` entry point with inline dependencies. Run directly, it resolves the dependencies of the revision that is checked out.
- `~/.local/bin/machine` is a symlink to `machine_cli/machine` of the checkout; `detect_repo()` finds the checkout from it.

## Goals / Non-Goals

**Goals:**
- The steps after the checkout update run with the `machine_cli` of the new revision when `machine_cli/` changed.
- Manual and automatic updates both hand over; the automatic update keeps its revert on the first failure.
- No change when `machine_cli/` did not change: one process, as before.

**Non-Goals:**
- Running the steps before the merge (resolvers, plan, conflict choices, rebase) with new code. They have to run before the new code exists.
- New update steps or a different step selection: "Targeted update" stays as it is.
- Fixing the first update that brings this change: the old code does not hand over yet.

## Decisions

**The old process starts the new code as a child and waits.** After `merge_upstream` (manual) or the fast-forward (automatic), `machine` checks `git diff --name-only <previous> HEAD -- machine_cli/`. If it is not empty, it runs the checkout's `machine_cli/machine update` with hidden resume options and waits for it, while still holding the update lock. The child skips the lock, because the parent holds it for the whole update. The child inherits the terminal, so prompts (env pull questions, bootstrap offer) work as before. Rejected: replacing the process with `os.execv` and passing on the lock descriptor. Nothing of the old process would be left, so the revert of the automatic update would run the new code against the reverted old checkout (the same mismatch in reverse), and a crash of the new code could not be reverted.

**The revert stays in the old process.** In the automatic update the child runs the dotfile apply, the tool install and the zsh health check and writes the result (failure reason and event code) to a file named by the parent. The parent reads it. If the child reports a failure, exits non-zero, cannot be started or writes no result, the parent reverts as before. After `git reset --hard <previous>` the checkout again matches the code that is running, so the re-apply of the dotfile groups uses matching code. A new `machine_cli` that crashes is reverted like a failed step, with the event code `resume-failed`.

**The child recomputes the steps from the previous revision.** The child gets the previous revision and computes the steps from `<previous>..HEAD` with its own classification (`plan_steps` for the manual update, `classify_paths` for the automatic one). This is the same diff the parent used before the merge, now classified by the new rules.

**Manual update: the parent returns the child's exit code.** The parent records the `update` event with the child's exit code; the child records none. If the child exits non-zero and has not recorded needs-attention (for example after a traceback), the parent records needs-attention naming the stopped child. Ctrl-C reaches both processes; the parent stops at once as before (exit 130). If the entry point cannot be started (`OSError`), the manual update warns and runs the remaining steps in the parent, because the user is present and the steps are idempotent.

**The resume options are an internal, versioned interface.** `machine update --resume-from <rev>` (manual; `--system` and `--skip-ansible` are passed on) and `machine update --auto --resume-from <rev> --resume-result <file>` (automatic) are hidden from `--help`. The caller is always an older revision of `machine`, so later changes keep accepting these options and their meaning. An incompatible change gets a new protocol version instead.

**The new checkout declares which handoff it accepts.** `machine_cli/resume-protocol` lists the protocol versions the CLI of that revision accepts (currently `1`). The running code hands over only when its own version is listed; otherwise it logs that the new code does not accept the handoff and runs the remaining steps itself, as before this change. Without this check, an update to a revision without the resume options (a rollback of this change, or of `machine_cli` to before it) would start a child that rejects the options: the automatic update would revert it and the manual update would fail until it was run a second time. A plain file is used because the running code cannot import the new revision's modules, and asking the new CLI (for example through its help) would start a process for every update.

**How the child is started.** `<checkout>/machine_cli/machine` directly when it is executable, so `uv` resolves the dependencies of the new revision; otherwise the running interpreter with the script as argument. `--debug` is passed on when it is on.

## Risks / Trade-offs

- [The child cannot import or start, for example a new dependency that `uv` cannot fetch offline] → the automatic update reverts; the manual update ends with an error and needs-attention, and the user runs `machine update` again once the cause is fixed.
- [A later change breaks the resume interface without changing the protocol version] → old code would start a child that rejects the options; the automatic update would revert every time. Recorded in Decisions as a versioned interface; a unit test fixes the command line.
- [Two processes print to the same terminal or journal] → the parent prints nothing between starting the child and its exit, apart from its own summary on failure.

## Migration Plan

No migration. The first update that brings this change runs the rest with the old code; the handoff works from the next update on. Rollback: revert the commits. The reverted checkout has no `machine_cli/resume-protocol`, so the update that brings the revert runs its remaining steps with the code that is running and does not hand over.

## Assumptions

- `uv` is on `PATH` wherever `machine` runs, because `machine` itself starts through `uv run --script`.
