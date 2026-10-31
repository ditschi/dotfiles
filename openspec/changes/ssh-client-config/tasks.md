# Tasks

## 1. Key data (done during planning)

- [x] 1.1 Collect the ed25519 host keys of nas, nas-backup, netmaster, homeassistant, homeserver, ucg, octoprint, privatecloud and contabo into `machine/ssh_host_keys/`, cross-checked against verified logins where possible, with a README
- [x] 1.2 Add the missing user public keys `machine/ssh_keys/privatecloud.pub` (Oracle) and `machine/ssh_keys/NAS-Ditscher.pub`
- [x] 1.3 Reduce `machine/ssh_keys/ditschi-ThinkPad-L13-Yoga-Gen-2.pub` to the selected key (via the new update check in 4.2, not by hand)

## 2. Base config

- [x] 2.1 Add `home/core/.ssh/config` with the includes and `Host *` defaults from the `ssh-client-config` spec
- [x] 2.2 `machine apply`: create `~/.ssh/cm` (700) and `~/.ssh/config.d` (700), set the repository file to 644; a regular `~/.ssh/config` is moved aside as `config.pre-dotfiles` (existing dotfile rule) and its remaining hosts are written to `config.d/90-legacy` with an attention item
- [x] 2.3 Unit tests: `ssh -G` on the base config with and without `config.local`/`config.d`, mode fix, one-time backup

## 3. ssh-route

- [x] 3.1 Add `home/core/.local/bin/ssh-route`: argument parsing (`%n`, `lan=`, `ts=`, `jump=`), route order, error summary
- [x] 3.2 Network cache in `~/.cache/ssh-route/networks`: gateway hardware address → home/away with timestamp, away expiry 12 h, learning via `ssh-keyscan -T1` against the known host key of the `HostKeyAlias`
- [x] 3.3 Tailscale tier (installed, logged in, peer online, probe) and jump tier with the local shortcut on the jump host
- [x] 3.4 Second home gateway: event without hardware address and attention item with "remove older entry"
- [x] 3.5 Unit tests with stubbed `ip`, `ssh-keyscan`, `tailscale`, `nc`/`ssh`: home, away, replaced gateway, foreign network with same subnet, Tailscale hanging, on the jump host, no route

## 4. Host keys and sync gap

- [x] 4.1 Generate `~/.ssh/known_hosts.d/home` from `machine/ssh_host_keys/*.pub` in `machine apply` (also background) on private hosts only
- [x] 4.2 Manual update and setup on home hosts: write `machine/ssh_keys/<hostname>.pub` (selected key only) and `machine/ssh_host_keys/<hostname>.pub` when missing or different, without Bitwarden
- [x] 4.3 Attention item "SSH key files not pushed yet" with `machine commit`
- [x] 4.4 `machine ssh known-hosts add <alias>`: resolve address via `ssh -G`, keyscan, fingerprint confirm, keep-existing default on difference
- [x] 4.5 Tests in `tests/unit/test_ssh_client.py` (next to `test_ssh_host_keys.py`): repo check without session, extra key removed, unpushed item, known-hosts generation, work host gets no file

## 5. Host list from Bitwarden

- [x] 5.1 Read `ssh/home/config` / `ssh/work/config` and write `~/.ssh/config.d/20-<class>` (600) in setup, manual update and `machine ssh pull`; validate with `ssh -G -F`; keep the file on errors or without session; no `bw` in the background update
- [x] 5.2 Detect local host blocks, carry them into a marked local-only section, numbered choices (add to Bitwarden / move to `config.local` / remove / skip), attention item
- [x] 5.3 Safe note writes: `bw sync`, apply to current note content, origin comment, failure keeps local data and records an attention item
- [x] 5.4 Unit tests with a fake `bw`: pull, missing note, invalid note, local block choices, concurrent change, write failure, work host reads only `ssh/work/config`

## 6. Commands and setup

- [x] 6.1 `machine ssh add [alias]` with prompts, route questions on private hosts (builds the `ssh-route` `ProxyCommand` and `HostKeyAlias`), target choice, preview, login test with hints
- [x] 6.2 `machine ssh edit` (editor, ssh validation, edit again/discard) and `machine ssh remove <alias>`
- [x] 6.3 `machine setup` offer "add this host to the SSH list" with prefilled values
- [x] 6.4 Zsh/Bash completion for the new `machine ssh` subcommands: `machine ssh` is a click group, so the generated `machine completion` covers them
- [x] 6.5 Unit tests for add/edit/remove/setup offer, including alias already present and declined offer

## 7. Documentation

- [x] 7.1 Readme: SSH client section (layers, `config.local`, `machine ssh` commands, `ssh-route`, how to add a host)

## 8. Validation

- [x] 8.1 `pytest tests/unit -q` (shared update/attention paths and cross-module contracts change); record result
  - 2026-10-31: 796 passed; after black formatting the affected files (`test_ssh_client.py`, `test_ssh_route.py`, `test_ssh_host_keys.py`, `test_update_and_env.py`, `test_machine_cli.py`) again: 208 passed
- [x] 8.2 `pre-commit run --files` on all changed and added paths; record result
  - 2026-10-31: all hooks pass after black reformatted six files and an unused import was removed
- [x] 8.3 `openspec validate ssh-client-config --strict`
  - 2026-10-31: valid
- [ ] 8.4 Manual check on the laptop: `ssh homeserver` at home and with the LAN route blocked (jump), `ssh nas` without prompt, on Oracle `ssh homeserver` without jump; record results
  - 2026-10-31, before rollout, with the worktree's `ssh-route` as explicit `ProxyCommand`: LAN route to homeserver ok (home gateway learned, 0.9 s), jump route through Oracle ok, `scp` over the LAN route ok. Open until merged and `ssh/home/config` exists: alias with managed known hosts without prompt, Oracle local-tunnel shortcut

## Workflow follow-up

- Owner creates `ssh/home/config` in Bitwarden from the reviewed draft, then runs `machine update` on each private host.
- Archive inside the worktree; ask the owner before merging the branch and removing the worktree.
