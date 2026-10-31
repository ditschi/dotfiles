# Proposal

## Why

A `BW_SESSION` in the environment or in `~/.env.local` means that Bitwarden is set up on the host and that the user expects `machine` to use it. Today an expired session is only reported in passing (for example "SSH host key not checked: Bitwarden is not unlocked"), the interactive update does not renew it, and the background update does not notice it at all. An expired session should be renewed right away in an interactive run, and the background update should raise a needs-attention item so that the user knows to log in again.

## What Changes

- A host *expects Bitwarden* when `BW_SESSION` is set in the environment or in `~/.env.local`.
- In an interactive run (terminal, without `--yes`) an expected but expired or locked session is renewed at once, without a yes/no question: `bw unlock`, or `bw login` and unlock when logged out. The new session replaces the saved one in `~/.env.local`.
- Without a terminal, including the background update, an expected session that `bw status` does not report as unlocked records a needs-attention item and a prompt segment; the item offers to log in now. The background update calls only `bw status` for this, and only when Bitwarden is expected.
- When a valid session is seen again, the item and the segment are cleared.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `secret-tools`: expected Bitwarden, interactive renewal, attention item and prompt segment for an expired session, replacing a saved session.
- `ssh-host-keys`: the background update may call `bw status` when Bitwarden is expected; the manual update renews an expected session in a terminal before the key check.

## Impact

Hosts with a saved or exported `BW_SESSION` (private and work). Code: `machine_cli/bw_client.py`, the callers that use `bitwarden_session_ready` (`ssh_keys.py`, `ssh_client.py`), `machine_cli/auto_update.py`, `machine_cli/attention.py`, `home/core/.shell/common/update-state.sh`, `home/prompt/.config/starship.toml`, unit tests. Hosts without `bw` (for example the aarch64 hosts) are unchanged.

Made in the worktree `.worktrees/bitwarden-session-renewal`, because `machine_cli` and the shell files are used live from the main clone.
