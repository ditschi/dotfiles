from __future__ import annotations

import pytest

PROFILES = [
    "home-laptop",
    "work-machine",
    "home-server",
    "rpi",
    "rpi-zero",
    "container",
]

# antidote clones ~11 plugins from GitHub on first start. A stub antidote whose bundle
# only runs compinit keeps the startup test offline and deterministic while all of our
# own config (including the compdef-based machine completion) still runs.
ANTIDOTE_STUB = r"""
stub="$HOME/.cache/antidote-stub/antidote/mattmc3/antidote"
mkdir -p "$stub"
cat > "$stub/antidote.zsh" <<'Z'
antidote() {
  [[ $1 == bundle ]] || return 0
  cat >/dev/null
  print -r -- 'autoload -Uz compinit && compinit -u -d "$HOME/.cache/zcompdump"'
}
Z
"""
STUB_ENV = 'XDG_DATA_HOME="$HOME/.cache/antidote-stub"'
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
    if profile == "work-machine":
        assert work_zsh.exists
        assert work_tools.exists
        assert work_ldap.exists
    else:
        assert not work_zsh.exists
        assert not work_tools.exists
        assert not work_ldap.exists

    # One prompt config for every profile; Powerlevel10k is gone.
    assert not host.file("/home/tester/.p10k.zsh").exists
    assert host.file("/home/tester/.config/starship.toml").is_symlink

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
        if profile == "work-machine"
        else "chris@ditscher.me"
    )
    assert host.check_output("git -C /tmp config user.email") == expected


@pytest.mark.docker
@pytest.mark.parametrize("profile_env", PROFILES, indirect=True)
def test_shells_start_cleanly(profile_env):
    host, profile = profile_env
    work = "true" if profile == "work-machine" else ""
    host.run_test(ANTIDOTE_STUB)

    zsh = host.run(
        f"{STUB_ENV} TERM=xterm zsh -i -c "
        "'print -r -- \"$MACHINE_PROFILE|${WORK_SETUP:-}|$(alias g)\"'"
    )
    assert zsh.rc == 0, zsh.stderr
    assert zsh.stderr == "", f"zsh startup wrote to stderr:\n{zsh.stderr}"
    assert zsh.stdout.strip().splitlines()[-1] == f"{profile}|{work}|g=git"

    bash = host.run(
        "TERM=xterm bash -i -c "
        '\'echo "${STARSHIP_SHELL:-none}|$(command -v starship || echo none)"; '
        'echo "$MACHINE_PROFILE|${WORK_SETUP:-}|$(alias g)"\''
    )
    assert bash.rc == 0, bash.stderr
    errors = [
        line
        for line in bash.stderr.splitlines()
        if not any(noise in line for noise in BASH_TTY_NOISE)
    ]
    assert errors == [], "bash startup wrote to stderr:\n" + "\n".join(errors)
    *_, prompt, last = bash.stdout.strip().splitlines()
    assert last == f"{profile}|{work}|alias g='git'"
    # Starship drives the bash prompt when installed; without it bash starts cleanly anyway.
    starship_shell, starship_bin = prompt.split("|")
    assert starship_shell == ("none" if starship_bin == "none" else "bash")


@pytest.mark.docker
@pytest.mark.parametrize("profile_env", ["container"], indirect=True)
def test_dev_container_with_work_user_starts_cleanly(profile_env):
    # sdx dev containers run as the Bosch user id: the container profile keeps
    # WORK_SETUP off, and chezmoi does not link the work modules for it.
    host, _profile = profile_env
    host.run_test(ANTIDOTE_STUB)
    for shell in (
        f"{STUB_ENV} USER=abc1de TERM=xterm zsh -i -c",
        "USER=abc1de TERM=xterm bash -i -c",
    ):
        res = host.run(f"{shell} 'echo \"$MACHINE_PROFILE|${{WORK_SETUP:-}}\"'")
        errors = [
            line
            for line in res.stderr.splitlines()
            if not any(noise in line for noise in BASH_TTY_NOISE)
        ]
        assert res.rc == 0 and errors == [], f"{shell}:\n{res.stderr}"
        assert res.stdout.strip().splitlines()[-1] == "container|"


@pytest.mark.docker
@pytest.mark.apt
@pytest.mark.parametrize("profile_env", ["rpi-zero"], indirect=True)
def test_rpi_zero_apt_packages(profile_env):
    host, _profile = profile_env
    assert host.package("zsh").is_installed
    assert not host.package("fzf").is_installed
    assert not host.package("tmux").is_installed
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
