"""Data shared by the analysers, the smell rules and the scoring."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceFile:
    """A file to analyse: its repository path, its text and whether it holds tests."""

    path: str
    text: str
    is_test: bool = False


@dataclass
class FunctionMetrics:
    """Raw metrics of one function (or of a shell script's top-level code)."""

    name: str
    line: int
    loc: int
    cyclomatic: int = 1
    cognitive: int = 0
    nesting: int = 0
    arguments: int = 0
    annotated_arguments: int = 0
    primitive_arguments: int = 0
    bumps: list[int] = field(default_factory=list)
    conditionals: list[tuple[int, int]] = field(default_factory=list)
    top_level: bool = False
    # Normalised code tokens of the body, for duplicate detection.
    tokens: list[str] = field(default_factory=list, repr=False)

    @property
    def is_constructor(self) -> bool:
        return self.name.endswith("__init__")


@dataclass
class ClassMetrics:
    name: str
    line: int
    loc: int
    methods: int
    cohesion_components: int


@dataclass
class AssertionBlock:
    """Consecutive assert statements inside one test function."""

    function: str
    line: int
    statements: tuple[str, ...]


@dataclass
class FileMetrics:
    path: str
    language: str
    loc: int
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: list[ClassMetrics] = field(default_factory=list)
    assertion_blocks: list[AssertionBlock] = field(default_factory=list)
    has_logic: bool = True
    suppressions: dict[int, dict[str, str]] = field(default_factory=dict)
    is_test: bool = False
    # What the large-file rule counts: lines of code, or tasks in an Ansible file.
    units: int | None = None
    unit: str = "lines"

    @property
    def size(self) -> int:
        return self.loc if self.units is None else self.units


@dataclass
class Smell:
    rule: str
    line: int
    target: str
    detail: str
    penalty: float


@dataclass
class FileReport:
    path: str
    part: str
    loc: int
    score: float
    smells: list[Smell]
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "part": self.part,
            "loc": self.loc,
            "score": self.score,
            "smells": [smell.__dict__ for smell in self.smells],
            "errors": self.errors,
        }
