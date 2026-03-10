"""Tests for ignore-spec handling."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from codectx.ignore import build_ignore_spec, should_ignore


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary repo structure."""
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\n")
    (tmp_path / ".ctxignore").write_text("docs/\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "out.js").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("")
    (tmp_path / "app.log").write_text("")
    (tmp_path / "data.txt").write_text("")
    return tmp_path


def test_always_ignore_git(temp_repo: Path) -> None:
    """ALWAYS_IGNORE should catch .git."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / ".git" / "config", temp_repo)


def test_always_ignore_pycache(temp_repo: Path) -> None:
    """ALWAYS_IGNORE should catch __pycache__."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / "__pycache__" / "mod.cpython-312.pyc", temp_repo)


def test_always_ignore_node_modules(temp_repo: Path) -> None:
    """ALWAYS_IGNORE should catch node_modules."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / "node_modules" / "pkg" / "index.js", temp_repo)


def test_gitignore_log_files(temp_repo: Path) -> None:
    """.gitignore pattern *.log should match."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / "app.log", temp_repo)


def test_gitignore_build_dir(temp_repo: Path) -> None:
    """.gitignore pattern build/ should match."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / "build" / "out.js", temp_repo)


def test_ctxignore_docs(temp_repo: Path) -> None:
    """.ctxignore pattern docs/ should match."""
    spec = build_ignore_spec(temp_repo)
    assert should_ignore(spec, temp_repo / "docs" / "readme.md", temp_repo)


def test_allowed_files(temp_repo: Path) -> None:
    """Regular source files should NOT be ignored."""
    spec = build_ignore_spec(temp_repo)
    assert not should_ignore(spec, temp_repo / "src" / "main.py", temp_repo)
    assert not should_ignore(spec, temp_repo / "data.txt", temp_repo)


def test_extra_patterns(temp_repo: Path) -> None:
    """Extra patterns from config should apply."""
    spec = build_ignore_spec(temp_repo, extra_patterns=("*.txt",))
    assert should_ignore(spec, temp_repo / "data.txt", temp_repo)
