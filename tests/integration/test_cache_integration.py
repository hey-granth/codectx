"""Integration tests for cache functionality."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from codectx.cache import Cache
from codectx.cache.manifest import load_manifest
from codectx.cache.paths import get_cache_root, get_manifest_path
from codectx.config.loader import load_config


class TestCacheIntegration:
    """Integration tests for end-to-end cache behavior."""

    def test_cache_directory_creation(self):
        """Test that cache directories are created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()

            # Mock CACHE_DIR_NAME to use a temp directory
            with patch("codectx.cache.cache.CACHE_DIR_NAME", ".temp_cache"):
                temp_cache_dir = repo_root / ".temp_cache"

                assert not temp_cache_dir.exists()

                # Accessing cache should create directory
                cache = Cache(repo_root)
                cache.save()  # This creates the directory
                assert temp_cache_dir.exists()
                assert temp_cache_dir.is_dir()

    def test_manifest_up_to_date_check(self):
        """Test manifest-based up-to-date checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()

            # Create a test file
            test_file = repo_root / "test.py"
            test_file.write_text("print('hello')")

            # Load config
            config = load_config(repo_root, token_budget=100000, output_format="markdown")

            # Initially no manifest, should not be up to date
            cache = Cache(repo_root)
            assert not cache.is_output_up_to_date(config)

            # Create manifest manually
            from codectx.cache.manifest import save_manifest, collect_file_hashes, Manifest, ManifestOptions
            from codectx import __version__
            import time

            manifest_path = get_manifest_path(str(repo_root))
            file_hashes = collect_file_hashes([str(test_file)], str(repo_root))
            manifest = Manifest(
                codectx_version=__version__,
                generated_at=time.time(),
                repo_root=str(repo_root),
                options=ManifestOptions(
                    budget=100000,
                    format="markdown",
                    exclude=[],
                ),
                files=file_hashes,
            )
            save_manifest(manifest_path, manifest)

            # Now should be up to date
            assert cache.is_output_up_to_date(config)

            # Change file content
            test_file.write_text("print('changed')")

            # Should not be up to date anymore
            assert not cache.is_output_up_to_date(config)

    def test_parse_result_caching(self):
        """Test caching of parse results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()

            # Create test file
            test_file = repo_root / "test.py"
            test_file.write_text("def hello():\n    return 'world'")

            cache = Cache(repo_root)

            # Initially no cached result
            import hashlib
            file_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
            cached = cache.get_parse_result(test_file, file_hash)
            assert cached is None

            # Parse and cache
            from codectx.parser.treesitter import parse_files
            parse_results = parse_files([test_file])
            result = parse_results[test_file]

            cache.put_parse_result(test_file, file_hash, result)
            cache.save()

            # Should be cached now
            cached = cache.get_parse_result(test_file, file_hash)
            assert cached is not None
            assert cached.language == result.language
            assert cached.raw_source == result.raw_source

            # Different hash should not match
            cached_wrong = cache.get_parse_result(test_file, "wronghash")
            assert cached_wrong is None

    def test_cache_export_import(self):
        """Test cache export and import functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            repo_root = tmpdir_path / "repo"
            repo_root.mkdir()

            # Create some cache data
            cache = Cache(repo_root)
            cache.save()  # Creates cache directory

            # Add a parse result
            test_file = repo_root / "test.py"
            test_file.write_text("print('test')")

            from codectx.parser.treesitter import parse_files
            import hashlib

            parse_results = parse_files([test_file])
            result = parse_results[test_file]
            file_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

            cache.put_parse_result(test_file, file_hash, result)
            cache.save()

            # Export cache
            archive_path = tmpdir_path / "cache.tar.gz"
            cache.export_cache(archive_path)
            assert archive_path.exists()

            # Create new repo and import
            new_repo = tmpdir_path / "new_repo"
            new_repo.mkdir()

            Cache.import_cache(archive_path, new_repo)

            # Verify import worked
            new_cache = Cache(new_repo)
            cached = new_cache.get_parse_result(test_file, file_hash)
            assert cached is not None

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir) / "repo"
            repo_root.mkdir()

            cache = Cache(repo_root)
            cache.save()  # Creates cache directory

            cache_dir = cache.cache_dir
            assert cache_dir.exists()

            # Clear cache
            import shutil
            shutil.rmtree(cache_dir)
            assert not cache_dir.exists()

    def test_repo_isolation(self):
        """Test that different repos have isolated caches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            repo1 = tmpdir_path / "repo1"
            repo1.mkdir()
            repo2 = tmpdir_path / "repo2"
            repo2.mkdir()

            cache1 = Cache(repo1)
            cache2 = Cache(repo2)

            cache_root1 = get_cache_root(str(repo1))
            cache_root2 = get_cache_root(str(repo2))

            assert cache_root1 != cache_root2
            assert str(cache_root1) != str(cache_root2)

            # Create file in repo1 cache
            test_file1 = cache_root1 / "test.txt"
            test_file1.write_text("repo1")

            # Should not exist in repo2 cache
            test_file2 = cache_root2 / "test.txt"
            assert not test_file2.exists()

