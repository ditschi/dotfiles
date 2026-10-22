# Design

## Context

This change writes the current shell behaviour down as baseline specs. It changes no code. See proposal.md for motivation and the specs for the confirmed behaviour.

Facts established with the owner:

- The machine profile (`machine-profile.sh`) sets `MACHINE_PROFILE` and `WORK_SETUP` so both bash and zsh know the host type; it is shared by both shells.
- On all work hosts the account is centrally managed and is not in the local password database, so the login shell cannot be changed with `chsh`. The company route is documented by the `chsh-bosch` helper. This is why zsh is reached through a handoff from bash.
- The externally managed blocks are rewritten by an external tool (osd-ansible) when they are changed, so they stay unchanged.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep every unclear point visible, with a suggestion and its reason, as input for later changes.

**Non-Goals:**
- Fixes or improvements to the behaviour.
- The zsh startup health check (separate change `add-zsh-startup-check`, to be reworked on top of `shell-handoff`).

## Decisions

1. **Handoff stays the way to reach zsh.** Because `chsh` is not available on work hosts, the bash handoff is the accepted mechanism for now. Whether `exec` from `.bashrc` is the most elegant way is open (see Investigations).
2. **Numeric prefixes order module loading.** Some modules must load first, so lexical order with numbers is the accepted rule today. The owner is open to a better loading scheme.
3. **Edit aliases are to be removed.** They exist per module but are rarely used; `code ~/dotfiles` is fast enough. The removal is an improvement, so it is a later change and not part of this baseline.
4. **Bare zsh is worse than bash.** The underlying goal of the handoff is to use zsh with the customisation. Where it cannot load completely (for example zinit fails or required pieces are missing) bash is preferred, because bash is still nicer than an uncustomised zsh. This is delivered by `add-zsh-startup-check`.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Default handoff outside Docker and outside `bash -c`.** The owner could not confirm why the default handoff skips Docker and command strings. Suggestion: check each case against real use (devcontainers `sde`/`sdx`, scripts calling `bash -c`) and either state the reason in the spec or remove the guard. Why: a guard without a known reason may block a wanted handoff or protect something unknown.
2. **Handoff mechanism.** Suggestion: compare `exec zsh` from `.bashrc` with alternatives that work without `chsh`: the documented company route (SSSD `override_shell`), `.profile`-based handoff, and terminal or SSH settings that start zsh directly. Why: the current approach works, but its guards grew incrementally and an alternative may need fewer of them.
3. **Folder structure of the shell configuration.** Suggestion: split `~/.zsh` into zsh-only, bash-and-zsh shared, and work folders (for example `zsh`, `bash`, `common`, `work`). Why: the bash module list is hard-coded today and the work modules are mixed with the rest; a structure that expresses this would make the bash subset and the work condition self-evident.
4. **Module loading scheme.** Suggestion: keep numbering but evaluate an explicit ordered list or named stages. Why: with numbers, inserting a module before an existing one is hard, although so far never needed.
5. **chsh on work hosts.** Suggestion: provide a `chsh` alias or function in the work context that writes `~/.preferred-shell`, in the same way the `machine` command could do once Ansible and chezmoi are applied and zsh starts without problems. Why: it gives work hosts the familiar `chsh` workflow without needing a login shell change.

## Risks / Trade-offs

- Baseline specs omit the unconfirmed guards (Docker, `bash -c`) → the specs do not claim them, but the current code still has them; later changes must not remove them silently.
- A restructure of the shell folders touches every profile → needs its own change with a migration plan.

## Open Questions

- Which dev-container profile expectations (`sde`/`sdx`) apply to the Docker guard? To be answered in investigation 1.
