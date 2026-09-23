#!/usr/bin/env bash
# Local verification: unit tests always, Docker profile tests when Docker works.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
if [[ ! -d tests/.venv ]]; then
    "$PYTHON" -m venv tests/.venv
fi
# shellcheck disable=SC1091
source tests/.venv/bin/activate
pip install -q -r tests/requirements.txt

"$PYTHON" -m py_compile home/dot_local/bin/executable_machine install.py
pytest tests/unit -q "$@"

if command -v ansible-playbook >/dev/null 2>&1; then
    ansible-playbook --syntax-check -i ansible/inventory/local.yml ansible/workstation.yml
fi

if command -v ansible-lint >/dev/null 2>&1; then
    ansible-lint ansible/workstation.yml ansible/homelab.yml ansible/site.yml ansible/dump_packages.yml ansible/dump_monitoring.yml
fi

if docker info >/dev/null 2>&1; then
    pytest tests/integration -q -m "docker and not apt and not apt_gnome" "$@"
    echo "Docker preset smoke tests passed. Full apt profile: pytest tests/integration -m apt"
    echo "Host-YAML clean install: pytest tests/integration/test_host_yaml_install.py -q"
    echo "Interactive lab: docker compose -f tests/compose.yaml run --rm shell"
    echo "Migration lab:   docker compose -f tests/compose.yaml run --rm migrate"
else
    echo "Docker not available; skipped tests/integration"
fi
