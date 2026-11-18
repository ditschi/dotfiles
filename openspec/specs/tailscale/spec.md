# tailscale Specification

## Purpose
Installs Tailscale on hosts with the feature `tailscale` from Tailscale's own apt repository and offers the login after setup, without replacing an install that came from elsewhere.

## Requirements

### Requirement: Feature installs Tailscale from the official repository
When `tailscale` is among the host's features and Tailscale is not installed, provisioning SHALL add Tailscale's stable apt repository for the host's distribution and release, signed by a key pinned in the repository, and install the package `tailscale`.

#### Scenario: Fresh private server
- **WHEN** Ansible runs on an Ubuntu 26.04 server with the feature `tailscale` and no Tailscale installed
- **THEN** the Tailscale apt source and pinned key are present and `tailscale` and `tailscaled` are installed

#### Scenario: Feature not selected
- **WHEN** Ansible runs on a host without the feature `tailscale`
- **THEN** no Tailscale source, key or package is added

### Requirement: Snap install is not replaced automatically
When Tailscale is installed as a snap, provisioning SHALL NOT install the package next to it and SHALL NOT remove the snap; it SHALL report that the snap is kept and point to the documented one-time move to the package.

#### Scenario: Host with the snap
- **WHEN** Ansible runs with the feature `tailscale` on a host where Tailscale is installed as a snap
- **THEN** no package is installed, the snap keeps running and the output names the manual move

#### Scenario: After the manual move
- **WHEN** the snap was removed by hand and Ansible runs again
- **THEN** the package is installed from the official repository

### Requirement: Unsupported release is a warning
When the repository serves no build for the host's distribution and release, provisioning SHALL install nothing for Tailscale and SHALL report why, without failing the run.

#### Scenario: Release not served
- **WHEN** Ansible runs with the feature `tailscale` on a release for which the repository has no packages
- **THEN** a warning names the distribution and release, nothing is installed and the run continues

### Requirement: Setup reports a missing Tailscale truthfully
When `machine setup` reaches the Tailscale login with the feature selected and no `tailscale` command, it SHALL say that Tailscale is not installed and how to log in once it is, and SHALL NOT claim that Ansible installs it.

#### Scenario: Ansible skipped
- **WHEN** `machine setup` runs with the feature `tailscale` and `--skip-ansible` on a host without Tailscale
- **THEN** setup says Tailscale is not installed and names `sudo tailscale up` for later
