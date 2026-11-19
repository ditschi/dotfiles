"""jump_host role against a real sshd: only the own loopback port can be forwarded.

Runs on Ubuntu 22.04, the release of oracle (OpenSSH 8.9), so the Match block in the
drop-in is checked with the sshd version it meets there.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from conftest import REPO, docker_available

IMAGE = "ubuntu:22.04"

SCRIPT = r"""
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends openssh-server openssh-client \
  ansible-core python3 iproute2 >/dev/null
mkdir -p /run/sshd /root/.ssh
ssh-keygen -q -t ed25519 -N '' -f /root/.ssh/dev
ssh-keygen -q -t ed25519 -N '' -f /root/.ssh/other
cat > /tmp/vars.json <<EOF
{"jump_host_tunnels": [{"alias": "dev", "port": 2223,
  "key": "$(cut -d' ' -f1,2 /root/.ssh/dev.pub)"}],
 "jump_host_missing_keys": ["machine/ssh_tunnel_keys/gone.pub"]}
EOF
cat > /tmp/play.yml <<'EOF'
- hosts: localhost
  become: false
  gather_facts: true
  roles: [jump_host]
EOF
ANSIBLE_ROLES_PATH=/roles ansible-playbook -c local -i localhost, /tmp/play.yml \
  -e @/tmp/vars.json >/tmp/ansible.log 2>&1 || { cat /tmp/ansible.log; exit 1; }
# A second run with no host list keeps the keys.
echo '{"jump_host_tunnels": null}' > /tmp/none.json
ANSIBLE_ROLES_PATH=/roles ansible-playbook -c local -i localhost, /tmp/play.yml \
  -e @/tmp/none.json >>/tmp/ansible.log 2>&1 || { cat /tmp/ansible.log; exit 1; }
/usr/sbin/sshd
sleep 1
O="-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
check() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }
forward() {  # forward <key> <listen spec>: did the remote listener come up?
  timeout 6 ssh $O -i "$1" -N -o ExitOnForwardFailure=yes -R "$2:localhost:22" \
    tunnel@localhost &
  pid=$!
  sleep 3
  if kill -0 "$pid" 2>/dev/null; then kill "$pid"; wait "$pid" 2>/dev/null; echo yes
  else wait "$pid" 2>/dev/null; echo no; fi
}
listen_addr() {
  timeout 6 ssh $O -i /root/.ssh/dev -N -R 127.0.0.1:2223:localhost:22 tunnel@localhost &
  pid=$!; sleep 3
  ss -ltnH 'sport = :2223' | awk '{print $4}' | sort -u | tr '\n' ' '
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null || true
}
effective() {  # effective <user>: the sshd options this change cares about
  sshd -T -C "user=$1,host=x,addr=127.0.0.1" \
    | grep -E '^(allowtcpforwarding|permittty|clientalive[a-z]*|gatewayports) ' \
    | sort | tr '\n' ';'
}
# ForceCommand ends the session anyway; the client reports the refused PTY request.
TTY="$(timeout 6 ssh $O -tt -i /root/.ssh/dev tunnel@localhost true 2>&1 </dev/null \
  | grep -c 'PTY allocation request failed' || true)"
LOCAL_FORWARD="$(check timeout 6 ssh $O -i /root/.ssh/dev -W localhost:22 \
  tunnel@localhost </dev/null)"
cat <<EOF
{
 "shell": "$(check timeout 6 ssh $O -i /root/.ssh/dev tunnel@localhost true)",
 "tty": "$TTY",
 "local_forward": "$LOCAL_FORWARD",
 "own_port": "$(forward /root/.ssh/dev 127.0.0.1:2223)",
 "other_port": "$(forward /root/.ssh/dev 127.0.0.1:2299)",
 "all_addresses": "$(forward /root/.ssh/dev 0.0.0.0:2223)",
 "other_key": "$(forward /root/.ssh/other 127.0.0.1:2223)",
 "listen": "$(listen_addr)",
 "keys": $(grep -c permitlisten /var/lib/tunnel/.ssh/authorized_keys),
 "missing_warned": "$(grep -c 'machine/ssh_tunnel_keys/gone.pub' /tmp/ansible.log)",
 "sshd_t": "$(effective tunnel)",
 "others": "$(effective root)"
}
EOF
"""


@pytest.mark.docker
@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_tunnel_user_can_only_listen_on_its_port():
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{REPO}/ansible/roles/jump_host:/roles/jump_host:ro",
            IMAGE,
            "bash",
            "-c",
            SCRIPT,
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    start = out.index("{")
    data = json.loads(out[start:])
    assert data["shell"] == "no"
    assert data["tty"] == "1"  # PermitTTY no
    assert data["local_forward"] == "no"
    assert data["own_port"] == "yes"
    assert data["other_port"] == "no"
    assert data["all_addresses"] == "no"
    assert data["other_key"] == "no"
    assert data["listen"].split() == ["127.0.0.1:2223"]
    assert data["keys"] == 1
    assert data["missing_warned"] != "0"
    assert data["sshd_t"] == (
        "allowtcpforwarding remote;clientalivecountmax 3;clientaliveinterval 30;"
        "gatewayports no;permittty no;"
    )
    # The Match block ends with the drop-in: other users keep the defaults.
    assert data["others"] == (
        "allowtcpforwarding yes;clientalivecountmax 3;clientaliveinterval 0;"
        "gatewayports no;permittty yes;"
    )
