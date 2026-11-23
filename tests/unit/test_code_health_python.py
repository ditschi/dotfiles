"""Python metrics of the code health checker."""

import textwrap

import pytest

from code_health import python_metrics
from code_health.model import SourceFile


def functions(source: str, is_test: bool = False) -> dict:
    metrics = python_metrics.analyse(
        SourceFile("x.py", textwrap.dedent(source), is_test)
    )
    return {function.name: function for function in metrics.functions}


def only(source: str):
    (function,) = functions(source).values()
    return function


@pytest.mark.parametrize(
    "body, expected",
    [
        ("return 1", 1),
        ("if a:\n        return 1", 2),
        ("if a and b or c:\n        return 1", 4),
        ("for x in y:\n        pass\n    while a:\n        pass", 3),
        (
            "try:\n        pass\n    except A:\n        pass\n    except B:\n        pass",
            3,
        ),
        ("return [x for x in y if x]", 3),
        ("return a if b else c", 2),
    ],
)
def test_cyclomatic_complexity(body, expected):
    assert only(f"def f(a, b, c, y):\n    {body}\n").cyclomatic == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ("def f(a):\n    if a:\n        if a:\n            return 1\n", 3),
        (
            "def f(a):\n    if a:\n        pass\n    elif a:\n        pass\n    else:\n        pass\n",
            3,
        ),
        ("def f(a, b, c):\n    return a and b and c\n", 1),
        ("def f(a, b, c):\n    return a and b or c\n", 2),
        (
            "def f(y):\n    for x in y:\n        try:\n            pass\n        except E:\n            pass\n",
            3,
        ),
    ],
)
def test_cognitive_complexity(source, expected):
    assert only(source).cognitive == expected


def test_elif_stays_on_the_level_of_its_if():
    source = """
    def f(a):
        if a:
            pass
        elif a:
            pass
        elif a:
            if a:
                pass
    """
    assert only(source).nesting == 2


def test_nesting_counts_control_structures_only():
    source = """
    def f(a):
        with a:
            for x in a:
                while x:
                    try:
                        if x:
                            pass
                    except E:
                        pass
    """
    assert only(source).nesting == 4


def test_bumps_are_separate_nested_chunks():
    source = """
    def f(a):
        if a:
            if a:
                pass
        x = 1
        for y in a:
            if y:
                pass
        if a:
            pass
    """
    assert only(source).bumps == [2, 2]


def test_conditionals_count_and_or_operators_per_branch():
    source = """
    def f(a, b, c):
        if a and b and c:
            pass
        while a or b:
            pass
        return a and b
    """
    assert only(source).conditionals == [(3, 2), (5, 1)]


def test_arguments_without_self_and_with_primitive_annotations():
    source = """
    class C:
        def m(self, a: str, b: int | None, c: Path, d, *rest, e: bool = True):
            pass

        @staticmethod
        def s(self, a):
            pass
    """
    found = functions(source)
    method = found["C.m"]
    assert (
        method.arguments,
        method.annotated_arguments,
        method.primitive_arguments,
    ) == (5, 4, 3)
    assert found["C.s"].arguments == 2


def test_lines_of_code_skip_comments_blank_lines_and_docstrings():
    source = '''
    def f():
        """Doc.

        More doc.
        """
        # comment

        return 1
    '''
    assert only(source).loc == 2


def test_nested_functions_are_separate_and_not_in_outer_tokens():
    source = """
    def outer(a):
        def inner(b):
            return b + 1
        return inner(a)
    """
    found = functions(source)
    assert set(found) == {"outer", "outer.inner"}
    assert "+" not in found["outer"].tokens


def test_literals_are_normalised_in_tokens():
    assert only("def f():\n    return g('x', 2)\n").tokens == [
        "return",
        "g",
        "(",
        "<str>",
        ",",
        "<num>",
        ")",
    ]


def cohesion(source: str) -> int:
    (cls,) = python_metrics.analyse(
        SourceFile("x.py", textwrap.dedent(source), False)
    ).classes
    return cls.cohesion_components


def test_cohesion_of_connected_methods():
    source = """
    class C:
        def a(self):
            return self.x
        def b(self):
            self.x = 1
        def c(self):
            return self.a()
    """
    assert cohesion(source) == 1


def test_cohesion_of_unrelated_methods():
    source = """
    class C:
        def a(self):
            return self.x
        def b(self):
            return self.y
    """
    assert cohesion(source) == 2


def test_assertion_blocks_only_in_tests():
    source = """
    def test_x(a):
        assert a
        assert a
        a.call()
        assert a
    """
    blocks = python_metrics.analyse(
        SourceFile("t.py", textwrap.dedent(source), True)
    ).assertion_blocks
    assert [(b.line, len(b.statements)) for b in blocks] == [(3, 2), (6, 1)]
    assert not python_metrics.analyse(
        SourceFile("t.py", textwrap.dedent(source), False)
    ).assertion_blocks


def test_suppression_comments_are_collected():
    source = (
        "def f():  # code-health: ignore[complex-method] generated table\n    pass\n"
    )
    metrics = python_metrics.analyse(SourceFile("x.py", source, False))
    assert metrics.suppressions == {1: {"complex-method": "generated table"}}
