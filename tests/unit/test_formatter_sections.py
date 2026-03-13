"""Tests for deterministic formatter section ordering and presence."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.budget import TokenBudget
from codectx.compressor.tiered import CompressedFile
from codectx.graph.builder import DepGraph
from codectx.output.formatter import format_context


def test_sections_always_present_in_order(tmp_path: Path) -> None:
    """Formatter should always emit all canonical sections in fixed order."""
    budget = TokenBudget(10_000)
    content = format_context(
        compressed=[],
        dep_graph=DepGraph(),
        root=tmp_path,
        budget=budget,
    )

    headers = [
        "## ARCHITECTURE",
        "## DEPENDENCY_GRAPH",
        "## ENTRY_POINTS",
        "## CORE_MODULES",
        "## PERIPHERY",
    ]
    content_str = "".join(content.values())
    positions = [content_str.index(h) for h in headers]
    assert positions == sorted(positions)


def test_formatter_is_deterministic_for_same_inputs(tmp_path: Path) -> None:
    """Formatter output should be byte-identical across repeated runs."""
    f = tmp_path / "main.py"
    cf = CompressedFile(
        path=f,
        tier=1,
        score=0.9,
        content="### `main.py`\n\n```python\nprint('x')\n```\n",
        token_count=20,
        language="python",
    )

    graph = DepGraph()
    graph.add_file(f)

    out1 = format_context(
        compressed=[cf],
        dep_graph=graph,
        root=tmp_path,
        budget=TokenBudget(10_000),
    )
    out2 = format_context(
        compressed=[cf],
        dep_graph=graph,
        root=tmp_path,
        budget=TokenBudget(10_000),
    )

    assert out1 == out2
