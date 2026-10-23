from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from package_sets import REPO

HELPER = REPO / "home/core/.zsh/zsh-handoff-check.sh"
BASHRC = REPO / "home/core/.bashrc"
TOOLS = ("mktemp", "head", "rm", "mkdir", "timeout", "ps", "tr", "cat", "sleep", "grep")

STUB = """\
#!/bin/bash
# Stub zsh: MODE selects the behaviour; a trial start gets "-c", a handoff does not.
echo "$@" >> "$HOME/zsh-calls"
if [ "$1 $2 $3" != "-l -i -c" ]; then
    echo STUB-ZSH-HANDOFF
    exit 0
fi
case "$(cat "$HOME/mode")" in
    ok) echo "DOTFILES_ZSH_LOADED=1 DOTFILES_ZSH_DEFERRED_LOADED=1" ;;
    plain) echo "DOTFILES_ZSH_LOADED=0 DOTFILES_ZSH_DEFERRED_LOADED=0" ;;
    nodefer) echo "DOTFILES_ZSH_LOADED=1 DOTFILES_ZSH_DEFERRED_LOADED=0" ;;
    noisy) echo "some error" >&2; echo "DOTFILES_ZSH_LOADED=1 DOTFILES_ZSH_DEFERRED_LOADED=1" ;;
    crash) exit 3 ;;
    hang) sleep 30 ;;
esac
"""


@pytest.fixture
def env(tmp_path: Path):
    home = tmp_path / "home"
    (home / ".zsh/config").mkdir(parents=True)
    (home / ".zsh/config/00_LOADER.zsh").write_text("")
    (home / ".zshrc").write_text("")
    (home / "mode").write_text("ok")
    (home / ".zsh/plugins.txt").write_text("")
    (home / ".local/share/antidote/mattmc3/antidote").mkdir(parents=True)
    (home / ".cache/zsh").mkdir(parents=True)
    (home / ".cache/zsh/plugins.zsh").write_text("# generated")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in TOOLS:
        found = shutil.which(tool)
        if found:
            (bin_dir / tool).symlink_to(found)
    zsh = bin_dir / "zsh"
    zsh.write_text(STUB)
    zsh.chmod(0o755)
    old = time.time() - 100
    for path in (
        home / ".zshrc",
        home / ".zsh/config/00_LOADER.zsh",
        home / ".zsh/plugins.txt",
        zsh,
    ):
        os.utime(path, (old, old))
    environ = {
        "HOME": str(home),
        "PATH": str(bin_dir),
        "SHLVL": "0",
        "TERM": "dumb",
    }
    return home, bin_dir, environ


def check(environ: dict, snippet: str = "dotfiles_zsh_handoff_ok"):
    script = f'. "{HELPER}"; {snippet}; echo "rc=$?"'
    return subprocess.run(
        [shutil.which("bash"), "-c", script],
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


def touch_later(path: Path):
    time.sleep(0.05)  # coarse filesystem timestamps
    path.touch()


def trial_calls(home: Path) -> int:
    calls = home / "zsh-calls"
    return len(calls.read_text().splitlines()) if calls.exists() else 0


def test_healthy_zsh_passes(env):
    _, _, environ = env
    result = check(environ)
    assert "rc=0" in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("plain", "config did not load completely"),
        ("nodefer", "plugins did not load completely"),
        ("noisy", "printed errors on startup: some error"),
        ("crash", "failed to start (exit 3)"),
    ],
)
def test_startup_failures_are_reported(env, mode, expected):
    home, _, environ = env
    (home / "mode").write_text(mode)
    result = check(environ)
    assert "rc=1" in result.stdout
    assert expected in result.stderr


def test_missing_loader_and_missing_zsh(env):
    home, bin_dir, environ = env
    (home / ".zsh/config/00_LOADER.zsh").unlink()
    assert "00_LOADER.zsh is missing" in check(environ).stderr
    (bin_dir / "zsh").unlink()
    assert "zsh is not installed" in check(environ).stderr


def test_hanging_zsh_times_out(env):
    home, _, environ = env
    (home / "mode").write_text("hang")
    result = check({**environ, "DOTFILES_ZSH_CHECK_TIMEOUT": "1"})
    assert "zsh startup timed out" in result.stderr
    assert "rc=1" in result.stdout
    assert not (home / ".local/state/dotfiles/zsh-handoff").exists()
    (home / "mode").write_text("ok")
    assert "rc=0" in check(environ).stdout


@pytest.mark.parametrize("missing", ["antidote", "generated"])
def test_fresh_machine_without_antidote_hands_off_unchecked(env, missing):
    home, _, environ = env
    if missing == "antidote":
        shutil.rmtree(home / ".local/share/antidote")
    else:
        (home / ".cache/zsh/plugins.zsh").unlink()
    (home / "mode").write_text("crash")
    result = check(environ)
    assert "rc=0" in result.stdout
    assert trial_calls(home) == 0


def test_only_old_zinit_data_counts_as_fresh(env):
    home, _, environ = env
    shutil.rmtree(home / ".local/share/antidote")
    (home / ".local/share/zinit/zinit.git").mkdir(parents=True)
    (home / "mode").write_text("crash")
    assert "rc=0" in check(environ).stdout
    assert trial_calls(home) == 0


def test_failed_deferred_plugins_are_cached(env):
    home, _, environ = env
    (home / "mode").write_text("nodefer")
    first = check(environ)
    assert "rc=1" in first.stdout and "plugins did not load completely" in first.stderr
    again = check(environ)
    assert "rc=1" in again.stdout and "plugins did not load completely" in again.stderr
    assert trial_calls(home) == 1


def test_cached_pass_and_failure_skip_trial_start(env):
    home, _, environ = env
    check(environ)
    check(environ)
    assert trial_calls(home) == 1

    (home / "mode").write_text("crash")
    touch_later(home / ".zshrc")
    assert "rc=1" in check(environ).stdout
    assert trial_calls(home) == 2
    again = check(environ)
    assert "rc=1" in again.stdout and "failed to start" in again.stderr
    assert trial_calls(home) == 2


@pytest.mark.parametrize(
    "watched",
    [
        ".zshrc",
        ".zsh/config/00_LOADER.zsh",
        ".zsh/plugins.txt",
        ".preferred-shell",
        "bin/zsh",
    ],
)
def test_watched_file_change_triggers_recheck(env, watched):
    home, bin_dir, environ = env
    check(environ)
    target = bin_dir / "zsh" if watched == "bin/zsh" else home / watched
    touch_later(target)
    check(environ)
    assert trial_calls(home) == 2


def test_removed_config_file_triggers_recheck(env):
    home, _, environ = env
    extra = home / ".zsh/config/09_extra.zsh"
    extra.write_text("")
    check(environ)
    time.sleep(0.05)
    extra.unlink()
    check(environ)
    assert trial_calls(home) == 2


def test_update_marker_and_reset(env):
    home, _, environ = env
    check(environ)
    (home / ".dotfiles-update-available").touch()
    check(environ)
    assert trial_calls(home) == 2
    result = check(environ, "zsh-recheck")
    assert "check passed" in result.stdout
    assert trial_calls(home) == 3


def run_bashrc(environ: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which("bash"), "--rcfile", str(BASHRC), "-i"],
        input="echo SHELL-STAYED-IN-BASH\n",
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )


def install_helper(home: Path):
    shutil.copy(HELPER, home / ".zsh/zsh-handoff-check.sh")


def test_bashrc_hands_off_when_healthy(env):
    home, _, environ = env
    install_helper(home)
    result = run_bashrc(environ)
    assert "STUB-ZSH-HANDOFF" in result.stdout
    assert "SHELL-STAYED-IN-BASH" not in result.stdout


def test_bashrc_stays_in_bash_when_unhealthy(env):
    home, _, environ = env
    install_helper(home)
    (home / "mode").write_text("plain")
    result = run_bashrc(environ)
    assert "STUB-ZSH-HANDOFF" not in result.stdout
    assert "SHELL-STAYED-IN-BASH" in result.stdout
    assert "zsh handoff skipped" in result.stderr


def test_bashrc_without_helper_still_hands_off(env):
    _, _, environ = env
    result = run_bashrc(environ)
    assert "STUB-ZSH-HANDOFF" in result.stdout


def test_bashrc_skips_check_for_nested_shell(env):
    home, _, environ = env
    install_helper(home)
    (home / "mode").write_text("plain")
    result = run_bashrc({**environ, "SHLVL": "1"})
    assert "zsh handoff skipped" not in result.stderr
    assert trial_calls(home) == 0


def test_bash_has_no_generic_update_hint(env):
    home, _, environ = env
    install_helper(home)
    (home / "mode").write_text("plain")
    (home / ".dotfiles-update-available").touch()
    assert "Hint: Dotfiles update available" not in run_bashrc(environ).stdout


STATE_SH = REPO / "home/core/.zsh/update-state.sh"


def write_state(home: Path, state: str, reason: str = "", revision: str = "r1") -> None:
    (home / ".dotfiles-update-state").write_text(
        f"state={state}\nreason={reason}\nrevision={revision}\n"
    )


def indicator(shell: str, home: Path, steps: str = "") -> str:
    """Start a shell (reads the state), apply `steps`, then evaluate the prompt segment."""
    script = (
        f'. "{STATE_SH}"; dotfiles_update_startup; {steps}\n'
        'dotfiles_update_prompt; echo "SEG=$DOTFILES_UPDATE_SEGMENT_KIND"'
    )
    result = subprocess.run(
        [shutil.which(shell), "-c", script],
        env={"HOME": str(home), "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def write_state_cmd(home: Path, state: str, revision: str) -> str:
    return (
        f"printf 'state={state}\\nreason=\\nrevision={revision}\\n' "
        f'> "{home}/.dotfiles-update-state"'
    )


SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]


@pytest.mark.parametrize("shell", SHELLS)
def test_indicator_states(shell, tmp_path):
    assert indicator(shell, tmp_path).strip() == "SEG="
    write_state(tmp_path, "none")
    assert indicator(shell, tmp_path).strip() == "SEG="
    write_state(tmp_path, "available")
    out = indicator(shell, tmp_path)
    assert "SEG=available" in out and "Dotfiles update" not in out
    write_state(tmp_path, "attention", "history has diverged")
    out = indicator(shell, tmp_path)
    assert "needs attention: history has diverged" in out
    assert "SEG=attention" in out


@pytest.mark.parametrize("shell", SHELLS)
def test_indicator_follows_state_in_open_shell(shell, tmp_path):
    write_state(tmp_path, "available", revision="r1")
    update = write_state_cmd(tmp_path, "updated", "r2")
    assert "SEG=reload" in indicator(shell, tmp_path, update)
    # a shell started after the update shows nothing
    write_state(tmp_path, "updated", revision="r2")
    assert indicator(shell, tmp_path).strip() == "SEG="
    back = write_state_cmd(tmp_path, "none", "r1")
    write_state(tmp_path, "attention", "x")
    assert "SEG=" in indicator(shell, tmp_path, back)
