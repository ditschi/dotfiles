# Tasks

Implementation follows design.md, which incorporates the approved investigation, and the three capability deltas. All tasks below are implementation work, not completed by consolidating or authoring this plan.

## 1. Capture the Behavior Baseline

- [x] 1.1 Run `pytest tests/unit/test_zsh_handoff.py tests/unit/test_command_prefix.py -q` against the current working tree, including command-prefix recovery; record the result and tool availability in design.md so later failures can be distinguished from preexisting ones.
- [x] 1.2 Capture warm first-prompt and deferred-readiness measurements using the archived shell benchmark method on a disposable HOME, with identical tool/profile settings for the later comparison; record median/p90, environment and reproducible commands in design.md, or document a concrete unavailable prerequisite before proceeding. The pre-move snapshot timed out before the deferred-load marker in the archived container; no timing samples were treated as valid.

## 2. Split Configuration by Interpreter

- [x] 2.1 Move shared aliases, environment, machine profile, cache, update state and command-prefix matching into `home/core/.shell/common`; retarget their existing shell consumers as part of the move. Keep interactive mise activation out of shared environment loading. Update the existing credential/env/matcher fixtures and verify both interpreters accept the shared files, env-file precedence is unchanged, and standalone env loading does not initialize prompts/plugins.
- [x] 2.2 Extract Bash handoff, settings, history, tools, Readline and prompt owners under `.shell/bash`, add its explicit `init.bash`, and reduce `.bashrc` to the guarded entry flow and final local override. Extend `test_zsh_handoff.py` and `test_command_prefix.py` with once-only/order assertions, an unregistered sentinel, non-interactive return, local-last ordering and preserved history/mise/update/status hooks; run those focused tests with Starship and fallback paths.
- [x] 2.3 Move zsh owners and the plugin list under `.shell/zsh`, add explicit `init.zsh`, and thin `.zshrc`. Source machine completion once after deferred or offline `compinit`, preserve check-mode queue draining/markers and plugin order, and update the existing shell fixtures. Verify ordered/once-only loading, an unregistered sentinel, normal PTY startup, missing optional tools, offline completion and failing deferred-plugin detection with the focused shell tests.
- [x] 2.4 Move work tools/environment into `home/work/.shell/work/common` and LDAP helpers into `.shell/work/zsh`; preserve defensive guards and managed-block text, updating existing work/profile tests and fixtures. Verify tools-before-environment order, both work shells, Bash exclusion of LDAP, and no work side effects for private/container eligibility; run the affected tests in `test_bw_and_answers.py` and `test_machine_cli.py` plus focused shell coverage.
- [x] 2.5 Update the README shell section with the authored directory map, both entry/load sequences, new plugin-list path and unchanged local extension points. Verify each documented include path exists in the refactored tree, no active instructions name the old authored loader paths, and no managed block was rewritten while moving files.

## 3. Coordinate Path Consumers and Health Checks

- [x] 3.1 Relocate the cached Bash health implementation to `.shell/bash/zsh-health.bash`, update handoff and `machine_cli/auto_update.py::zsh_health_failure`, and preserve the callable helper interface. Update tests in the existing update/shell test modules; verify a relocated deliberately failing helper is detected by the Python consumer rather than skipped, and existing handoff eligibility/failure/fresh-host/timeout scenarios still pass.
- [x] 3.2 Replace the required loader/watch paths with the `.shell` inputs and relevant parent directories. Extend `test_zsh_handoff.py` for shared/zsh/work edits, removal and rename, local overrides, plugin-list edits, the health helper and manual reset; verify cached pass and failure rechecks occur as specified, while a local Bash-only prompt/history/editor edit alone does not force a zsh check.
- [x] 3.3 Retarget `git-credential-env`, convenience edit/reload/reset helpers, plugin/deferred source references and remaining active path consumers. Update existing `test_gitconfig.py` and `test_update_and_env.py` fixtures and run their affected tests; verify credentials load in a non-interactive Bash process and both `reload` and `zsh-recheck` still reach the relocated owners.
- [x] 3.4 Ensure existing generated plugin bundles are regenerated safely if they reference removed authored paths, retaining current XDG cache and antidote checkout locations. Add a preexisting-cache regression case in the existing shell tests and verify no plugin reinstall is needed, offline startup retains usable cached data, and no generated file is written into the linked source tree.
- [x] 3.5 Update the README health/reset and credential-loading references for the relocation. Verify its commands against a disposable configured HOME and review active source/test/document references to the retired paths, excluding historical archived/investigation records.

## 4. Verify Deployment and Lint Coverage

- [x] 4.1 Extend `test_dotfiles.py` and the existing update-classification tests for files added, modified and removed under core/work `.shell` paths. Verify the existing mise group enumeration, apply/prune and update steps cover the new layout; add minimal production support only for a failing case demonstrated by these tests.
- [x] 4.2 Add old-layout migration and work-to-private/container transition cases to the existing dotfile/profile tests. Verify new links point into the selected checkout, obsolete repository-managed links are pruned, local files/overrides/backups remain intact, and no whole-directory or plugin/cache deletion occurs; document the tested apply and rollback procedure in the README.
- [x] 4.3 Adjust shell lint selection only as needed for shared `.sh`, Bash `.bash` and zsh `.zsh` modules. Verify shared/Bash code receives the intended ShellCheck/shfmt checks, zsh is not parsed as Bash, interpreter syntax checks pass, and the hooks also process explicit newly added paths.

## 5. Run Integration and Required Gates

- [x] 5.1 Run `pytest tests/unit -q`, `pre-commit run --all-files`, and pre-commit with all newly added paths explicitly listed. Record complete results; fix only regressions introduced by this change and distinguish unrelated failures or missing prerequisites.
- [x] 5.2 Run `pytest tests/integration/test_profile_containers.py tests/integration/test_host_yaml_install.py -q` with the repository's Docker/test dependencies available. Verify clean and migrated work/private/container setups, shell startup, completion, final local overrides, work exclusion and persistent cache reuse; record any unavailable environment rather than marking unexecuted checks as passed. The focused nox Docker selection passed 11 profile, transition and host-YAML container tests.
- [x] 5.3 Repeat task 1.2's measurements on the same setup, compare first-prompt and fully-loaded median/p90 against baseline, and record results in design.md. Owner-confirmed acceptance (2026-10-30): the refactor is accepted when startup is not slower than before; the archived absolute targets (Bash under 70 ms, zsh prompt under 50 ms) are not met on this installation by the old or the new layout and are recorded as such. Bash improved on both profiles; zsh container prompt/loaded medians differ by +1.9 ms/+9.6 ms in one run.
- [x] 5.4 Run `openspec validate restructure-shell-config --strict` and reconcile the implemented source map, design and every delta scenario with the completed tests. Verify no runtime behavior was removed, no secrets were committed and all implementation tasks have recorded evidence before requesting archive.

## Workflow Follow-up

- Review the completed implementation before deploying it to the live home through the normal update workflow.
- Archive this consolidated change after its required checks and owner review; its design retains the assessment and decision record.
