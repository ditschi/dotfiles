from __future__ import annotations

import errno
import os
import pty
import select
import signal
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from package_sets import REPO

HELPER = REPO / "home/core/.shell/common/command-prefix.sh"
SHELLS = [shell for shell in ("bash", "zsh") if shutil.which(shell)]


def match_prefix(shell: str, line: str) -> str:
    result = subprocess.run(
        [
            shell,
            "-c",
            'source "$1"; dotfiles_command_prefix "$2"; '
            'printf "%s" "$DOTFILES_COMMAND_PREFIX_SUGGESTION"',
            "prefix-test",
            str(HELPER),
            line,
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    assert result.stderr == ""
    return result.stdout


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("git git status", "git status"),
        ("git remote git remote -v", "git remote -v"),
        ("in the in the command", "in the command"),
        ("git git git git status", "git git status"),
        ("  git\tgit  status  ", "git  status  "),
        ("git remote\tgit  remote   -v", "git  remote   -v"),
        ("git git", "git"),
        ("git status", ""),
        ("echo git git status", ""),
        ("gi git status", ""),
        ("", ""),
        ("   ", ""),
    ],
)
def test_literal_prefix(shell: str, line: str, expected: str):
    assert match_prefix(shell, line) == expected


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize(
    "suffix",
    [
        "'quoted'",
        '"quoted"',
        r"escaped\ word",
        "$HOME",
        "${HOME}",
        "$(touch MARKER)",
        "`touch MARKER`",
        "; touch MARKER",
        "&& touch MARKER",
        "|| touch MARKER",
        "| touch MARKER",
        "> MARKER",
        "< MARKER",
        "\ntouch MARKER",
        "*",
        "?",
        "[abc]",
        "{a,b}",
        "~",
        "# comment",
        "!history",
        "NAME=value",
    ],
)
def test_reject_shell_syntax(shell: str, suffix: str, tmp_path: Path):
    marker = tmp_path / "must-not-exist"
    assert match_prefix(shell, "git git " + suffix.replace("MARKER", str(marker))) == ""
    assert not marker.exists()


class ShellSession:
    def __init__(self, shell: str, home: Path):
        self.home = home
        self.calls = home / "calls"
        self.buffer = b""
        self.pid, self.terminal = pty.fork()
        if self.pid == 0:
            environment = {
                "HOME": str(home),
                "ZDOTDIR": str(home),
                "PATH": "/usr/bin:/bin",
                "TERM": "xterm",
                "LC_ALL": "C.UTF-8",
                "CALLS": str(self.calls),
                "SHLVL": "2",
            }
            arguments = [shell, "-dfi"] if shell == "zsh" else [shell, "--norc", "-i"]
            os.execve(shutil.which(shell), arguments, environment)

    def send(self, value: str):
        os.write(self.terminal, value.encode())

    def until(self, text: str) -> str:
        expected = text.encode()
        deadline = time.monotonic() + 5
        while expected not in self.buffer:
            remaining = deadline - time.monotonic()
            assert remaining > 0, self.buffer.decode(errors="replace")
            readable, _, _ = select.select([self.terminal], [], [], remaining)
            assert readable, self.buffer.decode(errors="replace")
            try:
                self.buffer += os.read(self.terminal, 65536)
            except OSError as error:
                if error.errno == errno.EIO:
                    pytest.fail(self.buffer.decode(errors="replace"))
                raise
        position = self.buffer.index(expected) + len(expected)
        output, self.buffer = self.buffer[:position], self.buffer[position:]
        return output.decode(errors="replace")

    def close(self):
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0)
        os.close(self.terminal)


@pytest.fixture(params=["fallback", "starship"])
def zsh_session(request, tmp_path: Path):
    if not shutil.which("zsh"):
        pytest.skip("zsh is not installed")
    tmp_path = tmp_path / "zsh-home"
    tmp_path.mkdir()
    (tmp_path / ".shell").symlink_to(REPO / "home/core/.shell")
    prompt_setup = ""
    if request.param == "starship":
        starship = shutil.which("starship")
        if not starship:
            pytest.skip("Starship is not installed")
        initializer = subprocess.run(
            [starship, "init", "zsh", "--print-full-init"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        (tmp_path / "starship-init.zsh").write_text(initializer.stdout)
        prompt_setup = (
            'source "$HOME/starship-init.zsh"; '
            '_test_prompt() { PROMPT="READY:${STARSHIP_CMD_STATUS:-0} "; }; '
            "precmd_functions+=(_test_prompt); "
        )
    session = ShellSession("zsh", tmp_path)
    request.addfinalizer(session.close)
    setup = (
        "unsetopt correct correctall; bindkey -e; HISTFILE=$HOME/history; HISTSIZE=100; "
        "SAVEHIST=100; "
        'probe() { printf "%s\\n" "$*" >> "$CALLS"; '
        'case "$*" in "probe "* | "remote probe "*) return 7;; esac; }; '
        + prompt_setup
        + 'source "$HOME/.shell/zsh/keybindings.zsh"; '
        "PROMPT='READY:%? '; RPROMPT=''; printf '\\nSETUP_DONE\\n'\n"
    )
    session.send(setup)
    session.until("\r\nSETUP_DONE\r\n")
    session.until("READY:0 ")
    yield session


@pytest.fixture(
    params=[
        ("emacs", "fallback"),
        ("vi", "fallback"),
        ("emacs", "starship"),
        ("vi", "starship"),
    ]
)
def bash_session(request, tmp_path: Path):
    if not shutil.which("bash"):
        pytest.skip("bash is not installed")
    tmp_path = tmp_path / "bash-home"
    tmp_path.mkdir()
    (tmp_path / ".shell").symlink_to(REPO / "home/core/.shell")
    (tmp_path / ".preferred-shell").write_text("bash")
    editing_mode, prompt = request.param
    if prompt == "starship":
        starship = shutil.which("starship")
        if not starship:
            pytest.skip("Starship is not installed")
        (tmp_path / ".local/bin").mkdir(parents=True)
        (tmp_path / ".local/bin/starship").symlink_to(starship)
    session = ShellSession("bash", tmp_path)
    request.addfinalizer(session.close)
    prompt_setup = "PS1='READY:${_dotfiles_prefix_status:-0} '; "
    if prompt == "starship":
        prompt_setup = (
            "_test_prompt() { starship_precmd; PS1='READY:${STARSHIP_CMD_STATUS:-0} '; }; "
            "PROMPT_COMMAND=_test_prompt; "
        )
    setup = (
        f"set -o {editing_mode}; "
        f'source "{REPO / "home/core/.bashrc"}"; '
        "HISTFILE=$HOME/history; HISTSIZE=100; HISTCONTROL=''; "
        'probe() { printf "%s\\n" "$*" >> "$CALLS"; '
        'case "$*" in "probe "* | "remote probe "*) return 7;; esac; }; '
        + prompt_setup
        + "printf '\\nSETUP_DONE\\n'\n"
    )
    session.send(setup)
    session.until("\r\nSETUP_DONE\r\n")
    session.until("READY:0 ")
    yield session


@pytest.mark.parametrize(
    ("command", "suggestion", "first_call", "second_call"),
    [
        ("probe probe argument", "probe argument", "probe argument", "argument"),
        (
            "probe remote probe remote argument",
            "probe remote argument",
            "remote probe remote argument",
            "remote argument",
        ),
    ],
)
def test_zsh_offers_without_executing(
    zsh_session, command, suggestion, first_call, second_call
):
    session = zsh_session
    session.send(command + "\r")
    session.until("READY:7 ")
    session.until(suggestion)
    assert session.calls.read_text().splitlines() == [first_call]
    session.send("\r")
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == [first_call, second_call]


def test_zsh_suggestion_can_be_edited(zsh_session):
    session = zsh_session
    session.send("probe probe argument\r")
    session.until("READY:7 ")
    session.until("probe argument")
    session.send("-edited\r")
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == [
        "probe argument",
        "argument-edited",
    ]


def test_zsh_success_and_cancellation(zsh_session):
    session = zsh_session
    session.send("true true argument\r")
    session.until("READY:0 ")
    session.send("probe clean\r")
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == ["clean"]
    session.send("probe probe argument\r")
    session.until("READY:7 ")
    session.until("probe argument")
    session.send("\x03")
    session.until("\x1b[?2004h")
    session.send("probe after-cancel\r")
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == [
        "clean",
        "probe argument",
        "after-cancel",
    ]


@pytest.mark.parametrize("accept", ["\r", "\n"])
@pytest.mark.parametrize(
    ("command", "suggestion", "first_call", "second_call"),
    [
        ("probe probe argument", "probe argument", "probe argument", "argument"),
        (
            "probe remote probe remote argument",
            "probe remote argument",
            "remote probe remote argument",
            "remote argument",
        ),
    ],
)
def test_bash_offers_without_executing(
    bash_session, accept, command, suggestion, first_call, second_call
):
    session = bash_session
    session.send(command + accept)
    session.until("READY:7 ")
    session.until(suggestion)
    assert session.calls.read_text().splitlines() == [first_call]
    session.send(accept)
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == [first_call, second_call]


def test_bash_success_edit_and_cancel(bash_session):
    session = bash_session
    session.send("true true argument\r")
    session.until("READY:0 ")
    session.send("probe clean\r")
    session.until("READY:0 ")
    session.send("probe probe argument\r")
    session.until("READY:7 ")
    session.until("probe argument")
    session.send("-edited\r")
    session.until("READY:0 ")
    session.send("probe probe cancelled\r")
    session.until("READY:7 ")
    session.until("probe cancelled")
    session.send("\x03")
    session.until("\x1b[?2004h")
    session.send("probe after-cancel\r")
    session.until("READY:0 ")
    assert session.calls.read_text().splitlines() == [
        "clean",
        "probe argument",
        "argument-edited",
        "probe cancelled",
        "after-cancel",
    ]


def test_queued_input_is_not_replaced(zsh_session, bash_session):
    for session in (zsh_session, bash_session):
        session.send("probe probe argument\rprobe queued\r")
        session.until("READY:7 ")
        session.until("READY:0 ")
        assert session.calls.read_text().splitlines() == ["probe argument", "queued"]


def test_original_history_and_no_stale_suggestion(zsh_session, bash_session):
    for session in (zsh_session, bash_session):
        session.send("probe probe argument\r")
        session.until("READY:7 ")
        session.until("probe argument")
        session.send("\x03")
        session.until("\x1b[?2004h")
        session.send('fc -ln -10 > "$HOME/history-copy"\r')
        session.until("READY:0 ")
        history = (session.home / "history-copy").read_text().splitlines()
        assert "probe probe argument" in [line.strip() for line in history]
        assert "probe argument" not in [line.strip() for line in history]
        session.send("false\r")
        session.until("READY:1 ")
        session.send("probe fresh\r")
        session.until("READY:0 ")
        assert session.calls.read_text().splitlines() == ["probe argument", "fresh"]


@pytest.mark.parametrize("shell", SHELLS)
def test_noninteractive_has_no_recovery_hooks(shell: str, tmp_path: Path):
    (tmp_path / ".shell").symlink_to(REPO / "home/core/.shell")
    config = (
        REPO / "home/core/.bashrc"
        if shell == "bash"
        else REPO / "home/core/.shell/zsh/keybindings.zsh"
    )
    result = subprocess.run(
        [
            shell,
            "-c",
            'source "$1"; typeset -f _dotfiles_prefix_precmd',
            "test",
            str(config),
        ],
        env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        timeout=5,
    )
    assert result.stdout == ""
    assert result.returncode == 1


def test_existing_paste_and_sudo_helpers(zsh_session, bash_session):
    for session in (zsh_session, bash_session):
        for prompt_character in ("$", "❯"):
            session.send(f"{prompt_character} probe pasted\r")
            session.until("READY:0 ")
        session.send("probe toggle-sudo\x1b\x1b\x1b\x1b\r")
        session.until("\r\n")
        session.until("READY:0 ")
        session.send("printf '\\nHELPER_DONE\\n'\r")
        session.until("\r\nHELPER_DONE\r\n")
        assert session.calls.read_text().splitlines() == [
            "pasted",
            "pasted",
            "toggle-sudo",
        ]


def test_existing_editor_text_is_preserved(zsh_session, bash_session):
    for session, editor_variable, callback in (
        (zsh_session, "BUFFER", "_dotfiles_prefix_line_init"),
        (bash_session, "READLINE_LINE", "_dotfiles_prefix_insert"),
    ):
        session.send(
            f"{editor_variable}='probe existing'; _dotfiles_prefix_pending='probe replacement'; "
            f'{callback}; printf "\\nEDITOR:%s:PENDING:%s\\n" "${editor_variable}" '
            '"$_dotfiles_prefix_pending"\r'
        )
        session.until("\r\nEDITOR:probe existing:PENDING:\r\n")


@pytest.mark.parametrize("command", ["git git status", "git remote git remote -v"])
def test_documented_git_examples(zsh_session, bash_session, command):
    for session in (zsh_session, bash_session):
        subprocess.run(["git", "init", "-q", str(session.home)], check=True, timeout=5)
        session.send('cd "$HOME"\r')
        session.until("READY:0 ")
        session.send(command + "\r")
        session.until("READY:")
        suggestion = "git status" if command == "git git status" else "git remote -v"
        session.until(suggestion)
        session.send("\r")
        session.until("READY:0 ")
