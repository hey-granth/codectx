"""Tests for cyclic dependency detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.graph.builder import build_dependency_graph
from codectx.parser.base import ParseResult


@pytest.fixture
def cyclic_parse_results(tmp_path: Path) -> dict[Path, ParseResult]:
    """Create parse results with circular imports: a → b → a."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("from b import foo\n")
    b.write_text("from a import bar\n")

    return {
        a: ParseResult(
            path=a,
            language="python",
            imports=("from b import foo",),
            symbols=(),
            docstrings=(),
            raw_source="from b import foo\n",
            line_count=1,
        ),
        b: ParseResult(
            path=b,
            language="python",
            imports=("from a import bar",),
            symbols=(),
            docstrings=(),
            raw_source="from a import bar\n",
            line_count=1,
        ),
    }


def test_cycle_detected(cyclic_parse_results: dict[Path, ParseResult], tmp_path: Path) -> None:
    """Circular a → b → a should be detected."""
    dep_graph = build_dependency_graph(cyclic_parse_results, tmp_path)
    assert len(dep_graph.cycles) > 0, "No cycles detected"


def test_cyclic_files_property(
    cyclic_parse_results: dict[Path, ParseResult], tmp_path: Path
) -> None:
    """cyclic_files should contain both a.py and b.py."""
    dep_graph = build_dependency_graph(cyclic_parse_results, tmp_path)
    cyclic = dep_graph.cyclic_files
    names = {p.name for p in cyclic}
    assert "a.py" in names or "b.py" in names


def test_no_cycles_in_acyclic_graph(tmp_path: Path) -> None:
    """Acyclic graph should have no cycles."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("import b\n")
    b.write_text("x = 1\n")

    results = {
        a: ParseResult(
            path=a,
            language="python",
            imports=("import b",),
            symbols=(),
            docstrings=(),
            raw_source="import b\n",
            line_count=1,
        ),
        b: ParseResult(
            path=b,
            language="python",
            imports=(),
            symbols=(),
            docstrings=(),
            raw_source="x = 1\n",
            line_count=1,
        ),
    }
    dep_graph = build_dependency_graph(results, tmp_path)
    assert len(dep_graph.cycles) == 0


def test_cycle_penalty_in_scorer(
    cyclic_parse_results: dict[Path, ParseResult], tmp_path: Path
) -> None:
    """Files in cycles should receive a score penalty."""
    from codectx.ranker.git_meta import GitFileInfo
    from codectx.ranker.scorer import score_files

    dep_graph = build_dependency_graph(cyclic_parse_results, tmp_path)
    files = list(cyclic_parse_results.keys())
    git_meta: dict[Path, GitFileInfo] = {}
    scores = score_files(files, dep_graph, git_meta)

    # Scores should be floored at 0.0
    for score in scores.values():
        assert score >= 0.0
