# Investigation report: kerberos and code-quality-tests

Read-only research for the investigations in the archived changes `2026-10-22-baseline-kerberos` and `2026-10-22-baseline-code-quality-tests` (design.md). Nothing was changed in code. Decisions stay with the owner. Internal URLs and hostnames are replaced by placeholders.

# Part A: baseline-kerberos

## A1. Feature name and content

**Findings**
- Verified: the feature `kerberos` maps to `*packages_work` in `ansible/group_vars/all.yml`, which lists `krb5-user` and `ldap-utils`. The description in `home/dot_local/lib/machine_cli/core.py` reads "krb5-user + ldap-utils (work)".
- Verified: the name appears in `ansible/profiles/work-machine.yml`, `machine/hosts/*.yml` (two hosts), the Readme feature list, `tests/unit/test_package_presets.py`, `tests/unit/test_machine_cli.py` and the integration tests. A rename touches all of them plus stored `profile.yml` answers on existing machines.
- Verified: the LDAP helpers (`home/dot_zsh/config/01_work_ldap_helpers.zsh`) are loaded only when `WORK_SETUP` is `true`, independent of the feature. They call `ldapsearch`, so they need `ldap-utils`.
- Unverified: whether any machine wants LDAP without Kerberos or the reverse.

**Suggestion:** keep the feature as is for now. If renamed, add an alias in the machine CLI that maps the old name for stored answers, and rename in one change with the tests. Reason: only the name is misleading; the package set is correct for work machines, and the rename has a real cost for existing profile files.

## A2. Aliases that use the helpers

**Findings** (verified by search of `home/`, `tests/`, Readme)
- `get-password`: `vpn-pw` (`01_work.zsh`: `get-password | osd-vpn-connect -k`, alias `osd-vpn-connect-pw` points to it), `update-system` (`00_alias.zsh`: `get-password | sudo -S apt update && ...`), and `kinit-pw` (calls `get-password` from its own directory).
- `kinit-pw`: called by `ensure-kerberos-token` when present, otherwise it falls back to plain `kinit`.
- So both aliases do use `get-password`. `update-system` is not work-specific: it lives in the general alias file, so it also depends on the keyring or `$PASSWORD` on non-work hosts.
- `get-password` reads the keyring through `secret-tool` (looked up by user), then `$PASSWORD`. It does not know Bitwarden or `VPN_PASSWORD`.
- No unit test calls `get-password`, `kinit-pw` or `ensure-kerberos-token` (verified by search in `tests/`).

**Suggestion:** record these three callers in the kerberos spec or decision record, and add a small unit test for `get-password` order (keyring, then `$PASSWORD`, then exit 1) using a stub `secret-tool`. Reason: the helper is the common point of three flows and is untested.

## A3. Refresher managed by Ansible

**Findings**
- Verified: `setup-ensure-kerberos-cron` supports `--install`, `--update`, `--uninstall` and `--freq` (default 15 minutes), and writes a marked block (`BEGIN ensure-kerberos-token`) in the user crontab.
- Verified: `01_work.zsh` prints a tip with the install command when no marked block is found in the crontab.
- Verified: no Ansible role or task under `ansible/` calls it; `ansible/roles/` has no kerberos role.
- Unverified: whether the cron job should run on every work machine (a missing keyring password would make each run fail quietly or log errors).

**Suggestion:** add a task to the work-machine path that runs the script with `--update` (idempotent), only when `get-password` can succeed, or leave the hint in place. Reason: the script is already idempotent and marker-based, so Ansible can own it with little code. Confirm that the cron environment can reach the keyring first (see A4).

## A4. Password fallback across contexts

**Findings**
- Verified current order in `get-password`: keyring (`secret-tool`), then `$PASSWORD`.
- Verified callers by context: interactive shell (`vpn-pw`, `update-system`, `kinit-pw` via `ensure-kerberos-token` from the prompt hook), cron (`ensure-kerberos-token` via `kinit-pw`), and the LDAP helpers, which use `$PASSWORD` directly (`-w "$PASSWORD"`) and do not call `get-password`.
- Unverified (hypothesis): in cron there is usually no D-Bus session, so `secret-tool` may fail and `$PASSWORD` is not set either; containers have neither. I did not test this.
- The Readme mentions Bitwarden custom fields such as `VPN_PASSWORD` for frequently changed passwords; `get-password` does not use them.

**Suggestion:** document the table caller × source, then define one order: keyring, then `$PASSWORD`, then optionally a Bitwarden-backed variable loaded by the env layer. Make the LDAP helper use `get-password` so there is one source. Reason: today two different mechanisms exist and only one is helper-based. Test the cron case on a real work machine before promising a fallback there.

## A5. LDAP region selection

**Findings** (verified by reading `01_work_ldap_helpers.zsh`)
- The base helper `ldapsearch-bosch` connects to one fixed server `<LDAP_URL>` (not region-specific in the code).
- The region for the bind identity is derived from the active Kerberos principal: it parses `klist`, takes the realm part after `@`, keeps the first label, lowercases it, and binds as `<region>\<user>`. Without a ticket it uses `$LDAP_DOMAIN`, then the default `de`.
- The search base is separate: `ldap-user-info` and `ldap-user-info-full` use `$LDAP_USER_BASE` or the default `DC=<de>,DC=<org>,DC=com`; `ldap-user-groups` hardcodes the same `de` base with no override.
- So a user from another region gets the right bind domain but still searches the `de` base, unless `LDAP_USER_BASE` is set. For other regions, results may be wrong or empty (unverified, I did not run queries).
- Unverified: whether the server exposes a global catalog or root DSE (`namingContexts`) that could be used for discovery.

**Suggestion:** derive the search base from the same region value as the bind domain, and let `ldap-user-groups` honour `$LDAP_USER_BASE`. Optionally ask the server's root DSE for naming contexts, or search a global catalog, and compare with the principal-based approach on a machine with access. Reason: the bind uses the region but the base does not, so region handling is only half done. Quick win: reuse `LDAP_USER_BASE` in `ldap-user-groups`.

# Part B: baseline-code-quality-tests

## B1. Format `.bashrc` except externally managed blocks

**Findings**
- Verified: `.pre-commit-config.yaml` excludes `\.bashrc` from `shfmt`. The spec (pre-commit-checks) gives the reason: work Ansible blocks.
- Verified: the repository's `home/dot_bashrc` contains no `ANSIBLE MANAGED` markers and `ansible/` has no `blockinfile` task for it (the only marker pair, `# BEGIN/END ANSIBLE MANAGED BLOCK`, is in `home/dot_profile`, lines 34-40). The `lineinfile` task in `ansible/roles/sshd_home` touches sshd config only.
- Verified: shellcheck already runs on `^home/dot_(bashrc|profile)$` as a separate hook.
- Verified: `dot_bashrc` has code that `shfmt` would likely change (for example `\. "$NVM_DIR/nvm.sh"  # ...` with double spaces, long one-line `alert` alias).
- Unverified: the "work Ansible setup" that adds blocks to `.bashrc` is not in this repo; it probably lives outside (corporate tooling). The markers it uses are unknown here.

**Suggestion:** ask the owner which external tool edits `~/.bashrc` and which markers it writes. If the file in `$HOME` is a symlink into the repo, such edits land in the repo file, which explains the exclusion. Then either keep the exclusion, or move repo code into a sourced file (for example `~/.bashrc.d/` or `dot_bash/…`) that `shfmt` formats, leaving `.bashrc` a thin stub. Reason: the thin-stub route avoids marker-aware tooling.

## B2. Remove the commented-out `protect-files` hook

**Findings** (verified by search of the whole repo)
- The only references are the commented block at the end of `.pre-commit-config.yaml` (the `ditschi/pre-commit-hooks` repo, protecting `.gitconfig`) and the OpenSpec proposal/design that mention the investigation. No workflow, doc, test or script refers to it.
- It was added in commit `ae36cd6` ("install script with hardlinks and gitconfig rework"). The local hook `gitconfig-no-host-settings` now guards `home/dot_gitconfig`, which covers a similar goal.
- The owner already said they want it removed.

**Suggestion:** delete the commented lines (the last 7 lines of `.pre-commit-config.yaml`). Reason: dead, unreferenced, and its purpose is covered by the local gitconfig hook.

## B3. Checks required before a commit

**Findings**
- Measured (verified): `uvx nox -s tests` (unit tests, 191 passed) took about 1m42s wall-clock here, of which about 100s is pytest itself; venv setup was cached. Docker and APT tests were not run, by instruction. Pre-commit was not timed.
- `.github/workflows/verify.yml` runs on every push and pull request: `unit` (reject host-only Git settings, chezmoi, py_compile, unit tests, Ansible syntax), `pre-commit` (all hooks, 15 min timeout), `presets` (Docker smoke, matrix of 6 profiles), `host-yaml-container` (clean install and migration), `apt-rpi-zero` (2 Ubuntu versions, `-m apt`), `apt-home-laptop` (`-m apt_gnome`), `unit-arm`, and `ansible-lint` only when `ansible/**` or host files change. No job needs another except `ansible-lint` needing `changes`. Job durations are not available offline; unverified.
- `noxfile.py` default sessions are `compile`, `tests`, `ansible`, `docker` (Docker skips itself if unavailable). APT tests are not in nox, only logged as manual commands.
- Readme states what is deliberately not in CI (real hardware, Kerberos against the KDC, Cosmic, real `bw login`, real Influx).
- There is no local git hook that runs tests; `pre-commit` has only a `commit-msg` hook (`no-co-authored-by`) beyond the file hooks.

**Suggestion:** require before commit: `pre-commit run` (file hooks, fast) as the default. Run `nox -s compile tests ansible` before push, with unit tests as the gate. Keep Docker and APT in CI only, or run them locally when touching `ansible/`, `machine/hosts/` or the installer (the CI `changes` filter already marks those paths). Reason: 100s for unit tests is acceptable before push but long for every commit; APT and Docker are slow and are better caught by CI. To decide with data, time `pre-commit run --all-files` and a Docker smoke job in CI logs.
