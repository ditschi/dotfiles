# Tests

Automated tests, CI, manual tests in Compose and tests against this home.

## Automated

```bash
uvx nox                         # compile + unit + Ansible lint + Docker smoke (without full APT), in uv venvs
uvx nox -l                      # list sessions; run one with `uvx nox -s tests -- -k handoff`
DOTFILES_TEST_INSECURE_TLS=1 uvx nox -s docker   # test containers skip TLS verification (hosts that intercept TLS)
# automatic on work machines; DOTFILES_TEST_INSECURE_TLS=0 forces verification there
pytest tests/unit -q            # logic incl. apply revert, host YAML schema (needs tests/requirements.txt)
pytest tests/integration -n auto -m "docker and not apt and not apt_gnome"   # -n: parallel (pytest-xdist)
pytest tests/integration -n auto -m apt # Pi Zero APT + tests/hosts/ci-rpi-zero.yml
pytest tests/integration -m apt_gnome  # private desktop APT + ci-home-laptop.yml (slow on a cold cache)
ansible-lint ansible/*.yml      # locally / in CI on changes under ansible/ or machine/hosts/
ansible-galaxy collection install -r ansible/requirements.yml
```

Locally the APT tests download through a caching apt proxy (`dotfiles-test-apt-cache`, apt-cacher-ng on the Docker network `dotfiles-test`), so later runs fetch almost nothing. It is started on first use and kept running; `docker rm -f dotfiles-test-apt-cache` stops it (after a change to `tests/docker/apt-cache/` as well), `docker volume rm dotfiles-test-apt-cache` drops the cache. It is off in CI; `DOTFILES_TEST_APT_CACHE=0|1` overrides. The test image installs no recommended packages.

CI (`.github/workflows/verify.yml`):

- Unit + Ansible syntax (amd64 + arm)
- Docker matrix of context/device combinations (without APT)
- Clean install from `tests/hosts/ci-container.yml`
- APT + Ansible from `tests/hosts/ci-rpi-zero.yml` and `ci-home-laptop.yml` (CI host configs, read through `MACHINE_HOSTS_DIR=tests/hosts`)
- **ansible-lint + host YAML validation** only when `ansible/**`, `machine/hosts/**` or `tests/hosts/**` (or similar) changed

**Deliberately not in CI:** real Pi hardware, Kerberos against the work KDC, Cosmic session, real `bw login`/2FA, real Influx.

## Manual (Compose)

```bash
docker compose -f tests/compose.yaml run --rm shell
# inside the container:
./bootstrap                                # with prompts
./bootstrap --context private --device desktop --yes    # quiet
machine setup                              # previous answers preselected
machine update                             # only bring up to date
```

## Against this home (`machine testenv`)

Runs a command against the real home of this host, as it is right now (including `~/dotfiles` with its branch and local changes), in a container; the home is a read-only lower layer of an overlay, so nothing on the host changes, and all changes inside are discarded on exit. Needs Docker (rootless or rootful) and `/dev/fuse`. The image is built from the host's distribution on first use.

```bash
machine testenv                                        # login shell inside
machine testenv -- 'machine update && machine'         # quote shell syntax, or the host shell runs it
python3 machine_cli/testenv.py -- machine              # same, from a checkout when the installed machine is broken
```

Inside, `machine` uses the host's applied context and device (`--context` / `--device` to change them) and the host name. The container has no systemd user bus and no `bw`, so the timer, linger and `~/.env` steps are skipped there, and Ansible system steps only change the container.
