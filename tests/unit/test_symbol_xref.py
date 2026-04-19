"""Tests for symbol cross-reference graph edges."""

from __future__ import annotations

from pathlib import Path

from codectx.graph.builder import build_dependency_graph
from codectx.parser.base import ParseResult, Symbol


def _pr(
    path: Path,
    symbols: tuple[Symbol, ...],
    source: str,
    symbol_usages: dict[str, list[str]] | None = None,
) -> ParseResult:
    return ParseResult(
        path=path,
        language="python",
        imports=(),
        symbols=symbols,
        docstrings=(),
        raw_source=source,
        line_count=max(source.count("\n"), 1),
        symbol_usages=symbol_usages or {},
    )


def test_symbol_definition_collected(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("class ClassFoo:\n    pass\n")
    pr = _pr(
        a,
        (Symbol("ClassFoo", "class", "class ClassFoo", "", 1, 2),),
        a.read_text(),
    )

    graph = build_dependency_graph({a: pr}, tmp_path)
    assert graph.node_count == 1


def test_cross_file_reference_creates_edge(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("class ClassFoo:\n    pass\n")
    b.write_text("def run(x: ClassFoo) -> None:\n    pass\n")

    pr_a = _pr(
        a,
        (Symbol("ClassFoo", "class", "class ClassFoo", "", 1, 2),),
        a.read_text(),
    )
    pr_b = _pr(
        b,
        (Symbol("run", "function", "def run(x: ClassFoo)", "", 1, 2),),
        b.read_text(),
        symbol_usages={"ClassFoo": []},
    )

    graph = build_dependency_graph({a: pr_a, b: pr_b}, tmp_path)
    src = graph.path_to_idx[b]
    dst = graph.path_to_idx[a]
    assert graph.graph.has_edge(src, dst)
    assert graph.graph.get_edge_data(src, dst) == "symbol_ref"


def test_no_self_reference_edge(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("class ClassFoo:\n    pass\n\nvalue: ClassFoo | None = None\n")

    pr = _pr(
        a,
        (Symbol("ClassFoo", "class", "class ClassFoo", "", 1, 2),),
        a.read_text(),
        symbol_usages={"ClassFoo": []},
    )

    graph = build_dependency_graph({a: pr}, tmp_path)
    idx = graph.path_to_idx[a]
    assert not graph.graph.has_edge(idx, idx)


def test_missing_symbol_no_crash(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    a.write_text("def run(x: UnknownSymbol) -> None:\n    pass\n")

    pr = _pr(
        a,
        (Symbol("run", "function", "def run(x: UnknownSymbol)", "", 1, 2),),
        a.read_text(),
        symbol_usages={"UnknownSymbol": []},
    )

    graph = build_dependency_graph({a: pr}, tmp_path)
    assert graph.edge_count == 0


def test_get_symbol_references_returns_correct_data(tmp_path: Path) -> None:
    a = tmp_path / "defs.py"
    b = tmp_path / "use.py"
    a.write_text("class Widget:\n    pass\n")
    b.write_text("def build(w: Widget) -> None:\n    pass\n")

    pr_a = _pr(a, (Symbol("Widget", "class", "class Widget", "", 1, 2),), a.read_text())
    pr_b = _pr(
        b,
        (Symbol("build", "function", "def build(w: Widget)", "", 1, 2),),
        b.read_text(),
        symbol_usages={"Widget": []},
    )

    graph = build_dependency_graph({a: pr_a, b: pr_b}, tmp_path)
    refs = graph.get_symbol_references()

    assert refs
    assert refs[0].symbol == "Widget"
    assert refs[0].defined_in.endswith("defs.py")
    assert refs[0].used_in.endswith("use.py")
