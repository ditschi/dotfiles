# Design

## Context

See proposal.md for the motivation. State found on 2026-10-31 by logging in to every host of the laptop's config:

- `~/.ssh/config` is hand-written and differs on every host. The copies on netmaster, homeserver and the NAS still point to port 5115 for hosts that now listen on 22, use addresses that changed (m93/m720q), and name a USG that was replaced by the UCG. Oracle holds the reverse-tunnel blocks (netmaster `localhost:2224`, homeserver `localhost:2223`); the tunnels work end to end. Contabo, the UCG and Home Assistant have no client config.
- The repository already versions user public keys in `machine/ssh_keys/` for `authorized_keys` (`sshd_home`, not exclusive), and Bitwarden holds each host's whole user key in `ssh/<class>/hosts/<hostname>`. The manual update compares local ↔ Bitwarden only; local ↔ repository is not checked.
- Hosts with dotfiles: laptops, homeserver, netmaster, Oracle (`privatecloud`, user `ubuntu`) and Contabo (as root, without host profile and without a user key). Devices without dotfiles: NAS, backup NAS, Home Assistant add-on, UCG, OctoPrint, Rinkhals, Vigor.
- zigbee2mqtt (`rpi-zero-2w-1`) no longer resolves and is dropped from the host list; m93 is powered off and stays out until it is reinstalled.
- The repository is public; addresses, users, ports and gateway data must stay out of it.

## Goals / Non-Goals

**Goals:**
- One alias per host that works at home, away and on the jump host.
- New hosts and keys are added through `machine` prompts, not by editing files on each host.
- Every host of a context converges to the same client config and the same trusted host keys.

**Non-Goals:**
- Changing `sshd_home` or how `authorized_keys` is filled.
- Backing up private sshd host keys.
- Managed host keys or routes for work hosts.
- Collecting ad-hoc hosts that were accepted with plain `ssh`.
- A periodic background scan for the home network.

## Decisions

**Public material in the repository, private material and network details in Bitwarden.** Public keys must propagate without a Bitwarden session: a new laptop must reach homeserver after a `git push` and the background update, without someone first logging in to homeserver to run a manual update. So user public keys stay in `machine/ssh_keys/` (the recorded decision of `ssh-host-keys-in-bitwarden`), and the sshd host keys join them in `machine/ssh_host_keys/`. Host lists contain addresses, users and tunnel ports and live in Bitwarden. Rejected: host keys as an extra field on the Bitwarden item `ssh/<class>/hosts/<host>` - devices without dotfiles have no such item (an SSH key item needs a private key), which would split the logic into two kinds of hosts, and the known-hosts file could then only be refreshed with Bitwarden. Rejected: `authorized_keys` from Bitwarden - chicken-and-egg for new hosts.

**Host list as ready `ssh_config` text in one secure note per context.** It is editable in the Bitwarden app and written 1:1, with a check by `ssh -G -F <tmp>` before writing. Rejected: a structured (YAML/JSON) note from which `machine` generates blocks - more uniform, but worse to edit by hand, and options such as the Vigor's legacy algorithms would need a passthrough anyway.

**Layer order follows ssh's first-match rule.** `Include ~/.ssh/config.local`, then `Include ~/.ssh/config.d/*`, then `Host *` defaults. ssh takes the first value per option, so host-only settings must come first and defaults last. `config.local` is named after `~/.gitconfig.local`.

**Local host blocks handled like local-only env keys.** The generated file is not a link; edits there would be overwritten. Reusing the `env-files` pattern (local-only section, numbered choices, skip preselected, attention item) keeps one mental model. `ssh/<context>/config` writes use the same "append with origin comment" style as env keys, applied to the note as read right before the write, after `bw sync`.

**`ssh-route` as `ProxyCommand` instead of `Match exec` rules.** `Match exec "tailscale status"` sees only whether Tailscale runs, not whether a connection works, and ssh never falls back after choosing a host. A `ProxyCommand` script probes each route and connects over the first that answers; `HostKeyAlias` makes all routes share one known-hosts entry. Rejected: separate `jump-*` aliases (today's state) - the user has to know where they are. Rejected: Tailscale MagicDNS names only - Tailscale is often logged out and drops connections.

**Home network learned from the target's host key.** A configured gateway MAC would silently go stale when the UCG is replaced. Instead the default gateway's hardware address is only a cache key: unknown networks are probed once with `ssh-keyscan -T1` at the LAN address, and a match with the alias's known host key marks the network as home. Away entries expire after 12 hours so that a probe does not slow every connection. A second home gateway is reported in `machine attention` so that old entries get cleaned up. Rejected: a fixed subnet test (`192.168.1.0/24` is common in foreign networks); `Match localnetwork` (needs OpenSSH 10 and older clients reject the whole file); a periodic scan (detection at connection time is enough, and an unused stale entry does no harm).

**Host key file names.** A host with a host profile uses its short hostname (`privatecloud`, even though its alias is `oracle`), so that it can find and write its own file. A device without a profile uses its alias. The host block sets `HostKeyAlias` to that name.

**Sync gap closed in the manual update, commit stays manual.** The manual update rewrites `machine/ssh_keys/<hostname>.pub` (only the selected key) and `machine/ssh_host_keys/<hostname>.pub` when they differ, also without Bitwarden, and lists unpushed key files as one attention item with `machine commit`. Rejected: automatic commit and push by `machine update`.

**Transition through the old config (owner decision).** The link replaces each hand-written `~/.ssh/config` with the first background update after the merge, long before every host has pulled the host list (netmaster cannot pull it at all yet). The old file is moved aside by the general dotfile rule as `config.pre-dotfiles`, and `machine apply` writes its sections that neither the host list nor `config.local` define to `config.d/90-legacy`. The list wins for every host it defines, so stale options such as port 5115 do not leak into listed hosts, and `machine attention` walks through the remaining hosts. Rejected: including the old file directly (its options would fill gaps in listed hosts, e.g. an old `Port`); moving it to `config.local` (stale entries would win over the list); only backing it up (all host entries missing until the next manual update with Bitwarden).

**`%k` as the alias for `ssh-route`.** ssh passes the host key alias as `%k` (the alias itself when no `HostKeyAlias` is set), so `ssh-route` checks the same name ssh verifies against, including `privatecloud` for the alias `oracle`. The jump host is recognised by its hostname or its `HostKeyAlias`. The script is plain Python 3 with the standard library and relays the connection itself, so it needs no `nc`.

**Base config mode fixed by `machine apply`.** Checkouts with umask 002 give the repository file mode 664. Debian and Ubuntu accept that for the linked config, other distributions reject it; `machine apply` sets it to 644.

**Shared defaults.** Keep-alive (30 s × 4) ends hanging sessions after about two minutes. Connection sharing (`ControlPersist 10m`, socket in `~/.ssh/cm/%C`) makes repeated connections and `scp`/`rsync`/`git` fast and runs `ssh-route` once per host; the short persist limits how long a master stays on an old route after a network change. `IdentitiesOnly yes` prevents "Too many authentication failures". `HashKnownHosts no` keeps known hosts readable. `AddKeysToAgent` is not set because the keys have no passphrase; `ForwardAgent` stays off and can be set per host in `config.local`.

**Work context stays lean.** One network, no jump host, few hosts: only the host list from `ssh/work/config`, no `ssh-route`, no managed host keys.

## Risks / Trade-offs

- [A control master stays on the old route after moving from home to away] → keep-alive ends it within about two minutes; `ssh -O exit <alias>` ends it at once; `ControlPersist` is only 10 minutes.
- [First connection on an unknown network costs up to about 1 s per skipped route] → result cached per gateway; repeated connections reuse the master.
- [Two hosts write the host-list note at the same time] → sync before write and apply the change to the current note; failures leave local data in place and record an attention item.
- [A device without dotfiles is reinstalled and gets a new host key] → ssh fails verification loudly; `machine ssh known-hosts add` replaces the key after confirmation.
- [Host list changes reach other hosts only with the next manual update] → `machine ssh pull`; host keys are not affected, they come with Git.
- [netmaster is aarch64 and `machine` has no Bitwarden CLI build for it, so it cannot pull the host list] → it keeps working with the base config and the managed host keys from Git; the host list follows once `bw` can be installed on aarch64 (separate change).
- [Host keys of nas-backup and OctoPrint were taken on first use (no earlier trust)] → recorded as such in the migration; confirm the fingerprints on the devices when convenient.

## Migration Plan

1. Host key files for nas, nas-backup, netmaster, homeassistant, homeserver, ucg, octoprint, privatecloud and contabo were collected on 2026-10-31. For netmaster, homeserver, contabo, privatecloud, ucg, nas and homeassistant the scanned key matched the key read over an already verified login; nas-backup and octoprint were first use. Also added: the user key of Oracle (`machine/ssh_keys/privatecloud.pub`) and of the NAS (`machine/ssh_keys/NAS-Ditscher.pub`).
2. The owner creates `ssh/home/config` in Bitwarden from the reviewed draft (from the scratch file of this change, not committed) once `ssh-route` is merged.
3. Rollout per host with `machine update`: the hand-written `~/.ssh/config` is moved aside as `~/.ssh/config.pre-dotfiles` and replaced by the link; its hosts stay usable through `config.d/90-legacy`; the host list and the known-hosts file are written. Then `machine attention` walks through the old hosts.
4. Rollback: remove the link and move `config.pre-dotfiles` back; the Bitwarden note and key files can stay.

## Open Questions

- Is the NAS reachable from outside on `nas.ditschers.de:5115`? From the LAN the port is refused; the block is kept unchanged until it is checked from outside.
- Rinkhals refuses the user key (password only) and offers no ed25519 host key on scan; it stays in the list without a managed host key.
- Contabo runs the dotfiles as root without a host profile and without a user key; whether it gets a host profile (and a key for `ssh_allow_from`) is left to a later `machine setup` there.
