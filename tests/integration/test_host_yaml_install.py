from __future__ import annotations

import re

import pytest
import yaml
import testinfra

from conftest import (
    MACHINE_CLI,
    REPO,
    apt_proxy_for,
    host_env,
    run_checked,
    running_container,
    wants_apt,
)


# Hardware the CI hosts stand for; Docker shows none of it to Ansible.
HARDWARE = {"ci-rpi-zero": "pi,pi-zero", "ci-home-laptop": "laptop,l13-yoga-gen2"}
APPLIED = "/home/{user}/.local/share/machine/applied-host.yml"


@pytest.fixture
def host_yaml_container(docker_image, request):
    """Clean container whose hostname matches tests/hosts/<name>.yml."""
    hostname = request.param
    host_file = REPO / "tests" / "hosts" / f"{hostname}.yml"
    assert host_file.is_file(), f"missing host config {host_file}"
    # sudo_prompt marker: user whose sudo prompts; Ansible gets the password from a file.
    with_password = request.node.get_closest_marker("sudo_prompt") is not None
    user = "pwtester" if with_password else "tester"
    exec_env = (
        (f"ANSIBLE_BECOME_PASSWORD_FILE=/home/{user}/.become-password",)
        if with_password
        else ()
    )
    # --no-become: never prompt; pwtester's password comes from the file
    setup_cmd = [*MACHINE_CLI, "setup", "--yes", "--no-become"]
    if not wants_apt(request):
        setup_cmd.append("--skip-ansible")

    config = yaml.safe_load(host_file.read_text())
    hardware = HARDWARE.get(hostname, "")
    with running_container(
        docker_image,
        f"hy-{hostname}",
        hostname=hostname,
        user=user,
        env=(
            "MACHINE_SKIP_BW=1",
            "MACHINE_SKIP_TOOLS=1",
            "MACHINE_HOSTS_DIR=tests/hosts",
            *host_env(config.get("context", ""), config["device"], hardware),
        ),
        exec_env=exec_env,
        apt_proxy=apt_proxy_for(request),
    ) as (name, exec_cmd):
        run_checked(
            exec_cmd, [*MACHINE_CLI, "host", "sync"], f"host sync for {hostname}"
        )
        run_checked(exec_cmd, setup_cmd, f"setup from host yaml for {hostname}")
        yield testinfra.get_host(f"docker://{name}"), hostname, host_file


def assert_second_apply_is_idempotent(host) -> None:
    """A second `machine apply` must not change anything (changed=0 in the recap)."""
    result = host.run("cd /dotfiles && machine_cli/machine apply --no-become 2>&1")
    assert result.rc == 0, result.stdout
    recap = result.stdout.split("PLAY RECAP", 1)
    assert len(recap) == 2, f"no PLAY RECAP in output:\n{result.stdout[-3000:]}"
    changed = re.findall(r"changed=(\d+)", recap[1])
    assert changed and all(n == "0" for n in changed), (
        "not idempotent, tasks reported changed on the second run:\n"
        + "\n".join(
            line
            for line in result.stdout.splitlines()
            if line.startswith(("changed:", "TASK ["))
        )[-4000:]
    )


@pytest.mark.docker
@pytest.mark.parametrize("host_yaml_container", ["ci-container"], indirect=True)
def test_clean_install_from_versioned_host_yaml_container(host_yaml_container):
    host, _hostname, host_file = host_yaml_container
    expected = host_file.read_text(encoding="utf-8")
    local = host.file(APPLIED.format(user="tester"))
    assert local.exists
    assert "device: container" in local.content_string
    assert "device: container" in expected
    zshrc = host.file("/home/tester/.zshrc")
    assert zshrc.exists
    assert zshrc.is_symlink
    assert not host.file("/home/tester/.p10k.zsh").exists
    assert host.file("/home/tester/.config/starship.toml").is_symlink


def assert_telegraf_installed_without_output(host):
    """Telegraf from the InfluxData source; no Bitwarden in CI, so no output."""
    assert host.package("telegraf").is_installed
    assert host.file("/etc/apt/sources.list.d/influxdata.sources").exists
    default = host.file("/etc/default/telegraf")
    assert default.exists and default.mode == 0o600
    assert not host.file("/etc/telegraf/telegraf.d/00_remote_urls.conf").exists
    assert not host.run("sudo ls /etc/telegraf/telegraf.d/99_output_*.conf").rc == 0


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.parametrize("host_yaml_container", ["ci-rpi-zero"], indirect=True)
def test_clean_install_from_versioned_host_yaml_rpi_zero(host_yaml_container):
    """Full ansible apply driven by tests/hosts/ci-rpi-zero.yml."""
    host, _hostname, _host_file = host_yaml_container
    local = host.file(APPLIED.format(user="tester"))
    assert local.exists
    assert "device: server" in local.content_string
    assert "monitoring" in local.content_string
    assert host.package("zsh").is_installed
    assert not host.package("fzf").is_installed
    assert not host.package("tmux").is_installed
    assert host.package("unattended-upgrades").is_installed
    assert host.package("etckeeper").is_installed
    assert host.file("/etc/.git").is_directory
    assert not host.package("ldap-utils").is_installed
    conf_dir = host.file("/etc/telegraf/telegraf.d")
    assert conf_dir.exists
    assert conf_dir.is_directory
    main_conf = host.file("/etc/telegraf/telegraf.conf")
    assert main_conf.exists
    pi_conf = host.file("/etc/telegraf/telegraf.d/machine_pi.conf")
    assert pi_conf.exists
    assert_telegraf_installed_without_output(host)
    assert_second_apply_is_idempotent(host)


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.sudo_prompt
@pytest.mark.parametrize("host_yaml_container", ["ci-rpi-zero"], indirect=True)
def test_install_with_sudo_password(host_yaml_container):
    """Ansible become through a real password prompt (sudo-rs on Ubuntu 25.10+)."""
    host, _hostname, _host_file = host_yaml_container
    # pwtester's home is not readable for the default container user
    assert host.run(f"sudo test -f {APPLIED.format(user='pwtester')}").rc == 0
    assert "NOPASSWD" not in host.check_output("sudo -l -U pwtester")
    assert host.package("zsh").is_installed
    assert host.file("/etc/telegraf/telegraf.conf").user == "root"


@pytest.mark.docker
@pytest.mark.apt_gnome
@pytest.mark.parametrize("host_yaml_container", ["ci-home-laptop"], indirect=True)
def test_clean_install_from_versioned_host_yaml_home_laptop(host_yaml_container):
    """Full ansible apply mirroring the L13 Yoga host config."""
    host, _hostname, _host_file = host_yaml_container
    local = host.file(APPLIED.format(user="tester"))
    assert local.exists
    assert "device: desktop" in local.content_string
    assert "monitoring" in local.content_string
    assert "gnome" in local.content_string
    assert host.package("zsh").is_installed
    assert host.package("flameshot").is_installed
    assert not host.package("ldap-utils").is_installed
    assert host.file("/etc/telegraf/telegraf.conf").exists
    assert host.file("/etc/telegraf/telegraf.d/machine_laptop.conf").exists
    assert host.file("/etc/telegraf/telegraf.d/machine_base.conf").exists
    assert_telegraf_installed_without_output(host)
    # Role installs files; systemd enable is skipped in containers
    assert host.file("/usr/local/lib/machine/stylus_touch_guard.py").exists
    assert host.file("/etc/systemd/system/stylus-touch-guard.service").exists
    # Laptop features (MACHINE_HARDWARE=laptop) and the L13 Yoga model role
    assert host.file("/usr/local/bin/battery-charge").exists
    assert host.file("/etc/systemd/system/battery-charge-limit.service").exists
    assert host.file("/usr/local/lib/machine/power-profile-switch").exists
    assert host.file("/etc/systemd/logind.conf.d/50-lid-switch.conf").exists
    assert not host.file("/usr/local/bin/thinkpad-charge").exists
    assert host.file("/etc/systemd/zram-generator.conf").exists
    assert host.file("/etc/systemd/user/tablet-osk.service").exists
    assert not host.file("/etc/ssh/sshd_config.d/99-machine-port.conf").exists
    assert_second_apply_is_idempotent(host)
