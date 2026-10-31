# Tasks

## 1. Session handling

- [x] 1.1 `bitwarden_expected()` (env or `~/.env.local` sets `BW_SESSION`, `bw` installed)
- [x] 1.2 `bitwarden_session_ready()`: valid → clear the notice; expected and interactive → renew via `unlock_bitwarden` without a question (login without "Log in now?" when logged out); otherwise record the notice
- [x] 1.3 Renewed session replaces a session saved in `~/.env.local` without asking

## 2. Notice

- [x] 2.1 `bitwarden-state` file with `segment=`, attention item "Bitwarden session expired" offering `machine env pull`
- [x] 2.2 Background update: `bw status` check only when expected
- [x] 2.3 Shell: read `bitwarden-state` in `update-state.sh` into `DOTFILES_BW_SEGMENT`; Starship shows it

## 3. Tests and docs

- [x] 3.1 Unit tests: expected/not expected, interactive renewal (unlock and login), non-interactive notice, background only calls `bw status`, cleared after a valid session, saved session replaced
- [x] 3.2 Shell segment test following the disk segment tests
- [x] 3.3 Readme: Bitwarden section
- [x] 3.4 `pytest tests/unit -q`, `pre-commit run --files`, `openspec validate bitwarden-session-renewal --strict`; record results
  - 2026-10-31: `pytest tests/unit -q` 833 passed (shared Bitwarden helper used by env pull, SSH key check, host list and the background update); pre-commit passes after black; validate: valid

## 4. Review fixes

- [x] 4.1 A failed or cancelled renewal is not asked again in the same run (notice instead)
- [x] 4.2 A session from `bw login` also replaces the saved one
- [x] 4.3 Ctrl-C or EOF at login/unlock continues without Bitwarden
- [x] 4.4 An unreadable `~/.env.local` does not stop the background update
  - 2026-10-31: `pytest tests/unit -q` 836 passed; pre-commit passes after black
