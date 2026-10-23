# Tasks

## 0. Spike gate

- [x] 0.1 In a container without root, repeat the spike with the real repository and the pinned `mise` version: dotfile groups with `MISE_DOTFILES_ROOT` pointing at a checkout in a non-default path (the variable is required; `-C` alone fails), apply with removal on a profile switch, and the lockfile location. Record the `mise` version and the result in `design.md`.
- [x] 0.2 Confirm with the owner that the `mise` release used contains the dotfile and bootstrap features, then continue with group 1. Do not start group 2 before this.

## 1. Tools through mise

- [x] 1.1 Install `mise` in `./bootstrap` (user-local, no root, skipped when present) and add the activation to `home/dot_bashrc` and `home/dot_zshrc`. Verify the `bootstrap` scenarios in `tests/unit` and that an interactive bash and zsh find a tool installed by `mise`.
- [x] 1.2 Add tool fragments for the tools of the zsh and bash configuration (`fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`) and the other user-space tools (`gh`, `yazi`, Node), and the lockfile including `linux-arm64`. Verify `mise install` in a container without root installs all fragments of the `work-machine` profile.
- [x] 1.3 Done by `adopt-antidote-starship` (zsh plugins, `fzf --zsh`, no z.lua, no zinit-installed `eza`/`fd`). Verify there that zsh starts without error on a host with only `mise` tools and the zsh handoff tests pass. In `home/dot_bashrc` the distribution fzf search and z.lua are already replaced by `fzf --bash` and `zoxide init bash`; that change moves them to the cached init.
- [x] 1.4 Add the repository checks: a tool declared in two fragments fails, and a tool in a fragment and in an Ansible package list fails. Verify both with unit tests and run them from `pre-commit` and CI.
- [x] 1.5 Remove the Ansible roles `user_tools`, `node_tools`, `yazi`, `gh_cli` and the user-space parts of `az_cli` and `git_min` that `mise` replaces, update `packages_by_feature` and `packages_*` for the packages that move, and keep an existing NVM default untouched. Verify `ansible-lint ansible/*.yml` passes and the Docker provisioning tests listed in the Readme still pass.
- [x] 1.6 Install a user-space Git on every host (`conda:git`, replaces `git_min`), add the `mise` shims directory to `~/.zshenv` and `~/.profile` for Git and `git-lfs`, and seed `http.sslCAInfo` into `~/.gitconfig.local` on work hosts (the user-space Git ignores `/etc/gitconfig` and the system CA bundle). Verify in a container with an old Git that `includeIf hasconfig` works and that a non-interactive `git` resolves to the user-space build.
- [x] 1.7 Add the Fira Code Nerd Font without Ansible, linked into `~/.local/share/fonts` with a font-cache refresh. The bash shell setup (`starship`, `zoxide`, `fzf --bash`) and the MesloLGS removal are done by `adopt-antidote-starship`; ble.sh is not used (owner decision in `investigate-shell-plugin-manager`). Verify the font is linked on a host with the `fonts` feature and that `machine update` refreshes it.
- [x] 1.8 Add a persistent `~/.local/share/mise` cache mount to `sde` and `sdx` next to the antidote cache. Verify a second container start does not download tools again.
- [x] 1.9 Set the terminal font to Fira Code Nerd Font from the dotfiles on hosts with the `fonts` feature and a desktop: Guake through `gsettings set guake.style.font style` and the VS Code terminal through `terminal.integrated.fontFamily` in `settings.json`, each only when the application exists and applied after the font is linked. First spike how to set only that key in `settings.json` without replacing the file (mise edit mode or a small step in `machine`), and record the result in `design.md`. Verify on a desktop host that both applications use the font and that other VS Code settings are untouched, and that a host without Guake or VS Code is not affected.
- [x] 1.10 Add `delta` and `tealdeer` to the shell tool fragment (`home/dot_config/mise/conf.d/10-shell.toml`) and update `mise.lock` including `linux-arm64` (owner decision in `investigate-shell-plugin-manager`; `adopt-antidote-starship` uses delta as Git pager and removes diff-so-fancy). Verify `mise install` in a container without root installs both and `git show` uses delta.

## 2. Dotfile groupst

- [x] 2.1 Move `home/` into group directories with real file names in one commit that only renames files (`core`, `work`, `prompt`, `systemd`, plus others the profiles need). Verify `git log --follow` follows a moved file and no content changed (`git diff -M --stat` shows renames only).
- [x] 2.2 Derive the group list for a host from its profile and features and write it into the local `mise` configuration from `machine setup` and `machine update`; set `MISE_DOTFILES_ROOT` from the checkout path. Verify unit tests for each profile (`work-machine`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`) and that the `work` group is only selected for `work-machine`.
- [x] 2.3 Replace `chezmoi apply` in `machine_cli/tools.py` and the setup and update commands by the `mise` apply with removal, and report same-target conflicts. Verify the `repo-layout` group scenarios (profile switch, same target in two groups, deleted upstream file) with unit tests and one container run.
- [x] 2.4 Create `~/.gitconfig.local` once from the profile in `machine setup` (identity, `safe.directory` on work and container profiles) and leave an existing file unchanged. Verify unit tests for first setup, existing file and missing file with Git.
- [x] 2.5 Migrate existing hosts by re-applying: after the group apply with removal, sweep dangling symlinks in `$HOME` whose old target lay inside the repository (checkout or former `dot_*` paths) and leave everything else alone; leave the old chezmoi configuration and state in place. Remove the chezmoi install step, `.chezmoiignore`, `.chezmoiremove`, `.chezmoi.yaml.tmpl`, `.chezmoiscripts` and the chezmoi config writing. Verify a container set up with the previous commit migrates, a removed file leaves no dangling link, an unrelated broken link stays, and `machine setup` stays idempotent.

## 3. Update flow

- [x] 3.1 Replace the per-commit classification and the safe-target search by the file difference between the current and the target revision and the targeted steps (dotfile apply, tool install, shell refresh, system step, profile apply). Verify the `update-flow` scenarios "Clean fast-forward", "Home-only change", "System change pending", "Only a shell file changed" and "Tool lockfile changed" with unit tests.
- [x] 3.2 Merge the update state, pending marker and failed-revision bookkeeping into one state file, keeping what the prompt segment and the safety net read. Verify `tests/unit/test_update_check_job.py`, `tests/unit/test_zsh_handoff.py` and the update-hint tests pass.
- [x] 3.3 Rename the tools in the safety net to the `mise` apply and tool install, and add the failed tool download case. Verify the safety-net scenarios including "Tool download fails" with unit tests; the revert behaviour itself is unchanged.
- [x] 3.4 Store `ansible_applied_rev` after each successful Ansible run and implement the relevance filter (always-count paths, roles filtered by the host's enabled roles, unevaluable conditions count, no report on a host without Ansible runs). Verify unit tests for each "Relevant system changes only" scenario.
- [x] 3.5 Add `machine attention`, also run by plain `machine` without arguments: list all open items from the state file and the local-overrides helper and guide through each with the toolkit's prompts; background runs only record items. Verify unit tests for each item type and that no prompt happens non-interactively.
- [x] 3.6 Verify end to end on a throwaway clone: an upstream commit with a home change, one with a lockfile change and one with an `ansible/**` change produce the specified state, and a dirty checkout produces needs-attention.

- [x] 3.7 End `machine update` with the converge check: `mise install` for missing tools, `uv tool install azure-cli --python-preference only-managed` when the `azure-cli` feature is on and `az` is missing (`uv tool upgrade azure-cli` otherwise), the dotfile apply with prune, and a fresh shell when run interactively (a function in the shell config that runs `exec` on the current shell after `machine update` succeeds, since a child process cannot reload its parent). Verify unit tests for "Nothing incoming but a tool is missing", "Link missing" and "Fresh shell after the update" (shell part in `tests/unit/test_zsh_handoff.py`).

## 4. Documentation and final checks

- [x] 4.1 Update `Readme.md`, `ansible/README.md` and the comments in `home/` that mention chezmoi, `dot_*` names or the removed roles. Verify `grep -rni chezmoi` finds only the migration code and archived records.
- [x] 4.2 Run `pre-commit run --all-files`, `pytest tests/unit -q`, `ansible-lint ansible/*.yml` and the Docker tests listed in the Readme "Tests" section. Verify all pass.
- [x] 4.3 Run `openspec validate adopt-mise --strict` and verify it passes.

## Workflow follow-up

- Archive `simplify-machine-cli` first; its local-overrides helper and toolkit are used here.
- Archive this change after review; make sure the archived `design.md` states the decisions and their rationale in plain prose.
