# Dotfiles + machine setup

Ein Repo für Shell-Dotfiles und Maschinen-Bootstrap. Git ist die Quelle: Dateien unter `$HOME` sind Symlinks in dieses Repo. Änderungen auf jedem Host committen und pushen, andere Hosts `machine update`.

## Schnellstart (auf dem neuen Host, ohne Control Node)

```bash
git clone https://github.com/ditschi/dotfiles.git ~/dotfiles
cd ~/dotfiles
./bootstrap
```

Nicht-interaktiv:

```bash
./bootstrap --profile home-laptop --yes
./bootstrap --profile work-laptop --yes
./bootstrap --profile rpi-zero --yes --no-become
```

Vom Laptop auf ein erreichbares Gerät:

```bash
./bootstrap --limit rpi-zero-1 --profile rpi-zero
```

## Alltag

| Aktion | Befehl |
| --- | --- |
| Alias ändern, für alle Hosts | Datei in `$HOME` editieren (trifft Git), `machine commit -m "..." && machine push` |
| Andere Hosts nachziehen | `machine update` (zieht Host-Profil, apply bei Drift) |
| Pakete/System | `machine update --system` oder `machine apply` |
| Host-Profil remote anwenden | `machine apply --limit homeserver` |
| Volles Setup / Features ändern | `machine setup` (gespeicherte Antworten als Default) |
| Host-Profil ins Repo | `machine profile save` |
| Layout von `main` → chezmoi | `machine migrate` |
| Migration rückgängig | `machine rollback` |
| Status / Drift | `machine status` / `machine profile show` |
| Inventar (Vault) | `machine inventory edit ansible/inventory/hosts.yml` |
| `~/.env` aus Bitwarden | `machine env pull` |
| SSH-Pubkey nach Bitwarden | `machine ssh publish` |
| Collections installieren | `ansible-galaxy collection install -r ansible/requirements.yml` |

Uncommittete lokale Änderungen blockieren `machine update` (außer `--force`).

`~/.zshrc-local` ist nur für echte Einzel-Host-Ausnahmen und nicht im Git.

## Struktur

```
bootstrap                 # ruft machine setup
home/                     # chezmoi-Source, mode=symlink
machine/
  hosts/                  # versionierte Host-Antworten (<hostname>.yml)
  ssh_keys/               # öffentliche Host-Keys für ssh_allow_from
ansible/
  workstation.yml         # Pakete + user_tools + monitoring + sshd + stylus
  homelab.yml             # Stub — Stacks leben im Homelab-Repo
  requirements.yml        # ansible.posix (+ Galaxy-Hinweise)
  inventory/local.yml     # immer localhost
  inventory/hosts.example.yml
  profiles/               # Feature-Defaults pro Profil
  roles/
    monitoring/           # Telegraf-Agent-Configs
    sshd_home/            # Port 5115 + authorized_keys
    stylus_touch_guard/   # Yoga Stylus/Touch (ex helpers-and-automation)
    user_tools/           # starship, fonts
docs/                     # Deprecation-Hinweise u.ä.
tests/                    # unit + Docker/CI
```

Profil-Cache: `~/.config/machine/profile.yml` (nicht im Git).  
**Source of Truth pro Host:** [`machine/hosts/<hostname>.yml`](machine/hosts/) — Features und `ssh_allow_from`. Chezmoi-Config: `~/.config/chezmoi/chezmoi.yaml`.

### Host-Profile versionieren und pushen

```bash
# Auf dem Host einmalig (oder nach Feature-Änderung):
machine setup                 # interaktiv
machine profile save          # → machine/hosts/$(hostname -s).yml
machine commit -m "host profile" && machine push

# Laptop: Server darf jetzt von diesem Laptop SSH
# edit machine/hosts/homeserver.yml → ssh_allow_from: [dieser-hostname]
machine commit -m "allow laptop on homeserver" && machine push

# Auf dem Server:
machine update                # pull → sync profile → apply bei Drift

# Oder vom Laptop ohne Login auf dem Server:
machine apply --limit homeserver
```

`machine apply` lokal: bei Ansible-/Health-Fail wird die vorherige `profile.yml` wiederhergestellt und Ansible erneut mit dem alten Stand gefahren. Remote (`--limit`): kein Auto-Revert — Profil im Git korrigieren und erneut apply.

## Secrets / Bitwarden

Die **CLI** (`bw`) wird beim Setup auf echten Hosts nach `~/.local/bin` installiert (nicht das Snap der GUI). Interaktiv fragt der Wizard nur: „Willst du dich jetzt einloggen?“ Ohne Login bleiben `~/.env` und Key-Uploads aus.

### Inventar

- Echte Hosts/IPs nach `ansible/inventory/hosts.yml` kopieren und mit Ansible Vault verschlüsseln.
- Vault-Passwort in Bitwarden, Item-Name `ansible-vault` (überschreibbar: `MACHINE_VAULT_BW_ITEM`).
- Rollen und Paketlisten bleiben Klartext.

```bash
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
machine inventory encrypt ansible/inventory/hosts.yml
```

### `~/.env` aus Bitwarden

Passwort in Bitwarden ändern, dann auf dem Host `machine env pull` oder `machine update`. Es gibt kein Push von Bitwarden auf die Geräte — der Host holt den Stand beim Apply (`bw sync`). Ohne entsperrtes `bw` bleibt die letzte `~/.env` liegen.

`~/.env` ist **nicht** im Git und kein Symlink. Overlay für echte Snowflakes: `~/.env.local` (wird nicht überschrieben). Vor dem ersten Überschreiben liegt ein Backup unter `~/.local/share/machine/env-backup/`.

Item-Namen (Secure Note oder Login mit Notiz + Custom Fields). Spätere Items und Custom Fields gewinnen bei gleichen Keys:

| Schicht | Item-Name | Beispiel |
| --- | --- | --- |
| Klasse shared | `env/<class>-shared` | `env/work-shared`, `env/home-shared`, `env/iot-shared` |
| Profil | `env/profiles/<profile>` | `env/profiles/work-laptop` |
| Dieser Host | `env/hosts/<hostname>` | `env/hosts/ditschi-ThinkPad-L13-Yoga-Gen-2` |
| Infra | `ansible-vault` | Vault-Passwort |

**Ordner in Bitwarden** (persönlicher Vault) oder Collections (Organisation), gleiche Namen:

- `work` — nur Work-Laptops (`env/work-shared`, `env/profiles/work-laptop`, SSH/VPN)
- `home` — private Rechner und gemeinsame Home-Secrets
- `iot` — Pis / Zero (`env/iot-shared`, `env/hosts/rpi-zero-1`)
- `infra` — `ansible-vault`, Host-Passwort-Hashes, nicht für Shell-`.env`

Inhalt eines `env/…`-Items:

- **Notes:** bestehendes `.env` als Text (`KEY=value`, eine Zeile pro Variable)
- **Custom fields** (Hidden): oft geänderte Passwörter, z. B. `VPN_PASSWORD` — überschreiben denselben Key aus den Notes

Work-Secrets nicht in `env/home-*` legen. Home-Hosts fragen `env/work-*` nicht ab.

```bash
machine env status    # welche Items existieren
machine env pull      # ~/.env schreiben
```

### SSH-Keys (Home / Work getrennt)

Pro Host optional `~/.ssh/id_ed25519_<hostname>`. Public Key als Textfeld `public_key` in Bitwarden:

- Home: `ssh/home/hosts/<hostname>`
- Work: `ssh/work/hosts/<hostname>`

In `profile.yml` steuert `ssh_allow_from:` welche Hostnamen (gleiche Klasse) auf **diesen** Rechner sshen dürfen. Ansible/Setup holt nur Public Keys derselben Klasse. Privatschlüssel nur nach expliziter Nachfrage.

```bash
machine ssh publish           # Public Key hochladen
machine ssh publish --private # inkl. Privatschlüssel
machine ssh restore           # Privatschlüssel zurückholen
```

## Profile / Features

`work-laptop`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`

Features (Auswahl im Bootstrap, Antworten in `profile.yml`): `zsh-full`, `fonts`, `starship`, `desktop`, `gnome`, `cosmic`, `docker`, `kerberos`, `work-cli`, `monitoring`, `unattended-upgrades`, `syncthing`, `tailscale`, `ssh-host-key`, `stylus-touch-guard`, `sshd-home`

Home-Profile bekommen `monitoring` (Telegraf) defaultmäßig. Config-Namen stehen **nur** in `ansible/group_vars/all.yml` → `monitoring_by_profile` und werden in `tasks/resolve_monitoring.yml` aufgelöst (nicht in der CLI). Bevorzugt Remote-Configs über `INFLUX_TELEGRAF_CONFIG_BASE` / `INFLUX_URL` aus Bitwarden; sonst Dateien unter `ansible/roles/monitoring/files/`.

Yoga/Convertible (L13): Feature `stylus-touch-guard` → Rolle `stylus_touch_guard`. Früher: [helpers-and-automation](https://github.com/ditschi/helpers-and-automation) (**archived / deprecated**).

SSH Home-Fleet: Feature `sshd-home` → Port **5115** (`roles/sshd_home`) + `authorized_keys` aus [`machine/ssh_keys/`](machine/ssh_keys/) für Einträge in `ssh_allow_from`.

### Galaxy vs. lokale Rollen

| Bedarf | Entscheidung |
| --- | --- |
| Telegraf | **Lokal** `roles/monitoring` (Influx-Env + `machine/*` Fragmente). Galaxy `dj-wasabi.telegraf` / `boutetnico.telegraf` möglich, aber schwerer und weniger passend. |
| Docker | **apt** `docker.io` / `compose-v2`. Später optional `geerlingguy.docker` oder Collection `community.docker`. |
| SSH keys/port | **Lokal** `sshd_home` + Collection `ansible.posix` (`authorized_key`). |
| Stylus | **Lokal** (ex helpers-and-automation). |

Collections: `ansible-galaxy collection install -r ansible/requirements.yml`.

### Architektur (kurz)

| Schicht | Zuständig |
| --- | --- |
| `machine/hosts/*.yml` | Gewünschter Zustand (profile, features) |
| `machine` CLI | Orchestrator, UX, Secrets, Git, chezmoi-Aufruf |
| chezmoi | Dotfiles |
| Ansible | apt, `/etc`, Telegraf, user_tools, stylus-touch-guard, sshd-home |
| Inventory | Nur Erreichbarkeit — keine Features |

Work-Module (`01_work.zsh`) werden nur bei Profil `work-laptop` verlinkt.

## Migration (von altem Root-Layout)

Auf einem Host, der noch `main` mit Symlinks nach `~/dotfiles/.zshrc` hat:

```bash
cd ~/dotfiles
git fetch && git checkout feat/machine-setup   # oder main, sobald gemerged
./bootstrap          # oder: machine migrate
```

`machine update` erkennt kaputte/alte Root-Symlinks und fragt interaktiv, ob ein volles Setup laufen soll. Nicht-interaktiv bricht es mit dem Hinweis `machine migrate --yes` ab.

Sicherung unter `~/.local/share/machine/migration/<stamp>/`. Rollback:

```bash
machine rollback
# oder: ~/.local/share/machine/rollback.sh
```

Hosts, die **schon** auf dem chezmoi-Layout laufen, brauchen keine zweite Migration — nur `machine update` bzw. bei Feature-Änderungen `machine setup`.

## Revert

```bash
~/.local/share/machine/rollback.sh
# oder manuell:
cd ~/dotfiles
git checkout <alter-sha>          # steht in rollback.sh / migration meta.json
python3 install.py --update --force
```

Das `install.py` **dieses** Commits legt die Root-Symlinks wieder an. Danach läuft der alte Update-Pfad.

## Alte Befehle

`python3 install.py` bleibt ein Wrapper auf `machine setup` / `machine update`.

## Tests

### Automatisch

```bash
./tests/run.sh                  # unit + Docker-Smoke (ohne volles APT)
pytest tests/unit -q            # Logik inkl. apply-revert, Host-YAML-Schema
pytest tests/integration -m "docker and not apt and not apt_gnome"
pytest tests/integration -m apt # rpi-zero APT + machine/hosts/ci-rpi-zero.yml
pytest tests/integration -m apt_gnome  # home-laptop APT + ci-home-laptop.yml (~10+ min)
ansible-lint ansible/*.yml      # lokal / CI bei Änderungen unter ansible/ oder machine/hosts/
ansible-galaxy collection install -r ansible/requirements.yml
```

CI (`.github/workflows/verify.yml`):

- Unit + Ansible-Syntax (amd64 + arm)
- Docker-Matrix aller Profile (ohne APT)
- Clean-Install aus `machine/hosts/ci-container.yml`
- APT + Ansible aus `machine/hosts/ci-rpi-zero.yml` und `ci-home-laptop.yml`
- **ansible-lint + Host-YAML-Validierung** nur wenn `ansible/**` oder `machine/hosts/**` (o.ä.) geändert

**Bewusst nicht in CI:** echte Pi-Hardware, Kerberos gegen Work-KDC, Cosmic-Session, echtes `bw login`/2FA, echtes Influx.

### Manuell (Compose)

```bash
docker compose -f tests/compose.yaml run --rm shell
# im Container:
./bootstrap --profile home-laptop          # Fragen
./bootstrap --profile home-laptop --yes    # still
machine setup                              # vorherige Antworten vorausgewählt
machine update                             # nur nachziehen

docker compose -f tests/compose.yaml run --rm migrate
# präparierte alte Symlinks → Prompt „Setup wechseln?“ / machine migrate
```
