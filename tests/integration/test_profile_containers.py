from __future__ import annotations

import pytest

PROFILES = ["home-laptop", "work-laptop", "home-server", "rpi", "rpi-zero", "container"]


@pytest.mark.docker
@pytest.mark.parametrize("profile_env", PROFILES, indirect=True)
def test_profile_dotfiles(profile_env):
    host, profile = profile_env
    zshrc = host.file("/home/tester/.zshrc")
    assert zshrc.exists
    assert zshrc.is_symlink

    work_zsh = host.file("/home/tester/.zsh/config/01_work.zsh")
    work_tools = host.file("/home/tester/.zsh/config/01_work_tools.zsh")
    work_ldap = host.file("/home/tester/.zsh/config/01_work_ldap_helpers.zsh")
    if profile == "work-laptop":
        assert work_zsh.exists
        assert work_tools.exists
        assert work_ldap.exists
    else:
        assert not work_zsh.exists
        assert not work_tools.exists
        assert not work_ldap.exists

    p10k = host.file("/home/tester/.p10k.zsh")
    starship = host.file("/home/tester/.config/starship.toml")
    if profile in {"rpi-zero", "container"}:
        assert not p10k.exists
        assert not starship.exists
    else:
        assert p10k.exists
        assert starship.exists

    timer = host.file(
        "/home/tester/.config/systemd/user/dotfiles-update-check.timer"
    )
    if profile == "container":
        assert not timer.exists
    else:
        assert timer.exists

    profile_file = host.file("/home/tester/.config/machine/profile.yml")
    assert profile_file.exists
    assert f"profile: {profile}" in profile_file.content_string


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.parametrize("profile_env", ["rpi-zero"], indirect=True)
def test_rpi_zero_apt_packages(profile_env):
    host, _profile = profile_env
    assert host.package("zsh").is_installed
    assert host.package("fzf").is_installed
    assert host.package("tmux").is_installed
    assert not host.package("guake").is_installed
    assert not host.package("ldap-utils").is_installed
