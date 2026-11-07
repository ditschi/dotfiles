"""Run a command in a pseudo-terminal and type a password at sudo's prompt.

Usage: type_password_once.py PASSWORD_FILE COMMAND [ARG...]

Echoes the command's output, answers every password prompt with the password from
PASSWORD_FILE, and fails unless exactly one prompt appeared: a local `machine` run
authenticates once and then runs Ansible as root.
"""

from __future__ import annotations

import os
import pty
import re
import sys

PROMPT = re.compile(rb"(?i)(password|passwort)[^\n]*: ?$")


def main() -> int:
    with open(sys.argv[1], encoding="utf-8") as handle:
        password = handle.read().strip()
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(sys.argv[2], sys.argv[2:])
    tail, prompts = b"", 0
    while True:
        try:
            chunk = os.read(fd, 4096)
        except OSError:  # EIO once the child has closed the terminal
            break
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()
        tail = (tail + chunk)[-200:]
        if PROMPT.search(tail):
            prompts += 1
            os.write(fd, password.encode() + b"\n")
            tail = b""
    status = os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])
    print(f"\nsudo prompts: {prompts}")
    if status:
        return status
    return 0 if prompts == 1 else 3


if __name__ == "__main__":
    sys.exit(main())
