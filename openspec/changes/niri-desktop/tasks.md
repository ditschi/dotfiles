# Tasks

## 1. Feature and Ansible role

- [x] 1.1 Add the feature `niri` to `ansible/group_vars/all/features.yml` (desktop optional, server and container excluded, group `niri`) and cover menu and exclusions in `tests/unit/test_features.py`; verify `pytest tests/unit/test_features.py -q`
- [x] 1.2 Add `ansible/roles/niri_desktop/` (defaults, `files/duxlabs.asc`, two deb822 templates, `tasks/main.yml`, README) modelled on `cosmic_desktop`: Release check for both PPAs, warning when unsupported, removal of the `add-apt-repository` files, install `niri dms ghostty`, display manager unchanged; wire it into `ansible/workstation.yml` behind the feature (tag `niri`); verify `ansible-lint ansible/*.yml` and `ansible-playbook --syntax-check ansible/site.yml`
- [x] 1.3 Add `tests/unit/test_niri_desktop.py`: key fingerprint `6354D7C7146C2DD8F98892895ABFA2A5F21E824E`, source templates (`Signed-By`, URIs), role wired behind the feature; verify `pytest tests/unit/test_niri_desktop.py -q`

## 2. Dotfile group and machine step

- [x] 2.1 Add `home/niri/.config/niri/dotfiles.kdl` (F12 → `ghostty +toggle-quick-terminal`, Mod+E → `xdg-open ~`, a header comment saying it is the place for own niri customizations) and `home/niri/.config/ghostty/quick-terminal.conf`; verify `niri validate -c` on a config that includes it and `ghostty +validate-config`
- [x] 2.2 Add the `niri config` step to `machine setup` and `machine update` after Ansible: one-time `dms setup headless --compositor niri --terminal ghostty --skip-existing`, include lines added once, `dms systemd enable` when niri does not want `dms.service`, warning for a `graphical-session.target` enable; unit tests with a scratch HOME and a stubbed `dms` for fresh host, existing config, include already present, no feature and container; verify `pytest tests/unit -q -k niri`
- [x] 2.3 Add the cached `dms completion` lines to `home/core/.shell/zsh/plugins.zsh` and inside the bash-completion guard of `home/core/.shell/bash/tools.bash`; verify `dms <TAB>` in new zsh and bash shells and that bash without bash-completion starts cleanly
- [x] 2.4 Describe the feature in `docs/features.md` (PPAs, GDM stays, F12 with the quick terminal tab keys Ctrl+T or Ctrl+Shift+T, Ctrl+Tab, Alt+1…9, Ctrl+Shift+W, Mod+E, where to put own niri customizations, what DMS owns, undo); verify links resolve

## 3. Validation

- [ ] 3.1 Run `machine update` on the L13 and confirm: PPA sources replaced without duplicates (`apt update` clean), `dms setup` skipped, both include lines present once, F12 toggles the quick terminal and Mod+E opens the file manager after `niri msg action load-config-file`, GNOME login does not start `dms.service`
- [x] 3.2 Run `pytest tests/unit -q` (setup and update flow changed), then `pre-commit run --files <changed paths>`, then `openspec validate niri-desktop --strict`
- [ ] 3.3 Review the branch diff against main with a fresh reviewer (`/review` or a review subagent), because the change touches the setup and update flow and adds a shared Ansible role; fix findings

## Workflow follow-up

- Archive the change with `/opsx:archive` after review.
