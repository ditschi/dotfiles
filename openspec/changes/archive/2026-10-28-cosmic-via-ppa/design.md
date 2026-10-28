# Design

## Context

The feature `cosmic` exists in the feature table (optional on desktops, excluded on servers and in containers) but has no packages. `tasks/resolve_packages.yml` only warns when it is selected. See proposal.md for the motivation.

Facts checked on 2026-10-26:

- Ubuntu 26.04 ("resolute") has no COSMIC packages in its own archive.
- The PPA `ppa:hepp3n/cosmic-epoch` (Launchpad, display name "COSMIC™ DE") publishes `resolute` and `stonking` (26.10), plus older `jammy`, `noble` and `devel` directories. Its signing key fingerprint is `EB141BFC014828F92C2EF883210C6A47471454A0`.
- `resolute/main/binary-amd64` contains 48 packages: COSMIC components, Pop themes and fonts, and a few metapackages. It contains no Mesa, Wayland, LLVM or Rust packages, although several install guides warn that the PPA replaces them. The PPA builds against Ubuntu's `-proposed` pocket.
- `cosmic-session` 1.11.0 depends on `cosmic-greeter`. `cosmic-greeter` provides `x-display-manager` and uses debconf, so installing it raises the question `shared/default-x-display-manager`.
- The owner's host runs Ubuntu 26.04.1 with `/etc/X11/default-display-manager` = `/usr/sbin/gdm3`. An old, disabled System76 PPA file for `noble` exists there; it is unrelated and stays untouched.
- Facts checked on 2026-10-28 on the owner's host: `/usr/bin/start-cosmic` exports `DCONF_PROFILE=/usr/share/dconf/profile/cosmic` (profile `user-db:cosmic`, `user-db:user`) and runs `systemctl --user import-environment ... DCONF_PROFILE ...`. Linger is on (`machine` enables it for the update timer), so the user manager outlives the COSMIC session and keeps the variable. The GNOME session started afterwards without a reboot ran with that profile: gnome-shell and the settings daemon read `~/.config/dconf/cosmic` first and wrote only there, GNOME showed the COSMIC font and icon settings, and `dconf reset` exposed the older value from `~/.config/dconf/user`. In GNOME 50 the session manager (`gnome-session-manager@.service`) is ordered `After=gnome-session-pre.target`, and `org.gnome.Shell@wayland.service` after `gnome-session-manager.target`; both take their environment from the user manager.
- No role in this repository adds a third-party apt source yet. The comment in `workstation.yml` notes that the uv-installed Ansible has no apt Python bindings.

## Goals / Non-Goals

**Goals:**
- A host that selects `cosmic` on a supported Ubuntu release can log in to COSMIC after `machine apply`, and GNOME remains available.
- Runs are idempotent, and unsupported platforms produce a clear warning instead of an apt failure.

**Non-Goals:**
- Configuring COSMIC itself (themes, panels, keybindings).
- Removing COSMIC or the PPA when the feature is deselected.
- Running a COSMIC session in CI (`tests-and-ci` excludes it).
- Supporting Ubuntu 24.04 through a different PPA.

## Decisions

**Install `cosmic-session` with its recommended packages.** This gives the session and the COSMIC apps (Term, Edit, Store, Player, Viewer). Everything else is already present on an Ubuntu desktop. The alternatives were rejected: `cosmic-session` without recommends leaves out the COSMIC apps, and the `cosmic-desktop` metapackage pulls in a whole Ubuntu desktop again (snapd, cloud-init, printer drivers and more).

**GDM stays the display manager.** The owner wants to keep GNOME as a fallback. `cosmic-greeter` as the only login screen was the alternative and was not chosen.

**Pop!_OS is left alone.** COSMIC is already part of Pop!_OS, so the feature has nothing to do there.

**Deselecting removes nothing.** This matches the other package features, which also do not uninstall anything when deselected. Removing only the source file was rejected because the packages would stay without updates. A full rollback with `ppa-purge` was rejected because it downgrades dependencies and is error-prone when run automatically. The role README documents the manual cleanup.

**Own role instead of a `packages_by_feature` entry.** The PPA has to exist before apt can install `cosmic-session`, and the display-manager preseed has to happen before the install. The package table installs everything in one apt call in the packages play. A role `cosmic_desktop` in its own play keeps these steps together and in order. `packages_by_feature` gets no `cosmic` entry.

**The key is pinned in the repository.** The armored public key is fetched once, its fingerprint is checked against the value above, and it is committed under the role's `files/`. Ansible installs it to `/etc/apt/keyrings/cosmic-epoch.asc` and references it with `Signed-By`. Fetching the key at run time was rejected because it trusts whatever the keyserver returns on every run.

**The source is a templated deb822 file** (`/etc/apt/sources.list.d/cosmic-epoch.sources`), not `deb822_repository` or `apt_repository`. Those modules need Python bindings (`python3-debian`, `python3-apt`) that the uv-installed Ansible lacks. A file also matches what `add-apt-repository` writes today.

**Platform check.** The role acts only when the distribution is `Ubuntu`, the version is at least 26.04, and the PPA publishes the host's codename. The codename check fetches `dists/<codename>/Release` from the PPA. Without it, a future Ubuntu release that the PPA does not build yet would add a source that fails `apt update` for every later apt task. Otherwise the role prints the warning required by the spec and stops.

**Display-manager preseed.** Before the install, the role reads the current display manager from `/etc/X11/default-display-manager` and preseeds `shared/default-x-display-manager` to it, defaulting to `gdm3` when the file is missing. This keeps the current display manager even if the non-interactive install would pick `cosmic-greeter`.

**Drop COSMIC's dconf profile when GNOME starts (owner decision).** The feature `cosmic` selects a dotfile group `cosmic` that ships `~/.config/systemd/user/drop-cosmic-dconf-profile.service` (`Type=oneshot`, `DefaultDependencies=no`, `Before=gnome-session-pre.target`, `ExecStart=systemctl --user unset-environment DCONF_PROFILE`) and a drop-in `~/.config/systemd/user/gnome-session-pre.target.d/drop-cosmic-dconf-profile.conf` with `Wants=` on it. A drop-in is a plain file, so nothing has to be enabled with `systemctl enable`, and the group needs no change to the `machine` CLI (`feature-selection`). The unit only removes the variable from the user manager; COSMIC sets it again on its next start. Alternatives not chosen: removing it when the COSMIC session ends (`ExecStop` bound to `cosmic-session.target`; misses a crashed session), rebooting after every COSMIC session, and turning linger off (the update timer needs it).

**The warning in `resolve_packages.yml` is removed.** The role prints its own warnings, which name the actual reason.

## Risks / Trade-offs

- [The PPA is unofficial, has a single maintainer, and builds against `-proposed`] → The feature stays optional and opt-in on desktops only. The key is pinned, so a key change is noticed instead of being accepted silently. The README names the source and the cleanup steps.
- [A later upload adds core packages such as Mesa that override Ubuntu's] → This is not the case for amd64 `resolute` today. The README tells the reader to check `apt policy` after upgrades. Pinning the PPA to COSMIC packages only was considered too fragile for now (package names change between releases).
- [The PPA drops a release or goes away] → The codename check turns this into a warning on the next run. Sources that are already installed would then fail `apt update`, and the README describes how to remove them.
- [The debconf preseed is ignored and `cosmic-greeter` becomes the default] → A post-install check that `/etc/X11/default-display-manager` is unchanged; it fails loudly if not.

- [GNOME changes the order of its session units, and the unit runs too late] → the verification task checks the environment after a COSMIC-then-GNOME login; the unit test pins the ordering the design relies on.
- [A running user manager does not see the new unit files] → `ensure_update_timer` already runs `systemctl --user daemon-reload` in `machine setup` and `machine update`. That it runs after the dotfile apply is an assumption that task 4.3 checks.

## Migration Plan

No host config lists `cosmic` in the committed state, so nothing changes until a host selects it. A host that already ran GNOME with the COSMIC profile keeps those GNOME settings only in `~/.config/dconf/cosmic`; after the fix GNOME reads `~/.config/dconf/user` again. The README describes how to carry the GNOME keys over by hand (on the owner's host this was done on 2026-10-28, leaving out `org/gnome/desktop/interface` and `org/gnome/desktop/wm/preferences`, which COSMIC set). Rollback: deselect the feature, then remove the source and packages by hand as the README describes (`ppa-purge ppa:hepp3n/cosmic-epoch`).
