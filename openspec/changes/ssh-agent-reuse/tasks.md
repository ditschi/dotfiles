# Tasks

Resolve design.md Open Questions Q1-Q4 with the owner before group 2; the tasks below follow the recommendations.

## 1. Investigation

- [ ] 1.1 On the work VM, in a Remote-SSH terminal and in a plain SSH login, record `echo "$SSH_AUTH_SOCK"`, `pgrep -u "$USER" -ax ssh-agent`, `ls /usr/lib/systemd/user/ | grep -i agent` and `systemctl --user is-enabled ssh-agent.socket` in design.md (Q2); done when the findings are written there and Q1-Q4 are answered or explicitly left as recommended.

## 2. Agent reuse in `.zprofile`

- [ ] 2.1 Add `tests/unit/test_ssh_agent.py` that sources `home/core/.zprofile` in `sh`/`zsh` with a scratch `HOME` and `XDG_RUNTIME_DIR` (stub or real `ssh-agent`/`ssh-add` on `PATH`) and covers every scenario of `specs/ssh-agent/spec.md`: existing socket kept, second and concurrent logins reuse one agent, stale socket replaced, systemd `openssh_agent` socket preferred, `DOTFILES_ZSH_CHECK=1` starts nothing, missing `ssh-agent` or `XDG_RUNTIME_DIR` prints nothing; verify the new tests fail against the current `.zprofile`.
- [ ] 2.2 Replace the agent block in `home/core/.zprofile` with the approach from design.md (POSIX `sh`, no output on success, kill any test-started agent in teardown); verify `pytest tests/unit/test_ssh_agent.py -q` passes.
- [ ] 2.3 Add a health-check test in `tests/unit/test_zsh_handoff.py` (or the new file) that runs the real trial against the real `.zprofile` without `SSH_AUTH_SOCK` and asserts no new agent process remains; verify it passes.
- [ ] 2.4 Describe in `docs/ssh.md` which agent a shell uses (existing `SSH_AUTH_SOCK`, systemd socket, fixed socket, none) and how to list leftover agents from before the change; verify the documented commands run as written.

## 3. Validation

- [ ] 3.1 Run `pytest tests/unit/test_ssh_agent.py tests/unit/test_zsh_handoff.py -q` (changed behaviour plus its consumer, the health check) and record the result.
- [ ] 3.2 In `machine testenv`, start two zsh logins without `SSH_AUTH_SOCK` and confirm one agent with `pgrep -u "$USER" -ax ssh-agent`; on the desktop confirm a GNOME terminal still uses `$XDG_RUNTIME_DIR/gcr/ssh`.
- [ ] 3.3 Run `pre-commit run --files home/core/.zprofile docs/ssh.md tests/unit/test_ssh_agent.py tests/unit/test_zsh_handoff.py openspec/changes/ssh-agent-reuse/*.md openspec/changes/ssh-agent-reuse/specs/ssh-agent/spec.md` and fix findings.
- [ ] 3.4 Run `openspec validate ssh-agent-reuse --strict` and fix findings.

## Workflow follow-up

- Archive the change with spec sync after the tasks pass, following the archive guidance in `openspec/config.yaml`.
- After `machine update` on each host, end agents left over from earlier logins by hand if desired (see `docs/ssh.md`).
