"""Tests for CI cache export/import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codectx.cache import Cache


@pytest.fixture
def populated_cache(tmp_path: Path) -> Path:
    """Create a project with a populated cache."""
    (tmp_path / "main.py").write_text("print('hello')\n")

    from codectx.cli import _run_pipeline
    from codectx.config.loader import load_config

    config = load_config(tmp_path, no_git=True)
    _run_pipeline(config)

    assert (tmp_path / ".codectx_cache" / "cache.json").is_file()
    return tmp_path


def test_export_creates_archive(populated_cache: Path) -> None:
    """export_cache should create a tar.gz archive."""
    cache = Cache(populated_cache)
    archive = populated_cache / "cache_export.tar.gz"
    cache.export_cache(archive)

    assert archive.is_file()
    assert archive.stat().st_size > 0


def test_round_trip(populated_cache: Path, tmp_path: Path) -> None:
    """Exported cache should be importable into a fresh directory."""
    # Export
    cache = Cache(populated_cache)
    archive = populated_cache / "cache_export.tar.gz"
    cache.export_cache(archive)

    # Import into fresh directory
    fresh_root = tmp_path / "fresh_project"
    fresh_root.mkdir()

    _ = Cache.import_cache(archive, fresh_root)

    # Verify cache data was restored
    cache_file = fresh_root / ".codectx_cache" / "cache.json"
    assert cache_file.is_file()

    original_data = json.loads((populated_cache / ".codectx_cache" / "cache.json").read_text())
    imported_data = json.loads(cache_file.read_text())
    assert len(imported_data) == len(original_data)


def test_export_from_empty_cache(tmp_path: Path) -> None:
    """export_cache from empty cache should still create an archive (cache dir is created by save)."""
    cache = Cache(tmp_path)
    archive = tmp_path / "cache.tar.gz"

    # export_cache calls save() first, so cache dir is created
    cache.export_cache(archive)
    assert archive.is_file()


def test_import_raises_without_archive(tmp_path: Path) -> None:
    """import_cache should raise if archive doesn't exist."""
    with pytest.raises(FileNotFoundError):
        Cache.import_cache(tmp_path / "nonexistent.tar.gz", tmp_path)
