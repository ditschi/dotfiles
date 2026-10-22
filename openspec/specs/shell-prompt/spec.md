# shell-prompt Specification

## Purpose
Defines which prompt each interactive shell shows, so that zsh keeps its familiar Powerlevel10k look and bash gets a prompt when one is available.

## Requirements

### Requirement: Powerlevel10k prompt in zsh
Interactive zsh SHALL use the Powerlevel10k prompt configured by the user's `~/.p10k.zsh`, and the prompt MAY show a marker when running inside Docker.

#### Scenario: Prompt configuration present
- **WHEN** `~/.p10k.zsh` exists
- **THEN** it is loaded and the Powerlevel10k prompt is shown

#### Scenario: Prompt configuration absent
- **WHEN** `~/.p10k.zsh` does not exist
- **THEN** zsh starts without error

### Requirement: Starship prompt in bash
Interactive bash SHALL use the Starship prompt when Starship is installed.

#### Scenario: Starship installed
- **WHEN** an interactive bash starts and Starship is installed
- **THEN** the Starship prompt is shown

#### Scenario: Starship not installed
- **WHEN** an interactive bash starts and Starship is not installed
- **THEN** bash keeps its default prompt
