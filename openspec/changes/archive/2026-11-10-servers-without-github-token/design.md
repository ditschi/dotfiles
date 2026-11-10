# Design

## Context

See proposal.md - Why. Today `env_item_names()` (`machine_cli/profile.py`) picks the items from the context only: `env/groups/<group>` for each group in `ENV_GROUPS[context]` (`machine_cli/core.py`), then `env/hosts/<hostname>`. `_env_generated()` (`machine_cli/env_pull.py`) writes every item except the last into `~/.env` under a `# --- <item> ---` section (later items win) and the host item into `~/.env.host`. `env_files()` maps `~/.env` to the first item, which is the target for "add to Bitwarden". `machine env push` writes a changed key back to the item named by its section, so it already handles more than one group item per file. The device (`current_device()`) is known but not used for items.

A key that the existing file sets but no generated file or `~/.env.local` sets is a local-only key: it is carried into a `# --- local only ---` section and offered for "add to Bitwarden" (spec `env-files`). `local_only_content()` already records in `was_in` the item a key came from (its section in the last generated file, or a `# was in <item>` marker once it was carried over).

Host configs with the device `server`: privatecloud, contabo, homeserver, netmaster (context `private`) and ABTVL421 (context `work`, keeps the work token).

## Goals / Non-Goals

**Goals:**
- Desktops and servers get a device group item; the private `GITHUB_TOKEN` lives only in `env/groups/private-desktop`.
- A server's `~/.env` holds no `GITHUB_TOKEN` after the first pull following the update and the move in Bitwarden.

**Non-Goals:**
- Moving keys in Bitwarden (the owner does it by hand).
- Cleaning older files in `env-backup/`.
- Rotating the token: the owner keeps it (owner decision, 2026-11-10).

## Decisions

**Group item plus device item (owner decision, 2026-11-10).** Hosts read `env/groups/<context>`, then `env/groups/<context>-desktop` on desktops or `env/groups/<context>-server` on servers. The owner moves `GITHUB_TOKEN` to the desktop item so only desktops receive it; keys are synced from Bitwarden like the existing items. Rejected alternative: a filter in `machine env pull` that drops desktop-only keys on servers while keeping them in the shared item; with separate items the token never reaches a server, and Bitwarden alone describes what each kind of host gets.

**One rule for every context, no key names in code (owner decision, 2026-11-10).** There are three items per context: the group item for every host of the context, and a device item that adds keys only for desktops or only for servers. The code applies this rule and knows no key names; Bitwarden alone decides which host gets a key, and moving a key between the items is reflected on every affected host by the next pull. The device items exist for work too, for cases that need them, but the work `GITHUB_TOKEN` stays in `env/groups/work` and keeps reaching every work host, ABTVL421 included.

**Item names from context and device.** `ENV_GROUPS` keeps the group per context; `env_item_names()` appends `<group>-<device>` when the device is `desktop` or `server`, before the host item. The device item thus lands in `~/.env` and wins over the shared item, while `env_files()` keeps the shared group item as the "add to Bitwarden" target.

**Only GITHUB_TOKEN moves for now (owner decision, 2026-11-10).** Further keys are moved later by name in Bitwarden; no code change is needed for that.

**The owner moves the key by hand (owner decision, 2026-11-10).** `docs/secrets.md` describes creating the desktop item and moving the line. This keeps the rule that machine moves nothing in Bitwarden without the user.

**The env sync follows Bitwarden on every host (owner decision, 2026-11-10).** The pull compares three versions of each key: the last pull (`env-generated/<file>`), the current file and the new Bitwarden content. Changed in Bitwarden but not locally → the file takes the Bitwarden state, which for a deleted key means it is removed without a prompt. Changed locally → it is a local edit: in a terminal the existing push / discard / skip choice resolves the conflict, without one the file stays unchanged with an attention item. Removed locally → also a local edit, which `machine env push` sends back to Bitwarden as a removal. Only the first case is new: `env_unpushed_edits()` and `machine env push` already cover the other two, while `env_local_only()` today treats a key deleted in Bitwarden as local-only ("was in …; deleted there?"). It now leaves out keys that the last pull wrote from an item and the file holds unchanged. This removes the old `GITHUB_TOKEN` line on the servers without key names in the code. Rejected alternatives: a list of desktop-only key names in `machine_cli`, removal on servers only (an earlier answer, replaced by this decision), and removing the line by hand via `machine attention`.

**Backup without removed lines (owner decision, 2026-11-10).** The backup a pull makes of a file leaves out the lines it removes because Bitwarden no longer sets them, so the new backup does not hold the token. Older backups are left alone; the log names the backup directory once.

## Risks / Trade-offs

- [A key deleted from a Bitwarden item by mistake disappears from every host that left it unchanged, and the new backup does not keep it] → Accepted by the owner with the decision above; recovery is from Bitwarden (item history) or an older backup.
- [The owner moves the token before a server runs the new code] → Old code then carries the line into the local-only section with a `# was in` origin, where it stays as a kept local-only key. Docs say to update the servers first; otherwise the owner picks "remove" in `machine attention`.
- [Desktops pull after the key was removed from the shared item but before the desktop item exists] → The desktop's line is removed and comes back with the next pull once the desktop item exists; docs state the order: create the desktop item first.
- [Something on a server relied on `GITHUB_TOKEN` over HTTPS] → On homelab servers fetch uses the deploy key and push the forwarded agent key; a host that needs a token can set one in `env/hosts/<hostname>` or `~/.env.local`.

## Migration Plan

1. Merge; run `machine update` on all servers and desktops (no visible change while the items are unchanged).
2. Owner creates `env/groups/private-desktop` with `GITHUB_TOKEN`, then removes the key from `env/groups/private`.
3. `machine update` (or `machine env pull`) on each host: desktops keep the token from the desktop item, servers drop the line.

Rollback: move `GITHUB_TOKEN` back to `env/groups/private` and revert the commit.
