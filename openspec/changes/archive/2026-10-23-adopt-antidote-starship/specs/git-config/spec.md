## MODIFIED Requirements

### Requirement: Shared Git config
`~/.gitconfig` SHALL be a symlink into the repository and identical on all hosts. It SHALL hold the shared defaults (`push.default=current`, `pull.rebase`, `fetch.prune`, rerere, `init.defaultBranch=main`, meld, delta as diff pager and LFS) and the aliases, so that `git config --global alias...` changes the shared file.

#### Scenario: Adding a global alias
- **WHEN** a user runs `git config --global alias.x ...`
- **THEN** the change lands in the repository file and syncs to other hosts with the dotfiles

#### Scenario: delta installed
- **WHEN** a user runs `git diff` or `git show` and delta is installed
- **THEN** the output is shown through delta

#### Scenario: delta not installed
- **WHEN** a user runs `git diff` on a host without delta
- **THEN** the output is shown through `less` (or printed plainly without `less`) and no error appears
