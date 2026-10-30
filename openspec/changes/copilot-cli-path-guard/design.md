# Design

## Context

VS Code adds `…/globalStorage/github.copilot-chat/copilotCli` to the `PATH` of its terminals; on Remote SSH the prefix is `$HOME/.vscode-server/data/User`. That directory holds a `copilot` script that runs `copilotCLIShim.js` with Electron's Node. Before it starts the real CLI, the shim runs `copilot --version`. Its environment for that call removes its own directory from `PATH` by literal text (shim 0.0.394, seen in the bundled source):

```js
PATH: (process.env.PATH || "").replaceAll(`${__dirname}:`, "").replaceAll(`:${__dirname}`, "")
```

Node resolves the main script's symlinks, so `__dirname` is the canonical path. When `$HOME` is an alias of another path (ABTVL421: `/home/dci2lr` and `/mnt/data/home/dci2lr`), the `PATH` entry keeps the alias, nothing is removed, and `copilot --version` starts the wrapper again. The kernel log from that incident shows 665 `copilot`/`sh` processes before the global OOM.

The real CLI is installed by mise (`npm:@github/copilot`), so it is found later in `PATH` once the wrapper entry is gone.

`home/core/.shell/common/environment.sh` is sourced by both interactive loaders (Bash `init.bash`, zsh `init.zsh`) and by `git-credential-env`. It runs after VS Code has set the terminal's environment.

## Goals / Non-Goals

**Goals:**
- Stop the recursion on every host with an aliased home, without per-host configuration.
- Never require running `copilot` (wrapper or real) to verify the fix.

**Non-Goals:**
- Rewriting other `PATH` entries, or changing `$HOME`.
- Patching or replacing files inside VS Code's global storage (VS Code overwrites them on update).
- Containing processes that VS Code starts without a shell (no such launch path was observed).

## Decisions

**Canonicalise only the wrapper entry, in `environment.sh`.** Each `PATH` entry ending in `/github.copilot-chat/copilotCli` that is a directory is replaced by `cd -P -- "$dir" && pwd`. That is POSIX, works in Bash and zsh, and runs no external program. The loop splits on `:`, keeps empty entries and order, and is idempotent. With the entry canonical, the shim's literal filter removes it, so `copilot --version` finds the mise-installed CLI. `environment.sh` is the one module both shells and the credential helper share, and it runs after VS Code's injection.

Alternatives considered:
- *Canonicalise every `PATH` entry under `$HOME`*: would also cover future tools with the same flaw, but touches mise, `~/.local/bin` and others for no observed benefit. Rejected for a smaller blast radius.
- *Alias or function `copilot` to the real binary*: covers only interactive use by name, not the shim's own `copilot --version` lookup, and needs a per-host path. Rejected.
- *Fix each host by hand (alias, or set the canonical home in `/etc/passwd`)*: does not protect the next host with the same layout. Rejected as the main fix; the status note makes such hosts visible.

**Informational note in `machine status`.** The host row gets a note such as `· home is /mnt/data/home/u` when `Path(os.environ["HOME"])` differs from its `resolve()`. It is information, not an attention item: with the shell fix nothing needs manual action.

**Upstream report.** The agent drafts an issue for `microsoft/vscode-copilot-chat` (canonicalise both sides before filtering, plus a recursion guard such as an environment marker) and files it after the owner approves the text. The local fix stays even when upstream fixes the bug, because older extension versions remain installed on hosts.

## Risks / Trade-offs

- [VS Code changes the directory name or the shim logic] → The rewrite is a no-op for unknown names; the upstream issue asks for a fix at the source.
- [A terminal not started through the dotfiles shells (e.g. `sh`, or a profile with `--norc`)] → Not protected; accepted, since the incident came from a normal interactive terminal.
- [VS Code re-applies its environment after shell start (terminal relaunch on extension env change)] → The relaunched shell runs `environment.sh` again, so the entry is canonicalised again.
- [Testing the fix by running `copilot` could reproduce the OOM] → Tests check `PATH` resolution only (`command -v`-style lookup with the shim's filter reproduced in the test), never execute the wrapper.

## Migration Plan

Deployed by a normal `machine update`; new terminals pick it up. Rollback: revert the commit. Until a host is updated, avoid typing `copilot` in VS Code terminals there, or call the mise-installed binary by its absolute path.
