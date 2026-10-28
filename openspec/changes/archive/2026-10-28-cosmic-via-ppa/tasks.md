# Tasks

## 1. Role `cosmic_desktop`

- [x] 1.1 Fetch the PPA's armored public key (fingerprint `EB141BFC014828F92C2EF883210C6A47471454A0`) and commit it as `ansible/roles/cosmic_desktop/files/cosmic-epoch.asc`. Verify that `gpg --show-keys` prints exactly that fingerprint.
- [x] 1.2 Add a unit test that reads the committed key with `gpg --show-keys --with-colons` and asserts the fingerprint, so a swapped key fails CI. Verify that `pytest tests/unit -q` passes.
- [x] 1.3 Add the platform check to the role: act only when `ansible_facts.distribution == 'Ubuntu'`, the version is at least `26.04`, and `dists/<codename>/Release` of the PPA answers 200. Print no warning on Pop!_OS. On every other platform print a warning that names the release and the reason, then end the role. Verify that `ansible-lint ansible/*.yml` passes.
- [x] 1.4 Install the key to `/etc/apt/keyrings/cosmic-epoch.asc` and template `/etc/apt/sources.list.d/cosmic-epoch.sources` (deb822, `Suites: <codename>`, `Components: main`, `Signed-By:` the keyring path). Refresh the apt cache (without `cache_valid_time`) when the key or source changed or `cosmic-session` has no candidate yet. Verify that `ansible-lint ansible/*.yml` passes.
- [x] 1.5 Read `/etc/X11/default-display-manager` (default `gdm3` when missing), preseed `shared/default-x-display-manager` to it for `gdm3` and `cosmic-greeter`, install `cosmic-session` with recommends, then assert that `/etc/X11/default-display-manager` is unchanged. Verify that `ansible-lint ansible/*.yml` passes.
- [x] 1.6 Write `ansible/roles/cosmic_desktop/README.md`: purpose, the supported releases, the source and key with their fingerprint, the note that GDM stays the display manager, that deselecting removes nothing, the manual cleanup (`ppa-purge ppa:hepp3n/cosmic-epoch`, removing the `.sources` file and the keyring), and the advice to check `apt policy` for core packages after upgrades. Verify that `pre-commit run --all-files` passes.

## 2. Wiring and cleanup

- [x] 2.1 Add a play "COSMIC desktop" to `ansible/workstation.yml` after the packages play, with the role gated by `'cosmic' in machine_features`. Verify `ansible-playbook --syntax-check ansible/workstation.yml`, and check that `pytest tests/unit -q` (including the system-relevance tests) passes.
- [x] 2.2 Add a unit test (next to the feature-table tests in `tests/unit/test_features.py`) that `cosmic` is offered on private and work desktops and dropped by `features.split` for a server and a container. Verify `pytest tests/unit -q` passes.
- [x] 2.3 Change the `cosmic` help text in `ansible/group_vars/all/features.yml` to "COSMIC desktop session (Ubuntu 26.04+ via PPA; built into Pop!_OS)". Remove the task "Warn when Cosmic selected on non-Pop" from `ansible/tasks/resolve_packages.yml`. Verify that `git grep -n -i 'Cosmic selected'` finds nothing and that `pytest tests/unit -q` passes.
- [x] 2.4 Update the docs: the role tree and the feature notes in `Readme.md`, and the role table in `ansible/README.md` (`cosmic_desktop` | `cosmic`, Ubuntu 26.04+, nothing on Pop!_OS). Verify that `pre-commit run --all-files` passes.

## 3. Verification

- [x] 3.1 Run `pre-commit run --all-files`, `pytest tests/unit -q` and `ansible-lint ansible/*.yml`. All three must pass.
- [x] 3.2 On the owner's Ubuntu 26.04 desktop, select `cosmic` and run `machine apply`. Verify that `apt policy cosmic-session` shows the PPA as the source, that `/etc/X11/default-display-manager` still names `gdm3`, and that GDM offers both GNOME and COSMIC sessions. Run `machine apply` again and check that the role reports no changes.
  Result (2026-10-28): `cosmic-session` 1.11.0 from `hepp3n/cosmic-epoch resolute/main`, `/etc/X11/default-display-manager` = `/usr/sbin/gdm3`, GDM offers GNOME, Ubuntu and COSMIC; the second `machine apply` reported every task of the play "COSMIC desktop (Ubuntu via PPA)" as `ok` or `skipping`.
- [x] 3.3 After the install, check with `apt policy libgl1-mesa-dri libwayland-client0` that core graphics packages still come from the Ubuntu archive. Note the result in the role README if it differs.

## 4. GNOME after COSMIC without the COSMIC dconf profile

- [x] 4.1 Declare the dotfile group `cosmic` in `mise.toml` (root `home/cosmic`) and set `groups: [cosmic]` for `cosmic` in `ansible/group_vars/all/features.yml`. Add a unit test that the feature `cosmic` selects the group `cosmic`. Verify that `pytest tests/unit -q` passes.
- [x] 4.2 Add `home/cosmic/.config/systemd/user/drop-cosmic-dconf-profile.service` (`Type=oneshot`, `DefaultDependencies=no`, `Before=gnome-session-pre.target`, `ExecStart=/usr/bin/systemctl --user unset-environment DCONF_PROFILE`) and `home/cosmic/.config/systemd/user/gnome-session-pre.target.d/drop-cosmic-dconf-profile.conf` (`[Unit]` `Wants=drop-cosmic-dconf-profile.service`). Add a unit test for the ordering, the command and the `Wants=`. Verify with `systemd-analyze --user verify` on both files and `pytest tests/unit -q`.
- [x] 4.3 Check that `machine update` runs `systemctl --user daemon-reload` after the dotfile apply, so a running user manager loads the new files. If it does not, report it to the owner instead of changing the CLI on the side.
  Result (2026-10-28): `machine setup` reloads after the dotfile apply, but `machine update` calls `ensure_update_timer` (and with it `daemon-reload`) before the apply, and `machine update --auto` not at all. Reported to the owner. Right after `machine update` the running manager showed `NeedDaemonReload=yes` and no drop-in for `gnome-session-pre.target`, but the GNOME logout unloaded the target, and the next GNOME login (21:42, without `daemon-reload`) loaded it with the drop-in. No CLI change needed for this fix.
- [x] 4.4 Document the cause, the fix and the manual workaround (`systemctl --user unset-environment DCONF_PROFILE`, then log out and in; carrying GNOME keys from `~/.config/dconf/cosmic` to `user`) in `ansible/roles/cosmic_desktop/README.md` and the COSMIC feature note in `Readme.md`. Verify that `pre-commit run --all-files` passes.
- [x] 4.5 On the owner's host: log in to COSMIC, log out, log in to GNOME without a reboot. Verify that `systemctl --user show-environment` has no `DCONF_PROFILE`, that `tr '\0' '\n' < /proc/$(pgrep -x gnome-shell)/environ` has none either, and that a changed GNOME setting lands in `~/.config/dconf/user`.
  Result (2026-10-28): GNOME → COSMIC → GNOME without a reboot and without `daemon-reload`: the unit ran at the GNOME start, neither the user manager nor gnome-shell has `DCONF_PROFILE`, and GNOME writes `~/.config/dconf/user` again (COSMIC kept writing `~/.config/dconf/cosmic`).
