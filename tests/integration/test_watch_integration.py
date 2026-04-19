"""Integration tests for watch command behavior."""

from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from codectx.cli import app

runner = CliRunner()


def test_watch_regenerates_for_source_changes(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    original_import_module = importlib.import_module

    def import_side_effect(name: str, package: str | None = None):
        if name in {"watchdog.events", "watchdog.observers"}:
            raise ImportError("no watchdog")
        return original_import_module(name, package)

    with (
        patch("importlib.import_module", side_effect=import_side_effect),
        patch("watchfiles.watch") as mock_watch,
        patch("codectx.cli._run_pipeline") as mock_run,
    ):
        mock_run.return_value = None

        def fake_watch(*args, **kwargs):
            yield {(1, str(tmp_path / "main.py"))}
            raise KeyboardInterrupt()

        mock_watch.side_effect = fake_watch
        result = runner.invoke(app, ["watch", str(tmp_path)])

    assert result.exit_code == 0
    # Initial run + one relevant change
    assert mock_run.call_count == 2


def test_watch_ignores_lock_file_changes(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    original_import_module = importlib.import_module

    def import_side_effect(name: str, package: str | None = None):
        if name in {"watchdog.events", "watchdog.observers"}:
            raise ImportError("no watchdog")
        return original_import_module(name, package)

    with (
        patch("importlib.import_module", side_effect=import_side_effect),
        patch("watchfiles.watch") as mock_watch,
        patch("codectx.cli._run_pipeline") as mock_run,
    ):
        mock_run.return_value = None

        def fake_watch(*args, **kwargs):
            yield {(1, str(tmp_path / "uv.lock"))}
            raise KeyboardInterrupt()

        mock_watch.side_effect = fake_watch
        result = runner.invoke(app, ["watch", str(tmp_path)])

    assert result.exit_code == 0
    # Only initial run should occur
    assert mock_run.call_count == 1
