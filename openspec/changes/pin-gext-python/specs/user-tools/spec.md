# Spec Delta

## ADDED Requirements

### Requirement: Python tools are locked for one Python minor
A tool that `mise` installs through the pipx backend SHALL name one Python minor in its fragment, so that its locked dependency graph covers only that Python and pins no dependency versions for other Python versions. The tool's interpreter SHALL NOT change which `python3` an interactive shell finds on `PATH`. A pipx tool without a Python minor SHALL fail a repository check.

#### Scenario: Lock of a pipx tool
- **WHEN** the lockfile is regenerated for a pipx tool that names Python 3.14
- **THEN** its locked dependency graph contains one resolution for Python 3.14 and no entries for older Python versions

#### Scenario: System Python stays on PATH
- **WHEN** a host has a pipx tool installed with its own Python
- **THEN** `python3` in an interactive shell is still the Python it was before the tool was installed

#### Scenario: pipx tool without a Python minor
- **WHEN** a group fragment declares a pipx tool without a Python minor
- **THEN** the repository check fails and names the tool and its fragment
