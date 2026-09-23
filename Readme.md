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
| Andere Hosts nachziehen | `machine update` |
| Pakete/System | `machine update --system` |
| Status / Drift | `machine status` |
| Inventar (Vault) | `machine inventory edit ansible/inventory/hosts.yml` |
| `~/.env` aus Bitwarden | `machine env pull` |

Uncommittete lokale Änderungen blockieren `machine update` (außer `--force`).

`~/.zshrc-local` ist nur für echte Einzel-Host-Ausnahmen und nicht im Git.

## Struktur

```
bootstrap                 # ruft machine setup
home/                     # chezmoi-Source, mode=symlink
ansible/
  workstation.yml         # Pakete + user tools, local oder SSH
  homelab.yml             # Server-Stacks (Stub zum Portieren)
  inventory/local.yml     # immer localhost
  inventory/hosts.example.yml
  profiles/               # Feature-Defaults pro Profil
```

Profil liegt in `~/.config/machine/profile.yml` (nicht im Git). Chezmoi-Config: `~/.config/chezmoi/chezmoi.yaml`.

## Secrets / Bitwarden

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


## Profile / Features

`work-laptop`, `home-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`

Features (Auswahl im Bootstrap): `zsh-full`, `fonts`, `starship`, `desktop`, `gnome`, `cosmic`, `docker`, `kerberos`, `monitoring`

Work-Module (`01_work.zsh`) werden nur bei Profil `work-laptop` verlinkt.

## Alte Befehle

`python3 install.py` bleibt ein Wrapper auf `machine setup` / `machine update`.

## Tests

Presets werden in zwei Schichten geprüft, lokal und in CI:

- **Unit (schnell, ohne Docker):** Paketlisten aus `ansible/profiles/*` gegen `group_vars`, CLI-Help/Completion, optional Abgleich mit `ansible-playbook ansible/dump_packages.yml` wenn Ansible installiert ist.
- **Docker-Matrix:** Container als `home-laptop`, `work-laptop`, `home-server`, `rpi`, `rpi-zero`, `container`. Chezmoi-Symlinks und Ignore-Regeln (Work-Zsh nur auf Work, kein p10k auf Zero). Ein zusätzlicher Job installiert die **rpi-zero**-APT-Pakete.

```bash
./tests/run.sh                  # unit + Docker-Smoke (ohne volles APT)
pytest tests/unit -q            # nur Logik
pytest tests/integration -m docker and not apt
pytest tests/integration -m apt # Pi-Zero-Pakete im Container
```

Molecule bleibt sinnvoll für später portierte Homelab-Rollen. Für den ganzen `machine`-Bootstrap (Chezmoi + Profile + CLI) ist **pytest + testinfra + Docker** der bessere Fit: eine Parametrisierung statt eines Molecule-Szenarios pro Profil, gleiche Tests lokal und in GitHub Actions.

Pi-Hardware wird nicht emuliert; `rpi-zero` prüft dasselbe Preset auf amd64-Debian/Ubuntu. Bitwarden wird in CI nicht aufgerufen (`bw` fehlt, `~/.env`-Sync wird übersprungen).
