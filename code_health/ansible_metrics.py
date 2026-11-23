"""Raw metrics of Ansible task files, playbooks and Jinja templates.

Each task is one unit (like a function): its `when`-style conditions, the depth of the
`block` nesting below it, and its content for duplicate detection. A file's size is its
number of tasks. Templates count their Jinja `if`/`elif`/`for` tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from .model import FileMetrics, FunctionMetrics, SourceFile

PLAY_KEYS = {"pre_tasks", "tasks", "post_tasks", "handlers"}
BLOCK_KEYS = {"block", "rescue", "always"}
CONDITION_KEYS = ("when", "failed_when", "changed_when", "until")
JINJA_CONTROL = re.compile(r"\{%-?\s*(if|elif|for)\b")
OPERATORS = re.compile(r"\s(and|or)\s")


@dataclass
class _Task:
    metrics: FunctionMetrics
    is_block: bool


def analyse(source: SourceFile) -> FileMetrics:
    if source.path.endswith(".j2"):
        return _template(source)
    tasks = [task for node in _task_lists(_compose(source)) for task in _walk(node)]
    return FileMetrics(
        path=source.path,
        language="ansible",
        loc=_code_lines(source.text),
        functions=[task.metrics for task in tasks],
        has_logic=bool(tasks),
        units=sum(not task.is_block for task in tasks),
        unit="tasks",
    )


def _compose(source: SourceFile):
    try:
        return yaml.compose(source.text)
    except yaml.YAMLError as error:
        raise SyntaxError(str(error)) from error


def _code_lines(text: str) -> int:
    stripped = [line.strip() for line in text.splitlines()]
    return len([line for line in stripped if line[:1] not in ("", "#")])


def _task_lists(root) -> list:
    """Sequence nodes that hold tasks: the file itself, or the task sections of its plays."""
    items = root.value if isinstance(root, yaml.SequenceNode) else []
    plays = list(filter(_is_play, items))
    if plays:
        return [section for play in plays for section in _sections(play)]
    return [root] if items else []


def _is_play(node) -> bool:
    return bool(_keys(node) & {"hosts", "import_playbook"})


def _sections(play) -> list:
    return [value for key, value in _items(play) if key in PLAY_KEYS]


def _items(node) -> list:
    pairs = node.value if isinstance(node, yaml.MappingNode) else []
    return [(key.value, value) for key, value in pairs]


def _keys(node) -> set[str]:
    return {key for key, _ in _items(node)}


def _walk(sequence) -> list[_Task]:
    tasks = []
    for node in getattr(sequence, "value", []):
        children = [child for key, child in _items(node) if key in BLOCK_KEYS]
        nested = [task for child in children for task in _walk(child)]
        tasks += [_task(node, nested, is_block=bool(children)), *nested]
    return tasks


def _task(node, nested: list[_Task], is_block: bool) -> _Task:
    items = dict(_items(node))
    metrics = FunctionMetrics(
        name=str(getattr(items.get("name"), "value", "<unnamed task>")),
        line=node.start_mark.line + 1,
        loc=node.end_mark.line - node.start_mark.line,
        nesting=_block_depth(nested) if is_block else 0,
        conditionals=[_condition(items[key]) for key in CONDITION_KEYS if key in items],
        tokens=[] if is_block else _tokens(node, skip="name"),
    )
    metrics.conditionals = [entry for entry in metrics.conditionals if entry[1]]
    return _Task(metrics, is_block)


def _block_depth(nested: list[_Task]) -> int:
    return 1 + max(
        (task.metrics.nesting for task in nested if task.is_block), default=0
    )


def _condition(node) -> tuple[int, int]:
    """(line, operators): `and`/`or` in the texts, plus the implicit `and` of a list."""
    parts = node.value if isinstance(node, yaml.SequenceNode) else [node]
    texts = [str(part.value) for part in parts if isinstance(part, yaml.ScalarNode)]
    operators = len(texts) - 1 + sum(len(OPERATORS.findall(text)) for text in texts)
    return node.start_mark.line + 1, operators


def _tokens(node, skip: str = "") -> list[str]:
    """The node's keys and values in order, without the key `skip` at the top."""
    if isinstance(node, yaml.ScalarNode):
        return [str(node.value)]
    children = node.value if isinstance(node, yaml.SequenceNode) else []
    return _flatten(map(_tokens, children)) + _mapping_tokens(node, skip)


def _mapping_tokens(node, skip: str) -> list[str]:
    pairs = [(key, value) for key, value in _items(node) if key != skip]
    return _flatten([f"{key}:", *_tokens(value)] for key, value in pairs)


def _flatten(lists) -> list[str]:
    return [token for tokens in lists for token in tokens]


def _template(source: SourceFile) -> FileMetrics:
    tags = len(JINJA_CONTROL.findall(source.text))
    loc = _code_lines(source.text)
    template = FunctionMetrics(
        name="<template>", line=1, loc=loc, cyclomatic=1 + tags, top_level=True
    )
    return FileMetrics(
        path=source.path,
        language="ansible",
        loc=loc,
        functions=[template],
        has_logic=tags > 0,
        units=0,
        unit="tasks",
    )
