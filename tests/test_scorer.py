"""Tests for the composite file scorer."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.graph.builder import DepGraph
from codectx.parser.base import ParseResult, Symbol
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


def test_refactor_profile_differs_from_default(tmp_path: Path) -> None:
    """Refactor task should meaningfully shift ranking from default."""
    import time

    main_file = tmp_path / "main.py"
    core_file = tmp_path / "core.py"
    util_file = tmp_path / "util.py"
    helper_file = tmp_path / "helper.py"

    files = [main_file, core_file, util_file, helper_file]
    graph = DepGraph()
    for f in files:
        graph.add_file(f)

    # Make core.py the most depended-on file.
    graph.add_edge(main_file, core_file)
    graph.add_edge(util_file, core_file)
    graph.add_edge(helper_file, core_file)
    graph.add_edge(main_file, util_file)

    now = time.time()
    git_meta = {
        main_file: GitFileInfo(commit_count=40, last_modified_ts=now - 3600),
        core_file: GitFileInfo(commit_count=12, last_modified_ts=now - (86400 * 500)),
        util_file: GitFileInfo(commit_count=22, last_modified_ts=now - (86400 * 3)),
        helper_file: GitFileInfo(commit_count=5, last_modified_ts=now - (86400 * 2)),
    }

    # core.py is symbol-dense, which should help the refactor profile.
    parse_results = {
        main_file: ParseResult(main_file, "python", (), (), (), "", 1),
        core_file: ParseResult(
            core_file,
            "python",
            (),
            tuple(
                Symbol(
                    name=f"s{i}",
                    kind="function",
                    signature=f"def s{i}()",
                    docstring="",
                    start_line=i,
                    end_line=i,
                )
                for i in range(15)
            ),
            (),
            "",
            1,
        ),
        util_file: ParseResult(util_file, "python", (), (), (), "", 1),
        helper_file: ParseResult(helper_file, "python", (), (), (), "", 1),
    }

    default_scores = score_files(files, graph, git_meta, parse_results=parse_results)
    refactor_scores = score_files(
        files, graph, git_meta, task="refactor", parse_results=parse_results
    )

    default_ranked = [
        p for p, _ in sorted(default_scores.items(), key=lambda x: (-x[1], x[0].as_posix()))
    ]
    refactor_ranked = [
        p for p, _ in sorted(refactor_scores.items(), key=lambda x: (-x[1], x[0].as_posix()))
    ]

    assert default_ranked != refactor_ranked
    assert refactor_ranked[0] == core_file
