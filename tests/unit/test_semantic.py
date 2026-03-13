"""Tests for semantic search ranking module."""

from __future__ import annotations

from pathlib import Path


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
