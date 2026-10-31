"""monitoring role: pinned InfluxData key; config, output and start rule without root."""

from __future__ import annotations

import grp
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import ANSIBLE

ROLE = ANSIBLE / "roles/monitoring"
KEY = ROLE / "files/influxdata-archive.asc"
# Primary key of https://repos.influxdata.com/influxdata-archive.key (docs.influxdata.com).
FINGERPRINT = "24C975CBA61A024EE1B631787C3D57159FC2F927"  # pragma: allowlist secret


def test_pinned_key_has_the_influxdata_fingerprint(tmp_path):
    result = subprocess.run(
        ["gpg", "--show-keys", "--with-colons", str(KEY)],
        env={**os.environ, "GNUPGHOME": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    primary = [
        line.split(":")[9]
        for line in result.stdout.splitlines()
        if line.startswith("fpr:")
    ][0]
    assert primary == FINGERPRINT


needs_ansible = pytest.mark.skipif(
    not shutil.which("ansible-playbook"), reason="ansible-playbook not installed"
)


@pytest.fixture
def apply_role(tmp_path):
    """Run the role on localhost with paths under tmp_path; no install, no services."""
    etc = tmp_path / "etc"
    etc.mkdir()
    playbook = tmp_path / "play.yml"
    playbook.write_text(
        json.dumps(
            [
                {
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {"os_family": "Other"},
                        "machine_manage_services": False,
                        "monitoring_configs": ["machine/base", "machine/laptop"],
                        "monitoring_conf_dir": str(etc / "telegraf.d"),
                        "monitoring_main_conf": str(etc / "telegraf.conf"),
                        "monitoring_default_file": str(etc / "default-telegraf"),
                        "monitoring_service_group": grp.getgrgid(os.getgid()).gr_name,
                        "monitoring_sudoers_file": str(etc / "sudoers-telegraf"),
                        "influx_url": "",
                        "influx_token": "",
                        "influx_org": "home",
                        "influx_bucket": "telegraf",
                        "influx_username": "",
                        "influx_password": "",
                        "influx_database": "telegraf",
                        "influx_telegraf_config_base": "",
                    },
                    "roles": [{"role": str(ROLE)}],
                }
            ]
        ),
        encoding="utf-8",
    )

    def run(**extra) -> str:
        result = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                "localhost,",
                str(playbook),
                "-e",
                json.dumps(extra),
            ],
            env={**os.environ, "ANSIBLE_NOCOLOR": "1"},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    return etc, run


def _names(etc: Path) -> set[str]:
    return {p.name for p in (etc / "telegraf.d").iterdir()}


def _mode(path: Path) -> str:
    return oct(path.stat().st_mode & 0o777)


@needs_ansible
def test_without_credentials_local_fragments_and_no_output(apply_role):
    etc, run = apply_role
    out = run()
    assert _names(etc) == {"machine_base.conf", "machine_laptop.conf"}
    assert 'TELEGRAF_OPTS=""' in (etc / "default-telegraf").read_text()
    assert _mode(etc / "default-telegraf") == "0o600"
    assert "Telegraf has no output" in out
    # the system hostname, not the inventory name "localhost" of local runs
    assert not re.search(r"^\s*hostname\s*=", (etc / "telegraf.conf").read_text(), re.M)


@needs_ansible
def test_token_writes_v2_output_and_a_later_run_keeps_it(apply_role):
    etc, run = apply_role
    out = run(influx_url="https://influx.test", influx_token='to"k')
    output = etc / "telegraf.d/99_output_influx2.conf"
    assert 'token = "to\\"k"' in output.read_text()
    assert 'urls = ["https://influx.test"]' in output.read_text()
    # readable by the telegraf service group, not by everyone
    assert _mode(output) == "0o640"
    assert output.stat().st_gid == os.getgid()
    assert "Telegraf has no output" not in out

    out = run()  # Bitwarden locked: the output stays
    assert output.is_file()
    assert "Telegraf has no output" not in out


@needs_ansible
def test_v1_output_replaces_v2(apply_role):
    etc, run = apply_role
    run(influx_url="https://influx.test", influx_token="tok")
    run(influx_url="https://influx.test", influx_username="u", influx_password="p")
    assert "99_output_influx1.conf" in _names(etc)
    assert "99_output_influx2.conf" not in _names(etc)


@needs_ansible
def test_remote_base_replaces_local_fragments(apply_role):
    etc, run = apply_role
    run()
    out = run(influx_telegraf_config_base="https://influx.test/t", influx_token="tok")
    env = (etc / "default-telegraf").read_text()
    assert (
        'TELEGRAF_OPTS="--config https://influx.test/t/machine/base '
        '--config https://influx.test/t/machine/laptop"'
    ) in env
    assert 'INFLUX_TOKEN="tok"' in env
    assert _mode(etc / "default-telegraf") == "0o600"
    assert not {n for n in _names(etc) if n.startswith("machine_")}
    assert "Telegraf has no output" not in out

    # a later run without the token keeps the service environment
    run(influx_telegraf_config_base="https://influx.test/t")
    assert 'INFLUX_TOKEN="tok"' in (etc / "default-telegraf").read_text()

    run()  # back to the local fragments
    assert {"machine_base.conf", "machine_laptop.conf"} <= _names(etc)
    assert 'TELEGRAF_OPTS=""' in (etc / "default-telegraf").read_text()


@needs_ansible
def test_former_remote_url_note_is_removed(apply_role):
    etc, run = apply_role
    (etc / "telegraf.d").mkdir()
    (etc / "telegraf.d/00_remote_urls.conf").write_text("# old\n")
    run()
    assert "00_remote_urls.conf" not in _names(etc)


def _agent_tables(*paths: Path) -> int:
    return sum(len(re.findall(r"^\s*\[agent\]", p.read_text(), re.M)) for p in paths)


def test_fragments_have_no_agent_table():
    # telegraf.conf holds the only [agent] table; a second one makes Telegraf warn.
    fragments = sorted((ROLE / "files").glob("machine_*.conf"))
    assert fragments
    assert _agent_tables(*fragments) == 0


def test_only_the_smart_fragment_reads_smart():
    # SMART needs real disks and sudo; the other fragments run everywhere.
    readers = {
        p.name
        for p in (ROLE / "files").glob("machine_*.conf")
        if "inputs.smart" in p.read_text()
    }
    assert readers == {"machine_smart.conf"}
    assert "use_sudo = true" in (ROLE / "files/machine_smart.conf").read_text()


@needs_ansible
@pytest.mark.parametrize(
    ("configs", "interval"),
    [
        (["machine/base", "machine/laptop"], "30s"),
        (["machine/base", "machine/server"], "15s"),
        (["machine/base", "machine/pi"], "60s"),
        # server wins over laptop, as when both fragments set it and server loaded last
        (["machine/base", "machine/laptop", "machine/server"], "15s"),
        (["machine/base", "machine/docker"], None),  # Telegraf's default (10s)
    ],
)
def test_one_agent_table_with_the_machine_interval(apply_role, configs, interval):
    etc, run = apply_role
    run(monitoring_configs=configs)
    main = (etc / "telegraf.conf").read_text()
    assert _agent_tables(etc / "telegraf.conf", *(etc / "telegraf.d").iterdir()) == 1
    intervals = re.findall(r'^\s*interval\s*=\s*"([^"]*)"', main, re.M)
    assert intervals == ([interval] if interval else [])


@needs_ansible
def test_remote_base_leaves_the_interval_to_the_remote_configs(apply_role):
    etc, run = apply_role
    run(influx_telegraf_config_base="https://influx.test/t", influx_token="tok")
    main = (etc / "telegraf.conf").read_text()
    assert _agent_tables(etc / "telegraf.conf") == 1
    assert not re.search(r"^\s*interval\s*=", main, re.M)


@needs_ansible
def test_smart_fragment_brings_the_smartctl_rule_and_leaves_with_it(apply_role):
    etc, run = apply_role
    smart = ["machine/base", "machine/server", "machine/smart"]
    run(monitoring_configs=smart)
    rule = etc / "sudoers-telegraf"
    assert "machine_smart.conf" in _names(etc)
    assert _mode(rule) == "0o440"
    assert "telegraf ALL=(root) NOPASSWD: /usr/sbin/smartctl\n" in rule.read_text()

    run(monitoring_configs=["machine/base", "machine/server"])
    assert "machine_smart.conf" not in _names(etc)
    assert {"machine_base.conf", "machine_server.conf"} <= _names(etc)
    assert not rule.exists()
