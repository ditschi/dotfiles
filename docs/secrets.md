# Secrets / Bitwarden

The Bitwarden CLI, the vaulted inventory and the `~/.env*` files.

## Bitwarden CLI

Every host gets the **CLI** (`bw`, not the GUI snap) from mise as the `core` tool
`bitwarden`: the official Bitwarden release build for x86_64 and aarch64, with version and
checksums pinned in `mise.lock`. The version is fixed in the fragment (2026.10.1 fails
against the own Vaultwarden 2026.6.0); raise it only after checking it against the server. When `machine` needs `bw` before the dotfiles are linked,
it installs that pinned version from the repository's mise config. A `~/.local/bin/bw`
left by older setups is removed once mise provides `bw`.
Interactive `machine setup` offers Bitwarden configuration and login before
fetching secrets. For an unauthenticated CLI, it asks for the HTTPS server URL
(including self-hosted servers). Already authenticated accounts keep their server.
Passwords and two-factor codes are entered locally through the CLI.

After a successful unlock and sync, a separate, default-no prompt offers to save
`BW_SESSION`, `NODE_EXTRA_CA_CERTS`, and `NODE_USE_ENV_PROXY` in `~/.env.local`
with mode 600. Existing unrelated content is preserved, and repeated setup replaces
these exports rather than duplicating them. The helper first tries the existing
network settings. Only on a certificate trust error does it offer Ubuntu's system
CA bundle; only on a DNS/connection error with an HTTPS proxy configured does it
offer Node environment-proxy support. Neither workaround is added automatically,
and TLS verification stays enabled. Kerberos authenticates the proxy but does not
configure application proxy support or certificate trust.
Existing literal local exports are loaded without executing the file.

Saving the token grants local processes vault access while it remains valid;
it is never uploaded to Bitwarden or printed. Unlock again after expiry.
Declining storage keeps the session only for the setup process.
`--yes` / non-interactive setup never prompts or persists unlock tokens.
Without an unlocked vault, environment fetching and key uploads are skipped.

A `BW_SESSION` in the environment or in `~/.env.local` means Bitwarden is set up
and expected. When it has expired, an interactive run (terminal, no `--yes`)
unlocks, or logs in when logged out, at once without a yes/no question, and a
renewed session replaces the saved one. Without a terminal, and in the background
update (which then calls only `bw status`), an expired session shows
`⚠ bitwarden: log in (machine)` in the prompt and an item in `machine attention`
that offers to log in.

## Inventory

- Copy real hosts/IPs to `ansible/inventory/hosts.yml` and encrypt it with Ansible Vault.
- Vault password lives in Bitwarden, item name `ansible-vault` (override: `MACHINE_VAULT_BW_ITEM`).
- Roles and package lists stay plain text.

```bash
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
machine inventory encrypt ansible/inventory/hosts.yml
```

## `~/.env` from Bitwarden

Change the password in Bitwarden, then run `machine env pull` or `machine update` on the host. Bitwarden never pushes to devices — the host fetches the current state on apply (`bw sync`). Without an unlocked `bw`, the last `~/.env` stays in place.

The shell loads exactly these files, in order (later assignments win):

| File | Contents | Ownership |
| --- | --- | --- |
| `~/.env` | The context's Bitwarden group item | Generated |
| `~/.env.host` | This host's Bitwarden item | Generated |
| `~/.env.local` | Local overrides, certificate/proxy exports, `BW_SESSION` | Local; only appended to when you choose "keep locally" |

An env file that group or others may read or write is changed to mode `600`: by the next shell start (or `get-password`), which says so in one line, and by `machine env pull`, `machine setup` and `machine update`, also when Bitwarden is locked. If the mode cannot be changed, the shell warns with the `chmod 600` hint and still loads the file. The zsh health check run leaves the mode alone, so an open file does not make the check fail.

The arrows distinguish fetching from shell loading. The shell loads the three files in order; later assignments win.

```mermaid
graph LR
  linkStyle default stroke:#808080,stroke-width:2px;
  Group["Bitwarden group item<br/><i>env/groups/&lt;group&gt;</i>"]
  Host["Bitwarden host item<br/><i>env/hosts/&lt;hostname&gt;</i>"]
  Pull["machine env pull<br/><i>Unlocked vault; back up changed files</i>"]
  Shared["1. ~/.env<br/><i>Generated group values</i>"]
  Specific["2. ~/.env.host<br/><i>Generated host values</i>"]
  Local["3. ~/.env.local<br/><i>Local only; never overwritten by pull</i>"]
  Shell["Shell environment<br/><i>Last assignment wins</i>"]

  Group --> Pull
  Host --> Pull
  Pull -->|writes group values| Shared
  Pull -->|writes host values| Specific
  Shared -.->|then load| Specific
  Specific -.->|then load| Local
  Local -.-> Shell

  classDef source fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#fff;
  classDef control fill:#1E293B,stroke:#F59E0B,stroke-width:2px,color:#fff;
  classDef dotfiles fill:#1E293B,stroke:#3B82F6,stroke-width:2px,color:#fff;
  classDef mise fill:#1E293B,stroke:#10B981,stroke-width:2px,color:#fff;
  classDef system fill:#1E293B,stroke:#EF4444,stroke-width:2px,color:#fff;
  classDef secrets fill:#1E293B,stroke:#F472B6,stroke-width:2px,color:#fff;
  classDef context fill:#334155,stroke:#94A3B8,color:#fff;
  class Pull control;
  class Group,Host,Shared,Specific,Local secrets;
  class Shell context;
```

These files are **not** in git and are not symlinks. Before replacing changed
generated files, their previous contents are backed up with owner-only
permissions under `~/.local/share/machine/env-backup/`. Other `~/.env.*` files
are not loaded automatically.

Keep `BW_SESSION` local: it is needed to unlock the vault before fetching items,
and may expire. Pull refuses vault items containing a `BW_SESSION` assignment.
`~/.env.local` is never rewritten; it only gets lines appended when you choose
"keep locally" below.

A key in `~/.env` or `~/.env.host` that neither its Bitwarden item nor
`~/.env.local` sets is *local-only*. The pull never stops because of it and never
moves it without asking:

- In a terminal (`machine env pull`, `machine update`, `machine setup`, without
  `--yes`) it asks per key: add to the Bitwarden item of that file
  (`~/.env` → `env/groups/<group>`, `~/.env.host` → `env/hosts/<hostname>`;
  the line is appended to the item's notes under `# added from <host> on <date>`),
  keep locally (append to `~/.env.local`), remove, or skip. "Skip" is
  preselected. A key that its item no longer sets is shown with that item
  ("was in …; deleted there?").
- Skipped keys, and all keys without a terminal, stay set: they are written
  unchanged into a section `# --- local only: … ---` at the end of the generated
  file, and `machine attention` offers the same choices until they are resolved.
- A file with shell code (lines that are not `KEY=value`) is left unchanged; its
  choices are keep locally, remove or skip.

Warnings name the keys, the file, the item and the backup, never the values.

The group follows the context (`ENV_GROUPS` in `machine_cli/core.py`): `private` → `private`, `work` → `work`, a container without context → none.

Item names (secure note, or login with note + custom fields). Later items and custom fields win for identical keys:

| Layer | Item name | Example |
| --- | --- | --- |
| Group | `env/groups/<group>` | `env/groups/work`, `env/groups/private` |
| This host | `env/hosts/<hostname>` | `env/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2` |
| Infra | `ansible-vault` | vault password |
| Telegraf | `influxdb-telegraf-write` | Influx write token for Telegraf (not for shell `.env`) |

**Folders in Bitwarden** (personal vault) or collections (organization), same names:

- `work` — work laptops only (`env/groups/work`, SSH/VPN)
- `home` — private machines and shared home secrets
- `infra` — `ansible-vault`, host password hashes, not for shell `.env`

**Telegraf item** `influxdb-telegraf-write` (override: `MACHINE_INFLUX_BW_ITEM`): `machine setup`, `machine apply` and the apply step of `machine update` read it before Ansible on hosts with `monitoring` and hand the values only to Ansible (a private temp file, removed afterwards); they never reach `~/.env*`. Custom fields named like the variables win. For a login item, the password is used as `INFLUX_TOKEN` and the first URI as `INFLUX_URL` when those fields are missing.

| Field | Required | Meaning |
| --- | --- | --- |
| `INFLUX_URL` | yes (or login URI) | InfluxDB URL |
| `INFLUX_TOKEN` | for InfluxDB 2.x (or login password) | write token |
| `INFLUX_ORG` | for InfluxDB 2.x | organisation |
| `INFLUX_BUCKET` | no (default `telegraf`) | bucket |
| `INFLUX_TELEGRAF_CONFIG_BASE` | no | load the Telegraf configs from Influx instead of the local fragments |
| `INFLUXDB_USER`, `INFLUXDB_USER_PASSWORD`, `INFLUXDB_DB` | for InfluxDB 1.x | user, password, database (default `telegraf`) |

Missing item or locked vault: the run continues without credentials and keeps an existing Telegraf output.

Contents of an `env/…` item:

- **Notes:** existing `.env` as text (`KEY=value`, one line per variable)
- **Custom fields** (hidden): frequently changed passwords, e.g. `VPN_PASSWORD` — override the same key from the notes

Existing `.env` contents can be transferred manually into an approved work-vault
secure note named `env/groups/work`, or the host item for narrower scope.
Secrets should never be committed to dotfiles.
Vault folders are organizational labels, not enforced access boundaries; namespaced
item selection does not replace vault/organization permissions.

Don't put work secrets in `env/home-*`. Home hosts never query `env/work-*`.

```bash
machine env status    # which items exist
machine env pull      # write ~/.env and ~/.env.host; preserve ~/.env.local
machine env push      # write local edits of ~/.env back (--host: ~/.env.host)
```

### References to other items

A value in the notes or a custom field of an `env/…` item can name another
Bitwarden item instead of holding a copy, so a secret is kept once (for example
the work password in its login item):

| Reference | Value |
| --- | --- |
| `KEY={{bw:<item name>/password}}` | login password |
| `KEY={{bw:<item name>/username}}` | login username |
| `KEY={{bw:<item name>/field:<NAME>}}` | custom field `<NAME>` |

The item name must match exactly and exist once. `machine env pull` writes the
resolved value, after a comment `# KEY from Bitwarden "<item>" (<target>)`; the
shell, services and `get-password` never call `bw`. In a file with `export` lines
the value is shell-quoted, in a plain `KEY=value` file it is written literally,
as the loader reads it. When a reference cannot be resolved (item missing or not
unique, target empty, or a value with a line break or `${`, which the loader
would change), the pull keeps the value of the last pull, writes a
`# unresolved: …` comment and lists it in `machine attention`. The header of every
generated file repeats the syntax.

### Editing on the host: `machine env push`

Edit `~/.env` (or `~/.env.host`) and run `machine env push` (`--host`). The push
takes only the keys you added, changed or removed since the last pull, lists them
by name (references in clear, values never), checks every reference, and after a
confirmation writes the item and pulls again:

- a new or changed line goes into the item's notes (or its custom field);
- a reference line replaces the key's line, so changing a reference is one edit;
- a new value for a key that the item sets from a reference goes into the
  referenced item (for example a new work password into the login item), and the
  note keeps the reference;
- a removed key is removed only when you answer yes (default no);
- a key changed in Bitwarden since the last pull is a conflict only when both new
  values differ, and is overwritten only on yes (default no); a key changed only
  in Bitwarden is never written back.

The push needs a terminal and a previous pull, and refuses files with shell code.

### Unpushed local edits

The pull remembers what it last wrote (`~/.local/share/machine/env-generated/`,
mode 600). A key from an item that the file now changes or lacks is an unpushed
local edit; added keys stay local-only keys (see above). In a terminal the pull
asks once per file: push now, discard (regenerate after a backup) or skip
(default; the file stays). Without a terminal, for example in the background
update, the file stays unchanged and `machine attention` offers push or discard.
