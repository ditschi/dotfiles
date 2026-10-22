# Design

## Context

This change writes the confirmed provisioning behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `ansible/workstation.yml`, `ansible/group_vars/all.yml`, `ansible/profiles/`, `ansible/roles/` and `ansible/requirements.yml`.

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep alternatives and open decisions visible as investigations.

**Non-Goals:**
- Fixes or improvements.
- Replacing Ansible.

## Decisions

1. **Ansible for system provisioning.** Chosen after a comparison and because its playbooks are readable.
2. **One package table, thin local roles.** Galaxy roles were judged heavier and a worse fit.
3. **Existing installations are preserved.** Provisioning avoids replacing what a user already set up.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Provisioner comparison.** The owner is new to Ansible, so a clearly better and approachable alternative is worth evaluating. Suggestion: compare Ansible, plain scripts, Nix with home-manager and similar tools on readability, idempotence, setup and update needs for this repository. Why: the choice should hold up against alternatives.
2. **Privileged route for managed work machines.** Without root the system roles are skipped. Suggestion: list the tasks that need root and compare skipping them with an approved privileged route. Why: work machines should get tools without blocking the rest.
3. **Node per profile.** `node_tools` runs everywhere today. Suggestion: list which profiles use Node-based tools and what needs NVM or Node on each. Why: containers and small hosts may not need it.
4. **OpenSpec as an explicit feature.** Today it follows the LLM CLIs. The owner may prefer a separately selectable feature, so the dependency is visible. Suggestion: compare an explicit feature, a profile default and the conditional install by dependency and maintenance cost. Why: convenient availability without hiding the relationship.
5. **Purpose of `etckeeper`.** It is enabled on every non-container profile and the reason is unknown. Suggestion: check history and operations for why, and whether it should stay on every profile. Why: it tracks `/etc` in Git on all hosts, which has a cost.
6. **Remote updates.** Suggestion: compare how the current inventory and Ansible setup could update remote hosts and how that relates to `machine update`. Why: the home server should not need a manual login.
7. **Test policy.** Which checks are required before a commit is the same question as in the code-quality baseline; it is handled there.
