# Tasks

Start only after `telegraf-runs-reliably` is archived (see design.md, "Order after `telegraf-runs-reliably`").

## 1. Host config carries `disk_space`

- [x] 1.1 Extend `parse_profile_text`, `format_profile_yaml` and `profile_fingerprint` in `machine_cli/core.py` to read, write and compare an optional `disk_space` list unchanged, and pass it through every writer in `machine_cli/profile.py` (`write_profile`, `save_host_config_to_repo`, `takeover_legacy_profile`) and their callers. Verify with unit tests in `tests/unit/test_host_profiles.py`: a round trip keeps the entry, a file without it gets no key, and a changed entry changes the fingerprint.
- [x] 1.2 Document `disk_space` (`path`, `min_free`, `min_free_percent`, `ignore`) in `machine/hosts/README.md`. Add the `/mnt/data` entry to `machine/hosts/ABTVL421.yml` only if the owner asks for a non-default threshold. Verify that the README example parses with `parse_profile_text` (unit test).

## 2. Detection and thresholds

- [x] 2.1 Add `machine_cli/disk_space.py` with a reader for `/proc/self/mountinfo` (injectable path) that returns read-write ext4/xfs/btrfs/vfat mounts, one per major:minor under its shortest mount point, plus mount points named in `disk_space`, without the ignored ones. Verify with unit tests on fixture mountinfo files: VM with `/` and `/mnt/data`, bind mount, btrfs subvolumes, overlay root (container), read-only mount, named tmpfs mount, named mount point not mounted.
- [x] 2.2 Add the threshold check on `statvfs` values (injectable): space low when `f_bavail` is below 5 % and below 20 GiB; inodes low when `f_files > 0` and `f_favail` is below 5 %; `disk_space` thresholds replace both space defaults; an invalid entry warns and falls back to the defaults. Verify with unit tests for every scenario of the spec "Low-space threshold" and "Threshold per mount point".

## 3. Attention item and cleanup

- [x] 3.1 Add a `disk` item per low filesystem to `attention_items()` in `machine_cli/attention.py` with the text `<mount> is <n> % full (<free> free of <total>)` (or free inodes). Verify with unit tests: two low filesystems give two items, none gives none, and the non-interactive run lists without measuring.
- [x] 3.2 Implement the resolution: measure the known space users that are on the same device (Docker data only with the feature `docker`, `/var/log/journal`, `/var/cache/apt/archives`, `~/.cache`, the mise cache), then offer the matching cleanups (`sudo apt-get clean`, `sudo journalctl --vacuum-size=200M`, `docker system prune`, `mise cache clear`), the scan `du -xh -d 2 <mount>` (top 20, `sudo` when not root) and "nothing" as the default. Print the free space after a cleanup. Verify with unit tests using a fake `system.run` and `system.choose`: nothing runs on the default, only matching cleanups are offered, `~/.cache` is never cleaned, Docker is offered only with `docker` on the same device.
- [x] 3.3 Mention the disk item in the `machine attention` part of `Readme.md`. Verify that the Readme list matches the spec `update-flow` "Attention entry point".

## 4. Recorded state, timer and status

- [x] 4.1 Write the state file `~/.local/share/machine/disk-state` (`key=value`, atomic replace, ready-made `segment=` text, empty when nothing is low) from a `machine disk --record` command and at the end of every `machine` command, including after `machine attention`. Verify with unit tests: low → segment text names all low mounts, nothing low → empty segment, a failed write does not fail the command.
- [x] 4.2 Add `home/systemd/.config/systemd/user/machine-disk-check.{service,timer}` (15 min, `OnBootSec=5m`) running `machine disk --record`, and enable it where `dotfiles-update-check.timer` is enabled in `machine_cli/updates.py`. Verify with a unit test for the enable call and the integration test in `tests/integration/test_profile_containers.py` that the timer file is installed.
- [x] 4.3 Add the disk line to `cmd_status` in `machine_cli/commands.py` (low mounts with usage and `machine attention`, no line otherwise). Verify with unit tests for both cases and that piped output has no color codes.

## 5. Prompt segment

- [x] 5.1 Read the disk state in `home/core/.zsh/update-state.sh` with builtins only and export `DOTFILES_DISK_SEGMENT`, re-evaluated with the update segment. Show it in `home/prompt/.config/starship.toml` (new `env_var` module next to the update segment), in the zsh `RPROMPT` fallback of `home/core/.zsh/config/03_theme.zsh` and in the bash `PS1` of `home/core/.bashrc`. Print nothing at shell start. Verify with tests next to the existing segment tests in `tests/unit/test_zsh_handoff.py`: segment shown for a low state, both segments together, nothing for an empty or missing file, no extra process started.
- [x] 5.2 Describe the disk segment and the timer in `Readme.md` next to the update segment. Verify with `pre-commit run --all-files`.

## 6. Integration checks

- [x] 6.1 Run `pre-commit run --all-files` and `pytest tests/unit -q` and verify that both pass.
- [x] 6.2 On ABTVL421, run `machine update`. Verify that `systemctl --user list-timers machine-disk-check.timer` shows the timer, that `machine status` shows no disk line while `/` and `/mnt/data` have enough space, and that a temporary `disk_space` entry with `min_free` above the current free space of `/mnt/data` makes the item, the status line and the prompt segment appear (remove the entry afterwards). Verified on 2026-10-30 with `machine update --skip-ansible` (the system step needs a sudo password over SSH): the timer is enabled and fires every 15 minutes; with `/` at 78 % and `/mnt/data` at 86 % there was no disk line; a temporary `min_free: 500G` for `/mnt/data` in the applied host config produced the `[disk]` attention item, the status line and `segment=⚠ disk /mnt/data 86%`, which both bash and zsh read into `DOTFILES_DISK_SEGMENT` (checked with a state file, not a live prompt); the entry was removed afterwards.

## Workflow follow-up

- Archive the change after review, then check that `openspec/specs/disk-space/spec.md` has its Purpose and that "Attention entry point" in `openspec/specs/update-flow/spec.md` names low disk space.
