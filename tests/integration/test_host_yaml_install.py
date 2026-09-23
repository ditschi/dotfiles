from __future__ import annotations

import subprocess
import uuid

import pytest
import testinfra

from conftest import REPO


@pytest.fixture
def host_yaml_container(docker_image, request):
    """Clean container whose hostname matches machine/hosts/<name>.yml."""
    hostname = request.param
    run_apt = (
        request.node.get_closest_marker("apt") is not None
        or request.node.get_closest_marker("apt_gnome") is not None
    )
    name = f"dotfiles-hy-{hostname}-{uuid.uuid4().hex[:8]}"
    host_file = REPO / "machine" / "hosts" / f"{hostname}.yml"
    assert host_file.is_file(), f"missing versioned host profile {host_file}"

    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--hostname",
            hostname,
            "-v",
            f"{REPO}:/dotfiles:ro",
            "-e",
            "DOTFILES_REPO=/dotfiles",
            "-e",
            "DEBIAN_FRONTEND=noninteractive",
            "-e",
            "MACHINE_SKIP_BW=1",
            docker_image,
            "sleep",
            "infinity",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        exec_cmd = ["docker", "exec", "-u", "tester", "-w", "/dotfiles", name]
        subprocess.run(
            [
                *exec_cmd,
                "git",
                "config",
                "--global",
                "--add",
                "safe.directory",
                "/dotfiles",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        sync = subprocess.run(
            [
                *exec_cmd,
                "python3",
                "home/dot_local/bin/executable_machine",
                "profile",
                "sync",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if sync.returncode != 0:
            raise AssertionError(
                f"profile sync failed for {hostname}\n"
                f"STDOUT:\n{sync.stdout}\nSTDERR:\n{sync.stderr}"
            )

        setup_cmd = [
            "python3",
            "home/dot_local/bin/executable_machine",
            "setup",
            "--yes",
            "--no-become",
        ]
        if not run_apt:
            setup_cmd.append("--skip-ansible")
        result = subprocess.run(
            [*exec_cmd, *setup_cmd],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"setup from host yaml failed for {hostname}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        yield testinfra.get_host(f"docker://{name}"), hostname, host_file
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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
    assert not host.package("guake").is_installed
    conf_dir = host.file("/etc/telegraf/telegraf.d")
    assert conf_dir.exists
    assert conf_dir.is_directory
    main_conf = host.file("/etc/telegraf/telegraf.conf")
    assert main_conf.exists
    pi_conf = host.file("/etc/telegraf/telegraf.d/machine_pi.conf")
    assert pi_conf.exists


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
    assert host.file("/etc/ssh/sshd_config.d/99-machine-port.conf").exists
    assert "Port 5115" in host.file("/etc/ssh/sshd_config.d/99-machine-port.conf").content_string
