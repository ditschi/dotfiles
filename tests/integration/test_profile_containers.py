from __future__ import annotations

import pytest

PROFILES = ["home-laptop", "work-laptop", "home-server", "rpi", "rpi-zero", "container"]

# zinit clones ~10 plugins from GitHub on first start. A no-op stub keeps the
# startup test offline and deterministic while all of our own config still runs.
ZINIT_STUB = r"""
stub="$HOME/.cache/zinit-stub"
mkdir -p "$stub/zinit/zinit.git/.git"
cat > "$stub/zinit/zinit.git/zinit.zsh" <<'Z'
zinit() { :; }; zplugin() { :; }; zi() { :; }
zicompinit() { autoload -Uz compinit && compinit -u -d "$HOME/.cache/zcompdump"; }
zicdreplay() { :; }
Z
"""
# bash -i without a TTY always prints these; they are not from our config
BASH_TTY_NOISE = (
    "cannot set terminal process group",
    "no job control in this shell",
)


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

    timer = host.file("/home/tester/.config/systemd/user/dotfiles-update-check.timer")
    if profile == "container":
        assert not timer.exists
    else:
        assert timer.exists

    profile_file = host.file("/home/tester/.config/machine/profile.yml")
    assert profile_file.exists
    assert f"profile: {profile}" in profile_file.content_string

    assert host.file("/home/tester/.gitconfig").is_symlink
    local = host.file("/home/tester/.gitconfig.local")
    assert local.exists and not local.is_symlink
    expected = (
        "christian.ditscher@de.bosch.com"
        if profile == "work-laptop"
        else "chris@ditscher.me"
    )
    assert host.check_output("git -C /tmp config user.email") == expected


@pytest.mark.docker
@pytest.mark.parametrize("profile_env", PROFILES, indirect=True)
def test_shells_start_cleanly(profile_env):
    host, profile = profile_env
    work = "true" if profile == "work-laptop" else ""
    host.run_test(ZINIT_STUB)

    zsh = host.run(
        'XDG_DATA_HOME="$HOME/.cache/zinit-stub" TERM=xterm zsh -i -c '
        "'print -r -- \"$MACHINE_PROFILE|${WORK_SETUP:-}|$(alias g)\"'"
    )
    assert zsh.rc == 0, zsh.stderr
    assert zsh.stderr == "", f"zsh startup wrote to stderr:\n{zsh.stderr}"
    assert zsh.stdout.strip().splitlines()[-1] == f"{profile}|{work}|g=git"

    bash = host.run(
        "TERM=xterm bash -i -c "
        "'echo \"$MACHINE_PROFILE|${WORK_SETUP:-}|$(alias g)\"'"
    )
    assert bash.rc == 0, bash.stderr
    errors = [
        line
        for line in bash.stderr.splitlines()
        if not any(noise in line for noise in BASH_TTY_NOISE)
    ]
    assert errors == [], "bash startup wrote to stderr:\n" + "\n".join(errors)
    assert bash.stdout.strip().splitlines()[-1] == f"{profile}|{work}|alias g='git'"


@pytest.mark.docker
@pytest.mark.parametrize("profile_env", ["container"], indirect=True)
def test_dev_container_with_work_user_starts_cleanly(profile_env):
    # sdx dev containers run as the Bosch user id: WORK_SETUP is on, but chezmoi
    # does not link the work modules for the container profile.
    host, _profile = profile_env
    host.run_test(ZINIT_STUB)
    for shell in (
        'XDG_DATA_HOME="$HOME/.cache/zinit-stub" USER=abc1de TERM=xterm zsh -i -c',
        "USER=abc1de TERM=xterm bash -i -c",
    ):
        res = host.run(f"{shell} 'echo \"$MACHINE_PROFILE|$WORK_SETUP\"'")
        errors = [
            line
            for line in res.stderr.splitlines()
            if not any(noise in line for noise in BASH_TTY_NOISE)
        ]
        assert res.rc == 0 and errors == [], f"{shell}:\n{res.stderr}"
        assert res.stdout.strip().splitlines()[-1] == "container|true"


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


@pytest.mark.docker
@pytest.mark.apt_gnome
@pytest.mark.parametrize("profile_env", ["home-laptop"], indirect=True)
def test_home_laptop_gnome_apt_packages(profile_env):
    host, _profile = profile_env
    assert host.package("guake").is_installed
    assert host.package("flameshot").is_installed
    assert not host.package("ldap-utils").is_installed
