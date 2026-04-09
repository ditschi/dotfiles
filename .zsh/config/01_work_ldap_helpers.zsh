alias zshwork-ldap="nano $0"

if [[ "${WORK_SETUP}" != "true" ]]; then # set in 00_LOADER.zsh
    return
fi

# functions
# ---------------------------------------------------------------------------
# ldapsearch-bosch: base LDAP helper — working server + current user creds
# Usage: ldapsearch-bosch [ldapsearch options...]
# ---------------------------------------------------------------------------
ldapsearch-bosch() {
    # Derive bind DN domain prefix from active Kerberos principal (e.g. dci2lr@DE.BOSCH.COM -> de)
    # so this works for users from any region. Falls back to $LDAP_DOMAIN or 'de'.
    local kprincipal bind_dn
    kprincipal=$(klist 2>/dev/null | awk '/^\s*Principal:/ { print $2; exit }')
    if [[ -n "$kprincipal" ]]; then
        local kuser="${kprincipal%%@*}"
        local kdom="${${kprincipal##*@}%%.*}"
        bind_dn="${kdom:l}\\${kuser}"
    else
        bind_dn="${LDAP_DOMAIN:-de}\\$(whoami)"
    fi
    ldapsearch -H ldaps://rb-gc-lb.bosch.com:3269 \
        -D "$bind_dn" \
        -x \
        -w "$PASSWORD" \
        "$@"
}

ldap-user-info-full() {
    local nt_user="${1:-$(whoami)}"
    # Wildcard searches are slow on full domain; scope to regional OU.
    # Override LDAP_USER_BASE to search across regions.
    local base="${LDAP_USER_BASE:-OU=LR,DC=de,DC=bosch,DC=com}"
    ldapsearch-bosch \
        -b "$base" \
        "(|(displayName=*${nt_user}*)(samAccountname=*${nt_user}*))"
}

ldap-user-info() {
    local nt_user="${1:-$(whoami)}"
    local base="${LDAP_USER_BASE:-OU=LR,DC=de,DC=bosch,DC=com}"
    ldapsearch-bosch \
        -b "$base" \
        -z 1 \
        "(|(displayName=*${nt_user}*)(samAccountname=*${nt_user}*))" \
        cn givenName sn displayName uid mail c co l physicalDeliveryOfficeName department company
}

ldap-user-groups() {
    local group_by=false
    local username=""
    for arg in "$@"; do
        case "$arg" in
            -g|--group) group_by=true ;;
            *) username="$arg" ;;
        esac
    done
    username="${username:-$(whoami)}"

    local raw
    raw=$(ldapsearch-bosch \
        -b "DC=de,DC=bosch,DC=com" \
        "(samAccountname=${username})" \
        memberOf)

    if $group_by; then
        # LDIF wraps long lines with a leading space; join continuations before parsing.
        # Group by the 2nd OU component (1st is usually "Securitygroups"); fall back to 1st.
        printf '%s\n' "$raw" | awk '
            /^ /        { cur = cur substr($0, 2); next }
            /^memberOf/ { if (cur != "") record(cur); cur = $0; next }
                        { if (cur != "") { record(cur); cur = "" } }
            END         { if (cur != "") record(cur) }
            function record(s,    parts, n, i, cn, ou, ou1, nk) {
                sub(/^memberOf: /, "", s)
                n = split(s, parts, /,/)
                cn = ""; ou = "(other)"; ou1 = ""; nk = 0
                for (i = 1; i <= n; i++) {
                    gsub(/^ +| +$/, "", parts[i])
                    if (parts[i] ~ /^CN=/) cn = substr(parts[i], 4)
                    else if (parts[i] ~ /^OU=/) {
                        nk++
                        if (nk == 1) ou1 = substr(parts[i], 4)
                        if (nk == 2) ou  = substr(parts[i], 4)
                    }
                }
                if (nk == 1) ou = ou1
                if (cn != "") print ou "\t" cn
            }
        ' | sort | awk -F'\t' '
            BEGIN { prev = "" }
            {
                if ($1 != prev) {
                    if (prev != "") print ""
                    print "[" $1 "]"
                    prev = $1
                }
                print "  " $2
            }
        '
    else
        printf '%s\n' "$raw" | awk '
            /^ /        { cur = cur substr($0, 2); next }
            /^memberOf/ { if (cur != "") record(cur); cur = $0; next }
                        { if (cur != "") { record(cur); cur = "" } }
            END         { if (cur != "") record(cur) }
            function record(s) {
                sub(/^memberOf: /, "", s)
                split(s, p, /,/)
                gsub(/^ +| +$/, "", p[1])
                if (p[1] ~ /^CN=/) print substr(p[1], 4)
            }
        ' | sort
    fi
}

# ---------------------------------------------------------------------------
# _ldap-resolve-group-dn: resolve a group CN to its full DN (internal helper)
# ---------------------------------------------------------------------------
_ldap-resolve-group-dn() {
    ldapsearch-bosch \
        -b "DC=bosch,DC=com" \
        "(cn=$1)" \
        dn | awk '
            /^ /    { cur = cur substr($0, 2); next }
            /^dn: / { if (cur != "") { print substr(cur, 5); found=1; exit } cur = $0; next }
                    { if (cur != "") { print substr(cur, 5); found=1; exit } cur = "" }
            END     { if (!found && cur ~ /^dn: /) print substr(cur, 5) }
        '
}

# ---------------------------------------------------------------------------
# _ldap-group-member-dns: read member attribute from a group DN (internal helper)
# Returns all direct member DNs one per line (LDIF continuations joined).
# ---------------------------------------------------------------------------
_ldap-group-member-dns() {
    local group_dn="$1"
    ldapsearch-bosch \
        -b "$group_dn" \
        -s base \
        "(objectClass=*)" \
        member | awk '
            /^member: / { if (cur != "") { sub(/^member: /, "", cur); print cur }
                          cur = $0; next }
            /^ /        { if (cur ~ /^member: /) cur = cur substr($0, 2); next }
                        { if (cur != "") { sub(/^member: /, "", cur); print cur }
                          cur = "" }
            END         { if (cur ~ /^member: /) { sub(/^member: /, "", cur); print cur } }
        '
}

# ---------------------------------------------------------------------------
# ldap-group-overview: table of direct user members + list of included subgroups
# Usage: ldap-group-overview <group-name>
# ---------------------------------------------------------------------------
ldap-group-overview() {
    local group="$1"
    if [[ -z "$group" ]]; then
        echo "Usage: ldap-group-overview <group-name>"
        return 1
    fi
    local group_dn
    group_dn=$(_ldap-resolve-group-dn "$group")
    if [[ -z "$group_dn" ]]; then
        echo "Group '${group}' not found."
        return 1
    fi

    local all_members
    all_members=$(_ldap-group-member-dns "$group_dn")

    local -a user_ids subgroup_names
    user_ids=($(printf '%s\n' "$all_members" | grep -iv ',OU=Securitygroups,' \
        | grep -i '^CN=' \
        | awk -F'[=,]' '{ print tolower($2) }' | sort))
    subgroup_names=($(printf '%s\n' "$all_members" | grep -i ',OU=Securitygroups,' \
        | grep -i '^CN=' \
        | awk -F'[=,]' '{ print $2 }' | sort))

    printf "\nDirect members of group: %s (%d)\n\n" "$group" "${#user_ids[@]}"
    printf "%-15s %-40s %s\n" "NT-ID" "Display Name" "Email"
    printf "%-15s %-40s %s\n" "---------------" "----------------------------------------" "--------------------"

    if [[ ${#user_ids[@]} -gt 0 ]]; then
        local filter="(|$(printf '(sAMAccountName=%s)' "${user_ids[@]}"))"
        ldapsearch-bosch \
            -b "DC=bosch,DC=com" \
            "$filter" \
            sAMAccountName displayName mail | awk '
            /^sAMAccountName: / { sam = substr($0, 17); next }
            /^displayName: /    { dn  = substr($0, 14); next }
            /^mail: /           { mail = substr($0, 7); next }
            /^$/ {
                if (sam != "") {
                    printf "%-15s %-40s %s\n", tolower(sam), dn, mail
                    sam = ""; dn = ""; mail = ""
                }
            }
            END { if (sam != "") printf "%-15s %-40s %s\n", tolower(sam), dn, mail }
        ' | sort
    fi

    printf "\nIncluded subgroups (%d):\n" "${#subgroup_names[@]}"
    if [[ ${#subgroup_names[@]} -gt 0 ]]; then
        printf '  - %s\n' "${subgroup_names[@]}"
    else
        echo "  (none)"
    fi
    printf "\n"
}

# ---------------------------------------------------------------------------
# ldap-group-users: list NT IDs of direct user members (no subgroups)
# Usage: ldap-group-users <group-name>
# ---------------------------------------------------------------------------
ldap-group-users() {
    local group="$1"
    if [[ -z "$group" ]]; then
        echo "Usage: ldap-group-users <group-name>"
        return 1
    fi
    local group_dn
    group_dn=$(_ldap-resolve-group-dn "$group")
    if [[ -z "$group_dn" ]]; then
        echo "Group '${group}' not found."
        return 1
    fi
    _ldap-group-member-dns "$group_dn" \
        | grep -iv ',OU=Securitygroups,' \
        | grep -i '^CN=' \
        | awk -F'[=,]' '{ print tolower($2) }' \
        | sort
}

# ---------------------------------------------------------------------------
# ldap-group-emails: list email addresses of direct user members
# Usage: ldap-group-emails <group-name>
# ---------------------------------------------------------------------------
ldap-group-emails() {
    local group="$1"
    if [[ -z "$group" ]]; then
        echo "Usage: ldap-group-emails <group-name>"
        return 1
    fi
    local group_dn
    group_dn=$(_ldap-resolve-group-dn "$group")
    if [[ -z "$group_dn" ]]; then
        echo "Group '${group}' not found."
        return 1
    fi
    local user_ids
    user_ids=($(_ldap-group-member-dns "$group_dn" \
        | grep -iv ',OU=Securitygroups,' \
        | grep -i '^CN=' \
        | awk -F'[=,]' '{ print tolower($2) }'))
    if [[ ${#user_ids[@]} -eq 0 ]]; then
        return 0
    fi
    local filter="(|$(printf '(sAMAccountName=%s)' "${user_ids[@]}"))"
    ldapsearch-bosch \
        -b "DC=bosch,DC=com" \
        "$filter" \
        mail | awk '/^mail: / { print substr($0, 7) }' | sort
}

# ---------------------------------------------------------------------------
# ldap-group-subgroups: list direct subgroup names of a group
# Usage: ldap-group-subgroups <group-name>
# ---------------------------------------------------------------------------
ldap-group-subgroups() {
    local group="$1"
    if [[ -z "$group" ]]; then
        echo "Usage: ldap-group-subgroups <group-name>"
        return 1
    fi
    local group_dn
    group_dn=$(_ldap-resolve-group-dn "$group")
    if [[ -z "$group_dn" ]]; then
        echo "Group '${group}' not found."
        return 1
    fi
    _ldap-group-member-dns "$group_dn" \
        | grep -i ',OU=Securitygroups,' \
        | grep -i '^CN=' \
        | awk -F'[=,]' '{ print $2 }' \
        | sort
}
