"""Tests for JSON output formatter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from codectx.compressor.tiered import CompressedFile
from codectx.graph.builder import DepGraph
from codectx.output.formatter import (
    CompressionFileRecord,
    CompressionResult,
    build_compression_result,
    format_context,
    format_json,
)


def make_mock_compression_result() -> CompressionResult:
    return CompressionResult(
        version="0.3.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        repository="/tmp/repo",
        budget_tokens=50000,
        files=[
            CompressionFileRecord(
                path="src/foo.py",
                tier="CORE",
                tokens=1234,
                rank_score=0.87,
                summary="summary",
                included=True,
            )
        ],
        symbol_index={"ClassName": "src/foo.py"},
        stats={
            "total_files": 1,
            "included_files": 1,
            "total_tokens": 1234,
            "core_count": 1,
            "supporting_count": 0,
            "peripheral_count": 0,
        },
    )


def test_format_json_returns_valid_json() -> None:
    result = make_mock_compression_result()
    output = format_json(result)
    parsed = json.loads(output)
    assert "files" in parsed
    assert "stats" in parsed


def test_json_schema_fields_present() -> None:
    parsed = json.loads(format_json(make_mock_compression_result()))
    assert "version" in parsed
    assert "generated_at" in parsed
    assert "repository" in parsed
    for file_entry in parsed["files"]:
        assert {"path", "tier", "tokens", "included"} <= file_entry.keys()


def test_json_stats_counts_correct(tmp_path: Path) -> None:
    files = [
        CompressedFile(tmp_path / "a.py", 1, 0.9, "a", 10, "python"),
        CompressedFile(tmp_path / "b.py", 2, 0.5, "b", 20, "python"),
        CompressedFile(tmp_path / "c.py", 3, 0.1, "c", 30, "python"),
    ]
    result = build_compression_result(files, tmp_path, budget_tokens=100)
    assert result.stats["core_count"] == 1
    assert result.stats["supporting_count"] == 1
    assert result.stats["peripheral_count"] == 1


def test_markdown_format_unaffected(tmp_path: Path) -> None:
    path = tmp_path / "main.py"
    path.write_text("print('x')\n")
    graph = DepGraph()
    graph.add_file(path)
    sections = format_context(
        compressed=[CompressedFile(path, 1, 1.0, "content", 10, "python")],
        dep_graph=graph,
        root=tmp_path,
    )
    content = "".join(sections.values())
    assert "## ARCHITECTURE" in content
    assert "## CORE_MODULES" in content
