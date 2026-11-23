"""Raw metrics of Python files from the standard library `ast` and `tokenize` modules."""

from __future__ import annotations

import ast
import io
import tokenize

from .cognitive import DEFINITION_NODES, Cognitive, is_elif, mark_elifs
from .model import (
    AssertionBlock,
    ClassMetrics,
    FileMetrics,
    FunctionMetrics,
    SourceFile,
)
from .suppressions import parse_suppression

FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
NESTING_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.TryStar,
    ast.Match,
)
DECISION_NODES = (
    ast.If,
    ast.IfExp,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.match_case,
)
BRANCH_NODES = (ast.If, ast.While, ast.IfExp)
PRIMITIVES = {"str", "int", "float", "bool", "bytes"}
# Literals are compared by kind only, so copies that differ in data count as duplicates.
NORMALISED_TOKENS = {tokenize.STRING: "<str>", tokenize.NUMBER: "<num>"}
SKIPPED_TOKENS = {
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
}


def analyse(source: SourceFile) -> FileMetrics:
    tree = ast.parse(source.text, filename=source.path)
    mark_elifs(tree)
    tokens, suppressions = _scan_tokens(source.text)
    docstrings = _docstring_lines(tree)
    tokens = [(line, text) for line, text in tokens if line not in docstrings]
    metrics = FileMetrics(
        path=source.path,
        language="python",
        loc=len({line for line, _ in tokens}),
        suppressions=suppressions,
        is_test=source.is_test,
    )
    _Collector(metrics, tokens).visit(tree)
    return metrics


def _scan_tokens(text: str) -> tuple[list[tuple[int, str]], dict[int, dict[str, str]]]:
    """Code tokens as (line, normalised text) and the suppression comments by line."""
    tokens: list[tuple[int, str]] = []
    suppressions: dict[int, dict[str, str]] = {}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            suppressions.update(_suppression(token))
        elif token.type not in SKIPPED_TOKENS:
            tokens.extend(_code_token(token))
    return tokens, suppressions


def _code_token(token: tokenize.TokenInfo) -> list[tuple[int, str]]:
    text = NORMALISED_TOKENS.get(token.type, token.string)
    return [(line, text) for line in range(token.start[0], token.end[0] + 1)]


def _suppression(token: tokenize.TokenInfo) -> dict[int, dict[str, str]]:
    parsed = parse_suppression(token.string)
    return {token.start[0]: parsed} if parsed else {}


def _docstring(node: ast.AST) -> ast.Expr | None:
    body = getattr(node, "body", None)
    first = body[0] if isinstance(body, list) and body else None
    value = getattr(first, "value", None)
    is_text = isinstance(value, ast.Constant) and isinstance(value.value, str)
    return first if isinstance(first, ast.Expr) and is_text else None


def _docstring_lines(tree: ast.AST) -> set[int]:
    docstrings = filter(None, map(_docstring, ast.walk(tree)))
    return {
        line for doc in docstrings for line in range(doc.lineno, doc.end_lineno + 1)
    }


class _Collector(ast.NodeVisitor):
    """Walks the module, analysing every function and class on its own."""

    def __init__(self, metrics: FileMetrics, tokens: list[tuple[int, str]]):
        self.metrics = metrics
        self.tokens = tokens
        self.code_lines = {line for line, _ in tokens}
        self.prefix: list[str] = []
        self.in_class = False

    def _loc(self, node: ast.AST) -> int:
        return len(self.code_lines & set(range(node.lineno, node.end_lineno + 1)))

    def _name(self, node: ast.ClassDef | ast.FunctionDef) -> str:
        return ".".join([*self.prefix, node.name])

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        methods = [child for child in node.body if isinstance(child, FUNCTION_NODES)]
        self.metrics.classes.append(
            ClassMetrics(
                name=self._name(node),
                line=node.lineno,
                loc=self._loc(node),
                methods=len(methods),
                cohesion_components=cohesion_components(methods),
            )
        )
        self._descend(node, in_class=True)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        function = function_metrics(node, self._name(node), self.in_class)
        function.loc = self._loc(node)
        function.tokens = self._body_tokens(node)
        self.metrics.functions.append(function)
        if self.metrics.is_test and node.name.startswith("test"):
            self.metrics.assertion_blocks.extend(assertion_blocks(node, function.name))
        self._descend(node, in_class=False)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _body_tokens(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        lines = set(range(node.body[0].lineno, node.end_lineno + 1)) - _nested_lines(
            node
        )
        return [text for line, text in self.tokens if line in lines]

    def _descend(self, node: ast.ClassDef | ast.FunctionDef, in_class: bool) -> None:
        outer = self.in_class
        self.prefix.append(node.name)
        self.in_class = in_class
        self.generic_visit(node)
        self.prefix.pop()
        self.in_class = outer


def _nested_lines(node: ast.AST) -> set[int]:
    """Lines of functions and classes defined inside `node`, decorators included."""
    nested = [child for child in ast.walk(node) if isinstance(child, DEFINITION_NODES)]
    spans = [range(_first_line(child), child.end_lineno + 1) for child in nested[1:]]
    return {line for span in spans for line in span}


def _first_line(node: ast.FunctionDef | ast.ClassDef) -> int:
    return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])


def function_metrics(
    node: ast.FunctionDef | ast.AsyncFunctionDef, name: str, is_method: bool
) -> FunctionMetrics:
    arguments = _arguments(node, is_method)
    annotations = [arg.annotation for arg in arguments if arg.annotation is not None]
    return FunctionMetrics(
        name=name,
        line=node.lineno,
        loc=0,
        cyclomatic=1 + sum(map(_decisions, own_nodes(node))),
        cognitive=Cognitive().measure(node.body),
        nesting=max(map(nesting_depth, node.body), default=0),
        arguments=len(arguments),
        annotated_arguments=len(annotations),
        primitive_arguments=sum(map(_is_primitive, annotations)),
        bumps=bumps(node.body),
        conditionals=conditionals(node),
    )


def own_nodes(node: ast.AST):
    """All nodes below `node` that belong to it, not to nested functions or classes."""
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, DEFINITION_NODES):
            yield child
            yield from own_nodes(child)


def _arguments(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> list:
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    bound = is_method and not _is_static(node)
    has_receiver = bool(args) and args[0].arg in ("self", "cls")
    return args[1:] if bound and has_receiver else args


def _is_static(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return "staticmethod" in map(_decorator_name, node.decorator_list)


def _decorator_name(node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    return getattr(target, "attr", None) or getattr(target, "id", "")


def _is_primitive(annotation: ast.expr) -> bool:
    names = {n.id for n in ast.walk(annotation) if isinstance(n, ast.Name)}
    return bool(names & PRIMITIVES) and names <= PRIMITIVES | {"Optional", "Union"}


def _decisions(node: ast.AST) -> int:
    """Branches a node adds to the cyclomatic complexity (as radon counts them)."""
    if isinstance(node, DECISION_NODES):
        return 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    if isinstance(node, ast.BoolOp):
        return len(node.values) - 1
    return 0


def nesting_depth(node: ast.AST, level: int = 0) -> int:
    """Deepest nesting of control structures; an `elif` stays on the level of its `if`."""
    if isinstance(node, (*DEFINITION_NODES, ast.Lambda)):
        return level
    if isinstance(node, NESTING_NODES) and not is_elif(node):
        level += 1
    return max(
        [level, *(nesting_depth(child, level) for child in ast.iter_child_nodes(node))]
    )


def bumps(body: list[ast.stmt]) -> list[int]:
    """Nesting depth of each top-level chunk that nests conditional logic two or more levels."""
    wrapped = len(body) == 1 and isinstance(body[0], (ast.With, ast.AsyncWith, ast.Try))
    depths = map(nesting_depth, body[0].body if wrapped else body)
    return [depth for depth in depths if depth >= 2]


def conditionals(node: ast.AST) -> list[tuple[int, int]]:
    """(line, number of `and`/`or` operators) for each branch condition."""
    branches = [child for child in own_nodes(node) if isinstance(child, BRANCH_NODES)]
    counted = [(branch.lineno, _operators(branch.test)) for branch in branches]
    return [(line, operators) for line, operators in counted if operators]


def _operators(test: ast.expr) -> int:
    return sum(len(n.values) - 1 for n in ast.walk(test) if isinstance(n, ast.BoolOp))


def assertion_blocks(node: ast.AST, name: str) -> list[AssertionBlock]:
    bodies = [
        getattr(child, field, None)
        for child in [node, *own_nodes(node)]
        for field in ("body", "orelse", "finalbody")
    ]
    return [
        block
        for body in bodies
        if isinstance(body, list)
        for block in _assert_runs(body, name)
    ]


def _assert_runs(statements: list[ast.stmt], name: str) -> list[AssertionBlock]:
    runs: list[list[ast.stmt]] = [[]]
    for stmt in statements:
        if _is_assertion(stmt):
            runs[-1].append(stmt)
        elif runs[-1]:
            runs.append([])
    return [_block(run, name) for run in runs if run]


def _block(run: list[ast.stmt], name: str) -> AssertionBlock:
    return AssertionBlock(name, run[0].lineno, tuple(map(ast.unparse, run)))


def _is_assertion(stmt: ast.stmt) -> bool:
    call = getattr(stmt, "value", None) if isinstance(stmt, ast.Expr) else None
    attribute = getattr(call, "func", None) if isinstance(call, ast.Call) else None
    is_method = isinstance(attribute, ast.Attribute) and attribute.attr.startswith(
        "assert"
    )
    return isinstance(stmt, ast.Assert) or is_method


def cohesion_components(methods: list[ast.FunctionDef | ast.AsyncFunctionDef]) -> int:
    """LCOM4: connected groups of methods that share `self` attributes or call each other."""
    groups = _Groups([method.name for method in methods])
    owners: dict[str, str] = {}
    for method in methods:
        for attribute in _self_attributes(method):
            other = (
                attribute
                if attribute in groups.parent
                else owners.setdefault(attribute, method.name)
            )
            groups.join(method.name, other)
    return groups.count()


class _Groups:
    """Union-find over method names."""

    def __init__(self, names: list[str]):
        self.parent = {name: name for name in names}

    def find(self, name: str) -> str:
        while self.parent[name] != name:
            name = self.parent[name]
        return name

    def join(self, first: str, second: str) -> None:
        self.parent[self.find(first)] = self.find(second)

    def count(self) -> int:
        return len(set(map(self.find, self.parent)))


def _self_attributes(method: ast.AST) -> set[str]:
    attributes = [node for node in ast.walk(method) if isinstance(node, ast.Attribute)]
    return {node.attr for node in attributes if _is_receiver(node.value)}


def _is_receiver(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id in ("self", "cls")
