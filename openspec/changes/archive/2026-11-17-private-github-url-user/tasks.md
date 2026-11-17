# Tasks

Work only in the worktree `$(machine repo)/.worktrees/private-github-url-user` (see proposal.md).

## 1. Rule

- [x] 1.1 Add `[http "https://github.com/"] proactiveAuth = basic` to `home/core/.config/git/private.gitconfig` (with a short comment on why) and cover it in the existing Git config unit tests with a real `git` and a temporary HOME: `git config --get http.https://github.com/.proactiveauth` is `basic` in a repository with a personal github.com remote and with a `bosch-*` remote, the effective `credential.https://github.com.helper` of the `bosch-*` remote is still the work helper, `git remote -v` is unchanged, and an SSH remote is unaffected; verify with the new tests passing.
- [x] 1.2 Check on this host with the live `~/.netrc` (`github.com` entry present): `git push --dry-run` from the dotfiles checkout with its plain `https://github.com/ditschi/dotfiles.git` origin authenticates with the changed `private.gitconfig` included (`-c include.path=<changed file>`, the file that the dotfile apply links); verify the command prints `Everything up-to-date` or the ref update and no `403`, and that the same command without the file gives the `403`.

## 2. Documentation

- [x] 2.1 Describe the setting next to the `~/.netrc` note in `docs/git.md` (why it exists, that it needs Git 2.46 or newer, and that a first clone is not covered); verify the wording matches the spec.

## 3. Validation

- [x] 3.1 Run the Git config unit tests (`tests/unit/test_gitconfig.py` and `tests/unit/test_dotfiles.py`), then `pre-commit run --files <changed paths>` including untracked additions, then `openspec validate private-github-url-user --strict`; verify all pass.

## Workflow follow-up

- Archive with `/opsx-archive` following the archive guidance in `openspec/config.yaml`.
