"""Turns raw metrics into smells, using the rules that the file's part enables."""

from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from .config import Part, Rule
from .model import FileMetrics, FunctionMetrics, Smell


def detect(metrics: FileMetrics, part: Part) -> list[Smell]:
    smells = _function_smells(metrics, part) + _file_smells(metrics, part)
    return sorted(smells, key=lambda smell: (smell.line, smell.rule))


def _function_smells(metrics: FileMetrics, part: Part) -> list[Smell]:
    checks = [
        (part.rules[name], check) for name, check in FUNCTION_CHECKS if part.rule(name)
    ]
    return [
        smell
        for function in metrics.functions
        for rule, check in checks
        for smell in check(function, rule, part)
    ]


def _file_smells(metrics: FileMetrics, part: Part) -> list[Smell]:
    checks = [
        (part.rules[name], check) for name, check in FILE_CHECKS if part.rule(name)
    ]
    return [smell for rule, check in checks for smell in check(metrics, rule, part)]


def _at(function: FunctionMetrics) -> tuple[int, str]:
    return function.line, function.name


def _threshold_check(attribute: str, label: str, top_level: bool = True):
    """A function smell that fires when one metric exceeds the rule's threshold."""

    def check(function: FunctionMetrics, rule: Rule, part: Part) -> list[Smell]:
        value = getattr(function, attribute)
        applies = top_level or not function.top_level
        if not (applies and rule.fires(value)):
            return []
        return [rule.smell(value, _at(function), f"{label} {value}")]

    return check


def _excess_arguments(function: FunctionMetrics, rule: Rule, part: Part) -> list[Smell]:
    if function.is_constructor or not rule.fires(function.arguments):
        return []
    return [
        rule.smell(function.arguments, _at(function), f"{function.arguments} arguments")
    ]


def _constructor_over_injection(
    function: FunctionMetrics, rule: Rule, part: Part
) -> list[Smell]:
    if not (function.is_constructor and rule.fires(function.arguments)):
        return []
    detail = f"{function.arguments} constructor arguments"
    return [rule.smell(function.arguments, _at(function), detail)]


def _fires(part: Part, name: str, value: float) -> bool:
    rule = part.rule(name)
    return bool(rule) and rule.fires(value)


def _is_brain_method(function: FunctionMetrics, part: Part) -> bool:
    if function.top_level:
        return False
    complex_ = _fires(part, "complex-method", function.cyclomatic)
    return complex_ and _fires(part, "large-method", function.loc)


def _brain_method(function: FunctionMetrics, rule: Rule, part: Part) -> list[Smell]:
    if not _is_brain_method(function, part):
        return []
    detail = f"cyclomatic complexity {function.cyclomatic}, {function.loc} lines"
    return [rule.smell(1, _at(function), detail)]


def _bumpy_road(function: FunctionMetrics, rule: Rule, part: Part) -> list[Smell]:
    bumps = [depth for depth in function.bumps if depth >= rule.options["bump_depth"]]
    if not rule.fires(len(bumps)):
        return []
    detail = f"{len(bumps)} bumps (nesting {', '.join(map(str, bumps))})"
    return [rule.smell(len(bumps), _at(function), detail)]


def _complex_conditionals(
    function: FunctionMetrics, rule: Rule, part: Part
) -> list[Smell]:
    return [
        rule.smell(ops, (line, function.name), f"{ops} and/or operators")
        for line, ops in function.conditionals
        if rule.fires(ops)
    ]


FUNCTION_CHECKS = [
    ("complex-method", _threshold_check("cyclomatic", "cyclomatic complexity")),
    ("large-method", _threshold_check("loc", "lines", top_level=False)),
    ("brain-method", _brain_method),
    ("excess-arguments", _excess_arguments),
    ("constructor-over-injection", _constructor_over_injection),
    ("nested-complexity", _threshold_check("nesting", "nesting depth")),
    ("bumpy-road", _bumpy_road),
    ("complex-conditional", _complex_conditionals),
    ("cognitive-complexity", _threshold_check("cognitive", "cognitive complexity")),
]


def _whole(metrics: FileMetrics) -> tuple[int, str]:
    return 1, metrics.path


def _large_file(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    if not rule.fires(metrics.size):
        return []
    return [rule.smell(metrics.size, _whole(metrics), f"{metrics.size} {metrics.unit}")]


def _named_functions(metrics: FileMetrics) -> list[FunctionMetrics]:
    return [function for function in metrics.functions if not function.top_level]


def _overall_complexity(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    functions = _named_functions(metrics) or [FunctionMetrics("", 0, 0)]
    mean = round(sum(f.cyclomatic for f in functions) / len(functions), 2)
    if not rule.fires(mean):
        return []
    return [rule.smell(mean, _whole(metrics), f"mean cyclomatic complexity {mean}")]


def _many_functions(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    count = len(_named_functions(metrics))
    if not rule.fires(count):
        return []
    return [rule.smell(count, _whole(metrics), f"{count} functions")]


def _primitive_obsession(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    annotated = sum(f.annotated_arguments for f in metrics.functions)
    primitive = sum(f.primitive_arguments for f in metrics.functions)
    share = round(100 * primitive / max(annotated, 1))
    if annotated < rule.options["min_arguments"] or not rule.fires(share):
        return []
    detail = f"{share} % of {annotated} annotated arguments are primitive types"
    return [rule.smell(share, _whole(metrics), detail)]


def _brain_class(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    functions = _named_functions(metrics)
    if len(functions) < rule.options["min_functions"] or not _fires(
        part, "large-file", metrics.size
    ):
        return []
    if not any(_is_brain_method(function, part) for function in functions):
        return []
    detail = f"{metrics.size} lines, {len(functions)} functions and a brain method"
    return [rule.smell(1, _whole(metrics), detail)]


def _low_cohesion(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    return [
        rule.smell(
            cls.cohesion_components,
            (cls.line, cls.name),
            f"LCOM4 {cls.cohesion_components} (unrelated groups of methods)",
        )
        for cls in metrics.classes
        if cls.methods >= rule.options["min_methods"]
        and rule.fires(cls.cohesion_components)
    ]


def _duplication(metrics: FileMetrics, rule: Rule, part: Part) -> list[Smell]:
    candidates = [
        f
        for f in _named_functions(metrics)
        if f.loc >= rule.options["min_loc"]
        and len(f.tokens) >= rule.options.get("min_tokens", 0)
    ]
    smells = []
    for index, function in enumerate(candidates):
        twin = _most_similar(function, candidates[:index], rule.options["similarity"])
        if twin:
            other, ratio = twin
            detail = f"{ratio:.0%} similar to {other.name} (line {other.line})"
            smells.append(rule.smell(1, _at(function), detail))
    return smells


def _most_similar(
    function: FunctionMetrics, others: list[FunctionMetrics], minimum: float
):
    scored = [
        (other, _similarity(function.tokens, other.tokens, minimum)) for other in others
    ]
    best = max(scored, key=lambda pair: pair[1], default=None)
    return best if best and best[1] >= minimum else None


def _similarity(first: list[str], second: list[str], minimum: float) -> float:
    """Similarity ratio, or 0 when cheap upper bounds already rule out `minimum`."""
    lengths = len(first) + len(second)
    if 2 * min(len(first), len(second)) < minimum * lengths or not lengths:
        return 0.0
    matcher = SequenceMatcher(None, first, second, autojunk=False)
    return matcher.ratio() if matcher.quick_ratio() >= minimum else 0.0


def _sized_blocks(metrics: FileMetrics, rule: Rule) -> list:
    return [
        b
        for b in metrics.assertion_blocks
        if len(b.statements) >= rule.options["block_size"]
    ]


def _large_assertion_blocks(
    metrics: FileMetrics, rule: Rule, part: Part
) -> list[Smell]:
    large = _sized_blocks(metrics, rule)
    if not rule.fires(len(large)):
        return []
    lines = ", ".join(str(block.line) for block in large)
    detail = (
        f"{len(large)} blocks of {rule.options['block_size']}+ asserts (lines {lines})"
    )
    return [rule.smell(len(large), (large[0].line, metrics.path), detail)]


def _duplicated_assertion_blocks(
    metrics: FileMetrics, rule: Rule, part: Part
) -> list[Smell]:
    blocks = _sized_blocks(metrics, rule)
    counts = Counter(block.statements for block in blocks)
    seen: set[tuple[str, ...]] = set()
    repeated = []
    for block in blocks:
        if counts[block.statements] > 1 and block.statements in seen:
            repeated.append(block)
        seen.add(block.statements)
    return [
        rule.smell(
            1,
            (block.line, block.function),
            f"{len(block.statements)} asserts repeated from another test",
        )
        for block in repeated
    ]


FILE_CHECKS = [
    ("large-file", _large_file),
    ("overall-code-complexity", _overall_complexity),
    ("many-functions", _many_functions),
    ("primitive-obsession", _primitive_obsession),
    ("brain-class", _brain_class),
    ("low-cohesion", _low_cohesion),
    ("code-duplication", _duplication),
    ("large-assertion-blocks", _large_assertion_blocks),
    ("duplicated-assertion-blocks", _duplicated_assertion_blocks),
]
