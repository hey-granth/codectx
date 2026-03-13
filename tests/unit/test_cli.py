"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from codectx.cli import app

runner = CliRunner()


def test_analyze_command(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    result = runner.invoke(app, ["analyze", str(tmp_path)])

    # It might create CONTEXT.md
    assert result.exit_code == 0
    assert (tmp_path / "CONTEXT.md").exists()


def test_analyze_layers(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    result = runner.invoke(app, ["analyze", str(tmp_path), "--layers"])

    assert result.exit_code == 0
    assert (tmp_path / "REPO_MAP.md").exists()
    assert (tmp_path / "CORE_CONTEXT.md").exists()
    assert (tmp_path / "FULL_CONTEXT.md").exists()


def test_search_command(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    # We can mock semantic_score to avoid needing sentence-transformers in CI if it fails
    with (
        patch("codectx.ranker.semantic.is_available", return_value=True),
        patch("codectx.ranker.semantic.semantic_score") as mock_score,
    ):
        mock_score.return_value = {tmp_path / "main.py": 0.9}
        result = runner.invoke(app, ["search", "hello", "--root", str(tmp_path)])

        assert result.exit_code == 0
        assert "main.py" in result.output
        assert "0.9" in result.output


def test_search_command_not_found(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    with (
        patch("codectx.ranker.semantic.is_available", return_value=True),
        patch("codectx.ranker.semantic.semantic_score") as mock_score,
    ):
        mock_score.return_value = {tmp_path / "main.py": 0.0}
        result = runner.invoke(app, ["search", "hello", "--root", str(tmp_path)])

        assert result.exit_code == 0
        assert "No relevant files found" in result.output


def test_watch_command_interrupt(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    # Mock watchfiles to yield one change then raise KeyboardInterrupt
    with patch("watchfiles.watch") as mock_watch:

        def fake_watch(*args, **kwargs):
            yield {(1, str(tmp_path / "main.py"))}
            raise KeyboardInterrupt()

        mock_watch.side_effect = fake_watch

        result = runner.invoke(app, ["watch", str(tmp_path)])
        assert result.exit_code == 0
        assert "Watch stopped." in result.output
