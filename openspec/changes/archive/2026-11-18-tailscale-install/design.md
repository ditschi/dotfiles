# Design

## Context

The feature table already offers `tailscale` (optional on private desktops and servers, excluded for work and in containers), and `machine setup` offers `sudo tailscale up` after Ansible. What is missing is the install. Ubuntu and Debian ship no `tailscale` package; Tailscale publishes its own apt repository at `https://pkgs.tailscale.com/stable/<distro>` with suites per release codename (Ubuntu 26.04 `resolute` is served). The ThinkPad L13 runs Tailscale 1.102 as a snap (`snap.tailscale.tailscaled` active). The role `cosmic_desktop` is the existing pattern for a third-party apt repository: pinned key in `files/`, deb822 source from a template, a HEAD check of `dists/<codename>/Release` before adding anything.

## Goals / Non-Goals

**Goals:**
- Install Tailscale on hosts that select the feature, from the vendor's repository with a pinned key.
- Move the L13 from the snap to the apt package once, by hand, without a new login.
- Make the setup message match what actually happens.

**Non-Goals:**
- Logging in or configuring the tailnet (stays the interactive `sudo tailscale up` offer in setup).
- Removing Tailscale when the feature is deselected.

## Decisions

- **Own role `tailscale` instead of a line in `packages_by_feature`.** The package needs a repository first, and the existing-install check and the release check do not fit the plain package list. Pattern and layout follow `cosmic_desktop`, so both third-party repositories read the same way.
- **Official repository, not the `curl | sh` installer and not the snap.** The owner chose the official apt repository (owner decision, 2026-11-18). The install script would fetch and run code on every run; the snap is not available in all host types the feature covers and adds a second update mechanism.
- **Pinned key in the repository.** `files/tailscale.asc` holds Tailscale's package signing key (fingerprint `2596A99EAAB33821893C0A79458CA832957F5868`); a unit test checks the fingerprint, as for the COSMIC key. The key is not downloaded at run time, so a compromised download cannot slip in another key. Key: `/etc/apt/keyrings/tailscale.asc`; source: `/etc/apt/sources.list.d/tailscale.sources` (deb822, `Signed-By` the key).
- **Distribution mapping.** `ansible_facts.distribution` Ubuntu → `ubuntu`, Debian (also Raspberry Pi OS) → `debian`; the suite is `ansible_facts.distribution_release`. Anything else, or a 404 for `dists/<codename>/Release`, gives the warning and installs nothing.
- **The snap is moved by hand, once; the role never touches it** (owner decision, 2026-11-18). Only the L13 has the snap. Automatic migration code would stay in the role and run on every update of every host for a one-time move, and it stops Tailscale, which on a remote host reached through Tailscale could cut off access if a step fails. With the snap present the role installs nothing (two `tailscaled` must never run at once) and points to the README: stop the snap, copy `/var/snap/tailscale/common/tailscaled.state` to `/var/lib/tailscale/`, `snap remove --purge tailscale`, `machine update`. The copied state keeps the node name and address. The goal of one setup on every host stays; the move is done once by hand. Alternatives rejected: keeping the snap (hosts would differ) and an automatic migration in the role (first implementation).
- **A host set up with Tailscale's install script is adopted.** That script writes `/etc/apt/sources.list.d/tailscale.list` with the same repository; the role removes that file when it writes `tailscale.sources`, so apt does not see the source twice. The installed package stays.
- **Service.** The package enables `tailscaled` itself; the role does not manage the service. The feature is excluded in containers, so `machine_manage_services` needs no special case.
- **netmaster and homeserver get the feature** (owner decision, 2026-11-18). On 2026-11-18 neither had Tailscale (no package, snap, container or `tailscale0`); netmaster runs Debian 13 trixie, homeserver Ubuntu 24.04, both served by the repository. `tailscale` is added to `machine/hosts/netmaster.yml` and `machine/hosts/homeserver.yml`; each is logged in once with `sudo tailscale up`. contabo already selects the feature and gets the install with this change; privatecloud could not be checked (SSH login refused).
- **Setup message.** Without the binary, `maybe_tailscale_login` logs "tailscale not installed (see the Ansible output); later: sudo tailscale up" instead of "package install via ansible", which was wrong whenever Ansible was skipped or failed.
- **Completion.** `tailscale completion zsh|bash` generates Cobra completions. Zsh: one `dotfiles_cache_eval tailscale tailscale completion zsh` line in `dotfiles_cli_completions` (runs after compinit). Bash: the script calls `_get_comp_words_by_ref` from bash-completion, so the line goes into the existing block guarded by `declare -F _get_comp_words_by_ref`; without bash-completion nothing is loaded and the shell starts normally.

## Risks / Trade-offs

- [Tailscale rotates its signing key] → apt update fails with a signature error; the fingerprint test documents the expected key, update `files/tailscale.asc` from `https://pkgs.tailscale.com/stable/ubuntu/<codename>.noarmor.gpg`.
- [New release not yet in the repository right after an Ubuntu release] → warning, no failure; the next run after Tailscale adds the suite installs it.
- [State copy forgotten or the state format differs during the manual move] → `tailscale status` shows logged out; `sudo tailscale up` logs in again (new node, old node to delete in the admin console).

## Migration Plan

No migration. `contabo` and `privatecloud` get Tailscale on their next `machine update`; the ThinkPad is moved by hand with the README commands, then `machine update` installs the package. Deselecting the feature removes nothing; the README lists `sudo apt remove tailscale` and the two files to delete.
