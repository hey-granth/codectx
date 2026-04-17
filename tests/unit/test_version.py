"""Tests for package version exposure."""

from __future__ import annotations

import importlib
import inspect
from unittest.mock import patch


def test_version_is_string() -> None:
    from codectx import __version__

    assert isinstance(__version__, str)


def test_version_not_hardcoded() -> None:
    import codectx

    src = inspect.getsource(codectx)
    assert "importlib.metadata" in src


def test_version_fallback() -> None:
    from importlib.metadata import PackageNotFoundError

    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        import codectx

        importlib.reload(codectx)
        assert codectx.__version__ == "0.0.0-dev"

    import codectx

    importlib.reload(codectx)
