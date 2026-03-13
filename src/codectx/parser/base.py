"""Core data structures for the parser module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Symbol:
    """A top-level symbol extracted from a source file."""

    name: str
    kind: str  # "function", "class", "method"
    signature: str  # e.g. "def foo(x: int, y: str) -> bool"
    docstring: str  # empty string if none
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a single source file."""

    path: Path
    language: str  # e.g. "python", "typescript", or "unknown"
    imports: tuple[str, ...]  # raw import strings
    symbols: tuple[Symbol, ...]
    docstrings: tuple[str, ...]  # module-level docstrings
    raw_source: str
    line_count: int
    partial_parse: bool = False

    @property
    def is_empty(self) -> bool:
        return not self.imports and not self.symbols


def make_plaintext_result(path: Path, source: str) -> ParseResult:
    """Create a minimal ParseResult for unsupported language files."""
    return ParseResult(
        path=path,
        language="unknown",
        imports=(),
        symbols=(),
        docstrings=(),
        raw_source=source,
        line_count=source.count("\n") + 1 if source else 0,
        partial_parse=False,
    )
