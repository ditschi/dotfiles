from __future__ import annotations

import pytest
import testinfra

from conftest import TEST_HOSTS, host_env, run_checked, running_container
from test_profile_containers import ANTIDOTE_STUB, BASH_TTY_NOISE, STUB_ENV

JOB_STUB = (
    "env -u DOTFILES_REPO bash -c "
    '\'exec() { printf "%s|%s\\n" "$repo" "$*"; exit 0; }; '
    '. "$HOME/.local/bin/dotfiles-update-check-job"\''
)


@pytest.fixture
def checkout_elsewhere(docker_image):
    """Bootstrap from /dotfiles without DOTFILES_REPO, next to a stale ~/dotfiles."""
    context, device, hardware = TEST_HOSTS["container"]
    with running_container(
        docker_image,
        "checkout-elsewhere",
        env=("MACHINE_SKIP_TOOLS=1", *host_env(context, device, hardware)),
        set_repo_env=False,
    ) as (container, exec_cmd):
        run_checked(
            exec_cmd,
            ["sh", "-c", "mkdir -p ~/dotfiles/home && git init -q ~/dotfiles"],
            "stale clone",
        )
        run_checked(
            exec_cmd,
            [
                "./bootstrap",
                "--device",
                device,
                "--yes",
                "--skip-ansible",
                "--no-become",
            ],
            "bootstrap from /dotfiles",
        )
        yield testinfra.get_host(f"docker://{container}")


@pytest.mark.docker
def test_checkout_outside_home_dotfiles_is_live(checkout_elsewhere):
    host = checkout_elsewhere
    assert host.run("printenv DOTFILES_REPO").rc != 0

    repo = host.run("~/.local/bin/machine repo")
    assert repo.rc == 0, repo.stderr
    assert repo.stdout == "/dotfiles\n"

    status = host.run("~/.local/bin/machine status")
    assert status.rc == 0, status.stderr
    assert "/dotfiles · " in status.stdout
    assert "DOTFILES_REPO" not in status.stderr

    job = host.run(JOB_STUB)
    assert job.rc == 0, job.stderr
    assert job.stdout == "/dotfiles|/home/tester/.local/bin/machine update --auto\n"


@pytest.mark.docker
def test_shells_use_the_linked_checkout(checkout_elsewhere):
    host = checkout_elsewhere
    host.run_test(ANTIDOTE_STUB)

    zsh = host.run(f"{STUB_ENV} TERM=xterm zsh -i -c 'print -r -- \"$DOTFILES_REPO\"'")
    assert zsh.rc == 0, zsh.stderr
    assert zsh.stderr == "", f"zsh startup wrote to stderr:\n{zsh.stderr}"
    assert zsh.stdout.strip().splitlines()[-1] == "/dotfiles"

    bash = host.run("TERM=xterm bash -i -c 'echo \"$DOTFILES_REPO\"'")
    assert bash.rc == 0, bash.stderr
    errors = [
        line
        for line in bash.stderr.splitlines()
        if not any(noise in line for noise in BASH_TTY_NOISE)
    ]
    assert errors == [], "bash startup wrote to stderr:\n" + "\n".join(errors)
    assert bash.stdout.strip().splitlines()[-1] == "/dotfiles"
