"""Unit tests for cache functionality."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from codectx.cache.manifest import (
    Manifest,
    ManifestOptions,
    collect_file_hashes,
    hash_file,
    is_up_to_date,
    load_manifest,
    save_manifest,
)
from codectx.cache.paths import get_cache_root, get_embeddings_path, get_manifest_path


class TestPaths:
    """Test repo-scoped cache path resolution."""

    def test_get_cache_root_basic(self):
        """Test basic cache root generation."""
        repo_root = "/home/user/myproject"
        cache_root = get_cache_root(repo_root)
        expected_hash = hashlib.sha256(str(Path(repo_root).resolve()).encode()).hexdigest()[:16]
        assert expected_hash in str(cache_root)
        assert "codectx" in str(cache_root)

    def test_get_cache_root_xdg_env(self):
        """Test XDG_CACHE_HOME environment variable."""
        with patch.dict(os.environ, {"XDG_CACHE_HOME": "/tmp/xdg"}):
            cache_root = get_cache_root("/some/repo")
            assert str(cache_root).startswith("/tmp/xdg/codectx/")

    def test_get_cache_root_no_xdg(self):
        """Test fallback to ~/.cache when XDG_CACHE_HOME not set."""
        with tempfile.TemporaryDirectory() as tmp_home:
            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.home", return_value=Path(tmp_home)):
                    cache_root = get_cache_root("/some/repo")
                    assert str(cache_root).startswith(f"{tmp_home}/.cache/codectx/")

    def test_get_manifest_path(self):
        """Test manifest path generation."""
        repo_root = "/test/repo"
        manifest_path = get_manifest_path(repo_root)
        cache_root = get_cache_root(repo_root)
        assert manifest_path == cache_root / "manifest.json"

    def test_get_embeddings_path(self):
        """Test embeddings path generation."""
        repo_root = "/test/repo"
        embeddings_path = get_embeddings_path(repo_root)
        cache_root = get_cache_root(repo_root)
        assert embeddings_path == cache_root / "embeddings.lance"


class TestManifest:
    """Test manifest I/O and validation."""

    def test_hash_file(self):
        """Test SHA256 file hashing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            hash_value = hash_file(temp_path)
            expected = hashlib.sha256(b"test content").hexdigest()
            assert hash_value == expected
        finally:
            os.unlink(temp_path)

    def test_collect_file_hashes(self):
        """Test collecting hashes for multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            file1 = tmpdir_path / "file1.txt"
            file1.write_text("content1")
            file2 = tmpdir_path / "file2.txt"
            file2.write_text("content2")

            # Test absolute paths
            hashes = collect_file_hashes([str(file1), str(file2)], str(tmpdir_path))
            assert len(hashes) == 2
            assert hashes["file1.txt"] == hashlib.sha256(b"content1").hexdigest()
            assert hashes["file2.txt"] == hashlib.sha256(b"content2").hexdigest()

    def test_collect_file_hashes_relative(self):
        """Test collecting hashes with relative paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            file1 = tmpdir_path / "file1.txt"
            file1.write_text("content1")

            # Test relative path
            hashes = collect_file_hashes(["file1.txt"], str(tmpdir_path))
            assert len(hashes) == 1
            assert hashes["file1.txt"] == hashlib.sha256(b"content1").hexdigest()

    def test_collect_file_hashes_missing_file(self):
        """Test handling of missing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            hashes = collect_file_hashes(["nonexistent.txt"], tmpdir)
            assert len(hashes) == 0

    def test_save_and_load_manifest(self):
        """Test saving and loading manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"

            manifest = Manifest(
                codectx_version="0.3.0",
                generated_at=1234567890.0,
                repo_root="/test/repo",
                options=ManifestOptions(
                    budget=100000,
                    format="markdown",
                    exclude=["*.tmp"],
                ),
                files={"file1.py": "hash1", "file2.py": "hash2"},
            )

            save_manifest(manifest_path, manifest)
            loaded = load_manifest(manifest_path)

            assert loaded is not None
            assert loaded.codectx_version == "0.3.0"
            assert loaded.generated_at == 1234567890.0
            assert loaded.repo_root == "/test/repo"
            assert loaded.options.budget == 100000
            assert loaded.options.format == "markdown"
            assert loaded.options.exclude == ["*.tmp"]
            assert loaded.files == {"file1.py": "hash1", "file2.py": "hash2"}

    def test_load_manifest_missing_file(self):
        """Test loading non-existent manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "missing.json"
            loaded = load_manifest(manifest_path)
            assert loaded is None

    def test_load_manifest_invalid_json(self):
        """Test loading invalid JSON manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "invalid.json"
            manifest_path.write_text("invalid json")

            loaded = load_manifest(manifest_path)
            assert loaded is None

    def test_is_up_to_date_matching(self):
        """Test up-to-date check with matching manifest."""
        manifest = Manifest(
            codectx_version="0.3.0",
            generated_at=1234567890.0,
            repo_root="/test/repo",
            options=ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"]),
            files={"file1.py": "hash1", "file2.py": "hash2"},
        )

        current_hashes = {"file1.py": "hash1", "file2.py": "hash2"}
        current_options = ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"])
        current_version = "0.3.0"

        assert is_up_to_date(manifest, current_hashes, current_options, current_version)

    def test_is_up_to_date_version_mismatch(self):
        """Test up-to-date check with version mismatch."""
        manifest = Manifest(
            codectx_version="0.2.0",
            generated_at=1234567890.0,
            repo_root="/test/repo",
            options=ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"]),
            files={"file1.py": "hash1", "file2.py": "hash2"},
        )

        current_hashes = {"file1.py": "hash1", "file2.py": "hash2"}
        current_options = ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"])
        current_version = "0.3.0"

        assert not is_up_to_date(manifest, current_hashes, current_options, current_version)

    def test_is_up_to_date_options_mismatch(self):
        """Test up-to-date check with options mismatch."""
        manifest = Manifest(
            codectx_version="0.3.0",
            generated_at=1234567890.0,
            repo_root="/test/repo",
            options=ManifestOptions(budget=50000, format="markdown", exclude=["*.tmp"]),
            files={"file1.py": "hash1", "file2.py": "hash2"},
        )

        current_hashes = {"file1.py": "hash1", "file2.py": "hash2"}
        current_options = ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"])
        current_version = "0.3.0"

        assert not is_up_to_date(manifest, current_hashes, current_options, current_version)

    def test_is_up_to_date_files_mismatch(self):
        """Test up-to-date check with file hash mismatch."""
        manifest = Manifest(
            codectx_version="0.3.0",
            generated_at=1234567890.0,
            repo_root="/test/repo",
            options=ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"]),
            files={"file1.py": "hash1", "file2.py": "hash2"},
        )

        current_hashes = {"file1.py": "hash1", "file2.py": "different_hash"}
        current_options = ManifestOptions(budget=100000, format="markdown", exclude=["*.tmp"])
        current_version = "0.3.0"

        assert not is_up_to_date(manifest, current_hashes, current_options, current_version)

    def test_is_up_to_date_none_manifest(self):
        """Test up-to-date check with None manifest."""
        current_hashes = {"file1.py": "hash1"}
        current_options = ManifestOptions(budget=100000, format="markdown", exclude=[])
        current_version = "0.3.0"

        assert not is_up_to_date(None, current_hashes, current_options, current_version)


class TestEviction:
    """Test embedding eviction functionality."""

    @patch("codectx.ranker.semantic.lancedb")
    def test_evict_stale_embeddings(self, mock_lancedb):
        """Test eviction of stale embeddings."""
        from codectx.ranker.semantic import _evict_stale_embeddings
        from unittest.mock import MagicMock

        # Mock LanceDB table
        mock_table = MagicMock()
        mock_lancedb.connect.return_value.open_table.return_value = mock_table

        current_paths = {"file1.py", "file2.py"}
        _evict_stale_embeddings(mock_table, current_paths)

        # Verify delete was called with correct query format
        assert mock_table.delete.called
        call_args = mock_table.delete.call_args[0][0]
        assert call_args.startswith("file_path NOT IN (")
        assert "'file1.py'" in call_args
        assert "'file2.py'" in call_args
        assert call_args.endswith(")")

    @patch("codectx.ranker.semantic.lancedb")
    def test_evict_stale_embeddings_empty(self, mock_lancedb):
        """Test eviction with empty current paths."""
        from codectx.ranker.semantic import _evict_stale_embeddings

        mock_table = mock_lancedb.connect.return_value.open_table.return_value

        _evict_stale_embeddings(mock_table, set())

        # Should not call delete when no current paths
        mock_table.delete.assert_not_called()

    @patch("codectx.ranker.semantic.lancedb")
    def test_evict_stale_embeddings_error(self, mock_lancedb):
        """Test eviction handles errors gracefully."""
        from codectx.ranker.semantic import _evict_stale_embeddings

        mock_table = mock_lancedb.connect.return_value.open_table.return_value
        mock_table.delete.side_effect = Exception("DB error")

        current_paths = {"file1.py"}

        # Should not raise exception
        _evict_stale_embeddings(mock_table, current_paths)
