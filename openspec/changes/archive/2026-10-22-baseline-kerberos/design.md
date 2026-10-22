# Design

## Context

This change writes the confirmed Kerberos behaviour down as baseline specs and changes no code. See proposal.md for the motivation. Current code: `home/dot_local/bin/executable_{ensure-kerberos-token,kinit-pw,get-password,setup-ensure-kerberos-cron}`, the work shell start in `home/dot_zsh/config/01_work.zsh`, and the `kerberos` feature (packages `krb5-user` and `ldap-utils`, on by default for `work-machine`).

## Goals / Non-Goals

**Goals:**
- Record only confirmed behaviour as requirements.
- Keep unclear points visible as investigations.

**Non-Goals:**
- Fixes or improvements.

## Decisions

1. **Cron for the refresher.** It was the simplest choice. A systemd user timer is only worth it for a practical benefit.
2. **Keyring first, environment fallback.** Keyring access is not reliable in every context.
3. **`kinit-pw` is a script.** Aliases are not available in bash scripts or cron.

## Investigations (not decided, not in the specs)

Each is a candidate for a later change. The owner decides whether it is worth pursuing.

1. **Feature name and content.** The `kerberos` feature installs `krb5-user` and `ldap-utils`. LDAP has nothing to do with Kerberos but is needed for the work LDAP logic. Suggestion: rename the feature to something like `work-tools`, or split it into `kerberos` and `ldap`, and keep the old name working for one release. Why: a feature name should say what it installs.
2. **Aliases that use the helpers.** The owner is unsure that `vpn-pw` and `update-system` use them. Suggestion: search the aliases and scripts for calls to `get-password` and `kinit-pw` and list them. Why: any caller must be covered by the password flow.
3. **Refresher managed by Ansible.** Today cron setup is a manual command with a shell hint. Suggestion: have the work-machine feature install the cron job. Why: one place for provisioning, no hint needed.
4. **Password fallback across contexts.** Suggestion: list what each caller needs from the password source in shells, cron and containers, then define the fallback order (keyring, Bitwarden, `$PASSWORD`). Why: the keyring is not reliable everywhere, and the 0005 investigation already wants Bitwarden here.
5. **LDAP region selection.** Suggestion: find how the LDAP helper picks a region now, and compare supported query or discovery mechanisms. Why: choosing the wrong region gives wrong results.
