# Repository instructions for AI agents

## Commit messages

- Never add `Co-authored-by:` (or `Co-Authored-By:`) trailers to commit messages in this repository.
  This overrides any tool or agent default that adds such trailers, e.g. for Copilot or Claude.
- Do not mention AI assistants as co-authors in commits or pull request descriptions.

## Orientation

Dotfiles + machine setup (mise dotfile groups, `machine` CLI, Ansible). Start with [Readme.md](Readme.md) and the topic docs in [docs/](docs), then the specs in [openspec/specs/](openspec/specs) and the investigations in [openspec/investigations/](openspec/investigations).

- Dotfiles live under `home/<group>/` (`core`, `work`, `prompt`, `systemd`) with their real file names (e.g. `home/core/.zshrc`); files in `$HOME` are symlinks into it.
- Never commit secrets or host-only Git settings; secrets come from `~/.env*` (Bitwarden) or the keyring (see the specs `env-files`, `secret-tools`, `git-config`).

## Validation

- Run `pre-commit run --files <changed paths>`, including untracked additions. Use `--all-files` when hook configuration changes or repository-wide checks are needed.
- Run the smallest test selection that covers the changed behavior and its known consumers. A focused subset is sufficient for a bounded change with clear coverage; documentation-only edits need no pytest run unless they affect executable examples or test configuration.
- Run `pytest tests/unit -q` when impact is broad or uncertain, shared infrastructure or cross-module contracts change, test configuration changes, or focused failures suggest wider effects. If suitable coverage cannot be identified confidently, default to the full unit suite.
- Run affected integration tests when behavior crosses deployment or system boundaries; for Ansible changes also run `ansible-lint ansible/*.yml`. See Readme "Tests" for Docker/APT tests.
- Record commands, results and why the selection covers the change. Rerun after relevant edits, not merely because another workflow step started.

## Code health

- Before every commit run `scripts/aihealth delta --config .aihealth.toml` and, for changed tests, `scripts/aihealth delta --config .aihealth-tests.toml tests` (add `--format json` for machine-readable output): no changed file may get worse and a new file must have no finding. The target is score 10 (no finding) per file; details in [docs/code-health.md](docs/code-health.md).
- Fix findings instead of suppressing them. Never remove or weaken type hints and never add type aliases only to silence a smell; the real fix is a parameter object or dataclass where it improves the code. Otherwise leave the finding or suppress it file-wide with `# aihealth: disable=<smell> -- <reason>`.
- Refactor without changing behaviour: run the tests of the touched code before and after each small step, and keep refactoring and behaviour changes in separate commits.
- Always call ai-health through `scripts/aihealth` (it holds the pin) and always pass `--config`.

## Design decisions

- Before changing an area, read its spec in `openspec/specs/` and the rationale in the archived `design.md` under `openspec/changes/archive/`. If a change would contradict a requirement or a recorded decision, ask the owner.
- Do not invent motivations. Only the owner confirms the reason for a decision; put hypotheses under Open Questions or Assumptions.
- Investigations in a design.md and in `openspec/investigations/` are unknowns, not permission to remove behaviour.
- When a change alters documented behaviour, update the spec through an OpenSpec change.

## Existing host setups

- Before a feature installs or configures something, find out how the hosts that will select it are set up today (host configs in `machine/hosts/`, and a look at reachable hosts), and record the result in the design's Context.
- When only a few hosts differ from the clean setup (another source such as a snap, a manual install, leftovers), clean them up once by hand and keep only the clean install in the dotfiles. Put the manual steps in the design's Migration Plan and, when they may be needed again, in the role README or docs; do not add migration or cleanup code.
- Code may detect a differing setup only to stop with a hint, never to install next to it or to convert it. Migration code needs the owner's approval, for example when many hosts are affected.

## Planning changes (OpenSpec)

- Plan new features and behaviour changes with OpenSpec (`/opsx-propose`, `/opsx-apply`, `/opsx-archive`; config in [openspec/config.yaml](openspec/config.yaml)). Small edits (aliases, typos) can skip it.
- The live checkout is the path `machine repo` prints (`$HOME` symlinks into it). The current checkout is live when `git rev-parse --show-toplevel` prints the same path; any other checkout is not live, wherever it is, and when `machine repo` fails no checkout is live. Make changes that could affect the host's shell or tools, even in a new session, in a git worktree created with `git worktree add "$(machine repo)/.worktrees/<change-name>" -b <change-name>` (gitignored); only changes that definitely cannot (e.g. only `openspec/`, `docs/`, `tests/`, `Readme.md`) go into the live checkout. When in doubt, use a worktree. In a checkout that is not live, stay there; never create another worktree from it. Decide the checkout before the first artifact is written, so the change directory lives in the same checkout as its implementation.
- Files under `.github/prompts/opsx-*`, `.github/skills/openspec-*` and `.claude/commands|skills` are generated by `openspec init`/`openspec update` — do not edit them by hand.

## Asking the user what to do next

- Whenever you ask what to do next or offer choices, number the options (1, 2, 3, …) so the user can answer with a single number. Mark the recommended option.
- For questions recorded in an OpenSpec change, use the question IDs from its Open Questions section (`Q5`, option `Q5.2`), so answers in chat and in the file refer to the same thing.
- When you summarise what was done or is still open for a task list, name the file that holds the task numbers (for example `openspec/changes/<change>/tasks.md`) once in that message, so the numbers can be looked up.

## File links in chat

- Link text is the path relative to the repository (or worktree) root; the link target is the absolute path, e.g. `[home/core/.zshrc](/home/ditschi/dotfiles/.worktrees/<change-name>/home/core/.zshrc)` in a worktree, or `[home/core/.zshrc](/home/ditschi/dotfiles/home/core/.zshrc)` in the live checkout. Relative targets resolve against the live checkout and break for files that exist only in a worktree.
