## Decisions

- Bash prints the hint only when it stays in bash. When bash hands over to zsh (`exec zsh -l`), the handoff happens before the hint line, so only zsh prints it and there is no double hint. Observed in `dot_bashrc` order; the test verifies the stay-in-bash case.
- The hint text and marker file are shared by both shells; nothing new is added.

## Open Questions

- None.
