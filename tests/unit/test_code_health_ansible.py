"""Ansible metrics of the code health checker."""

import textwrap

import pytest

from code_health import ansible_metrics
from code_health.model import SourceFile

TASKS = """
- name: Plain task
  ansible.builtin.debug:
    msg: hi
  when: a and b or c

- name: Outer block
  when:
    - a
    - b or c
  block:
    - name: Inner block
      block:
        - name: Deep task
          ansible.builtin.command: "true"
          changed_when: false
      rescue:
        - name: Rescue task
          ansible.builtin.debug:
            msg: failed
"""


def analyse(source: str, path: str = "roles/r/tasks/main.yml"):
    return ansible_metrics.analyse(SourceFile(path, textwrap.dedent(source).lstrip()))


def by_name(metrics) -> dict:
    return {function.name: function for function in metrics.functions}


def test_tasks_blocks_and_size():
    metrics = analyse(TASKS)
    assert list(by_name(metrics)) == [
        "Plain task",
        "Outer block",
        "Inner block",
        "Deep task",
        "Rescue task",
    ]
    assert (metrics.units, metrics.unit, metrics.has_logic) == (3, "tasks", True)


def test_block_nesting_depth():
    found = by_name(analyse(TASKS))
    nesting = {
        name: found[name].nesting
        for name in ("Outer block", "Inner block", "Deep task")
    }
    assert nesting == {"Outer block": 2, "Inner block": 1, "Deep task": 0}


def test_conditions_count_operators_and_list_items():
    found = by_name(analyse(TASKS))
    assert found["Plain task"].conditionals == [(4, 2)]
    assert found["Outer block"].conditionals == [(8, 2)]


def test_tasks_inside_plays():
    source = """
    - name: Play
      hosts: all
      tasks:
        - name: One
          ansible.builtin.debug:
            msg: one
      handlers:
        - name: Two
          ansible.builtin.debug:
            msg: two
    - ansible.builtin.import_playbook: other.yml
    """
    metrics = analyse(source, "site.yml")
    assert list(by_name(metrics)) == ["One", "Two"]


def test_duplicate_tasks_have_equal_tokens_without_names():
    source = """
    - name: First
      ansible.builtin.setup:
        gather_subset: [hardware]
    - name: Second
      ansible.builtin.setup:
        gather_subset: [hardware]
    """
    first, second = analyse(source).functions
    assert first.tokens == second.tokens != []


def test_template_counts_jinja_control_tags():
    source = (
        "{% if a %}x{%- elif b %}y{% endif %}\n{% for i in l %}{{ i }}{% endfor %}\n"
    )
    metrics = analyse(source, "roles/r/templates/t.j2")
    assert metrics.functions[0].cyclomatic == 4
    assert analyse("plain {{ value }}\n", "roles/r/templates/t.j2").has_logic is False


def test_invalid_yaml_is_a_syntax_error():
    with pytest.raises(SyntaxError):
        analyse("- name: [unclosed\n")
