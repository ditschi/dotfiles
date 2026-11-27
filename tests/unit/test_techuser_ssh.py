"""ssh wrapper and Key Vault askpass helper (spec techuser-ssh-password)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from package_sets import REPO

WRAPPER = REPO / "home/work/.local/bin/ssh"
HELPER = REPO / "home/work/.local/bin/ssh-askpass-azkv"
USER_A, USER_B = "ci-user-a", "ci-user-b"
TECHUSERS = (
    f"{USER_A}=vault-a/technical-user-password {USER_B}=vault-b/technical-user-password"
)
SECRET = "s3cret-from-vault"  # pragma: allowlist secret


@pytest.fixture
def bin_dir(tmp_path: Path) -> Path:
    path = tmp_path / "bin"
    path.mkdir()
    az = path / "az"
    az.write_text(
        "#!/bin/sh\n"
        'echo "$@" >>"$FAKE_AZ_LOG"\n'
        '[ -z "$FAKE_AZ_FAIL" ] || { echo "Please run az login" >&2; exit 1; }\n'
        'echo "$FAKE_AZ_SECRET"\n'
    )
    ssh = path / "ssh"
    ssh.write_text(
        "#!/bin/sh\n"
        '[ "$1" = -G ] && { echo "user $FAKE_SSH_USER"; exit 0; }\n'
        'echo "askpass=${SSH_ASKPASS-} require=${SSH_ASKPASS_REQUIRE-} '
        'user=${AZKV_ASKPASS_USER-} args=$*"\n'
    )
    for script in (az, ssh):
        script.chmod(0o755)
    return path


def env(tmp_path: Path, bin_dir: Path, **extra: str) -> dict:
    base = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_AZ_LOG": str(tmp_path / "az.log"),
        "FAKE_AZ_SECRET": SECRET,
    }
    base.update(extra)
    return base


def wrapper(tmp_path, bin_dir, user, *args, **extra):
    return subprocess.run(
        [str(WRAPPER), *args],
        env=env(tmp_path, bin_dir, FAKE_SSH_USER=user, **extra),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def helper(tmp_path, bin_dir, prompt, tty="", **extra):
    tty_file = tmp_path / "tty"
    tty_file.write_text(tty)
    extra.setdefault("AZKV_ASKPASS_USER", USER_A)
    extra.setdefault("AZKV_TECHUSERS", TECHUSERS)
    if tty:
        extra["AZKV_ASKPASS_TTY"] = str(tty_file)
    return subprocess.run(
        [str(HELPER), prompt],
        env=env(tmp_path, bin_dir, **extra),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,  # no controlling terminal unless a test supplies one
    )


def az_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "az.log"
    return log.read_text().splitlines() if log.is_file() else []


def test_technical_user_gets_the_helper(tmp_path, bin_dir):
    out = wrapper(tmp_path, bin_dir, USER_A, "ci-agent", AZKV_TECHUSERS=TECHUSERS)
    assert f"askpass={HELPER} " in out
    assert "require=prefer" in out
    assert f"user={USER_A}" in out
    assert out.endswith("args=-o NumberOfPasswordPrompts=1 ci-agent")


def test_quoted_mapping_from_a_plain_env_file_matches(tmp_path, bin_dir):
    quoted = f'"{TECHUSERS}"'
    out = wrapper(tmp_path, bin_dir, USER_B, "ci-agent", AZKV_TECHUSERS=quoted)
    assert f"user={USER_B}" in out
    result = helper(
        tmp_path,
        bin_dir,
        f"({USER_B}@h) Password: ",
        AZKV_ASKPASS_USER=USER_B,
        AZKV_TECHUSERS=quoted,
    )
    assert result.stdout == SECRET + "\n"


def test_mapping_loaded_by_the_real_env_loader(tmp_path, bin_dir):
    (tmp_path / ".env").write_text(f'AZKV_TECHUSERS="{TECHUSERS}"\n')
    (tmp_path / ".env").chmod(0o600)
    loader = REPO / "home/core/.shell/common/envfiles.sh"
    out = subprocess.run(
        ["bash", "-c", f'. "{loader}"; dotfiles_load_envfiles; "{WRAPPER}" ci-agent'],
        env=env(tmp_path, bin_dir, FAKE_SSH_USER=USER_A),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert f"user={USER_A}" in out


def test_failing_config_resolution_runs_ssh_unchanged(tmp_path, bin_dir):
    (bin_dir / "ssh").write_text(
        '#!/bin/sh\n[ "$1" = -G ] && exit 1\necho "user=${AZKV_ASKPASS_USER-} args=$*"\n'
    )
    out = wrapper(tmp_path, bin_dir, USER_A, "ci-agent", AZKV_TECHUSERS=TECHUSERS)
    assert out == "user= args=ci-agent"


def test_other_user_is_unchanged(tmp_path, bin_dir):
    out = wrapper(
        tmp_path,
        bin_dir,
        "someone",
        "homeserver",
        AZKV_TECHUSERS=TECHUSERS,
        AZKV_ASKPASS_USER=USER_A,
    )
    assert out == "askpass= require= user= args=homeserver"


def test_without_mapping_nothing_changes(tmp_path, bin_dir):
    out = wrapper(tmp_path, bin_dir, USER_A, "ci-agent")
    assert out == "askpass= require= user= args=ci-agent"


def test_existing_askpass_is_kept(tmp_path, bin_dir):
    out = wrapper(
        tmp_path,
        bin_dir,
        USER_A,
        "ci-agent",
        AZKV_TECHUSERS=TECHUSERS,
        SSH_ASKPASS="/opt/editor-askpass",
    )
    assert "askpass=/opt/editor-askpass " in out
    assert f"user={USER_A}" in out
    assert out.endswith("args=ci-agent")


def test_wrapper_skips_itself_on_path(tmp_path, bin_dir):
    first = tmp_path / "first"
    first.mkdir()
    (first / "ssh").symlink_to(WRAPPER)
    out = subprocess.run(
        ["ssh", "-p", "22", "ci-agent"],
        env=env(
            tmp_path,
            bin_dir,
            PATH=f"{first}:{bin_dir}:/usr/bin:/bin",
            FAKE_SSH_USER=USER_A,
            AZKV_TECHUSERS=TECHUSERS,
        ),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip().endswith("args=-o NumberOfPasswordPrompts=1 -p 22 ci-agent")


def test_wrapper_without_real_ssh_fails(tmp_path):
    only = tmp_path / "only"
    only.mkdir()
    (only / "ssh").symlink_to(WRAPPER)
    for tool in ("bash", "readlink"):
        (only / tool).symlink_to(shutil.which(tool))
    result = subprocess.run(
        ["ssh", "host"],
        env={"PATH": str(only), "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 127
    assert "no ssh found" in result.stderr


@pytest.mark.parametrize(
    "prompt", [f"{USER_A}@ci-agent's password: ", f"({USER_A}@ci-agent) Password: "]
)
def test_password_prompt_is_answered_from_key_vault(tmp_path, bin_dir, prompt):
    result = helper(tmp_path, bin_dir, prompt)
    assert (result.returncode, result.stdout) == (0, SECRET + "\n")
    assert az_calls(tmp_path) == [
        "keyvault secret show --id "
        "https://vault-a.vault.azure.net/secrets/technical-user-password "
        "--query value -o tsv"
    ]


def test_second_user_uses_its_own_vault(tmp_path, bin_dir):
    helper(tmp_path, bin_dir, f"({USER_B}@h) Password: ", AZKV_ASKPASS_USER=USER_B)
    assert "vault-b.vault.azure.net" in az_calls(tmp_path)[0]


def test_prompt_of_another_account_is_not_answered(tmp_path, bin_dir):
    result = helper(tmp_path, bin_dir, "other@jump's password: ", tty="typed\n")
    assert result.stdout == "typed\n"
    assert az_calls(tmp_path) == []


@pytest.mark.parametrize(
    "prompt",
    [
        f"({USER_A}@h) New password: ",
        f"({USER_A}@h) Retype new password: ",
        f"({USER_A}@h) Current password: ",
    ],
)
def test_password_change_prompts_are_not_answered(tmp_path, bin_dir, prompt):
    result = helper(tmp_path, bin_dir, prompt, tty="typed\n")
    assert result.stdout == "typed\n"
    assert az_calls(tmp_path) == []


def test_informational_prompt_is_only_shown(tmp_path, bin_dir):
    result = helper(
        tmp_path, bin_dir, "Confirm user presence", SSH_ASKPASS_PROMPT="none"
    )
    assert (result.returncode, result.stdout) == (0, "")
    assert "Confirm user presence" in result.stderr
    assert az_calls(tmp_path) == []


def test_vault_failure_without_terminal_fails(tmp_path, bin_dir):
    result = helper(tmp_path, bin_dir, f"{USER_A}@h's password: ", FAKE_AZ_FAIL="1")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "az login" in result.stderr
    assert SECRET not in result.stderr


def test_vault_failure_asks_the_terminal(tmp_path, bin_dir):
    result = helper(
        tmp_path,
        bin_dir,
        f"{USER_A}@h's password: ",
        tty="typed\n",
        FAKE_AZ_FAIL="1",
    )
    assert (result.returncode, result.stdout) == (0, "typed\n")
    assert "asking here" in result.stderr


def test_passphrase_goes_to_the_terminal(tmp_path, bin_dir):
    result = helper(tmp_path, bin_dir, "Enter passphrase for key 'k': ", tty="phrase\n")
    assert result.stdout == "phrase\n"
    assert az_calls(tmp_path) == []


@pytest.mark.parametrize("answer,code", [("yes\n", 0), ("no\n", 1)])
def test_host_key_confirmation_uses_the_exit_status(tmp_path, bin_dir, answer, code):
    result = helper(
        tmp_path,
        bin_dir,
        "Are you sure you want to continue connecting (yes/no)? ",
        tty=answer,
        SSH_ASKPASS_PROMPT="confirm",
    )
    assert result.returncode == code
    assert az_calls(tmp_path) == []


def test_unknown_user_goes_to_the_terminal(tmp_path, bin_dir):
    result = helper(
        tmp_path,
        bin_dir,
        "Password: ",
        tty="typed\n",
        AZKV_ASKPASS_USER="other",
    )
    assert result.stdout == "typed\n"
    assert az_calls(tmp_path) == []


def test_scripts_are_executable():
    assert os.access(WRAPPER, os.X_OK) and os.access(HELPER, os.X_OK)


@pytest.mark.parametrize("shell,rc", [("bash", ".profile"), ("zsh", ".zprofile")])
def test_login_shell_finds_the_wrapper_first(tmp_path, shell, rc):
    if not shutil.which(shell):
        pytest.skip(f"{shell} is not installed")
    (tmp_path / ".local/bin").mkdir(parents=True)
    (tmp_path / ".local/bin/ssh").symlink_to(WRAPPER)
    (tmp_path / rc).symlink_to(REPO / "home/core" / rc)
    out = subprocess.run(
        [shell, "-l", "-c", "command -v ssh"],
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == str(tmp_path / ".local/bin/ssh")


def test_wrapper_is_only_in_the_work_group():
    paths = [
        *REPO.glob("home/*/.local/bin/ssh"),
        *REPO.glob("home/*/.local/bin/ssh-askpass-azkv"),
    ]
    assert len(paths) == 2
    assert {p.parts[-4] for p in paths} == {"work"}
