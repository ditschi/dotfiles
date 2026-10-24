# Design

## Context

Files in `$HOME` are symlinks into the checkout (`~/dotfiles`), and the `machine` CLI changes both the checkout and the home (links, mise tools, profile, systemd user units). A copy of the home is not practical: it is large (tool installs, caches, Docker data) and links are absolute, so the test must see the home at the original path. The repository already has Docker tests per profile (`tests/integration`), but they start from an empty home, not from the state of a real host. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- Run any command against the current home of this host, interactively or as a one-off, with the host home unchanged.
- Usable before the installed `machine` is fixed or updated.
- See what a command changed.

**Non-Goals:**
- Testing Ansible system changes faithfully: the container is not the host system (no systemd, other packages). System steps run in the container only.
- Isolating secrets: the container sees the whole home, including keys and `~/.env`, like the user does.
- CI use; the testenv checks the state of one host.

## Decisions

- **A container with the current home, started by a helper in `machine` (owner request).** The helper offers a one-off command (`machine testenv -- COMMAND`) and an interactive shell (`machine testenv`). The real home is not modified.
- **The current state, nothing more (owner decision).** The testenv provides the home as it is and does not check out other revisions. Bringing in a newer revision is the job of the command under test (`machine update`) or a manual step inside, because the goal is to see what happens when those steps are run on this state. A `--ref` option was dropped for that reason.
- **Docker stays visible, the host profile is used.** `/.dockerenv` stays, so `machine` still skips Bitwarden, linger and the update timer, which cannot work in the container. `MACHINE_PROFILE_OVERRIDE` is set to the host's saved profile, so profile-dependent steps match the host. Without it, `machine setup --yes` chose the `container` profile and removed the update timer, which would not happen on the host. Hiding Docker (removing `/.dockerenv`) was rejected because the Bitwarden and systemd steps would then fail in the container.
- **`fuse-overlayfs`, not the kernel overlay.** With rootless Docker, host ids other than the user's own are unmapped in the container. The kernel overlay then fails to copy up such directories (`EOVERFLOW`, seen with `~/.local/bin` owned by group 999). `fuse-overlayfs -o squash_to_root` avoids this; rootful Docker uses `allow_other`. Needs `--device /dev/fuse` and `CAP_SYS_ADMIN`.
- **`CAP_SYS_ADMIN` only for the mount.** The command runs with `sys_admin` removed from its bounding set, so it cannot remount the read-only host home, also not through `sudo`. Rootless Docker additionally locks the read-only bind mount.
- **User identity.** Rootless: container uid 0 is the host user, so the image puts a passwd and shadow entry with the user's name and home before `root`; `whoami`, `~` and `sudo` behave as on the host, while the process is uid 0 inside. Rootful: a user with the host uid and gid and passwordless `sudo`.
- **Image from the host's distribution.** `FROM <ID>:<VERSION_ID>` from `/etc/os-release`, so binaries in the home (mise, uv, tool installs) find the same libc. The Dockerfile is generated in the module and the tag carries its hash, so a change rebuilds automatically; the entry script is passed at run time and needs no rebuild.
- **Same host name and login shell.** `--hostname` matches the host so `machine/hosts/<hostname>.yml` applies; commands run through the user's login shell (`zsh -lc` or `bash -lc`), so PATH is the one of a terminal. A single COMMAND argument is a shell script (quoted on the host); several are quoted and joined.
- **Standard library only.** `testenv.py` does not import the rest of `machine_cli`, so it runs from any checkout with `python3`, also when the installed CLI is broken.

## Assumptions (to be confirmed by the owner)

- **Overlay, not a copy.** The home is bind-mounted read-only as the lower layer of an overlay mounted on the home path inside; the upper layer is a Docker volume (disk, not tmpfs, because tool installs reach several GB). Copying (rsync, `docker cp`) was rejected: too slow and too large for a real home.

## Risks / Trade-offs

- [The host home changes while a testenv runs] → the overlay result is undefined for files changed below it; start a new testenv after host changes.
- [Commands differ inside the container: no systemd user bus, no Bitwarden CLI, other packages] → a failure that only appears in the container is checked on the host; system steps are not representative.
- [Kept volumes use disk space] → `--list` shows them; `docker volume rm machine-testenv-<name>` removes one.
- [uid 0 inside rootless Docker] → tools that check for root may behave differently than on the host.
