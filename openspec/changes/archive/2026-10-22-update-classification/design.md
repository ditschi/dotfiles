## Context

Today `cmd_update` runs the Git config relocation, then stops on any dirty file, runs `git pull --ff-only`, runs `chezmoi apply` in full, pulls env files and runs Ansible only when the host profile changed or `--system` is given. The files in `$HOME` are symlinks into the checkout, so a tool that edits one of them makes the checkout dirty.

## Decisions

- Local-change handling reuses and extends the existing relocation logic (`machine/gitconfig.py`) as the first known resolver. Other resolvers are added the same way when a file turns out to get dirty regularly. After the resolvers the update either has no local change left or knows manual attention is needed and says why.
- Blocking rule: the update uses `git fetch` and `git merge --ff-only` and stops only when a locally changed file is also changed by the incoming commits, or the history diverged. Other remaining local changes are reported as a notice.
- Externally managed blocks in `~/.bashrc` (the owner's host has an `ANSIBLE MANAGED BLOCK - update colors`) are moved by a resolver into a new `~/.bashrc-local`, which `.bashrc` sources at its end like `.zshrc-local`.
- A locally changed `.p10k.zsh` follows the overlap rule: it updates unless the repository changes `.p10k.zsh` too; then the state is needs-attention and the user merges.
- Targeted update mapping: added, removed or renamed home files and `.chezmoiignore` need `chezmoi apply`; content changes to existing home files need only a shell refresh; `ansible/**` or packages need the system step; a changed host profile needs the profile apply; `machine/` and the CLI need nothing extra.
- Incoming changes that mix home and system commits: strategy B, decided in `auto-update` and implemented there; this change only provides the per-commit classification it needs.
- `machine update --check` (with `--json` for the background job) is the read-only check; `machine status` uses it.
- `machine update` ensures the update-check timer is enabled, and a lock is shared by background and manual updates.

## Considered and rejected

- Blocking on every dirty file as today: it hides the difference between expected and real local changes.
- Making `.p10k.zsh` user-owned or adding a p10k local file: not chosen; the overlap rule is enough.
- Deleting the external block from `.bashrc`: not chosen; it is moved, not discarded.
- A separate `machine update-plan` command and a check only inside `machine status`: not chosen.

## Verified (by test or by reading code)

- `git pull --ff-only` succeeds with a dirty file the incoming commits do not touch and refuses only on overlap. The shared gitconfig sets `pull.rebase = true`, which makes `git pull` refuse on any dirty tree, so the overlap rule needs `git fetch` plus `git merge --ff-only`.
- The source has only two templates (`.chezmoi.yaml.tmpl` and `create_dot_gitconfig.local.tmpl`, never overwritten); every other file is a plain symlink, so content changes are live after the pull.

## Open Questions

- Origin of the external `ANSIBLE MANAGED BLOCK` in `.bashrc`, and whether it is re-added after the resolver moved it (it would then be appended again on the next run of that tool).
- Whether other files get dirty regularly on other hosts (`.zshrc` from installers, `.config/starship.toml`); the resolver list starts with gitconfig and the `.bashrc` block and grows from evidence.
- Exact lock mechanism and the wait-or-fail behaviour for a manual update while a background update runs.
