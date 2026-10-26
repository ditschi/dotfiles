"""Tasks that read `apt-cache policy` run it in the C locale.

apt-cache translates "Candidate:" (German: "Installationskandidat:"), and the checks
after these tasks look for the English words.
"""

from __future__ import annotations

import yaml

from package_sets import ANSIBLE


def _tasks(node):
    """Every task mapping in a parsed playbook or task file, nested blocks included."""
    if isinstance(node, list):
        for item in node:
            yield from _tasks(item)
    elif isinstance(node, dict):
        yield node
        for key in (
            "tasks",
            "pre_tasks",
            "post_tasks",
            "handlers",
            "block",
            "rescue",
            "always",
        ):
            yield from _tasks(node.get(key))


def test_every_apt_cache_policy_task_sets_the_c_locale():
    files = [
        *ANSIBLE.glob("*.yml"),
        *ANSIBLE.glob("roles/*/tasks/*.yml"),
        *ANSIBLE.glob("tasks/*.yml"),
    ]
    found = []
    for path in files:
        for task in _tasks(yaml.safe_load(path.read_text(encoding="utf-8"))):
            command = task.get("ansible.builtin.command") or task.get("command") or ""
            if "apt-cache policy" in str(command):
                found.append((path.name, task.get("name")))
                assert (task.get("environment") or {}).get("LC_ALL") == "C", (
                    path,
                    task.get("name"),
                )
    assert ("workstation.yml", "Look up the Docker package candidate") in found
