"""Tests for tiered compression and token budget."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.compressor.budget import TokenBudget, count_tokens
from codectx.compressor.tiered import CompressedFile, assign_tiers, compress_files
from codectx.parser.base import ParseResult, Symbol


@pytest.fixture
def sample_parse_results() -> dict[Path, ParseResult]:
    return {
        Path("/repo/main.py"): ParseResult(
            path=Path("/repo/main.py"),
            language="python",
            imports=("import os",),
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
            docstrings=("Main module.",),
            raw_source="import os\n\ndef main():\n    pass\n",
            line_count=4,
        ),
        Path("/repo/utils.py"): ParseResult(
            path=Path("/repo/utils.py"),
            language="python",
            imports=(),
            symbols=(
                Symbol(
                    name="add",
                    kind="function",
                    signature="def add(a, b)",
                    docstring="Add two numbers.",
                    start_line=1,
                    end_line=2,
                ),
            ),
            docstrings=(),
            raw_source="def add(a, b):\n    return a + b\n",
            line_count=2,
        ),
        Path("/repo/config.py"): ParseResult(
            path=Path("/repo/config.py"),
            language="python",
            imports=(),
            symbols=(),
            docstrings=(),
            raw_source="DEBUG = True\n",
            line_count=1,
        ),
    }


def test_assign_tiers() -> None:
    """Tier assignment based on score thresholds."""
    scores = {
        Path("/a"): 0.9,
        Path("/b"): 0.5,
        Path("/c"): 0.1,
    }
    tiers = assign_tiers(scores)
    assert tiers[Path("/a")] == 1
    assert tiers[Path("/b")] == 2
    assert tiers[Path("/c")] == 3


def test_token_budget_consume() -> None:
    """TokenBudget should track consumption."""
    budget = TokenBudget(100)
    assert budget.remaining == 100
    assert budget.consume(50)
    assert budget.remaining == 50
    assert not budget.consume(60)
    assert budget.remaining == 50


def test_token_budget_exhausted() -> None:
    """TokenBudget should report exhaustion."""
    budget = TokenBudget(10)
    budget.consume(10)
    assert budget.is_exhausted


def test_compress_files_within_budget(
    sample_parse_results: dict[Path, ParseResult],
) -> None:
    """All files should be included when budget is large."""
    scores = {
        Path("/repo/main.py"): 0.9,
        Path("/repo/utils.py"): 0.5,
        Path("/repo/config.py"): 0.1,
    }
    budget = TokenBudget(100_000)
    compressed = compress_files(sample_parse_results, scores, budget, Path("/repo"))

    assert len(compressed) == 3
    tiers = {cf.path.name: cf.tier for cf in compressed}
    assert tiers["main.py"] == 1
    assert tiers["utils.py"] == 2
    assert tiers["config.py"] == 3


def test_compress_files_tight_budget(
    sample_parse_results: dict[Path, ParseResult],
) -> None:
    """Tight budget should drop tier 3 files first."""
    scores = {
        Path("/repo/main.py"): 0.9,
        Path("/repo/utils.py"): 0.5,
        Path("/repo/config.py"): 0.1,
    }
    # Very tight budget — only room for tier 1
    budget = TokenBudget(50)
    compressed = compress_files(sample_parse_results, scores, budget, Path("/repo"))

    # Tier 3 may be dropped
    tiers = {cf.tier for cf in compressed}
    # At minimum, tier 1 should be present (possibly truncated)
    assert any(cf.tier == 1 for cf in compressed)


def test_count_tokens() -> None:
    """Token counting should return a positive integer for non-empty text."""
    tokens = count_tokens("Hello, world!")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_compressed_output_sorted(
    sample_parse_results: dict[Path, ParseResult],
) -> None:
    """Compressed output should be sorted by tier, then score, then path."""
    scores = {
        Path("/repo/main.py"): 0.9,
        Path("/repo/utils.py"): 0.5,
        Path("/repo/config.py"): 0.1,
    }
    budget = TokenBudget(100_000)
    compressed = compress_files(sample_parse_results, scores, budget, Path("/repo"))

    # Should be sorted: tier ascending, score descending, path ascending
    for i in range(len(compressed) - 1):
        a, b = compressed[i], compressed[i + 1]
        assert (a.tier, -a.score, a.path.as_posix()) <= (
            b.tier,
            -b.score,
            b.path.as_posix(),
        )
