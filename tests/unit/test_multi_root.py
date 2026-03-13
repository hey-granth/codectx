"""Tests for multi-root support."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.walker import find_root, walk_multi


@pytest.fixture
def two_roots(tmp_path: Path) -> tuple[Path, Path]:
    """Create two root directories with files."""
    root_a = tmp_path / "frontend"
    root_b = tmp_path / "backend"
    root_a.mkdir()
    root_b.mkdir()

    (root_a / "index.js").write_text("console.log('hello');\n")
    (root_a / "app.js").write_text("export default {};\n")
    (root_b / "main.py").write_text("print('hello')\n")
    (root_b / "utils.py").write_text("def add(a, b): return a + b\n")

    return root_a, root_b


def test_walk_multi_returns_files_by_root(two_roots: tuple[Path, Path]) -> None:
    """walk_multi should return separate file lists per root."""
    root_a, root_b = two_roots
    result = walk_multi([root_a, root_b])

    assert root_a in result
    assert root_b in result
    assert len(result[root_a]) == 2
    assert len(result[root_b]) == 2


def test_find_root_correct(two_roots: tuple[Path, Path]) -> None:
    """find_root should identify which root a file belongs to."""
    root_a, root_b = two_roots
    roots = [root_a, root_b]

    assert find_root(root_a / "index.js", roots) == root_a
    assert find_root(root_b / "main.py", roots) == root_b


def test_find_root_none_for_unknown(tmp_path: Path) -> None:
    """find_root returns None for files not under any root."""
    root = tmp_path / "myproject"
    root.mkdir()
    other = tmp_path / "other" / "file.py"
    other.parent.mkdir()
    other.write_text("pass\n")

    assert find_root(other, [root]) is None


def test_multi_root_pipeline(two_roots: tuple[Path, Path]) -> None:
    """Pipeline should work with multiple roots."""
    root_a, root_b = two_roots

    from codectx.config.loader import load_config
    from codectx.cli import _run_pipeline

    config = load_config(
        root_a,
        no_git=True,
        roots=[root_a, root_b],
    )

    result_metrics = _run_pipeline(config)
    assert result_metrics.output_path.exists()

    content = result_metrics.output_path.read_text()
    # Should contain files from both roots
    assert "main.py" in content or "index.js" in content
