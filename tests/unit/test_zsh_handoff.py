from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from package_sets import REPO

HELPER = REPO / "home/core/.shell/bash/zsh-health.bash"
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
    (home / ".shell/zsh").mkdir(parents=True)
    (home / ".shell/zsh/init.zsh").write_text("")
    (home / ".zshrc").write_text("")
    (home / "mode").write_text("ok")
    (home / ".shell/zsh/plugins.txt").write_text("")
    (home / ".shell/common").mkdir()
    (home / ".shell/work/common").mkdir(parents=True)
    (home / ".shell/work/zsh").mkdir(parents=True)
    (home / ".shell/bash").mkdir()
    shutil.copy(HELPER, home / ".shell/bash/zsh-health.bash")
    for path in (
        home / ".shell/common/environment.sh",
        home / ".shell/work/common/environment.sh",
        home / ".shell/work/zsh/ldap-helpers.zsh",
    ):
        path.write_text("")
    for name in (
        "aliases.sh",
        "environment.sh",
        "machine-profile.sh",
        "cache-eval.sh",
        "update-state.sh",
        "command-prefix.sh",
    ):
        if name in {"environment.sh", "readline.bash"}:
            continue
        (home / ".shell/common" / name).symlink_to(
            REPO / "home/core/.shell/common" / name
        )
    for name in (
        "init.bash",
        "options.bash",
        "history.bash",
        "tools.bash",
        "readline.bash",
        "prompt.bash",
        "handoff.bash",
    ):
        if name == "readline.bash":
            continue
        (home / ".shell/bash" / name).symlink_to(REPO / "home/core/.shell/bash" / name)
    shutil.copy(
        REPO / "home/core/.shell/bash/readline.bash",
        home / ".shell/bash/readline.bash",
    )
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
        home / ".shell/zsh/init.zsh",
        home / ".shell/zsh/plugins.txt",
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
    script = f'. "$HOME/.shell/bash/zsh-health.bash"; {snippet}; echo "rc=$?"'
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


def test_zsh_loader_ignores_unregistered_module(tmp_path: Path):
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is not installed")

    home = tmp_path / "zsh-home"
    shell_root = home / ".shell"
    plugin_module = REPO / "home/core/.shell/zsh/plugins.zsh"
    plugin_source = plugin_module.read_text()
    (shell_root / "common").mkdir(parents=True)
    shutil.copytree(
        REPO / "home/core/.shell/common", shell_root / "common", dirs_exist_ok=True
    )
    shutil.copytree(REPO / "home/core/.shell/zsh", shell_root / "zsh")
    shutil.copy(REPO / "home/core/.zshrc", home / ".zshrc")
    shutil.copy(REPO / "home/core/.zshenv", home / ".zshenv")
    (home / ".zshrc-local").write_text(
        '[[ $DOTFILES_ZSH_LOADED == 1 ]] && print -r -- local > "$HOME/local-order"\n'
    )
    (shell_root / "zsh/unregistered.zsh").write_text(
        'print -r -- ran > "$HOME/unregistered-module"\n'
    )

    antidote = home / ".local/share/antidote/mattmc3/antidote"
    antidote.mkdir(parents=True)
    (antidote / "antidote.zsh").write_text(
        "antidote() {\n"
        "  [[ $1 == bundle ]] || return 0\n"
        "  cat >/dev/null\n"
        "  print -r -- 'dotfiles_check_mode_defer\n"
        'run-compinit() { autoload -Uz compinit && compinit -u -d "$HOME/.cache/zcompdump"; }\n'
        "dotfiles_defer_init\n"
        "zsh-defer -dmpr dotfiles_deferred_done'\n"
        "}\n"
    )
    generated = home / ".cache/zsh/plugins.zsh"
    generated.parent.mkdir(parents=True)
    generated.write_text('source "$HOME/.zsh/config/old.zsh"\n')
    os.utime(generated, (1, 1))
    bin_dir = home / "bin"
    bin_dir.mkdir()
    machine = bin_dir / "machine"
    machine.write_text(
        '#!/bin/sh\nprintf called >> "$HOME/machine-completion-calls"\n'
        "printf '# machine completion test\\n'\n"
    )
    machine.chmod(0o755)
    result = subprocess.run(
        [
            zsh,
            "-i",
            "-c",
            'print -r -- "LOADED:$DOTFILES_ZSH_LOADED DEFERRED:$DOTFILES_ZSH_DEFERRED_LOADED"',
        ],
        env={
            **os.environ,
            "HOME": str(home),
            "ZDOTDIR": str(home),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "TERM": "xterm",
            "DOTFILES_ZSH_CHECK": "1",
        },
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "LOADED:1 DEFERRED:1" in result.stdout
    assert not (home / "unregistered-module").exists()
    assert (home / "local-order").read_text() == "local\n"
    assert (home / "machine-completion-calls").read_text() == "called"
    assert ".zsh/config" not in generated.read_text()
    assert "compinit" in generated.read_text()
    assert plugin_module.read_text() == plugin_source


def test_zsh_loader_starts_offline_and_registers_completion(tmp_path: Path):
    zsh = shutil.which("zsh")
    if not zsh:
        pytest.skip("zsh is not installed")

    home = tmp_path / "zsh-home"
    shell_root = home / ".shell"
    (shell_root / "common").mkdir(parents=True)
    shutil.copytree(
        REPO / "home/core/.shell/common", shell_root / "common", dirs_exist_ok=True
    )
    shutil.copytree(REPO / "home/core/.shell/zsh", shell_root / "zsh")
    shutil.copy(REPO / "home/core/.zshrc", home / ".zshrc")
    shutil.copy(REPO / "home/core/.zshenv", home / ".zshenv")
    cache = home / ".cache"
    cache.mkdir()
    bin_dir = home / "bin"
    bin_dir.mkdir()
    git = bin_dir / "git"
    git.write_text('#!/bin/sh\n[ "$1" = clone ] && exit 1\nexec /usr/bin/git "$@"\n')
    git.chmod(0o755)
    machine = bin_dir / "machine"
    machine.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/machine-calls"\n'
        "printf '# machine completion test\\n'\n"
    )
    machine.chmod(0o755)
    result = subprocess.run(
        [zsh, "-i", "-c", 'print -r -- "LOADED:$DOTFILES_ZSH_LOADED"'],
        env={
            **os.environ,
            "HOME": str(home),
            "ZDOTDIR": str(home),
            "XDG_CACHE_HOME": str(cache),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "TERM": "xterm",
        },
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "LOADED:1" in result.stdout
    assert (home / "machine-calls").read_text().splitlines() == ["completion zsh"]


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
    (home / ".shell/zsh/init.zsh").unlink()
    assert ".shell/zsh/init.zsh is missing" in check(environ).stderr
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
        ".shell/zsh/init.zsh",
        ".shell/zsh/plugins.txt",
        ".shell/bash/zsh-health.bash",
        ".shell/common/environment.sh",
        ".shell/work/common/environment.sh",
        ".shell/work/zsh/ldap-helpers.zsh",
        ".zshrc-local",
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
    extra = home / ".shell/zsh/extra.zsh"
    extra.write_text("")
    check(environ)
    time.sleep(0.05)
    extra.unlink()
    check(environ)
    assert trial_calls(home) == 2


def test_renamed_config_file_triggers_recheck(env):
    home, _, environ = env
    original = home / ".shell/zsh/extra.zsh"
    original.write_text("")
    check(environ)
    touch_later(original)
    original.rename(home / ".shell/zsh/renamed.zsh")
    check(environ)
    assert trial_calls(home) == 2


def test_bash_only_edit_does_not_invalidate_zsh_health(env):
    home, _, environ = env
    bash_only = home / ".shell/bash/readline.bash"
    bash_only.write_text("# bash-only editor configuration\n")
    check(environ)
    touch_later(bash_only)
    check(environ)
    assert trial_calls(home) == 1


def test_pending_update_flag_and_reset(env):
    home, _, environ = env
    check(environ)
    (home / ".dotfiles-update-state").write_text("state=available\npending=1\n")
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
    shutil.copy(HELPER, home / ".shell/bash/zsh-health.bash")


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
    (home / ".dotfiles-update-state").write_text("state=available\npending=1\n")
    assert "Hint: Dotfiles update available" not in run_bashrc(environ).stdout


def test_bash_loader_ignores_unregistered_modules_and_loads_local_last(env):
    home, _, environ = env
    (home / "mode").write_text("plain")
    modules = [
        (".shell/bash/handoff.bash", "handoff", "prefix"),
        (".shell/bash/init.bash", "init", "prefix"),
        (".shell/common/machine-profile.sh", "machine-profile", "suffix"),
        (".shell/common/cache-eval.sh", "cache-eval", "suffix"),
        (".shell/common/update-state.sh", "update-state", "suffix"),
        (".shell/bash/options.bash", "options", "suffix"),
        (".shell/bash/tools.bash", "tools", "suffix"),
        (".shell/common/environment.sh", "environment", "suffix"),
        (".shell/common/aliases.sh", "aliases", "suffix"),
        (".shell/bash/history.bash", "history", "suffix"),
        (".shell/bash/readline.bash", "readline", "suffix"),
        (".shell/bash/prompt.bash", "prompt", "suffix"),
    ]
    expected_order = []
    for relative, label, position in modules:
        target = home / relative
        if target.is_symlink():
            target.unlink()
        source = REPO / "home/core" / relative
        shutil.copy(source, target)
        marker = f'printf "{label}\\n" >> "$HOME/load-order"\n'
        target.write_text(
            marker + target.read_text()
            if position == "prefix"
            else target.read_text() + marker
        )
        expected_order.append(label)
    extra = home / ".shell/bash/unregistered.bash"
    extra.write_text('printf ran > "$HOME/unregistered-ran"\n')
    (home / ".bashrc-local").write_text('printf "local\\n" >> "$HOME/load-order"\n')
    result = run_bashrc(environ)
    assert result.returncode == 0
    assert not (home / "unregistered-ran").exists()
    expected_order.append("local")
    assert (home / "load-order").read_text().splitlines() == expected_order


STATE_SH = REPO / "home/core/.shell/common/update-state.sh"


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


def run_machine_function(
    shell: str, tmp_path: Path, exit_code: int, *args: str, tty: bool
):
    """Run the `machine` shell function with a fake CLI; `reload` is replaced by an echo."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "machine"
    fake.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    fake.chmod(0o755)
    script = (
        f'. "{STATE_SH}"; reload() {{ echo RELOADED; }}; machine {" ".join(args)}; '
        'echo "RC=$?"'
    )
    env = {"HOME": str(tmp_path), "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    argv = [shutil.which(shell), "-c", script]
    if not tty:
        out = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=30)
        return out.stdout
    import pty

    master, slave = pty.openpty()
    proc = subprocess.Popen(argv, env=env, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    proc.wait(timeout=30)
    data = b""
    try:
        while chunk := os.read(master, 4096):
            data += chunk
    except OSError:
        pass
    os.close(master)
    return data.decode()


@pytest.mark.parametrize("shell", SHELLS)
def test_machine_update_reloads_the_interactive_shell_only_on_success(shell, tmp_path):
    assert "RELOADED" in run_machine_function(shell, tmp_path, 0, "update", tty=True)
    assert "RELOADED" not in run_machine_function(
        shell, tmp_path, 1, "update", tty=True
    )
    assert "RELOADED" not in run_machine_function(
        shell, tmp_path, 0, "update", "--check", tty=True
    )
    assert "RELOADED" not in run_machine_function(
        shell, tmp_path, 0, "status", tty=True
    )
    out = run_machine_function(shell, tmp_path, 0, "update", tty=False)
    assert "RELOADED" not in out and "RC=0" in out


def disk_segment(shell: str, home: Path, steps: str = "") -> str:
    """Evaluate both segments with no PATH, so an external command would fail."""
    script = (
        f'. "{STATE_SH}"; dotfiles_update_startup; {steps}\n'
        "PATH=/nonexistent; dotfiles_update_prompt\n"
        'echo "UPD=$DOTFILES_UPDATE_SEGMENT_KIND"; echo "DISK=$DOTFILES_DISK_SEGMENT"'
    )
    result = subprocess.run(
        [shutil.which(shell), "-c", script],
        env={"HOME": str(home), "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "not found" not in result.stderr
    return result.stdout


def write_disk_state(home: Path, segment: str) -> Path:
    path = home / ".local/share/machine/disk-state"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"segment={segment}\nmounts=\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("shell", SHELLS)
def test_disk_segment(shell, tmp_path):
    # missing file: nothing
    assert "DISK=\n" in disk_segment(shell, tmp_path)
    write_disk_state(tmp_path, "⚠ disk /mnt/data 97%")
    out = disk_segment(shell, tmp_path)
    assert "DISK=⚠ disk /mnt/data 97%" in out and "UPD=\n" in out
    # nothing printed at shell start for a low disk
    assert out.splitlines()[0].startswith("UPD=")
    # both segments together
    write_state(tmp_path, "available")
    out = disk_segment(shell, tmp_path)
    assert "UPD=available" in out and "DISK=⚠ disk /mnt/data 97%" in out
    # empty state: nothing
    write_disk_state(tmp_path, "")
    assert "DISK=\n" in disk_segment(shell, tmp_path)


@pytest.mark.parametrize("shell", SHELLS)
def test_disk_segment_follows_state_in_open_shell(shell, tmp_path):
    path = write_disk_state(tmp_path, "⚠ disk / 98%")
    freed = f"printf 'segment=\\nmounts=\\n' > \"{path}\""
    assert "DISK=\n" in disk_segment(shell, tmp_path, freed)


def test_prompts_show_the_disk_segment():
    starship = (REPO / "home/prompt/.config/starship.toml").read_text(encoding="utf-8")
    assert "${env_var.DOTFILES_DISK_SEGMENT}" in starship
    assert "[env_var.DOTFILES_DISK_SEGMENT]" in starship
    zsh_prompt = (REPO / "home/core/.shell/zsh/prompt.zsh").read_text(encoding="utf-8")
    assert "DOTFILES_DISK_SEGMENT" in zsh_prompt
    bash_prompt = (REPO / "home/core/.shell/bash/prompt.bash").read_text(
        encoding="utf-8"
    )
    assert "${DOTFILES_DISK_SEGMENT:+$DOTFILES_DISK_SEGMENT }" in bash_prompt
