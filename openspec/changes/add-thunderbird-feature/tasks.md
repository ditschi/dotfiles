# Tasks

## 1. Feature and defaults

- [x] 1.1 Add the feature `thunderbird` to `FEATURE_HELP` and to the defaults in `ansible/profiles/home-laptop.yml`. Verify `pytest tests/unit/test_host_profiles.py -q` passes.

## 2. System part (Ansible)

- [x] 2.1 Add `thunderbird` to `packages_by_feature`. Verify the package is in the resolved list for a host with the feature.
- [x] 2.2 Add the role `thunderbird`: merge `ExtensionSettings` for `thunderbird-ai@extension` (`normal_installed`, pinned release URL) into `/etc/thunderbird/policies/policies.json`, keeping other content; run it from `workstation.yml` when the feature is on. Verify `ansible-lint ansible/*.yml` and a run in a container, with and without an existing policy file.

## 3. User part (mise)

- [x] 3.1 Add the dotfile group `thunderbird` (`mise.toml`, `dotfile_groups`) with `home/thunderbird/.config/mise/conf.d/60-thunderbird.toml` for `npm:thunderbird-cli` and `npm:thunderbird-cli-bridge`; regenerate the lockfile. Verify `python3 -m machine_cli.mise_check` passes and a unit test that the group follows the feature.

## 4. Docs and checks

- [x] 4.1 Add the feature to the Readme feature list with the manual bridge start. Verify the text matches the behaviour.
- [x] 4.2 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate add-thunderbird-feature --strict`. Verify all pass.
