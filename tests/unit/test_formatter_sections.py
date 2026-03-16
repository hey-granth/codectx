"""Tests for deterministic formatter section ordering and presence."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.tiered import CompressedFile
from codectx.graph.builder import DepGraph
from codectx.output.formatter import _auto_architecture, format_context


def test_sections_always_present_in_order(tmp_path: Path) -> None:
    """Formatter should always emit all canonical sections in fixed order."""
    content = format_context(
        compressed=[],
        dep_graph=DepGraph(),
        root=tmp_path,
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
    )
    out2 = format_context(
        compressed=[cf],
        dep_graph=graph,
        root=tmp_path,
    )

    assert out1 == out2


def test_auto_architecture_uses_single_detected_language(tmp_path: Path) -> None:
    files = [
        CompressedFile(
            path=tmp_path / "a.py",
            tier=1,
            score=1.0,
            content="",
            token_count=1,
            language="python",
        ),
        CompressedFile(
            path=tmp_path / "b.py",
            tier=2,
            score=0.8,
            content="",
            token_count=1,
            language="python",
        ),
    ]

    text = _auto_architecture(files, tmp_path)
    assert text.startswith("A python-based project")


def test_auto_architecture_is_neutral_for_mixed_languages(tmp_path: Path) -> None:
    files = [
        CompressedFile(
            path=tmp_path / "a.py",
            tier=1,
            score=1.0,
            content="",
            token_count=1,
            language="python",
        ),
        CompressedFile(
            path=tmp_path / "b.ts",
            tier=1,
            score=0.9,
            content="",
            token_count=1,
            language="typescript",
        ),
    ]

    text = _auto_architecture(files, tmp_path)
    assert text.startswith("A software project")
