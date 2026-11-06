# User tools

User-space tools from mise, Node and the LLM CLIs.

## mise tools

User-space tools for every host (`fzf`, `zoxide`, `eza`, `fd`, `starship`, `jq`, `delta`, `lazygit` (started by hand only), `tmux`, `zellij`, `gh`,
`yazi`, Node, `uv`) come from mise fragments in `home/core/.config/mise/conf.d/`; the LLM CLIs,
OpenSpec and the fonts come from the feature groups (`home/<group>/.config/mise/conf.d/`). Versions are pinned in `home/core/.config/mise/mise.lock`
and `locks/` next to it; regenerate them with
`mise lock --global --platform linux-x64,linux-arm64` after a fragment change.
A `pipx:` tool names one Python minor (`{ version = "latest", python = "3.14" }`), so
its uv lock pins dependencies only for that Python; mise installs its own CPython for
it, and `python3` on `PATH` stays the system one.
A tool declared in two fragments, or in a fragment and an Ansible package list,
or a `pipx:` tool without a Python minor,
fails `python3 -m machine_cli.mise_check` (pre-commit and CI).

## Node and LLM tools

Node LTS (with npm) comes from mise (`20-tools.toml`), user-local and without sudo.
NVM and pyenv are no longer loaded by the shell configuration.

The LLM CLIs are features with their own dotfile groups: `claude-code` (group `claude`),
`copilot-cli` (group `copilot`) and `opencode` (group `opencode`). Each also selects the
group `openspec`, so OpenSpec comes with any of them. Private hosts preselect Claude Code,
work hosts Claude Code and Copilot; opencode and containers are opt-in. mise installs
them without sudo; authentication remains a manual step.

On hosts where `$HOME` is a symlink or bind mount (for example `/home/u` → `/mnt/data/home/u`), VS Code's Copilot CLI wrapper in `…/github.copilot-chat/copilotCli` fails to drop itself from `PATH` and starts itself recursively until memory runs out. `~/.shell/common/environment.sh` therefore rewrites that `PATH` entry to its canonical path, so `copilot` reaches the mise-installed CLI. `machine status` notes such a home in the host row (`home is …`).

## Open the work directory in an editor (`/editor`)

The feature `editor-command` (preselected on desktops, optional on servers) adds the
command `/editor` to Claude Code, Copilot CLI, VS Code Copilot Chat and opencode, and
the script `open-in-editor` behind it. It opens the root of the Git worktree the agent
works in (or the current directory outside Git) in your editor and returns at once.

- `/editor` opens the work root.
- `/editor <hint>`, for example `/editor editor.md`, also opens the file you most
  probably mean; the agent asks with numbered options when several fit.
- `/editor change [name]` opens proposal, design, tasks and delta specs of the
  OpenSpec change named like the branch (or the only active change, or `name`).

The editor is the Git key `editor.open`, default `code`. Set it per repository (kept in
`.git/config`, also used by its worktrees) or as a host default:

```bash
git config editor.open cursor
git config --file ~/.gitconfig.local editor.open "code --new-window"
```

`open-in-editor` works without an agent too: `open-in-editor [--change [NAME]] [FILE...]`.
It provides no shell completion; file names complete as usual. VS Code Copilot Chat
reads the skill from both `~/.claude/skills` and `~/.copilot/skills`, where it is the
same file.
