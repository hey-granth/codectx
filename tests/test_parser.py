"""Tests for tree-sitter parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.parser.treesitter import parse_file


@pytest.fixture
def python_file(tmp_path: Path) -> Path:
    """Create a Python file with known structure."""
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

    def multiply(self, a: int, b: int) -> int:
        return a * b
'''
    f = tmp_path / "example.py"
    f.write_text(code)
    return f


def test_parse_python_language(python_file: Path) -> None:
    """Parser should detect Python language."""
    result = parse_file(python_file)
    assert result.language == "python"


def test_parse_python_imports(python_file: Path) -> None:
    """Parser should extract import statements."""
    result = parse_file(python_file)
    assert len(result.imports) == 2
    assert any("os" in imp for imp in result.imports)
    assert any("pathlib" in imp for imp in result.imports)


def test_parse_python_functions(python_file: Path) -> None:
    """Parser should extract function symbols."""
    result = parse_file(python_file)
    func_names = [s.name for s in result.symbols if s.kind == "function"]
    assert "greet" in func_names


def test_parse_python_classes(python_file: Path) -> None:
    """Parser should extract class symbols."""
    result = parse_file(python_file)
    class_names = [s.name for s in result.symbols if s.kind == "class"]
    assert "Calculator" in class_names


def test_parse_python_docstrings(python_file: Path) -> None:
    """Parser should extract module-level docstrings."""
    result = parse_file(python_file)
    assert len(result.docstrings) > 0
    assert "Module docstring" in result.docstrings[0]


def test_parse_python_function_docstring(python_file: Path) -> None:
    """Parser should extract function docstrings."""
    result = parse_file(python_file)
    greet = [s for s in result.symbols if s.name == "greet"]
    assert len(greet) == 1
    assert "hello" in greet[0].docstring.lower()


def test_parse_unsupported_file(tmp_path: Path) -> None:
    """Unsupported file extensions should get a plain-text result."""
    f = tmp_path / "data.csv"
    f.write_text("a,b,c\n1,2,3\n")
    result = parse_file(f)
    assert result.language == "unknown"
    assert len(result.symbols) == 0


def test_parse_line_count(python_file: Path) -> None:
    """ParseResult should have accurate line count."""
    result = parse_file(python_file)
    assert result.line_count > 0


def test_parse_raw_source(python_file: Path) -> None:
    """ParseResult should contain the original source."""
    result = parse_file(python_file)
    assert "def greet" in result.raw_source
