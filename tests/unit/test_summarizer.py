"""Tests for LLM summarizer module."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.parser.base import ParseResult, Symbol


@pytest.fixture
def sample_result(tmp_path: Path) -> ParseResult:
    return ParseResult(
        path=tmp_path / "example.py",
        language="python",
        imports=("import os", "from pathlib import Path"),
        symbols=(
            Symbol(
                name="main",
                kind="function",
                signature="def main()",
                docstring="Entry point.",
                start_line=1,
                end_line=5,
            ),
        ),
        docstrings=("Example module.",),
        raw_source="import os\ndef main(): pass\n",
        line_count=2,
    )


def test_summarizer_import_works() -> None:
    """Module should import without LLM deps installed."""
    from codectx.compressor.summarizer import is_available

    # Should not raise, just return bool
    result = is_available()
    assert isinstance(result, bool)


def test_summarize_file_raises_without_deps(sample_result: ParseResult) -> None:
    """summarize_file should raise if no LLM deps and called directly."""
    from codectx.compressor.summarizer import _HAS_OPENAI, summarize_file

    if not _HAS_OPENAI:
        with pytest.raises((ImportError, ValueError)):
            summarize_file(sample_result, provider="openai")


def test_compress_files_fallback_without_llm(sample_result: ParseResult) -> None:
    """compress_files with llm_enabled should fall back silently when LLM unavailable."""
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import compress_files

    parse_results = {sample_result.path: sample_result}
    scores = {sample_result.path: 0.1}  # Tier 3
    budget = TokenBudget(100_000)

    # Should NOT raise even with llm_enabled=True when deps aren't available
    compressed = compress_files(
        parse_results,
        scores,
        budget,
        sample_result.path.parent,
        llm_enabled=True,
    )
    assert len(compressed) == 1
    assert compressed[0].tier == 3
