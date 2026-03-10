"""Tests for the composite file scorer."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.graph.builder import DepGraph
from codectx.ranker.git_meta import GitFileInfo
from codectx.ranker.scorer import score_files


@pytest.fixture
def sample_files() -> list[Path]:
    return [
        Path("/repo/src/main.py"),
        Path("/repo/src/utils.py"),
        Path("/repo/src/config.py"),
        Path("/repo/tests/test_main.py"),
    ]


@pytest.fixture
def dep_graph(sample_files: list[Path]) -> DepGraph:
    graph = DepGraph()
    for f in sample_files:
        graph.add_file(f)
    # main imports utils and config
    graph.add_edge(sample_files[0], sample_files[1])
    graph.add_edge(sample_files[0], sample_files[2])
    # test imports main
    graph.add_edge(sample_files[3], sample_files[0])
    return graph


@pytest.fixture
def git_meta(sample_files: list[Path]) -> dict[Path, GitFileInfo]:
    import time
    now = time.time()
    return {
        sample_files[0]: GitFileInfo(commit_count=50, last_modified_ts=now - 3600),
        sample_files[1]: GitFileInfo(commit_count=30, last_modified_ts=now - 86400),
        sample_files[2]: GitFileInfo(commit_count=5, last_modified_ts=now - 604800),
        sample_files[3]: GitFileInfo(commit_count=10, last_modified_ts=now - 172800),
    }


def test_scores_in_range(
    sample_files: list[Path],
    dep_graph: DepGraph,
    git_meta: dict[Path, GitFileInfo],
) -> None:
    """All scores should be between 0 and 1."""
    scores = score_files(sample_files, dep_graph, git_meta)
    for path, score in scores.items():
        assert 0.0 <= score <= 1.0, f"Score for {path} is {score}"


def test_main_scores_highest(
    sample_files: list[Path],
    dep_graph: DepGraph,
    git_meta: dict[Path, GitFileInfo],
) -> None:
    """main.py should score highest (most commits, most fan-in, most recent)."""
    scores = score_files(sample_files, dep_graph, git_meta)
    main_score = scores[sample_files[0]]
    for f in sample_files[1:]:
        assert main_score >= scores[f], f"Expected main.py >= {f.name}"


def test_empty_files() -> None:
    """Empty file list should return empty dict."""
    scores = score_files([], DepGraph(), {})
    assert scores == {}


def test_deterministic(
    sample_files: list[Path],
    dep_graph: DepGraph,
    git_meta: dict[Path, GitFileInfo],
) -> None:
    """Scoring should be deterministic."""
    scores1 = score_files(sample_files, dep_graph, git_meta)
    scores2 = score_files(sample_files, dep_graph, git_meta)
    assert scores1 == scores2
