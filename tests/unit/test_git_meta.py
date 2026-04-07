"""Tests for git metadata collection."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

from codectx.ranker.git_meta import collect_git_metadata, collect_recent_changes


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def test_collect_no_git(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("code\n")
    files = [f]
    res = collect_git_metadata(files, tmp_path, no_git=True)
    assert f in res
    assert res[f].commit_count == 0


def test_collect_git_success(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("code\n")
    files = [f]

    mock_pygit2 = MagicMock()
    mock_delta = MagicMock()
    mock_delta.new_file.path = "a.py"
    mock_commit = MagicMock()
    mock_commit.commit_time = 1000.0
    mock_commit.id = "12345678"
    mock_commit.message = "Initial commit"
    mock_commit.parents = []
    mock_commit.tree.diff_to_tree.return_value.deltas = [mock_delta]

    class DummyRepo:
        def __init__(self, path):
            self.head = MagicMock()

        def walk(self, *args):
            return [mock_commit]

    mock_pygit2.Repository = DummyRepo

    sys.modules["pygit2"] = mock_pygit2

    res = collect_git_metadata(files, tmp_path, no_git=False)
    assert res[f].commit_count == 1
    assert res[f].last_modified_ts == 1000.0

    del sys.modules["pygit2"]


def test_collect_recent_changes(tmp_path: Path) -> None:
    mock_pygit2 = MagicMock()
    mock_delta = MagicMock()
    mock_delta.new_file.path = "a.py"
    mock_commit = MagicMock()
    # 2 days ago
    import time

    mock_commit.commit_time = time.time() - 86400 * 2
    mock_commit.id = "12345678"
    mock_commit.message = "Initial commit"
    mock_commit.parents = []
    mock_commit.tree.diff_to_tree.return_value.deltas = [mock_delta]

    mock_repo = MagicMock()
    mock_repo.walk.return_value = [mock_commit]
    mock_pygit2.Repository.return_value = mock_repo

    sys.modules["pygit2"] = mock_pygit2

    out = collect_recent_changes(tmp_path, since="7 days ago")
    assert "a.py" in out
    assert "Initial commit" in out

    del sys.modules["pygit2"]


def test_collect_git_metadata_non_repo_falls_back(tmp_path: Path) -> None:
    file_path = tmp_path / "main.py"
    file_path.write_text("print('hello')\n")

    result = collect_git_metadata([file_path], tmp_path, no_git=False)

    assert file_path in result
    assert result[file_path].commit_count == 0
    assert result[file_path].last_modified_ts > 0


def test_collect_git_metadata_unborn_head_falls_back(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    file_path = tmp_path / "main.py"
    file_path.write_text("print('hello')\n")

    result = collect_git_metadata([file_path], tmp_path, no_git=False)

    assert file_path in result
    assert result[file_path].commit_count == 0
    assert result[file_path].last_modified_ts > 0


def test_collect_git_metadata_walks_non_main_default_branch(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "checkout", "-b", "trunk")
    _git(tmp_path, "config", "user.name", "Test User")
    _git(tmp_path, "config", "user.email", "test@example.com")

    file_path = tmp_path / "main.py"
    file_path.write_text("print('hello')\n")
    _git(tmp_path, "add", "main.py")
    _git(tmp_path, "commit", "-m", "Initial commit on trunk")

    result = collect_git_metadata([file_path], tmp_path, no_git=False)

    assert file_path in result
    assert result[file_path].commit_count >= 1
