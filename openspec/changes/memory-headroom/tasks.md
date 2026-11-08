# Tasks

## 0. Owner confirmation

- [x] 0.1 Get the owner's answers to Open Questions 1-9 in design.md (swap size rule, `MemoryHigh` per RAM size, further protection of the Claude app, oomd limit or oomd off, the `python3` process, Claude Code sessions, feature name and table values including VMs, `ManagedOOMSwap` on `-.slice`, `OOMPolicy=continue`) and to the Alternatives considered. Record the answers in design.md (move them from Open Questions into Decisions, and update the Implementation outline and Alternatives considered with the owner's reasons) and adjust the scenarios in `specs/` before any code task.

## 1. Verification on the L13

- [x] 1.1 On ThinkPad-L13-Yoga-Gen-2 (systemd 259), with the Claude desktop app running: check that `systemctl --user show <Claude scope> -p MemoryHigh` reports 8 GiB from the hand-made drop-ins, that `systemctl show user@$(id -u).service -p ManagedOOMMemoryPressureLimit` reports 80 %, that `swapon --show` lists zram at priority 100 and `/swap.img` with 16 GiB below it, and read `ManagedOOMSwap` of `-.slice` (`systemctl show -- -.slice -p ManagedOOMSwap`). Check in `systemd.resource-control(5)` of systemd 259 how `ManagedOOMPreference=` is treated for user cgroups. Replace the matching Assumptions in design.md with the verified facts.

## 2. Feature and dotfile group

- [x] 2.1 Add tests to `tests/unit/test_features.py` for the table values of `memory-headroom` and its group (scenarios of `specs/feature-selection/spec.md`); verify they fail.
- [x] 2.2 Add the row `memory-headroom` to `ansible/group_vars/all/features.yml`; verify `pytest tests/unit/test_features.py -q` passes.
- [x] 2.3 Add the group `home/memory-headroom/.config/systemd/user/` with `app-gnome-com.anthropic.Claude-.scope.d/50-memory-high.conf` and `app-com.anthropic.Claude-.scope.d/50-memory-high.conf` (`[Scope]`, `MemoryHigh=8G`, `OOMPolicy=continue`, a comment naming the reason), and a test that both exist with that content. `systemd-analyze verify` cannot load scope units from files ("Unit ... not found", checked with systemd 259), so the test checks the section and the settings directly.

## 3. Role `memory_headroom`

- [x] 3.1 Write `tests/unit/test_swapfile_grow.py` with the cases listed under Testing in design.md (grow order, already large enough, too little free disk space or RAM, btrfs, failure handling, no active swap file); verify they fail.
- [x] 3.2 Add `ansible/roles/memory_headroom/files/swapfile-grow` as outlined in design.md; verify `pytest tests/unit/test_swapfile_grow.py -q` passes.
- [x] 3.3 Write `tests/unit/test_memory_headroom_role.py` (role on localhost, `machine_manage_services: false`, paths under `tmp_path`): content of the oomd drop-in and of the `-.slice` drop-in (`ManagedOOMSwap=auto`), fstab line, swap script not run, second run unchanged; verify it fails.
- [x] 3.4 Add the role (`defaults`, `tasks`, `handlers`, `templates`, `README.md`) and its play in `ansible/workstation.yml` (after the zram play, tag `memory`, `'memory-headroom' in machine_features` and not `hw_pi`); verify `pytest tests/unit/test_memory_headroom_role.py -q` passes.
- [x] 3.5 Add `memory-headroom` to `tests/hosts/ci-home-laptop.yml` and `machine/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2.yml`; extend `tests/integration/test_host_yaml_install.py` (both oomd drop-ins present, no swap file created, second apply idempotent).

## 4. Documentation

- [x] 4.1 Add a paragraph on `memory-headroom` to `docs/features.md` (what it does, how to check, how to undo by hand), update the zram swap section of `docs/thinkpad-l13-yoga-gen2.md` with the disk swap size, and add the role to the role list in `Readme.md`.

## 5. Validation

- [x] 5.1 Run `pytest tests/unit/test_features.py tests/unit/test_swapfile_grow.py tests/unit/test_memory_headroom_role.py tests/unit/test_dotfiles.py tests/unit/test_package_presets.py -q`; they cover the feature table, the swap script, the role, the dotfile group and the package resolution that reads the feature table. Record the results here. Result (2026-11-08): 131 passed. The full unit suite `pytest tests/unit -q` also ran, because the feature table and the playbook are shared: 1066 passed (before the swap script was rebuilt; the rebuild touched only the script and its tests).
- [x] 5.2 Run `ansible-lint ansible/*.yml`, because the playbook and a role change, and the Docker integration test of the CI laptop host (`tests/integration/test_host_yaml_install.py`, see `docs/testing.md`), because the change crosses into system configuration. Record the results here. Result (2026-11-08): `uvx nox -s ansible` (syntax check and `ansible-lint` of all playbooks): passed, 0 failures, 0 warnings. `pytest tests/integration/test_host_yaml_install.py -m apt_gnome -q` (venv `.nox/ansible`): 1 passed in 3:44.
- [x] 5.3 Run `pre-commit run --files <changed paths>` (role, playbook, feature table, dotfile group, host configs, tests, docs and `openspec/changes/memory-headroom/**`) and record the result. Result (2026-11-08): passed after black and shfmt reformatted the new tests and the script.
- [x] 5.4 Run `openspec validate memory-headroom --strict` and record the result. Result (2026-11-08): valid.
- [x] 5.5 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change adds a play to the shared playbook, changes several capabilities and needed escalated validation; fix findings before archive. Result (2026-11-08): two rounds with a review subagent. Round 1 found that the kernel refuses to rename an active swap file, so the first script failed on every real run; the owner chose growing in place (decision 13) and a size of RAM + 2 GiB (decision 7). Round 2 found a full-size file left over from a failed run that later runs never formatted, a signal window after `swapoff`, `dd` rounding and backslash handling in the path; all fixed with tests.

## Workflow follow-up

- After merging, on ThinkPad-L13-Yoga-Gen-2: run `machine update` (the hand-made user drop-ins are moved aside, see Migration Plan in design.md), and check that the drop-ins are symlinks into the repository, that the values of task 1.1 are unchanged, that a newly started Claude scope reports `OOMPolicy=continue`, that `/etc/systemd/system/user@.service.d/90-oomd-limit.conf` is unchanged, and that `/etc/systemd/system/-.slice.d/90-oomd-no-swap-kill.conf` exists. On ditschi-ThinkPad-T480: run `machine setup`, select `memory-headroom`, and check `swapon --show`. This needs the merged code on the hosts, so it cannot be done before archiving.
