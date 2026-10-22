## 1. Resolver mechanism

- [x] 1.1 Introduce a resolver registry in the machine CLI; move `sanitize_git_config` behind it as the first entry
- [x] 1.2 Add `~/.bashrc-local` sourcing at the end of `home/dot_bashrc`
- [x] 1.3 Add the resolver that moves external managed blocks (BEGIN/END markers) from `~/.bashrc` into `~/.bashrc-local`, with a backup like the gitconfig resolver
- [x] 1.4 Run all resolvers at the start of `cmd_update`

## 2. Blocking rule and targeted update

- [x] 2.1 Replace `git pull --ff-only` and the dirty check with `git fetch` plus `git merge --ff-only`, stopping only on overlap or divergence; report other local changes as a notice
- [x] 2.2 Classify incoming changed paths (added/removed/renamed home files and `.chezmoiignore`, home content, `ansible/**` and packages, host profile, CLI) into steps
- [x] 2.3 Run only the needed steps in `cmd_update`
- [x] 2.4 Make `machine update` ensure the update-check timer is enabled
- [x] 2.5 Add a lock shared by background and manual updates

## 3. Check

- [x] 3.1 Add `machine update --check` with `--json`; use the same result in `machine status`

## 4. Validation

- [x] 4.1 Unit tests: resolvers, overlap versus unrelated local change, path classification, lock
- [x] 4.2 Update the Readme "Updates" section
- [x] 4.3 `pre-commit run --all-files` and `pytest tests/unit -q`
