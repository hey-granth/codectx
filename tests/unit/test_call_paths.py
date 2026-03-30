"""Tests for call path detection and formatting."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.tiered import CompressedFile
from codectx.graph.builder import DepGraph
from codectx.output.formatter import format_context
from codectx.output.sections import IMPORTANT_CALL_PATHS
from codectx.parser.base import ParseResult, Symbol


def _make_parse_result(path: Path, symbol_name: str) -> ParseResult:
    return ParseResult(
        path=path,
        language="python",
        imports=(),
        symbols=(
            Symbol(
                name=symbol_name,
                kind="function",
                signature=f"def {symbol_name}()",
                docstring="",
                start_line=1,
                end_line=1,
            ),
        ),
        docstrings=(),
        raw_source="",
        line_count=1,
    )


def test_detect_call_paths_returns_up_to_three_distinct_paths(tmp_path: Path) -> None:
    graph = DepGraph()

    entry = tmp_path / "main.py"
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"
    d = tmp_path / "d.py"
    e = tmp_path / "e.py"
    f = tmp_path / "f.py"

    for p in (entry, a, b, c, d, e, f):
        graph.add_file(p)

    # Entrypoint fans out into three branches.
    graph.add_edge(entry, a)
    graph.add_edge(entry, b)
    graph.add_edge(entry, c)
    graph.add_edge(a, d)
    graph.add_edge(b, e)
    graph.add_edge(c, f)

    paths = graph.detect_call_paths(max_depth=8, max_paths=3)

    entry_paths = [path for path in paths if path and path[0] == entry]
    assert len(entry_paths) == 3

    # Distinct paths must diverge after the entry node.
    second_hops = {path[1] for path in entry_paths if len(path) > 1}
    assert len(second_hops) == 3


def test_formatter_call_paths_include_symbol_annotations(tmp_path: Path) -> None:
    graph = DepGraph()

    entry = tmp_path / "main.py"
    core = tmp_path / "core.py"
    leaf = tmp_path / "leaf.py"

    for p in (entry, core, leaf):
        graph.add_file(p)

    graph.add_edge(entry, core)
    graph.add_edge(core, leaf)

    parse_results = {
        entry: _make_parse_result(entry, "main"),
        core: _make_parse_result(core, "run"),
        leaf: _make_parse_result(leaf, "execute"),
    }

    compressed = [
        CompressedFile(
            path=entry,
            tier=1,
            score=1.0,
            content="",
            token_count=0,
            language="python",
        )
    ]

    sections = format_context(
        compressed=compressed,
        dep_graph=graph,
        root=tmp_path,
        parse_results=parse_results,
    )

    call_paths_text = sections[IMPORTANT_CALL_PATHS.key]
    assert "main.main()" in call_paths_text
    assert "core.run()" in call_paths_text
    assert "leaf.execute()" in call_paths_text


def test_formatter_enhanced_call_paths_are_task_opt_in(tmp_path: Path) -> None:
    graph = DepGraph()

    entry = tmp_path / "main.py"
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    c = tmp_path / "c.py"

    for p in (entry, a, b, c):
        graph.add_file(p)

    graph.add_edge(entry, a)
    graph.add_edge(entry, b)
    graph.add_edge(entry, c)

    parse_results = {
        entry: _make_parse_result(entry, "main"),
        a: _make_parse_result(a, "alpha"),
        b: _make_parse_result(b, "beta"),
        c: _make_parse_result(c, "gamma"),
    }

    compressed = [
        CompressedFile(
            path=entry,
            tier=1,
            score=1.0,
            content="",
            token_count=0,
            language="python",
        )
    ]

    default_sections = format_context(
        compressed=compressed,
        dep_graph=graph,
        root=tmp_path,
        parse_results=parse_results,
    )
    arch_sections = format_context(
        compressed=compressed,
        dep_graph=graph,
        root=tmp_path,
        parse_results=parse_results,
        task="architecture",
    )

    default_text = default_sections[IMPORTANT_CALL_PATHS.key]
    arch_text = arch_sections[IMPORTANT_CALL_PATHS.key]

    assert default_text.count("main.main()") == 1
    assert arch_text.count("main.main()") == 3



