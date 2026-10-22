# Investigation report: architecture and profiles

Read-only research for the investigations in the archived changes `2026-10-22-baseline-repo-architecture` (6 items, section A) and `2026-10-22-baseline-profiles-work-separation` (7 items, section B). Nothing was changed. Decisions stay with the owner. Specs consulted: `repo-layout`, `bootstrap`, `machine-profiles`, `work-private-separation`. Items are marked verified (read in code/tests, or run) or unverified (not checked or only a hypothesis).

# A. Repository architecture

## A1. Bootstrap through `curl | bash`

**Findings**
- Verified: `bootstrap` assumes a checkout (`ROOT` from its own path). It installs `uv` via `curl ... | sh` if missing, then execs `executable_machine setup`. The Readme quick start begins with a manual clone.
- Verified: the remote is `https://github.com/ditschi/dotfiles.git`. `machine setup` and Ansible expect the repository at a known path (`~/dotfiles` in the Readme).
- Unverified: whether the repository is public. `repo-sensitivity.md` advises against sharing it unchanged, and a `curl | bash` URL from a private repository would need authentication.
- The existing `bootstrap` already pipes a remote script into `sh` for `uv`, so the pattern is not new here.

**Suggestion:** if wanted, add a short entry script that only checks for `git`, clones to the standard path, then runs `./bootstrap`. Decide first whether the repository will be public (see `repo-sensitivity.md`); until then a documented two-line clone and run is as good. Reason: a pipe-to-shell script has no review step, so keep it tiny and pin a tag or commit.

## A2. Python versions

**Findings**
- Verified: `executable_machine` declares `requires-python = ">=3.11,<3.14"` (PEP 723) with `typer==0.27.2` pinned exactly. The comment gives the reason: `completion` uses private typer modules.
- Verified: the Readme states 3.11–3.13. CI (`.github/workflows/verify.yml`) and `noxfile.py` use only 3.12. Nothing tests 3.11 or 3.13.
- Verified: `uv run --script` fetches a matching interpreter itself, so the host's system Python is not what limits the range. The upper bound is a manual cap.
- Verified: the Ansible and test Docker image installs system `python3`, separate from the script's range.
- Unverified: which dependency, if any, fails on 3.14.

**Suggestion:** add a CI matrix (3.11, 3.13, and a pre-release such as 3.14) for the unit tests, and widen the upper bound when green. Consider dropping the upper bound if `uv` always picks a working version, since the real constraint is the typer pin. Reason: the stated range is currently asserted but only 3.12 is tested.

## A3. Dotfile manager

**Findings**
- Verified chezmoi features in use: symlink mode (`home/.chezmoi.yaml.tmpl`, `mode: symlink`, source dir `home/`); source-name prefixes `dot_`, `executable_`, `create_`; one template with profile data (`create_dot_gitconfig.local.tmpl`); `.chezmoiignore` with `if` conditions on `.profile` (work modules, p10k/starship, systemd for container); `chezmoi apply` and `status` called from `machine_cli`.
- Verified: no use of encryption, externals, scripts (`run_`), or password-manager integration from chezmoi. Secrets go through the `machine env` Bitwarden flow instead.
- Needs-in-place edit and sync: symlink mode gives in-place edits in the repository; sync is `git pull` in `machine update`.
- Assessment (hypothesis): the used subset is profile-conditional files, a create-once file and symlinks. GNU Stow lacks conditionals and templates, so the profile ignore list and `create_` file would need replacing by `machine` code. yadm uses alternate-file suffixes for profile selection but has no symlink mode as such (unverified for current version). A plain linker would be small but would reimplement the ignore logic.
- Verified cost of switching: tests (`test_profile_containers.py` `test_profile_dotfiles`) and the migration code assume chezmoi.

**Suggestion:** keep chezmoi. Only the conditional ignore and one create-once template are really needed, and nothing else would remove code. Revisit only if chezmoi becomes a maintenance burden. Reason: no evidence of a clearly better fit.

## A4. `install.py` wrapper

**Findings**
- Verified: `install.py` maps `--update` to `machine update` and `--new-host`/`--ui` to `machine setup`, rejects `--dry-run`, and installs `uv` if missing. Introduced as a wrapper in commit `dddd08f` (machine CLI rewrite).
- Verified references: Readme "Legacy commands" and "Revert"; `noxfile.py` and `verify.yml` only `py_compile` it. Nothing in `tests/`, `ansible/` or `home/` runs it.
- Verified: the Revert/rollback path runs the `install.py` of the **old** commit, not this one. Removing the current file does not affect rollback.
- Unverified: external callers (other hosts' cron, shell history, notes). Cannot be checked from the repository.

**Suggestion:** remove `install.py`, its Readme "Legacy commands" lines, and the `py_compile` entries in `noxfile.py`/`verify.yml`. Clarify the Readme Revert text that it uses the old commit's file. Reason: only documentation and a compile check use it. First ask the owner whether any host still calls it.

## A5. Migration and rollback code

**Findings**
- Verified: `machine_cli/migration.py` (484 lines of about 2700 in `machine_cli`) plus migrate/rollback parts of `commands.py` (`needs_layout_migration` gate in `cmd_setup`, two `migrate` gates around lines 204–240, a status line) and `executable_machine` (`migrate`, `rollback`, `--rollback-ref`).
- Verified tests: `tests/integration/test_migrate.py` (128 lines, Docker), `test_needs_layout_migration_detects_old_root_symlink` and help-text asserts in `tests/unit/test_machine_cli.py` and `test_host_profiles.py`, `tests/compose.yaml` mentions. Readme sections "Migration" and "Revert".
- Verified: `machine update` and `setup` still call the layout-migration check, so removal also touches the normal setup path, not only the two subcommands.
- Unverified: the "all hosts migrated" claim and that no new issues appeared (plan: after 2026-10-28).

**Suggestion:** after the planned date and an owner check that no host still has root symlinks (`machine status` reports "needs migration"), remove in one change: `migration.py`, the gates in `commands.py`, the two subcommands, their tests and the Readme sections. Keep one-line git history pointer. Reason: contained dead code on the main setup path.

## A6. Essential `machine` subcommands

**Findings**
- Verified: subcommands in `executable_machine`: setup, migrate, rollback, update, apply, profile, env, ssh, status, commit, push, inventory, completion, help.
- Rough reference counts (verified by grep, mentions not semantics): setup, update, apply, profile, env are in Readme, tests and scripts; ssh and inventory are in Readme but only lightly or not at all in tests; commit, push, status are in Readme; `completion` is in no Readme section but has a test and Ansible/home references; migrate and rollback see A5.
- `commit` and `push` wrap plain `git`; `inventory` wraps ansible-vault (per help text). Unverified whether they add guard behaviour beyond the wrappers (not read in detail).

**Suggestion:** keep setup, update, apply, profile, env, ssh, status, completion. Candidates to drop after reading their code: commit, push (if they only wrap git) and inventory, plus migrate/rollback (A5). Reason: these lack tests or have a plain-tool equivalent. Check owner use first.

# B. Profiles and work/private separation

## B1. Order of the default profile checks

**Findings**
- Verified: `profile.py` `default_profile()` order: saved `~/.config/machine/profile.yml`, then repo host profile (`machine/hosts/<host>.yml`), then Docker detection, then inherited `MACHINE_PROFILE`, then Bosch-style user ID regex (work-machine), else home-laptop.
- Verified: `in_docker()` is `/.dockerenv` or `MACHINE_IN_DOCKER=1`.
- Verified: shell side (`home/dot_zsh/machine-profile.sh`) differs: saved file value wins, with no Docker check; otherwise user-ID regex gives work-machine, else home-laptop. So CLI and shell default differently for an unsaved container.
- Risk cases: a container sharing a mounted home gets the host's saved profile (it wins before Docker); a host with a stray `/.dockerenv` or exported `MACHINE_IN_DOCKER` gets `container`, which makes `maybe_persist_host_profile` and Ansible skip. Unverified whether either has occurred.
- Verified: the test `test_dev_container_with_work_user_starts_cleanly` shows the container profile with the work user ID gives `container|true`.

**Suggestion:** keep saved-first for non-container hosts, but add a test with a mounted host profile inside Docker and decide B2 from it. Reason: the order only matters in the shared-home case, and the CLI/shell inconsistency is the more concrete problem.

## B2. Container always gets the container setup

**Findings**
- Verified: with a saved profile, CLI Docker detection never runs (see B1). `maybe_persist_host_profile` already refuses to persist a profile inside Docker, and `cmd_setup`/`apply` skip steps when `profile == "container"` or in Docker.
- Verified: `.chezmoiignore` removes work modules, p10k, starship and systemd only for profile `container`, so a host profile inherited in a container would link the host's full set.
- Unverified: any real case of shared home between host and container in this setup.

**Suggestion:** in `default_profile()` and the saved-profile reader, let `in_docker()` return `container` first, with an override variable for the test image that wants another profile (the CI already sets a profile per image: check `conftest.py`). Mirror it in `machine-profile.sh` for the shell. Reason: one rule for CLI and shell; the owner's preference. Run B1's test first.

## B3. Group pattern beyond environment files

**Findings**
- Verified: `ENV_GROUPS` in `machine_cli/core.py` maps profile to groups (`work`, `private`, `server`, `iot`), merged in order. A host has one profile but belongs to several groups.
- Verified other single-profile keys: `SSH_CLASS` (work/home/""), `.chezmoiignore` (`ne .profile "work-machine"`, rpi-zero/container), `monitoring_by_profile` in `ansible/group_vars/all.yml`, `WORK_SETUP` detection, and Ansible `profiles/*.yml` presets.
- Hypothesis: `SSH_CLASS` is already a derived group and could be expressed in the same table; the work check (`ne .profile "work-machine"`) is a group named `work`.

**Suggestion:** define a small profile-to-groups table (`work`, `private`, `server`, `iot`, `minimal`) and use it for SSH class, work module ignore, and monitoring defaults. Reason: removes repeated profile-name lists. Not urgent; do it when a new profile is added.

## B4. `WORK_SETUP` in dev containers

**Findings**
- Verified setters: `home/dot_zsh/machine-profile.sh` exports `WORK_SETUP=true` when profile is `work-machine` or `USER` matches the company ID regex. Readers: `00_LOADER.zsh` (comment), `01_work.zsh`, `01_work_tools.zsh`, `01_work_ldap_helpers.zsh` (each returns if not true), and `dot_bashrc` (sources `01_work.zsh` when true).
- Verified: in a `container` profile chezmoi does not link the work modules, so `WORK_SETUP=true` only changes behaviour where those files exist (the `dot_bashrc` check also needs the file). The test `test_dev_container_with_work_user_starts_cleanly` pins `container|true` as expected, so changing it needs the test updated.
- Unverified: other consumers of `WORK_SETUP` outside this repository (project dev containers could read it).

**Suggestion:** make the user-ID regex apply only when no profile is saved and not in a container; otherwise `WORK_SETUP` follows `MACHINE_PROFILE == work-machine`. Update the test to expect `container|` (empty). Reason: neutral containers, one place that decides. Check external consumers first.

## B5. Work detection signals

**Findings**
- Verified: the signals in code are saved profile `work-machine` and the user ID regex `^[a-zA-Z]{3}[0-9]{1,2}[a-zA-Z]{2,3}$` (duplicated in `machine-profile.sh` and `profile.py`; the CLI uses `SUDO_USER` first). No hostname or domain check exists. Host profiles under `machine/hosts/` name some hosts (see `repo-sensitivity.md`).
- Verified: under `sudo`, the shell script uses `USER`/`id -un` while the CLI uses `SUDO_USER`; the results can differ.
- Hypothesis: a local user that matches the pattern (any three letters, a digit, two letters) on a private host or CI would misclassify. Not observed.
- Unverified: real hostnames/domains on the work hosts, so no comparison was done.

**Suggestion:** treat the saved profile as the strong signal and the regex as a first-run hint only (offered at setup, then saved). Keep the regex in one place. Do not add hostname or domain checks without owner input. Reason: the regex is weak and duplicated.

## B6. Profile versus feature

**Findings**
- Verified: profiles (6, in `core.py` `PROFILES`) choose the base set, env groups, SSH class and ignore rules. Features (about 19, `FEATURE_HELP`) select Ansible roles and are stored in `profile.yml`. Home profiles default `monitoring` (Readme).
- Overlap verified: `work-machine`-only behaviours (work zsh modules, work env group, Kerberos) are profile-keyed while `kerberos` and `azure-cli` are features; `container` and `rpi-zero` are profiles that mainly mean "minimal shell" (p10k/starship removed), and `starship` is also a feature; `home-*` profiles have `sshd-home` and monitoring features.
- Hypothesis: a profile is "who/where this host belongs" (affects secrets, identity, shell modules) and a feature is "what software or system config to install". Not confirmed by owner.

**Suggestion:** keep this rule of thumb in `machine-profiles` once the owner confirms it: identity, secrets and dotfile selection are profile-level; installed software and system services are features. Review `starship` and `container` overlap. Reason: gives a rule for new settings.

## B7. Sensitive details in the repository

**Findings**
- Verified: already covered in `openspec/investigations/repo-sensitivity.md` (work gitconfig identity, work zsh modules, example inventory, host mapping, public key comments). Not repeated here.
- Additional verified link to profiles: the user-ID regex in `machine-profile.sh` and `profile.py` encodes the company ID format, and test comments name "Bosch user id". It is low sensitivity, but belongs with work-specific logic.

**Suggestion:** follow the recommendations in `repo-sensitivity.md`. When B5 is done, consider moving the work ID pattern to local configuration (for example a value in `profile.yml`) so no company-specific pattern is needed in shared code. Reason: same as the report: generic logic stays shareable.
