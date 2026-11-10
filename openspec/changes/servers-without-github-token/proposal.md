# Proposal

## Why

`machine env pull` writes `~/.env` from the Bitwarden item `env/groups/private` on every host with the context `private`, servers included. That item holds `GITHUB_TOKEN`, so the private servers (privatecloud, contabo, homeserver, netmaster) get a GitHub token. The homelab servers must hold no GitHub credential except their per-host read-only deploy key (homelab repo `docs/compose-gitops.md`, "Host layout"; spec `homelab-node`, requirement "Push only with a forwarded agent key"). On 2026-11-09, `gh auth login` on privatecloud reported that the `GITHUB_TOKEN` environment variable was used for authentication.

## What Changes

- Every host with a context reads a device group item after its group item: `env/groups/<context>-desktop` on device `desktop`, `env/groups/<context>-server` on device `server` (so `private-desktop`, `private-server`, `work-desktop`, `work-server`). Both are written into `~/.env`; a missing item is skipped as today.
- The rule knows no key names: the group item holds the keys for every host of the context, the device items add keys only for desktops or only for servers. Moving a key between these items in Bitwarden is reflected on every affected host by the next pull.
- The owner moves `GITHUB_TOKEN` by hand from `env/groups/private` to `env/groups/private-desktop`, so only private desktops receive it. The work token stays in `env/groups/work` and reaches every work host as before.
- The env sync follows Bitwarden on every host: a key that the last pull wrote and the file left unchanged is removed when Bitwarden no longer sets it, instead of being carried over as a local-only key. This removes the old `GITHUB_TOKEN` line on the private servers. A local edit of such a key stays a conflict that the user resolves; a local removal goes back to Bitwarden with `machine env push`, as today.
- The backup made by that pull leaves out the lines removed because Bitwarden no longer sets them.
- `docs/secrets.md` describes the group and device items and how to move a key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `env-files`: hosts also read a device group item into `~/.env`; a key deleted in Bitwarden and unchanged locally is removed rather than carried over as local-only (changes "Local-only keys are carried over" and "Skip is preselected").

Affected profiles: every host with a context and the device `desktop` or `server`, private and work. Only the private servers (privatecloud, contabo, homeserver, netmaster) lose `GITHUB_TOKEN`; work hosts, including the work server ABTVL421, keep it. Containers without a context are unchanged.

## Impact

- Code: `machine_cli/core.py` (`ENV_GROUPS`), `machine_cli/profile.py` (`env_item_names`), `machine_cli/env_pull.py` (local-only detection against the last pull, backup).
- Tests: `tests/unit/test_update_and_env.py`, `tests/unit/test_machine_cli.py`.
- Docs: `docs/secrets.md`.
- Bitwarden (owner, by hand): new secure note `env/groups/private-desktop` with `GITHUB_TOKEN`, which is removed from `env/groups/private`. `env/groups/private-server`, `env/groups/work-desktop` and `env/groups/work-server` are created only when a key needs them.
- Consumers of `GITHUB_TOKEN` on servers: the github.com credential helper (spec `git-config`) finds no token on servers; on the homelab servers fetch uses the deploy key and push the forwarded agent key, as `homelab-node` requires.
- Outside the repo: the token has already been on public servers (privatecloud, contabo); the owner keeps it and does not rotate it (owner decision, 2026-11-10).

## Where the change is made

In the current checkout `/home/ditschi/dotfiles/.claude/worktrees/xenodochial-ellis-c9a21e`. It is not the live checkout (`machine repo` prints `/home/ditschi/dotfiles`), and AGENTS.md says to stay in a non-live checkout rather than create another worktree from it. The change touches `machine_cli`, which the host runs, so it must not be made in the live checkout.

## Assumptions

- A host with a context and the device `container` reads only its group item.
- A local-only key that the user chooses to add to Bitwarden from `~/.env` still goes to the shared group item (`env/groups/private` or `env/groups/work`).
- Leaving removed lines out of the backup applies to every line a pull removes because Bitwarden no longer sets it, on every host, not only to `GITHUB_TOKEN`.
- Keys without a Bitwarden origin (hand-written, never in an item) stay local-only as today.
- Keys already carried over in a local-only section with a `# was in <item>` origin stay there; the user chose to keep them before.
- Without a record of the last pull (no `env-generated/<file>`), the pull cannot tell a Bitwarden deletion from a local key and keeps today's local-only handling.
