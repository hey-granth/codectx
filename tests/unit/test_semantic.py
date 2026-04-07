"""Tests for semantic search ranking module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_semantic_import_works() -> None:
    """Module should import without semantic deps installed."""
    from codectx.ranker.semantic import is_available

    result = is_available()
    assert isinstance(result, bool)


def test_scorer_with_no_semantic_scores(tmp_path: Path) -> None:
    """score_files without semantic_scores should work normally."""
    from codectx.graph.builder import DepGraph
    from codectx.ranker.scorer import score_files

    f1 = tmp_path / "a.py"
    f1.write_text("pass\n")
    dep_graph = DepGraph()
    dep_graph.add_file(f1)

    scores = score_files([f1], dep_graph, {})
    assert f1 in scores
    assert 0.0 <= scores[f1] <= 1.0


def test_scorer_with_semantic_scores(tmp_path: Path) -> None:
    """score_files with semantic_scores should incorporate them."""
    from codectx.graph.builder import DepGraph
    from codectx.ranker.scorer import score_files

    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("pass\n")
    f2.write_text("pass\n")

    dep_graph = DepGraph()
    dep_graph.add_file(f1)
    dep_graph.add_file(f2)

    # f1 has high semantic score, f2 has low
    sem_scores = {f1: 1.0, f2: 0.0}

    scores = score_files([f1, f2], dep_graph, {}, semantic_scores=sem_scores)
    # f1 should score higher due to semantic boost
    assert scores[f1] > scores[f2]


def test_pipeline_with_query_no_deps(tmp_path: Path) -> None:
    """Pipeline with --query should gracefully degrade without semantic deps."""
    from codectx.cli import _run_pipeline
    from codectx.config.loader import load_config

    (tmp_path / "main.py").write_text("print('hello')\n")

    config = load_config(tmp_path, no_git=True, query="authentication")

    # Should NOT raise even without semantic deps
    result_metrics = _run_pipeline(config)
    assert result_metrics.output_path.exists()


def test_pipeline_query_flows_to_score_files(tmp_path: Path) -> None:
    """With semantic deps available, semantic scores should be passed to score_files."""
    from codectx.cli import _run_pipeline
    from codectx.config.loader import load_config

    main_file = tmp_path / "main.py"
    main_file.write_text("print('hello')\n")

    config = load_config(tmp_path, no_git=True, query="token budget enforcement")
    sem_scores = {main_file: 0.77}

    with (
        patch("codectx.ranker.semantic.is_available", return_value=True),
        patch("codectx.ranker.semantic.semantic_score", return_value=sem_scores) as mock_semantic,
        patch("codectx.ranker.scorer.score_files") as mock_score,
    ):
        mock_score.side_effect = (
            lambda files, dep_graph, git_meta, semantic_scores=None, task="default", parse_results=None: {
                f: 1.0 for f in files
            }
        )

        result = _run_pipeline(config)

    assert result.output_path.exists()
    assert mock_semantic.called
    assert mock_score.called
    assert mock_score.call_args.kwargs.get("semantic_scores") == sem_scores
