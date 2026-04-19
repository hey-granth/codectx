"""Integration test for analyze --format json."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from codectx.cli import app

runner = CliRunner()


def test_analyze_json_cli(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")

    result = runner.invoke(app, ["analyze", str(tmp_path), "--format", "json", "--no-git"])

    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert "files" in parsed
    assert "stats" in parsed
    assert result.stderr == ""
