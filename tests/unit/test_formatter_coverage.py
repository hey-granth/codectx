"""Tests for output formatting."""

from pathlib import Path

from codectx.graph.builder import DepGraph
from codectx.output.formatter import format_context, write_layer_files
from codectx.output.sections import ARCHITECTURE, CORE_MODULES
from codectx.parser.base import make_plaintext_result


def test_format_context_basic(tmp_path: Path) -> None:
    f1 = tmp_path / "a.py"
    f1.write_text("print('hi')\n")
    res = {f1: make_plaintext_result(f1, "print('hi')\n")}
    graph = DepGraph(res)
    scores = {f1: 1.0}
    tokens = {f1: 10}

    # We need to mock TokenBudget? No, None is not allowed, it expects TokenBudget.
    # Wait, in formatter.py: `def format_context(compressed: list[CompressedFile], dep_graph, ... budget...)`
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import CompressedFile

    budget = TokenBudget(1000)
    cf = CompressedFile(
        tier=1, token_count=10, content="print('hi')", path=f1, score=1.0, language="python"
    )

    sections = format_context(
        compressed=[cf],
        dep_graph=graph,
        root=tmp_path,
        budget=budget,
        parse_results=res,
    )

    assert "core_modules" in sections


def test_write_layer_files(tmp_path: Path) -> None:
    sections = {ARCHITECTURE.key: "arch content", CORE_MODULES.key: "core content"}
    write_layer_files(sections, tmp_path)
    assert (tmp_path / "REPO_MAP.md").read_text() == "arch content"
    assert (tmp_path / "CORE_CONTEXT.md").read_text() == "core content"
