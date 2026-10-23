# Design

## Context

`machine_cli/` is about 3,000 lines in mixin classes that share state through `self`; `bitwarden.py` (722 lines), `updates.py` (419) and `profile.py` (360) are the largest modules. The `machine` script reaches into private `typer` modules for completion and pins `typer==0.27.2`. See proposal.md for the motivation.

The update-flow simplification (file difference, update to the upstream tip, relevance filter for system changes, one state file, attention entry point) depends on the tools that shells need coming from `mise` instead of Ansible. It is therefore part of the change `adopt-mise`, which is archived after this one. This change contains everything that is independent of that move.

## Goals / Non-Goals

**Goals:**
- Fewer lines and fewer special cases in the CLI without changing command names, options or completion in bash and zsh.
- One generic mechanism for host-local additions to shared files.

**Non-Goals:**
- Replacing `bw` with `rbw` or another tool (see `openspec/backlog.md`).
- Moving tool installation to `mise` and simplifying the update flow; both are part of `adopt-mise`.

## Decisions

- **Bitwarden stays on `bw` only.** A two-tool setup (`rbw` for reads, `bw` for writes) was rejected because the logic would be maintained twice. A spike showed that `rbw` 1.15.0 cannot write to Vaultwarden 1.37 (missing `encryptedFor`, upstream `doy/rbw#385`) and cannot create secure notes with custom fields. A switch is considered only if one tool replaces the other completely. The code is split into a small `bw` client wrapper (status, unlock, get, list, upsert), `env pull` and the SSH-key logic; setup, status and settings-saving code is removed where it is redundant.
- **CLI toolkit is decided during implementation, with bash and zsh completion as the hard requirement.** Candidates are `cyclopts` and `click` with `argcomplete`. The choice must remove the private `typer` imports and the exact pin, and also covers the prompt helpers (`choose`, `choose_many`, `prompt_yes_no`).
- **Toolkit decision (task 1.1): plain `click`, without `typer`, `cyclopts` or `argcomplete`.** Spiked with `cyclopts` 4.25.3 and `click` 8.5.0 under bash and zsh.
  - `cyclopts` generates a static completion script; a `--limit` option cannot complete host names from `machine/hosts/*.yml` at tab time, so it fails the requirement.
  - `argcomplete` only supports `argparse` parsers, not `click`, so "click with argcomplete" is not a combination; `click` already has dynamic completion built in.
  - `click` provides dynamic completion through public API: `shell_complete=` callbacks on options and arguments, `click.shell_completion.get_completion_class(shell)(cli, {}, prog, var).source()` for `machine completion bash|zsh`, and `add_completion_class` to subclass the offer-options-on-empty-word behaviour. The script sourced without errors in bash (`complete -F _machine_completion machine`) and zsh (`_comps[machine]` registered), and `_MACHINE_COMPLETE=bash_complete` returned `alpha` for `--limit al`.
  - `typer` is only a thin layer over `click`; dropping it removes the private `typer._completion_*` and `typer._click` imports and the exact pin, at the cost of declaring options with `click` decorators. `click` is pinned with a compatible range in the script header.
- **Modules and functions instead of mixins.** The mixin classes are replaced by plain modules and functions that take a small context object. This is done module by module while each is touched, not as a separate rewrite.
- **One generic local-section helper.** It replaces `machine/gitconfig.py` and the `.bashrc` block relocation. Moved text is wrapped in marker comments in the `.local` file; identical text that reappears is removed without asking; diverging text is a conflict for the user. Shared files read their `.local` file with a guard (bash: `[[ ! -f ... ]] || source ...`, Git: `[include]`, which already exists in `home/dot_gitconfig`), so a missing file is not an error and the helper creates it only when something is moved.
- **Event log is append-only JSON Lines.** `events.jsonl` in `MACHINE_STATE_DIR`, written with the standard library, best effort (a write error never fails a command), capped at 5 MiB by dropping the oldest lines (roughly a year of events), with no age filter. Checks that find nothing new are not logged. Each line has timestamp, event, outcome, reason code, duration, short revision and profile; no secrets, paths or free text. Events: automatic update outcome (applied, reverted with reason, blocked with reason), manual update and `--force` use, subcommand usage, local-overrides actions, `env`/`ssh` outcomes and unlock failures, Ansible apply result. Frameworks were rejected: OpenTelemetry, statsd and Prometheus need a daemon or network; Telegraf (`monitoring` role) is not on work machines; journald misses manual runs and containers; logging libraries are not statistics. Read with `jq`; no `machine stats` command, to avoid another subcommand.
- **Conflict policy of the helper.** Text already known in `.local` is removed from the shared file without asking. New text without a conflict is accepted and not reported (it may be work in progress). A conflict is: the update changes the same file, or a Git key has a different value in the shared and the local file. Conflicts are recorded and the helper offers to resolve them interactively (in `adopt-mise` the same items appear in `machine attention`); nothing is overwritten.
- **The automatic revert stays as is (owner decision).** Its use is counted in the event log. Whether it is still needed is decided later from that data, not in this change; the "Automatic update safety net" requirement keeps its behaviour (`adopt-mise` only renames the tools it names).

## Risks / Trade-offs

- [Markers in `.local` files are edited by hand] → diverging text is reported as a conflict and never overwritten.
- [Non-interactive background run meets a conflict] → it records the conflict and moves nothing; new text without a conflict is left alone.
- [Replacing the CLI toolkit changes completion output] → the completion scenarios in `zsh-config-loading` and the existing unit tests are the acceptance check for bash and zsh.
- [Large refactor touches the 3,400 lines of tests] → keep command behaviour and the test cases, move code module by module, run `pytest tests/unit -q` after each module.

## Migration Plan

1. Toolkit and prompts first; they are independent of the rest.
2. `bw` client split.
3. Local-section helper; replace the `gitconfig` pre-commit hook and CI step; keep old behaviour until the helper passes the same cases.
4. Event log early, so revert data accumulates before the refactor.

Rollback is a revert of the respective commit; no data format outside `~/.local/state/` and the `.local` markers changes.
