# Tasks

Work only in the worktree `$(machine repo)/.worktrees/ssh-agent-reuse`.

## 1. Shells

- [x] 1.1 Add `tests/unit/test_ssh_agent.py`: with a scratch `HOME`, a scratch `XDG_RUNTIME_DIR` and a stub `ssh-agent` on `PATH` that records calls, cover in bash and zsh that `environment.sh` keeps a set `SSH_AUTH_SOCK`, exports `$XDG_RUNTIME_DIR/openssh_agent` when it is a socket, sets nothing without it or without `XDG_RUNTIME_DIR`, prints nothing, and that `zsh -l` reading `.zprofile` never calls `ssh-agent`; verify the tests fail before 1.2.
  - Result: 3 failed before 1.2 (systemd socket not exported in bash and zsh, `.zprofile` called `ssh-agent`).
- [x] 1.2 Remove the agent block from `home/core/.zprofile` and add the socket export to `home/core/.shell/common/environment.sh`; verify `pytest tests/unit/test_ssh_agent.py -q` passes.
  - Result: 9 passed.
- [x] 1.3 Describe in `docs/ssh.md` which agent a shell uses (existing `SSH_AUTH_SOCK`, the systemd socket, none) and how to list and end agents left by earlier logins.
  - Checked on the desktop: systemd runs `/usr/bin/ssh-agent -D`, gcr runs `ssh-agent -D -a .../gcr/.ssh`, a leftover showed as `ssh-agent -s`, so the documented `pkill -fx 'ssh-agent -s'` ends only leftovers.

## 2. Validation

- [x] 2.1 Run `pytest tests/unit/test_ssh_agent.py tests/unit/test_zsh_handoff.py tests/unit/test_work_net.py -q` (new behaviour, the health check that starts `zsh -l -i`, and the env loader tests that source `environment.sh`) and record the result.
  - Result: 166 passed.
- [x] 2.2 Run `pre-commit run --files <changed paths>` and `openspec validate ssh-agent-reuse --strict`; record the results.
  - Result: pre-commit passed; the change is valid.

## Workflow follow-up

- Archive inside the worktree, then ask the owner before merging into `main`.
- After `machine update` on each host, optionally end agents left by earlier logins (`docs/ssh.md`).
