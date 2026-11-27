# Tasks

Work only in the worktree `$(machine repo)/.worktrees/github-proactive-auth-token` (see proposal.md).

## 1. Token config

- [x] 1.1 In `machine_cli/dotfiles.py`, render `[http "https://github.com/"] proactiveAuth = basic` into `github-token.gitconfig` only when the token variable resolves (environment, else the checkout's `home/core/.shell/common/environment.sh` in Bash) and log whether it is on; cover with unit tests in `tests/unit/test_dotfiles.py` (token in environment, token only in `~/.env`, no token).
- [x] 1.2 Remove `proactiveAuth` from `home/core/.config/git/private.gitconfig`; in `tests/unit/test_gitconfig.py` assert that the effective `http.proactiveauth` of a personal and a work-owner github.com remote is empty when the token file is rendered without the token, and stays `basic` with it.

## 2. Documentation

- [x] 2.1 Update the `~/.netrc` note in `docs/git.md`: proactive auth only with the token, and correct the note that a first clone is not covered.

## 3. Validation

- [x] 3.1 Run `pytest tests/unit/test_dotfiles.py tests/unit/test_gitconfig.py -q`.
- [x] 3.2 Reproduce the CI failure check by hand: with the repository's Git config files in a temporary HOME and no token, `git clone --depth 1 https://github.com/zsh-users/zsh-autosuggestions` succeeds and prints nothing from the helper.
- [x] 3.3 Run the APT integration tests `tests/integration/test_host_yaml_install.py -k "rpi_zero or home_laptop"` if Docker is available.
- [x] 3.4 Run `pre-commit run --files <changed paths>` including untracked additions, then `openspec validate github-proactive-auth-token --strict`.

## Workflow follow-up

- Archive with `/opsx-archive` following the archive guidance in `openspec/config.yaml`.
