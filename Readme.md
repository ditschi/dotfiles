# Dotfiles

Personal Linux dotfiles repository for shell, Git, tmux, and prompt setup.
Goal: fast, reproducible setup with minimal manual configuration.

## Quick Setup

```bash
python3 install.py
```

Optional:

- `python3 install.py --dry-run` to preview changes without applying them
- `python3 install.py --no-backup` to skip back up existing dotfiles
- `python3 install.py --new-host --ui` for first-time host setup with packages/fonts

## Repository Structure

- `install.py`
  Core setup logic (linking, backup, package/font setup, Docker-specific paths, CLI flags).
- `.zshrc` and `.zsh/config/*.zsh`
  Modular zsh setup; files are split by topic and documented inline.
- `.gitconfig`
  Git defaults. Identity and GitHub credentials are picked by repo owner (`bosch-*`/`bosch_*`, GHES, Bitbucket → `.config/git/work.gitconfig`, other github.com → `.config/git/private.gitconfig`). Tokens come from `~/.env` via `.local/bin/git-credential-env` (`GITHUB_TOKEN`, `BDC_GITHUB_TOKEN`, `GITHUB_PRIVATE_TOKEN`). Per-repo override: `git user-work`, `git user-private`, `git user-unset-local`; check with `git user-show`.
- `.tmux.conf`
  tmux keybindings (including German keyboard layout mappings).
- `.bashrc`, `.profile`, `.zprofile`
  Compatibility/login shell parts and bridge into the dotfiles setup.
- `.pre-commit-config.yaml`
  Quality checks for shell/Python/YAML/secrets on commit.

## Where To Continue?

For details, jump directly into the referenced files.
Most logic is intentionally documented close to the code and clearly scoped per file.
