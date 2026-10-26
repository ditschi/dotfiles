## MODIFIED Requirements

### Requirement: Core tools on every host
The `core` group SHALL install on every host, containers included: Git and Git LFS, the shell tools (fzf, zoxide, eza, fd, Starship, jq, delta, lazygit, tealdeer, tmux, zellij), gh, yazi, Node.js and uv. LLM command line tools and OpenSpec SHALL NOT be in `core`.

#### Scenario: Container
- **WHEN** a container is set up without any LLM feature
- **THEN** Starship, yazi and gh are installed and no LLM CLI or OpenSpec is installed

#### Scenario: lazygit available
- **WHEN** any host is set up
- **THEN** `lazygit` is on the PATH; `machine` does not start it by itself
