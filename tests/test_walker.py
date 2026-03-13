"""Tests for the file walker."""

from __future__ import annotations

from pathlib import Path

import pytest

from codectx.walker import walk


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary repo with various files."""
    # Source files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.py").write_text("def add(a, b): return a + b")

    # Should be ignored
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"\x00")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg").mkdir()
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("")

    # Binary file
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    # Regular text file
    (tmp_path / "README.md").write_text("# Hello")
    (tmp_path / ".gitignore").write_text("")

    return tmp_path


def test_walk_finds_source_files(temp_repo: Path) -> None:
    """Walker should find regular source files."""
    files = walk(temp_repo)
    rel_paths = {f.relative_to(temp_repo).as_posix() for f in files}
    assert "src/main.py" in rel_paths
    assert "src/utils.py" in rel_paths
    assert "README.md" in rel_paths


def test_walk_skips_ignored_dirs(temp_repo: Path) -> None:
    """Walker should skip __pycache__ and node_modules."""
    files = walk(temp_repo)
    rel_paths = {f.relative_to(temp_repo).as_posix() for f in files}
    assert not any("__pycache__" in p for p in rel_paths)
    assert not any("node_modules" in p for p in rel_paths)


def test_walk_skips_binary_files(temp_repo: Path) -> None:
    """Walker should filter out binary files."""
    files = walk(temp_repo)
    rel_paths = {f.relative_to(temp_repo).as_posix() for f in files}
    assert "image.png" not in rel_paths


def test_walk_skips_invalid_utf8_binary(temp_repo: Path) -> None:
    """Files that fail UTF-8 decoding should be treated as binary."""
    (temp_repo / "blob.bin").write_bytes(b"\xff\xfe\xfd\xfa")
    files = walk(temp_repo)
    rel_paths = {f.relative_to(temp_repo).as_posix() for f in files}
    assert "blob.bin" not in rel_paths


def test_walk_returns_sorted(temp_repo: Path) -> None:
    """Result should be sorted by path."""
    files = walk(temp_repo)
    paths = [f.relative_to(temp_repo).as_posix() for f in files]
    assert paths == sorted(paths)


def test_walk_returns_absolute_paths(temp_repo: Path) -> None:
    """All returned paths should be absolute."""
    files = walk(temp_repo)
    assert all(f.is_absolute() for f in files)
