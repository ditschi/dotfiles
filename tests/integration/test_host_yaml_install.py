from __future__ import annotations

import re

import pytest
import testinfra

from conftest import MACHINE_CLI, REPO, run_checked, running_container, wants_apt


@pytest.fixture
def host_yaml_container(docker_image, request):
    """Clean container whose hostname matches machine/hosts/<name>.yml."""
    hostname = request.param
    host_file = REPO / "machine" / "hosts" / f"{hostname}.yml"
    assert host_file.is_file(), f"missing versioned host profile {host_file}"
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

    with running_container(
        docker_image,
        f"hy-{hostname}",
        hostname=hostname,
        user=user,
        env=("MACHINE_SKIP_BW=1",),
        exec_env=exec_env,
    ) as (name, exec_cmd):
        run_checked(
            exec_cmd, [*MACHINE_CLI, "profile", "sync"], f"profile sync for {hostname}"
        )
        run_checked(exec_cmd, setup_cmd, f"setup from host yaml for {hostname}")
        yield testinfra.get_host(f"docker://{name}"), hostname, host_file


def assert_second_apply_is_idempotent(host) -> None:
    """A second `machine apply` must not change anything (changed=0 in the recap)."""
    result = host.run(
        "cd /dotfiles && home/dot_local/bin/executable_machine apply --no-become 2>&1"
    )
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
    local = host.file("/home/tester/.config/machine/profile.yml")
    assert local.exists
    assert "profile: container" in local.content_string
    assert "profile: container" in expected
    zshrc = host.file("/home/tester/.zshrc")
    assert zshrc.exists
    assert zshrc.is_symlink
    assert not host.file("/home/tester/.p10k.zsh").exists


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.parametrize("host_yaml_container", ["ci-rpi-zero"], indirect=True)
def test_clean_install_from_versioned_host_yaml_rpi_zero(host_yaml_container):
    """Full ansible apply driven by machine/hosts/ci-rpi-zero.yml."""
    host, _hostname, _host_file = host_yaml_container
    local = host.file("/home/tester/.config/machine/profile.yml")
    assert local.exists
    assert "profile: rpi-zero" in local.content_string
    assert "monitoring" in local.content_string
    assert host.package("zsh").is_installed
    assert host.package("fzf").is_installed
    assert host.package("tmux").is_installed
    assert host.package("unattended-upgrades").is_installed
    assert host.package("etckeeper").is_installed
    assert host.file("/etc/.git").is_directory
    assert not host.package("guake").is_installed
    conf_dir = host.file("/etc/telegraf/telegraf.d")
    assert conf_dir.exists
    assert conf_dir.is_directory
    main_conf = host.file("/etc/telegraf/telegraf.conf")
    assert main_conf.exists
    pi_conf = host.file("/etc/telegraf/telegraf.d/machine_pi.conf")
    assert pi_conf.exists
    assert_second_apply_is_idempotent(host)


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.sudo_prompt
@pytest.mark.parametrize("host_yaml_container", ["ci-rpi-zero"], indirect=True)
def test_install_with_sudo_password(host_yaml_container):
    """Ansible become through a real password prompt (sudo-rs on Ubuntu 25.10+)."""
    host, _hostname, _host_file = host_yaml_container
    # pwtester's home is not readable for the default container user
    assert host.run("sudo test -f /home/pwtester/.config/machine/profile.yml").rc == 0
    assert "NOPASSWD" not in host.check_output("sudo -l -U pwtester")
    assert host.package("zsh").is_installed
    assert host.file("/etc/telegraf/telegraf.conf").user == "root"


@pytest.mark.docker
@pytest.mark.apt_gnome
@pytest.mark.parametrize("host_yaml_container", ["ci-home-laptop"], indirect=True)
def test_clean_install_from_versioned_host_yaml_home_laptop(host_yaml_container):
    """Full ansible apply mirroring the ThinkPad home-laptop host YAML."""
    host, _hostname, _host_file = host_yaml_container
    local = host.file("/home/tester/.config/machine/profile.yml")
    assert local.exists
    assert "profile: home-laptop" in local.content_string
    assert "monitoring" in local.content_string
    assert "gnome" in local.content_string
    assert host.package("zsh").is_installed
    assert host.package("guake").is_installed
    assert host.package("flameshot").is_installed
    assert not host.package("ldap-utils").is_installed
    assert host.file("/etc/telegraf/telegraf.conf").exists
    assert host.file("/etc/telegraf/telegraf.d/machine_laptop.conf").exists
    assert host.file("/etc/telegraf/telegraf.d/machine_base.conf").exists
    # Role installs files; systemd enable is skipped in containers
    assert host.file("/usr/local/lib/machine/stylus_touch_guard.py").exists
    assert host.file("/etc/systemd/system/stylus-touch-guard.service").exists
    assert host.file("/usr/local/bin/thinkpad-charge").exists
    assert host.file("/etc/systemd/zram-generator.conf").exists
    assert host.file("/etc/systemd/user/tablet-osk.service").exists
    assert host.file("/etc/ssh/sshd_config.d/99-machine-port.conf").exists
    assert (
        "Port 5115"
        in host.file("/etc/ssh/sshd_config.d/99-machine-port.conf").content_string
    )
    assert_second_apply_is_idempotent(host)
