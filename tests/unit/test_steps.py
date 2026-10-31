"""Setup and update steps: keep going after a failure, report every problem at the end."""

from __future__ import annotations

import subprocess
import sys

import pytest

from package_sets import REPO

sys.path.insert(0, str(REPO))

from machine_cli import steps  # noqa: E402
from machine_cli.core import die  # noqa: E402


def test_ok_step_is_recorded_and_nothing_reported():
    runner = steps.Steps()
    assert runner.run("dotfiles", lambda: None)
    assert runner.ok("dotfiles")
    assert runner.report("setup") is None


def test_failures_do_not_stop_later_steps():
    runner = steps.Steps()
    ran = []

    def failing():
        raise subprocess.CalledProcessError(1, ["bw", "sync"])

    assert not runner.run("env pull", failing)
    assert runner.run("ansible", lambda: ran.append("ansible"))
    assert ran == ["ansible"]
    assert runner.failed_names() == ["env pull"]
    assert "`bw sync` exited with 1" in runner.summary()


def test_die_inside_a_step_fails_only_that_step_with_its_message():
    runner = steps.Steps()
    assert not runner.run("tools", lambda: die("mise is not installed"))
    assert runner.summary() == "tools failed: mise is not installed"


def test_os_error_and_return_codes_count_as_failures():
    runner = steps.Steps()

    def broken():
        raise OSError("disk full")

    assert not runner.run("timers", broken)
    assert not runner.run("env pull", lambda: 1)
    assert runner.run("ssh", lambda: 0)
    assert runner.failed_names() == ["timers", "env pull"]


def test_step_is_skipped_when_a_step_it_needs_did_not_succeed():
    runner = steps.Steps()
    runner.run("dotfiles", lambda: die("mise dot apply failed"))
    ran = []
    assert not runner.run("tools", lambda: ran.append("tools"), needs=["dotfiles"])
    assert not runner.run("zsh check", lambda: ran.append("zsh"), needs=["tools"])
    assert ran == []
    assert runner.failed_names() == ["dotfiles"]
    assert "tools skipped: needs dotfiles, which failed" in runner.summary()
    assert "zsh check skipped: needs tools, which skipped" in runner.summary()


def test_a_step_that_was_not_run_does_not_block_the_steps_after_it():
    runner = steps.Steps()
    assert runner.run("tools", lambda: None, needs=["dotfiles"])


def test_ctrl_c_is_not_caught():
    runner = steps.Steps()

    def interrupted():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        runner.run("tools", interrupted)


def test_report_lists_every_problem_last(capsys):
    runner = steps.Steps()
    runner.run("env pull", lambda: 1)
    runner.fail("zsh check", "zsh prints an error")
    text = runner.report("update")
    assert text == "env pull failed: returned 1\nzsh check failed: zsh prints an error"
    out = capsys.readouterr().out
    assert out.index("update finished with problems") < out.index("env pull failed")
