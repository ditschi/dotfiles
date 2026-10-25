# Tasks

## 1. Feature and defaults

- [x] 1.1 Add the feature `thunderbird` to `FEATURE_HELP` and to the defaults in `ansible/profiles/home-laptop.yml`. Verify `pytest tests/unit/test_host_profiles.py -q` passes.
- [x] 1.2 Add `thunderbird` to `packages_by_feature`. Verify the package is in the resolved list for a host with the feature.

## 2. User part (mise)

- [x] 2.1 Add the dotfile group `thunderbird` (`mise.toml`, `dotfile_groups`) with `home/thunderbird/.config/mise/conf.d/60-thunderbird.toml` for `npm:thunderbird-cli` and `npm:thunderbird-cli-bridge`; regenerate the lockfile. Verify `python3 -m machine_cli.mise_check` passes, a unit test that the group follows the feature, and `tb`/`tb-bridge` in zsh and bash in `machine testenv`.
- [x] 2.2 Download the pinned extension XPI to `downloads/` (gitignored) during the tool install when the feature is on, verify its SHA-256, warn on failure. Verify unit tests for download, no second download, wrong checksum and no feature.

## 3. Docs and checks

- [x] 3.1 Describe the feature, the manual extension install and the manual bridge start in the Readme. Verify the text matches the behaviour.
- [x] 3.2 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and `openspec validate add-thunderbird-feature --strict`. Verify all pass.
