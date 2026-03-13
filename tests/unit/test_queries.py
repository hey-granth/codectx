"""Tests for .scm query file loading and data-driven extraction."""

from __future__ import annotations

from pathlib import Path

from codectx.parser.treesitter import (
    _get_query_spec,
    _load_query_spec,
    parse_file,
)


def test_load_python_query_spec() -> None:
    """Python .scm file should load with import and symbol types."""
    spec = _load_query_spec("python")
    assert spec is not None
    assert "import_statement" in spec.import_types
    assert "import_from_statement" in spec.import_types
    assert "function_definition" in spec.function_types
    assert "class_definition" in spec.class_types


def test_load_javascript_query_spec() -> None:
    """JavaScript .scm file should load correctly."""
    spec = _load_query_spec("javascript")
    assert spec is not None
    assert "import_declaration" in spec.import_types


def test_load_nonexistent_spec() -> None:
    """Missing .scm file should return None."""
    spec = _load_query_spec("nonexistent_language")
    assert spec is None


def test_cached_query_spec() -> None:
    """_get_query_spec should cache results."""
    spec1 = _get_query_spec("python")
    spec2 = _get_query_spec("python")
    assert spec1 is spec2


def test_parse_output_matches_with_queries(tmp_path: Path) -> None:
    """Parse output with query-driven extraction should match expectations."""
    code = '''"""Module docstring."""

import os
from pathlib import Path

def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
'''
    f = tmp_path / "example.py"
    f.write_text(code)

    result = parse_file(f)

    # Imports should still be extracted correctly
    assert len(result.imports) == 2
    assert any("os" in imp for imp in result.imports)
    assert any("pathlib" in imp for imp in result.imports)

    # Functions should still be extracted
    func_names = [s.name for s in result.symbols if s.kind == "function"]
    assert "greet" in func_names

    # Classes should still be extracted
    class_names = [s.name for s in result.symbols if s.kind == "class"]
    assert "Calculator" in class_names
