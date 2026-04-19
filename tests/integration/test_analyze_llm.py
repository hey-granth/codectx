"""Integration tests for analyze with --llm."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from codectx.cli import app

runner = CliRunner()


def test_analyze_llm_uses_summary_fallback_path(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "main.py").write_text("print('entry')\n")
    (tmp_path / "core.py").write_text("def work():\n    return 1\n")

    monkeypatch.setattr("codectx.cli._LLM_AVAILABLE", True)
    monkeypatch.setattr("codectx.llm.llm_summarize_sync", lambda *args, **kwargs: "LLM summary")

    result = runner.invoke(app, ["analyze", str(tmp_path), "--llm", "--no-git"])

    assert result.exit_code == 0
    assert (tmp_path / "CONTEXT.md").exists()
