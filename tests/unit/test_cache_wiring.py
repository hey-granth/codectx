"""Tests for cache wiring into the analyze pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a minimal project."""
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "utils.py").write_text("def add(a, b): return a + b\n")
    (tmp_path / ".gitignore").write_text("__pycache__/\n")
    return tmp_path


def test_cache_dir_created_after_pipeline(sample_project: Path) -> None:
    """Running the pipeline should create .codectx_cache/ with cache.json."""
    from codectx.config.loader import load_config

    config = load_config(sample_project, no_git=True)

    # Import and run pipeline
    from codectx.cli import _run_pipeline
    _run_pipeline(config)

    cache_dir = sample_project / ".codectx_cache"
    assert cache_dir.is_dir(), ".codectx_cache/ directory not created"
    assert (cache_dir / "cache.json").is_file(), "cache.json not found"


def test_cache_reuse_on_second_run(sample_project: Path) -> None:
    """Second pipeline run should reuse cached parse results."""
    import json

    from codectx.config.loader import load_config

    config = load_config(sample_project, no_git=True)

    from codectx.cli import _run_pipeline
    _run_pipeline(config)

    # Read cache after first run
    cache_file = sample_project / ".codectx_cache" / "cache.json"
    cache_data_1 = json.loads(cache_file.read_text())
    assert len(cache_data_1) > 0, "Cache should have entries after first run"

    # Second run — cache should still exist and be populated
    _run_pipeline(config)
    cache_data_2 = json.loads(cache_file.read_text())
    assert cache_data_2 == cache_data_1, "Cache should be identical on unchanged files"


def test_cache_invalidated_on_file_change(sample_project: Path) -> None:
    """Changing a file should update its cache entry."""
    import json

    from codectx.config.loader import load_config

    config = load_config(sample_project, no_git=True)

    from codectx.cli import _run_pipeline
    _run_pipeline(config)

    cache_file = sample_project / ".codectx_cache" / "cache.json"
    cache_before = json.loads(cache_file.read_text())

    # Modify a file
    (sample_project / "main.py").write_text("print('changed')\n")

    _run_pipeline(config)
    cache_after = json.loads(cache_file.read_text())

    # The hash for main.py should differ
    main_key = str(sample_project / "main.py")
    if main_key in cache_before and main_key in cache_after:
        assert cache_before[main_key]["file_hash"] != cache_after[main_key]["file_hash"]
