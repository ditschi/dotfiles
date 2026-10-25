# Tasks

## 1. Feature table and groups

- [x] 1.1 Split `ansible/group_vars/all.yml` into `ansible/group_vars/all/packages.yml` (unchanged content) and `ansible/group_vars/all/features.yml` with every feature's help text, groups and values for `private`, `work`, `desktop`, `server`, `container` as in `specs/feature-selection`; drop `starship`, `yazi`, `gh-cli`, add `opencode`. Update `tests/unit/package_sets.py` and other readers of the old path. Verify `pytest tests/unit -q` and `ansible-lint ansible/*.yml` pass.
- [x] 1.2 Add a resolver in `machine_cli` (stricter value wins, container without context uses only the device, groups from the table plus `core`/`prompt`/`systemd`/`work`) with unit tests for the scenarios in `specs/feature-selection`. Verify the tests pass.
- [x] 1.3 Define `machine_features` in the group vars (host `features` minus excluded and unknown ones, same rule as the resolver) and a unit test that compares the Ansible expression with the Python resolver for every context/device pair. Verify the test passes.
- [x] 1.4 Split `home/core/.config/mise/conf.d/30-llm.toml` into the groups `claude`, `copilot`, `opencode`, `openspec` (each `home/<group>/.config/mise/conf.d/…`, declared in `mise.toml`); move `uv` from `40-azure.toml` into a general `core` fragment; regenerate the lockfile. Verify `python3 -m machine_cli.mise_check` passes and `test_mise_tools.py` covers that a host without LLM features gets no LLM tool.

## 2. Host config in the CLI

- [x] 2.1 Replace `PROFILES` with `CONTEXTS` and `DEVICES`; read and write `context`, `device`, `features`, `ssh_allow_from`, `ansible` in host configs and in the applied host config `~/.local/share/machine/applied-host.yml`; take over `~/.config/machine/profile.yml` once with the mapping in `specs/machine-profiles`; pass the applied host config to Ansible. Remove `ansible/profiles/` and `FEATURE_HELP`. Verify unit tests for the takeover, the mapping and the round trip pass.
- [x] 2.2 Default context and device on setup (Docker, overrides, saved, inherited, company user ID, `systemctl get-default`); CLI options `--context`/`--device` on `setup`, `bootstrap` and `testenv`; remove `--profile`. Verify unit tests for each scenario in `specs/machine-profiles` pass and `machine setup --help` lists the new options.
- [x] 2.3 Feature menu: list only allowed features, preselect per the table, keep the host's selected ones; warn about excluded or unknown features on setup/apply/update and drop them on the next write. Verify unit tests for the menu and the warnings pass.
- [x] 2.4 Context-based behaviour: dotfile groups from the resolver, `ENV_GROUPS` (`private`/`work`/none), SSH class, Git identity and `safe.directory`, GitHub token variable, SSH remote switch, events with context and device, update notice with context/device changes, "host config" wording in messages. Verify `pytest tests/unit -q` passes with the adapted tests in `test_machine_cli.py`, `test_dotfiles.py`, `test_gitconfig.py`, `test_update_and_env.py`, `test_events.py`, `test_ssh_host_keys.py`, `test_host_profiles.py`.
- [x] 2.5 `ansible: false`: setup, apply and update skip Ansible and say so, and the update reports no pending system update; a failed `become` names the setting. Verify unit tests for the scenarios in `specs/system-provisioning`, `specs/machine-profiles` and `specs/update-flow` pass.

## 3. Ansible

- [x] 3.1 Add `ansible/tasks/detect_hardware.yml` (`hw_laptop`, `hw_pi`, `hw_pi_zero`; skipped for the container device) and include it where needed. Verify on this laptop with `ansible-playbook --check` or `machine apply` that `hw_laptop` is true and `hw_pi` false.
- [x] 3.2 Switch `resolve_packages.yml` (slim set on Pi Zero, host packages except Pi Zero/container, work packages for context `work`), `resolve_monitoring.yml` (fragment from hardware and device) and the Docker candidate check. Replace every `features` and `profile` condition in `workstation.yml`, `site.yml`, `homelab.yml` with `machine_features`, `context`, `device` or hardware facts; update `system_relevance.py` and its tests. Verify `ansible-lint ansible/*.yml` and `pytest tests/unit -q` (package presets, monitoring, relevance) pass.

## 4. Shell and launchers

- [x] 4.1 `home/core/.zsh/machine-profile.sh`: read the applied host config, export `MACHINE_CONTEXT`/`MACHINE_DEVICE` with the Docker rule and overrides, keep `WORK_SETUP` rules; remove `MACHINE_PROFILE`. Update `home/core/.local/bin/sde` (`--device container`), `machine_cli/testenv.py` (`--context`/`--device`, overrides from the applied host config) and `bootstrap`. Verify the shell unit tests and `test_testenv.py` pass, and a new zsh and bash on this host show `MACHINE_CONTEXT=private`, `MACHINE_DEVICE=desktop`, no `WORK_SETUP`.

## 5. Host configs, CI and docs

- [x] 5.1 Rewrite every file in `machine/hosts/` to `context`/`device` (L13 Yoga, `_example-thinkpad-copy.yml`, `ci-home-laptop` private/desktop; `LR-C-0042H`, `ABTVL421` work/desktop; `homeserver`, `netmaster`, `ci-rpi-zero` private/server; `ci-container` container), drop features the table excludes and the removed ones; update `machine/hosts/README.md`. Verify `test_repo_host_yamls_are_valid` passes and `git grep -n "^profile:" machine/` is empty.
- [x] 5.2 Adapt integration tests and the CI matrix (`tests/integration/*`, `.github/workflows/verify.yml`) to context/device; `ci-home-laptop` sets `MACHINE_DEVICE_OVERRIDE=desktop` and `MACHINE_CONTEXT_OVERRIDE=private` in its container. Verify `pytest tests/integration -q` for the Docker matrix passes, or note that Docker is unavailable.
- [x] 5.3 Update Readme (bootstrap examples, host config section, feature table and how to add a feature, Bitwarden groups, overrides, applied host config), `ansible/README.md`, and the no-root sentence in `openspec/config.yaml`. Verify `git grep -n -E "work-machine|home-laptop|home-server|rpi-zero|MACHINE_PROFILE|host profile"` only finds archived OpenSpec files and the takeover mapping.
- [x] 5.4 Move the CI host configs (`ci-container`, `ci-rpi-zero`, `ci-home-laptop`) to `tests/hosts/`, read through `MACHINE_HOSTS_DIR=tests/hosts` in the test containers; delete `machine/hosts/_example-thinkpad-copy.yml` (a new host gets its file from `machine setup`); update the host validation in CI and the docs. Verify the unit tests and `pytest tests/integration -m "docker"` pass.

## 6. Integration checks

- [ ] 6.1 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate profile-axes --strict`. Verify all pass.
- [ ] 6.2 Run `machine testenv -- 'machine update && machine apply'` and then `machine update` on the L13 Yoga. Verify the notice shows context `private` and device `desktop`, `~/.config/machine/profile.yml` is gone and `applied-host.yml` exists, the feature menu hides `kerberos`/`azure-cli`, and the apply succeeds.

## Workflow follow-up

- Archive the change after review; then rework `split-laptop-tuning` on top (laptop roles on `hw_laptop`, model role, `zram-swap` row in the feature table).
