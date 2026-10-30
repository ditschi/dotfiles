# Design

## Context

See proposal.md, Why, for motivation. The approved shell-layout assessment is incorporated here, together with the selected structure and implementation plan; no separate investigation change is required. The implementation starts from the current working tree, including command-prefix recovery; it must not replace that work with an older committed shell configuration.

Today `.bashrc` contains the handoff and most fallback behavior. `.zshrc` delegates to `.zsh/config/00_LOADER.zsh`, which loads helpers then glob-sources numeric modules. Environment and history modules mix shared and interpreter-specific concerns. Work files are deployed by a separate mise group but appear in the same `.zsh/config` directory.

Assessment refreshed on 2026-10-29: deployment uses real filenames in mise dotfile groups, not the former `home/dot_*` paths or `.chezmoiignore`. Antidote, zsh-defer and Starship have replaced zinit and Powerlevel10k; NVM/pyenv modules are no longer active. The old zinit `atinit` double-load question is obsolete. The remaining layout problem is interpreter ownership and explicit source order, not replacing the selected tooling.

Three contracts change: `zsh-config-loading`, `bash-shared-config` and the path-specific portions of `shell-handoff`. Prompt, plugin, env-file, managed-block and local-override behavior remain regression constraints. The archived `2026-10-23-adopt-antidote-starship/design.md` records why completion is deferred, why health checks drain deferred work, and why Bash retains Readline and the mise prompt hook.

The Python update health-check consumer is `machine_cli/auto_update.py::zsh_health_failure`; it sources the current Bash helper directly. `git-credential-env` loads the environment module without an interactive shell. Neither consumer can be left on the old path.

## Goals / Non-Goals

**Goals:**

- One readable, explicit load sequence per interpreter, with feature implementations outside the entry points.
- Interpreter ownership visible in both directory and suffix: shared `.sh`, Bash `.bash`, zsh `.zsh`.
- A move that works for fresh installations, existing managed homes and homes with local exceptions, with focused tests proving behavior is retained.

**Non-Goals:**

- A generic module registry, automatic recursive discovery, new plugin manager or new runtime dependency.
- POSIX conversion of all shared code; shared means accepted by Bash and zsh.
- Changing handoff eligibility, prompt appearance, command-prefix matching, history semantics, secret parsing or authentication side effects.
- Moving generated caches/checkouts, deleting old plugin-manager data, or altering Ansible configuration.

## Decisions

### Neutral root, explicit registration and thin entry points

Use the approved `.shell/{common,bash,zsh}` root and descriptive names. `.bashrc` retains its interactive guard, invokes Bash handoff before fallback initialization, loads `bash/init.bash` if the session stays in Bash, and sources `.bashrc-local` last. `.zshrc` invokes `zsh/init.zsh` and sources `.zshrc-local` last. Keep login responsibilities in `.profile` and minimal non-interactive behavior in `.zshenv`; update explanatory path references only where needed.

Each `init` contains direct, ordered source statements and clearly named calls for any deliberate synchronous/deferred stages. Registration is explicit: adding a file does not run it. Do not duplicate the list in a separate manifest or add numeric prefixes whose order competes with it. Shared helpers are included by the loader, not re-sourced by every feature module.

The owner approved this over keeping a `.zsh` root, which would continue to mislabel shared/Bash code, and over numeric/glob discovery, which obscures registration and dependencies. A file per tiny function was also excluded in the approved assessment; keep coherent concerns together.

### File ownership and migration map

The recommended authored tree is:

```text
home/core/
|-- .bashrc                         # interactive guard, handoff, Bash init, local override
|-- .zshrc                          # zsh init, local override
|-- .profile                        # login setup stays separate
|-- .zshenv                         # minimal non-interactive setup stays separate
`-- .shell/
    |-- common/
    |   |-- aliases.sh
    |   |-- environment.sh          # shared defaults and env-file loading
    |   |-- machine-profile.sh
    |   |-- cache-eval.sh
    |   |-- update-state.sh
    |   `-- command-prefix.sh       # matching logic, not editor integration
    |-- bash/
    |   |-- init.bash               # explicit ordered source list
    |   |-- handoff.bash            # existing handoff policy
    |   |-- zsh-health.bash         # cached startup health check
    |   |-- options.bash
    |   |-- history.bash
    |   |-- tools.bash              # mise, completion, git helpers, colors, fzf, zoxide
    |   |-- readline.bash           # keys, pasted prompts, command-prefix integration
    |   `-- prompt.bash             # prompt hooks, Starship and fallback
    `-- zsh/
        |-- init.zsh                # explicit ordered source list
        |-- options.zsh
        |-- history.zsh
        |-- tools.zsh               # interactive mise activation
        |-- plugins.zsh
        |-- plugins.txt
        |-- keybindings.zsh
        |-- prompt.zsh
        `-- machine-completion.zsh  # registered after compinit
home/work/
`-- .shell/work/
    |-- common/
    |   |-- tools.sh
    |   `-- environment.sh
    `-- zsh/
        `-- ldap-helpers.zsh
```

All target paths below are relative to the owning dotfile group and therefore to `$HOME` after deployment.

| Current source | Target owner | Separation |
| --- | --- | --- |
| `core/.zsh/config/00_alias.zsh` | `.shell/common/aliases.sh` | Keep shared aliases; retarget convenience edit/reload paths where necessary. |
| `core/.zsh/config/01_env.zsh` | `.shell/common/environment.sh` | Keep defaults and env-file precedence/parser; move zsh mise activation to zsh tools. |
| `core/.zsh/machine-profile.sh` | `.shell/common/machine-profile.sh` | Preserve profile/context/device rules. |
| `core/.zsh/cache-eval.sh` | `.shell/common/cache-eval.sh` | Keep shell-specific generated suffixes and existing cache paths. |
| `core/.zsh/update-state.sh` | `.shell/common/update-state.sh` | Keep state reading and update/reload behavior. |
| `core/.zsh/command-prefix.sh` | `.shell/common/command-prefix.sh` | Matching logic only; no editor hooks. |
| `core/.bashrc`, handoff policy | `.shell/bash/handoff.bash` | Preserve preference, parent/nesting and container guards. |
| `core/.zsh/zsh-handoff-check.sh` | `.shell/bash/zsh-health.bash` | Keep the callable health API used by Bash and `machine`. |
| `core/.bashrc`, shell settings | `.shell/bash/options.bash` | Window sizing, chroot/less handling and existing Bash extension setup. |
| `core/.zsh/config/06_history.zsh`, Bash branch | `.shell/bash/history.bash` | Bash history policy; editor bindings belong to Readline; prompt synchronization is assembled once. |
| `core/.bashrc`, tool setup | `.shell/bash/tools.bash` | Mise activation, completion, cached fzf/zoxide and plugin-checkout commands/colors. |
| `core/.bashrc`, editor helpers | `.shell/bash/readline.bash` | Keymaps, sudo, pasted prompt handling and command-prefix capture/insertion. |
| `core/.bashrc`, prompt setup | `.shell/bash/prompt.bash` | Single prompt-hook assembly point, Starship and built-in fallback. |
| `core/.zshrc`, options | `.shell/zsh/options.zsh` | Existing editor mode, correction, PATH and fpath settings. |
| `core/.zsh/config/06_history.zsh`, zsh branch | `.shell/zsh/history.zsh` | Existing zsh history options and file. |
| zsh mise activation in `01_env.zsh` | `.shell/zsh/tools.zsh` | No interactive activation in the shared environment module. |
| `core/.zsh/config/02_plugins.zsh` and `.zsh/plugins.txt` | `.shell/zsh/plugins.zsh` and `plugins.txt` | Antidote ownership and the same deferred plugin order. |
| `core/.zsh/config/04_keybindings.zsh` | `.shell/zsh/keybindings.zsh` | Existing ZLE widgets, plugin hook definitions and command-prefix integration. |
| `core/.zsh/config/03_theme.zsh` | `.shell/zsh/prompt.zsh` | Same Starship/built-in prompt and update hooks. |
| `core/.zsh/config/07_machine.zsh` | `.shell/zsh/machine-completion.zsh` | One explicit registration after completion initialization. |
| `core/.zsh/config/00_LOADER.zsh` | `.shell/zsh/init.zsh` | Replace discovery with the explicit sequence. |
| Work `01_work_tools.zsh` and `01_work.zsh` | `.shell/work/common/tools.sh` and `environment.sh` | Keep these in `home/work`, in tools-before-environment order. |
| Work `01_work_ldap_helpers.zsh` | `.shell/work/zsh/ldap-helpers.zsh` | zsh-only and still guarded by the work profile. |

### Explicit order, without forcing identical shell initialization

Both loaders use the shared machine profile before profile-dependent modules. Source shared cache/update/matching helpers before their consumers. Keep aliases and environment loading explicit; do not make `environment.sh` import interactive startup. The credential helper sources only that shared environment file, preserving current env-file handling and precedence.

Bash phases:

1. `.bashrc` returns for non-interactive use. Handoff runs before any Bash fallback configuration; successful `exec` does not continue through the fallback loader.
2. The fallback loader reads the profile and helper definitions, then the existing Bash settings and extension setup. Preserve the effective PATH and alias precedence, including `~/.bash_aliases`.
3. Keep mise activation before shared env loading as in current Bash startup, then explicit shared aliases/environment/history and eligible work tools/environment. Separate early activation from later tool integration within the tools owner where dependencies require it; the calls remain visible in `init.bash`.
4. Initialize optional completion, cached tools and plugin-checkout helpers before final Readline bindings. Load shared command-prefix logic before its shell-specific callbacks.
5. Assemble prompt hooks once in `prompt.bash`, retaining history synchronization, mise, update state and command-prefix hooks before Starship takes ownership. Preserve status capture with Starship's saved command status and the built-in prompt path; do not treat intermediate hook success as command success.
6. Preserve startup update reporting, then return to `.bashrc` for its final host-local include.

Zsh phases:

1. Load profile, shared helpers and shell options; retain alias/environment precedence. Activate mise through the zsh tools owner at the same effective point relative to shared environment processing, before dependent tool/plugin initialization.
2. Explicitly load eligible work tools/environment and LDAP helpers, followed by shell history and the synchronous plugin/keybinding/prompt setup in dependency order. `plugins.zsh` keeps antidote's synchronous declarations and queues the deferred chain; widget-hook definitions exist before deferred execution begins.
3. The first prompt does not wait for the normal deferred chain. Keep ez-compinit and zsh-defer `-dmpr`; one deferred init performs colors, `run-compinit`, machine completion, fzf and zoxide before dependent completion plugins. Keep history search/autosuggestions and syntax-highlighting order intact, with highlighting last.
4. The archived design registered machine completion through ez-compinit's placeholder during eager loading. The approved layout instead makes the dependency explicit by sourcing `machine-completion.zsh` once after `run-compinit`; it does not replace ez-compinit or add a general after-compinit registry. The offline no-bundle path also sources machine completion once after its built-in `compinit`.
5. In health-check mode, drain the same deferred queue only after all synchronous definitions are loaded, then set/check the existing full/deferred markers. Retain the current no-TTY fzf guard and fresh/offline behavior.
6. Preserve startup update reporting, then return to `.zshrc` for its final host-local include. Normal deferred work still runs later, as it does today; the refactor does not redefine local overrides as an after-all-plugins hook.

### Work selection and generated data stay separate

The `work` group deploys `.shell/work/common` and `.shell/work/zsh`; `core` does not contain copies or placeholders for work code. The loader includes optional work files only with the existing work conditions and file availability. Preserve the modules' defensive work guards and externally managed proxy block. Group selection and runtime eligibility remain separate checks.

Retain `${XDG_DATA_HOME:-$HOME/.local/share}/antidote` and `${XDG_CACHE_HOME:-$HOME/.cache}/zsh` for checkouts, generated plugin bundles, tool init, completion dumps and generated machine completion. Retarget the authored plugin-list path and ensure a preexisting bundle cannot retain a removed authored source path. Prefer the existing safe regeneration mechanism; do not delete checkouts or introduce generated files under the linked `.shell` tree.

### One health implementation with relocated consumers

Update both Bash handoff and `machine_cli/auto_update.py` to source `.shell/bash/zsh-health.bash`. Preserve the existing callable helper interface so the post-update check and interactive handoff test the same implementation. Keep `zsh-recheck` and update/reload helpers working after their source paths move.

The required loader becomes `.shell/zsh/init.zsh`. Watch entry points, preferred shell, local zsh override, health helper, plugin list, shared helpers and applicable work/zsh startup inputs. Include the relevant directories/parents so removal and rename invalidate cached outcomes even if the removed file cannot be statted. Do not mistake watching a directory for permission to source its contents. Local edits to Bash-only prompt/history/editor modules do not themselves invalidate zsh health; applying a dotfile update still does.

## Risks / Trade-offs

- [A file move silently bypasses the update health check] -> Test `zsh_health_failure` against a relocated failing helper, not only a mocked method; retain handoff PTY/subprocess coverage.
- [Extracting history or prompt code loses failure status or duplicates callbacks] -> Move responsibilities without changing their semantics; verify one callback registration, command-prefix cancellation/queued input, Starship and fallback prompts, and cross-session history behavior.
- [A glob test is updated to another glob and misses the new contract] -> Add an unregistered sentinel file and assert it never runs; trace registered modules and assert order/count.
- [Deferred definitions are moved after their consumers] -> Exercise both normal PTY startup and check-mode queue draining, plus the offline built-in completion path.
- [Old links, generated bundles or work files survive a profile switch] -> Exercise migration from the old layout and switching away from the work group, retaining a genuine local sentinel file and proving it is not deleted.
- [More includes add startup overhead] -> Compare the same host/config/tools before and after with warm caches; measure first prompt and deferred readiness separately.
- [New suffixes escape linting or zsh code is fed to Bash tooling] -> Explicitly cover shared/Bash modules with appropriate ShellCheck/shfmt selection; use interpreter syntax checks for zsh and exclude generated files.

## Migration Plan

1. Capture the existing focused shell test baseline and comparable startup measurements. Include current command-prefix changes and preserve unrelated working-tree edits.
2. Move modules and update entry points, internal source paths, aliases, plugin-list references, credential helper and the Python health-check consumer as a coordinated change. Preserve `.profile` managed blocks byte-for-byte; do not rewrite managed work-block content while moving it.
3. Reuse mise's existing group target enumeration, apply and pruning behavior. Verify added/removed files under `.shell` still trigger dotfile and shell-update steps. Add minimal migration-helper support only if existing focused tests demonstrate a gap.
4. Apply in disposable old-layout and clean homes. Prove new links target the selected checkout, obsolete repository-managed links are pruned, local exceptions/backups survive, and work modules are absent after switching to a private/container selection. Do not recursively remove `.zsh` or any user directory.
5. Verify health-cache invalidation and bundle regeneration on an existing installation. Run focused, full unit, lint and container gates; update the README with the source map and local extension points.
6. Deploy with the normal `machine update`/dotfile apply workflow only after review. Keep an existing session available for recovery and start a fresh shell to verify the result. Do not apply the author's live home during automated tests.

Rollback restores the previous repository revision through the normal reviewed update process and reapplies that revision's dotfile groups, recreating the old managed links and pruning the new managed links. Existing plugin checkouts, caches and host-local files remain in place. Reset the health cache with the restored `zsh-recheck` helper and confirm a fresh shell; do not roll back by deleting entire configuration directories.

## Implementation Baseline

Captured before the first shell-layout edit on 2026-10-30:

- `pytest tests/unit/test_zsh_handoff.py tests/unit/test_command_prefix.py -q`: 176 passed in 14.15 s.
- Bash and zsh are installed at `/usr/bin/bash` and `/usr/bin/zsh`; Starship 1.27.0 is on the mise PATH. Docker 29.8.1 is available and the `shell-spike:local` benchmark image exists. `hyperfine` and `zsh-bench` are not installed on the host; the archived image contains both.
- No shell files have been changed for this refactor at baseline capture. The shell feature changes already present in the working tree are included in the baseline test result.

The archived zsh-bench `--isolation user` launcher was attempted on 2026-10-30 but reported no ZLE TTY and timed out before the deferred-load marker. Its raw prompt-only values are not representative. The same archived setup script was then run directly in a `script`-provided PTY with the deferred marker, which produced valid warm measurements. To retain the command-prefix behavior already present at baseline capture, the pre-move snapshot uses the committed old layout with the current matcher and keybinding module overlaid; the old numeric loader and module tree remain in use. The marker script exits its install-time shell by signal after all plugins load (`install_rc=1`); the subsequent warm samples and feature checks completed.

## Performance Comparison

The archived `spike/configs/_common/setup.zsh` marker harness was then run directly in the same `shell-spike:local` Ubuntu 24.04 image, using `script` to provide a PTY, 13 warm starts and the summarizer's first-three-run warm-up drop. The isolated HOME was seeded from read-only plugin checkouts and the generated plugin cache. This yielded valid first-prompt (`prompt_ms`) and fully-deferred (`loaded_ms`) samples even though the zsh-bench CLI itself could not report a TTY. The pre-move snapshot came from committed `HEAD`; it does not contain the uncommitted command-prefix integration present at baseline test capture, so the comparison is indicative of layout cost, not a byte-identical feature comparison.

| Layout | Prompt median/p90 (ms) | Fully loaded median/p90 (ms) | Measured runs |
| --- | ---: | ---: | ---: |
| Pre-move layout with current command-prefix integration | 55.12 / 60.30 | 118.81 / 128.22 | 10 |
| `.shell` layout | 56.98 / 64.78 | 128.40 / 141.40 | 10 |

Both layouts completed deferred loading below 300 ms in this container. The `.shell` move added about 1.9 ms to prompt median and 9.6 ms to fully-loaded median in this run; both container prompt medians exceed the archived 50 ms target, so this container result does not certify that target on the reference host. The archived feature marker reports `sudo=0` for both runs because it looks for the historical `sudo-command-line` name, while the actual configuration uses `dotfiles_sudo_command_line`; the Bash/zsh PTY tests verify the binding behavior instead.

An auxiliary Bash first-prompt run with the current layout measured 101.72 ms median and 107.02 ms p90 over 10 warm starts in the same container. Two earlier attempts to use the marker on the host produced inconsistent values (0/1000 ms and 500/1000 ms), so those samples are invalid; the host marker did not reliably detect the first prompt.

On 2026-10-30, a same-host comparison was captured on `LR-C-0042H` (Ubuntu 24.04, physical work desktop, `/usr/bin/bash`, mise 2026.10.17, Starship 1.27.0). Each case used a disposable HOME, the same installed mise tool store and Antidote checkout, isolated XDG caches, 14 PTY starts via `timeout 20 script -qfec 'bash -i' /dev/null`, and the archived `SPIKE_EXIT_AT_PROMPT` prompt marker. `SHLVL=2` kept the timed Bash from performing its normal Bash-to-zsh handoff. The first start and three warm-ups were dropped; median/p90 use the remaining 10 starts. The baseline tree came from `git archive HEAD`; the refactor tree used the current `.shell` files. Private and work applied-host profiles were run separately, with the work modules present only in the work case.

| Profile | Baseline median/p90 (ms) | `.shell` median/p90 (ms) | Change |
| --- | ---: | ---: | ---: |
| Private | 565.14 / 626.46 | 551.12 / 605.20 | -14.02 / -21.26 |
| Work | 638.62 / 792.80 | 608.46 / 689.95 | -30.16 / -102.85 |

The refactor did not regress Bash startup in this comparison, and the difference between work and private profiles is visible separately. Both profiles remain far above the archived `<70 ms` Bash target, so this measurement does not verify that acceptance criterion. The archived Zsh container comparison above still has deferred loading below 300 ms, while both prompt medians exceed the archived `<50 ms` target. The owner accepted the refactor on 2026-10-30 on the basis that startup is not slower than before; the absolute historical targets are unmet by both layouts on this installation and are not claimed to pass.

A follow-up on the same disposable layouts compared ordinary interactive Bash startup with `bash --norc -i -c 'source "$HOME/.bashrc"'`, which bypasses the system rc while still loading the selected repository `.bashrc`. The system rc added about 143–159 ms median across the sampled baseline-private, baseline-work and refactor-work cases. The OSD proxy source and alias loader each took about 35–38 ms in isolation; `klist`, the disk checks and the update-file check each took about 1–5 ms. With the system rc bypassed, Bash startup still took about 313–332 ms, including the repository's `machine completion bash` call (130/144 ms median/p90) and Bash completion. These costs are shared by both layouts and explain why the comparison shows no material refactor penalty but cannot meet the historical 70 ms target on this installation. A post-run workstation check showed load 2.28 across 12 CPUs and a 4 GHz current CPU frequency; load was not captured during each timing sample.

An additional read-only check on 2026-10-30 resolved `osd-vm` to ABTVL421 (Ubuntu 22.04, Bash 5.1.16, work/server profile, four CPUs); its load average was 0.37–0.78. That host still has the legacy `.zsh` layout and does not have `mise`, `starship` or `machine` on PATH, so its installed startup is not comparable to the current desktop setup. An isolated temporary-HOME PTY attempt did not reach its prompt marker and was stopped; the temporary processes/directories were cleaned up and no timing samples are used.

## Git history and legacy records are evidence, not wording. Commits are incremental
  steps toward a result and are often badly worded. Abstract the intended behaviour or
  outcome, propose the most plausible motivation in clean prose, and have the owner
  confirm or reword it before it is written as fact. Verification

Reuse existing test modules rather than introducing a separate harness. Primary behavior checks are `tests/unit/test_zsh_handoff.py` and `tests/unit/test_command_prefix.py`. Extend shell assertions for explicit ordering/once-only execution, missing optional tools, work eligibility, local-last ordering and unchanged login/non-interactive behavior. Credential/env tests cover standalone env loading; update/dotfile tests cover the relocated Python consumer, classification, migration and preservation of local overrides.

Run the relevant existing Docker profile tests for clean and migrated work/private/container setups. Required final gates are `pre-commit run --all-files`, pre-commit with explicit new paths, `pytest tests/unit -q`, and strict validation of this change. Compare warm first-prompt and fully-loaded times against the captured baseline and existing targets: Bash first prompt under 70 ms on the reference setup; retain the archived zsh prompt/loaded targets and report work-host overhead separately. Ansible lint is not required unless implementation unexpectedly changes Ansible scope, which needs separate approval.

## Final Verification Results

- `pytest tests/unit -q`: 578 passed, 192 existing import deprecation warnings, 76.79 s.
- Focused shell suite after module extraction: 186 passed.
- Nox Docker selection for host dotfiles, four shell profiles, work-to-private pruning and clean host-YAML container install: 11 passed, 13 existing import deprecation warnings.
- `pre-commit run --all-files` and `pre-commit run --files` with all moved/new shell, test and planning paths: passed.
- `openspec validate restructure-shell-config --strict`: valid.
- `git diff --check`: passed; the externally managed OSD proxy block in the relocated work module matched the original bytes.
- Performance: Bash is slightly faster than the pre-refactor layout on the same host (private and work profiles); the zsh container run is about 2 ms (prompt) and 10 ms (loaded) slower, variance not measured. The archived absolute targets are unmet by both layouts here; the owner accepted the no-regression criterion for task 5.3.

## Assumptions

- The approved filenames are the starting boundaries, not a requirement to keep an empty file. Minor boundary adjustments can be made during implementation if explicit ownership, source order and all spec scenarios remain intact; record any adjustment here.
- Existing mise prune and update classification should already cover nested files under `home/`; prove this in focused tests before adding migration machinery. This is not permission to broaden cleanup beyond managed links.

No blocking design questions remain. Implementation is not started by creating these artifacts.

## Source Material

- Current working-tree shell files under `home/core/` and `home/work/`, assessed on 2026-10-29, including the recent command-prefix recovery work.
- Main specs for `bash-shared-config`, `zsh-config-loading`, `shell-handoff`, `shell-prompt`, `zsh-plugins`, `env-files` and `local-overrides`, together with this change's capability deltas.
- `openspec/changes/suggest-deduplicated-command-prefix/` for the recent matching and editor-integration behavior that this refactor preserves.
- `openspec/changes/archive/2026-10-21-baseline-shell-setup/design.md`, investigations 3 and 4, and `openspec/investigations/shell-and-prompt.md`, A3 and A4. These explain the original layout question; their old paths are historical, not the current source map.
- `openspec/changes/archive/2026-10-23-investigate-shell-plugin-manager/design.md` for the plugin-manager investigation and deferred-loading findings.
- `openspec/changes/archive/2026-10-23-adopt-antidote-starship/design.md` for the selected tooling, prompt and deferred-startup decisions; `openspec/changes/archive/2026-10-23-adopt-mise/design.md` for the non-interactive shims decision.
