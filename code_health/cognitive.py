"""Cognitive complexity after SonarSource, on the Python `ast`."""

from __future__ import annotations

import ast

DEFINITION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def mark_elifs(tree: ast.AST) -> None:
    """Flag every `if` that is the `elif` of another one, so it keeps its parent's level."""
    for node in ast.walk(tree):
        orelse = node.orelse if isinstance(node, ast.If) else []
        if len(orelse) == 1 and isinstance(orelse[0], ast.If):
            orelse[0].is_elif = True


def is_elif(node: ast.AST) -> bool:
    return getattr(node, "is_elif", False)


class Cognitive:
    """Cognitive complexity after SonarSource: +1 per break in the flow, +nesting when nested."""

    def __init__(self):
        self.nesting = 0

    def measure(self, nodes: list[ast.AST]) -> int:
        return sum(map(self.node, nodes))

    def nested(self, nodes: list[ast.AST]) -> int:
        self.nesting += 1
        score = self.measure(nodes)
        self.nesting -= 1
        return score

    def structure(self) -> int:
        return 1 + self.nesting

    def node(self, node: ast.AST) -> int:
        if isinstance(node, DEFINITION_NODES):
            return 0
        handler = getattr(self, f"visit_{type(node).__name__}", None)
        return (
            handler(node) if handler else self.measure(list(ast.iter_child_nodes(node)))
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> int:
        # Each run of the same operator counts once; a nested other operator is its own run.
        return 1 + self.measure(node.values)

    def visit_Lambda(self, node: ast.Lambda) -> int:
        return self.nested([node.body])

    def visit_If(self, node: ast.If) -> int:
        increment = 1 if is_elif(node) else self.structure()
        score = increment + self.node(node.test) + self.nested(node.body)
        chained = node.orelse[:1] if node.orelse and is_elif(node.orelse[0]) else []
        return score + (self.measure(chained) if chained else self._else(node.orelse))

    def _else(self, orelse: list[ast.stmt]) -> int:
        return 1 + self.nested(orelse) if orelse else 0

    def _loop(self, header: ast.expr, node: ast.For | ast.While) -> int:
        score = self.structure() + self.node(header)
        return score + self.nested(node.body) + self._else(node.orelse)

    def visit_For(self, node: ast.For | ast.AsyncFor) -> int:
        return self._loop(node.iter, node)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> int:
        return self._loop(node.test, node)

    def visit_Try(self, node: ast.Try) -> int:
        handlers = sum(self.structure() + self.nested(h.body) for h in node.handlers)
        return handlers + self.measure([*node.body, *node.orelse, *node.finalbody])

    visit_TryStar = visit_Try

    def visit_Match(self, node: ast.Match) -> int:
        cases = sum(self.nested(case.body) for case in node.cases)
        return self.structure() + self.node(node.subject) + cases

    def visit_IfExp(self, node: ast.IfExp) -> int:
        return self.structure() + self.nested([node.test, node.body, node.orelse])
