# Design

## Context

On the ThinkPad L13 (Ubuntu 26.04) niri and DMS were installed by hand: `ppa:duxlabs/dux-repo` (niri, quickshell, ghostty, xwayland-satellite, dux-search) and `ppa:duxlabs/dms` (dms), both signed by the Launchpad key `6354D7C7146C2DD8F98892895ABFA2A5F21E824E` and added with `add-apt-repository` (`/etc/apt/sources.list.d/duxlabs-ubuntu-{dux-repo,dms}-resolute.sources`). GDM is still the display manager; `/usr/share/wayland-sessions/niri.desktop` offers the session. `dms.service` is wanted by `niri.service` (`~/.config/systemd/user/niri.service.wants/dms.service`), not by `graphical-session.target`, although the unit's `[Install]` says `WantedBy=graphical-session.target`.

Compared with a fresh `dms setup headless --compositor niri --terminal ghostty` in a scratch HOME, the host's `~/.config/niri/config.kdl` is DMS's stock config plus one `binds { F12 { spawn "ghostty" "+toggle-quick-terminal"; } }` block, and `~/.config/ghostty/config` is DMS's stock config plus `quick-terminal-position = top`, `quick-terminal-size = 45%, 85%`, `quick-terminal-autohide = true`. `ghostty +toggle-quick-terminal` toggles the layer-shell surface `ghostty-quick-terminal` (tested). With an existing `config.kdl`, `dms setup headless --skip-existing` skips the whole niri part. niri accepts a bind defined in both `config.kdl` and an include (the later one wins), and `include optional=true` tolerates a missing file; Ghostty's `config-file = ?name` is an optional include relative to its config.

The `repo-layout` spec puts root work into Ansible and user work into `machine` or `mise`. In setup and update the tool step runs before Ansible, so a step that needs the packages must run after Ansible.

## Goals / Non-Goals

**Goals:**
- Reproduce the L13 setup on any Ubuntu desktop with the feature `niri`.
- Keep DMS in charge of its own config so DMS updates and its settings UI keep working.
- Ship only the owner's additions (F12 drop-down terminal) from the repository.

**Non-Goals:**
- The DMS greeter / greetd as login screen (owner decision, 2026-11-18: keep GDM).
- Managing DMS settings (`~/.config/dms/settings.json`), wallpapers or plugins.
- Other distributions than Ubuntu, and removal when the feature is deselected.

## Decisions

- **No `dux-files`** (owner decision, 2026-11-18): the DMS file manager is not installed; the role installs only `niri`, `dms` and `ghostty`.
- **Feature `niri`, optional on desktops in both contexts** (owner decision, 2026-11-18). One feature covers compositor, shell and terminal; they are not useful apart here. Table row: `desktop: optional`, `server: excluded`, `container: excluded`, `groups: [niri]`.
- **Role `niri_desktop` modelled on `cosmic_desktop`.** Pinned key `files/duxlabs.asc` (one key for both PPAs, fingerprint checked by a unit test), deb822 sources `/etc/apt/sources.list.d/duxlabs-dux-repo.sources` and `duxlabs-dms.sources` (rendered from one template), a HEAD check of `dists/<codename>/Release` for both PPAs, a warning instead of a failure when either is missing. The role removes the `add-apt-repository` files `duxlabs-ubuntu-*-<codename>.sources` it replaces, so apt does not see a source twice. Packages: `niri`, `dms`, `ghostty` with recommends (DMS recommends the portals and gnome-keyring it uses). The display manager is read before and asserted after the install, as in `cosmic_desktop`.
- **DMS writes the base config, once.** A new `machine` step `niri config` runs after Ansible in `machine setup` and `machine update`, only with the feature, outside containers and when `dms` is installed. If `~/.config/niri/config.kdl` does not exist it runs `dms setup headless --compositor niri --terminal ghostty --skip-existing`, which also enables `dms.service` for the niri session. Alternative rejected: shipping the full `config.kdl` and Ghostty config from the repository; DMS edits and regenerates parts of them, and a symlinked copy would drift from DMS's stock config with every DMS release.
- **All own niri customizations live in the dotfile group, like the zsh config** (owner decision, 2026-11-18). `~/.config/niri/dotfiles.kdl` is a symlink into `home/niri/` and is the one place for the owner's niri settings (binds, window rules, layout overrides); editing it in `$HOME` edits the checkout, and every host with the feature gets it with the next dotfile apply. niri reloads its config on change, so an edit applies at once. Because it is included after DMS's files, its binds win over DMS's. More files can be added next to it and included from it. Today it holds F12 (drop-down terminal) and Mod+E (file manager). The group also ships `~/.config/ghostty/quick-terminal.conf` (the three quick-terminal lines). The `niri config` step appends `include optional=true "dotfiles.kdl"` to `config.kdl` and `config-file = ?quick-terminal.conf` to the Ghostty config when the line is missing; nothing else in those files is touched. Without any Ghostty config the step creates `config` with only the include line. With `optional`/`?`, deselecting the feature (the group's links are removed) leaves working configs.
- **Mod+E runs `xdg-open ~`** (owner decision, 2026-11-18): it opens the host's default file manager for folders, so it follows the desktop the host has (COSMIC Files on the L13 today, Nautilus on plain Ubuntu); no file manager is installed by the role.
- **DMS only in the niri session.** The step runs `dms systemd enable --compositor niri` (without the flag DMS targets the running compositor, and `machine update` usually runs from GNOME or COSMIC) when `niri.service.wants/dms.service` is missing (DMS's own way, as on the L13), and warns when `dms.service` is enabled for `graphical-session.target`, which would start it in GNOME and COSMIC too.
- **Tabs in the quick terminal are Ghostty's own** (owner decision, 2026-11-18): the quick terminal supports tabs and splits like a normal window; the docs list the keys, no extra config.
- **Completion.** niri (`_niri`, `niri`) and Ghostty (`_ghostty`, `ghostty.bash`) install their own completion files. DMS ships none: add `dotfiles_cache_eval dms dms completion zsh` to `dotfiles_cli_completions` and `dotfiles_cache_eval dms dms completion bash` inside the existing bash-completion guard in `tools.bash` (the Cobra script needs `_get_comp_words_by_ref`).

## Risks / Trade-offs

- [The duxlabs PPAs are maintained by a small group and replace Ubuntu packages like `quickshell`] → pinned key; the README lists `apt policy niri dms quickshell` and how to remove the PPAs with `ppa-purge`.
- [`dms setup headless` changes its output or flags in a later release] → the step only runs on hosts without a niri config; failures are reported by the step runner and do not stop setup.
- [On the L13 the inline F12 block stays next to the include] → harmless (same bind); the README says it can be removed.
- [The quick terminal opens slowly when no Ghostty instance runs] → accepted; `gtk-single-instance = true` from DMS's Ghostty config keeps later toggles fast.

## Migration Plan

On the L13 the next `machine update` adopts the install: the role replaces the two PPA source files with its own (same URIs and key), the step skips `dms setup` (config exists), adds the two include lines and finds `dms.service` already wanted by niri. Rollback: deselect the feature; packages stay, the includes are optional.
