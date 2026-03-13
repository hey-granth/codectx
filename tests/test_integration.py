"""Integration test — runs codectx pipeline end-to-end."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal multi-file Python project."""
    src = tmp_path / "src"
    src.mkdir()
    pkg = src / "myapp"
    pkg.mkdir()

    (pkg / "__init__.py").write_text('"""My application."""\n')
    (pkg / "main.py").write_text(
        '"""Main entry point."""\n\n'
        "from myapp.utils import helper\n\n"
        "def main():\n"
        '    """Run the app."""\n'
        "    print(helper())\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    (pkg / "utils.py").write_text(
        '"""Utility functions."""\n\n'
        "def helper() -> str:\n"
        '    """Return a greeting."""\n'
        '    return "Hello from utils!"\n\n'
        "def unused() -> None:\n"
        '    """An unused function."""\n'
        "    pass\n"
    )
    (pkg / "config.py").write_text("DEBUG = True\nPORT = 8080\n")

    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    (tmp_path / "README.md").write_text("# My App\n\nA sample project.\n")

    return tmp_path


def test_full_pipeline(sample_project: Path) -> None:
    """Full pipeline should produce a CONTEXT.md file."""
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import compress_files
    from codectx.graph.builder import build_dependency_graph
    from codectx.output.formatter import format_context, write_context_file
    from codectx.parser.treesitter import parse_files
    from codectx.ranker.git_meta import collect_git_metadata
    from codectx.ranker.scorer import score_files
    from codectx.walker import walk

    # Walk
    files = walk(sample_project)
    assert len(files) > 0

    # Parse
    parse_results = parse_files(files)
    assert len(parse_results) == len(files)

    # Graph
    dep_graph = build_dependency_graph(parse_results, sample_project)
    assert dep_graph.node_count > 0

    # Rank
    git_meta = collect_git_metadata(files, sample_project, no_git=True)
    scores = score_files(files, dep_graph, git_meta)
    assert len(scores) == len(files)

    # Compress
    budget = TokenBudget(120_000)
    compressed = compress_files(parse_results, scores, budget, sample_project)
    assert len(compressed) > 0

    # Format
    content = format_context(
        compressed=compressed,
        dep_graph=dep_graph,
        root=sample_project,
        budget=budget,
    )
    content_str = "".join(content.values())
    assert "ARCHITECTURE" in content_str
    assert "DEPENDENCY_GRAPH" in content_str

    # Write
    output_path = sample_project / "CONTEXT.md"
    write_context_file(content, output_path)
    assert output_path.is_file()
    assert output_path.read_text().strip() != ""


def test_deterministic_output(sample_project: Path) -> None:
    """Running the pipeline twice should produce identical output."""
    from codectx.compressor.budget import TokenBudget
    from codectx.compressor.tiered import compress_files
    from codectx.graph.builder import build_dependency_graph
    from codectx.output.formatter import format_context
    from codectx.parser.treesitter import parse_files
    from codectx.ranker.git_meta import collect_git_metadata
    from codectx.ranker.scorer import score_files
    from codectx.walker import walk

    def run() -> str:
        files = walk(sample_project)
        parse_results = parse_files(files)
        dep_graph = build_dependency_graph(parse_results, sample_project)
        git_meta = collect_git_metadata(files, sample_project, no_git=True)
        scores = score_files(files, dep_graph, git_meta)
        budget = TokenBudget(120_000)
        compressed = compress_files(parse_results, scores, budget, sample_project)
        return format_context(
            compressed=compressed,
            dep_graph=dep_graph,
            root=sample_project,
            budget=budget,
        )

    output1 = run()
    output2 = run()
    assert output1 == output2, "Pipeline output is not deterministic"


def test_token_budget_respected(sample_project: Path) -> None:
    """Output should fit within the token budget."""
    from codectx.compressor.budget import TokenBudget, count_tokens
    from codectx.compressor.tiered import compress_files
    from codectx.graph.builder import build_dependency_graph
    from codectx.output.formatter import format_context
    from codectx.parser.treesitter import parse_files
    from codectx.ranker.git_meta import collect_git_metadata
    from codectx.ranker.scorer import score_files
    from codectx.walker import walk

    files = walk(sample_project)
    parse_results = parse_files(files)
    dep_graph = build_dependency_graph(parse_results, sample_project)
    git_meta = collect_git_metadata(files, sample_project, no_git=True)
    scores = score_files(files, dep_graph, git_meta)

    small_budget = 500
    budget = TokenBudget(small_budget)
    compressed = compress_files(parse_results, scores, budget, sample_project)
    content = format_context(
        compressed=compressed,
        dep_graph=dep_graph,
        root=sample_project,
        budget=budget,
    )

    # The compressed content consumed by files should be within budget
    total_file_tokens = sum(cf.token_count for cf in compressed)
    assert total_file_tokens <= small_budget
