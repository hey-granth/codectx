"""Tests for structured summary constants section."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.tiered import _structured_summary_content
from codectx.parser.base import ParseResult, Symbol


def _result(path: Path, source: str) -> ParseResult:
    return ParseResult(
        path=path,
        language="python",
        imports=(),
        symbols=(),
        docstrings=(),
        raw_source=source,
        line_count=max(source.count("\n"), 1),
    )


def test_all_caps_variable_detected(tmp_path: Path) -> None:
    src = "MAX_RETRIES = 3\nDATABASE_URL = 'postgres://'\n"
    path = tmp_path / "test.py"
    summary = _structured_summary_content(_result(path, src), path, tmp_path)
    assert "## Constants" in summary
    assert "MAX_RETRIES" in summary


def test_lowercase_variable_not_in_constants_when_symbols_exist(tmp_path: Path) -> None:
    src = "def run():\n    return 1\n\ncount = 0\n"
    path = tmp_path / "test.py"
    pr = ParseResult(
        path=path,
        language="python",
        imports=(),
        symbols=(
            Symbol(
                name="run",
                kind="function",
                signature="def run()",
                docstring="",
                start_line=1,
                end_line=2,
            ),
        ),
        docstrings=(),
        raw_source=src,
        line_count=4,
    )
    summary = _structured_summary_content(pr, path, tmp_path)
    if "## Constants" in summary:
        assert "count" not in summary.split("## Constants", 1)[-1]


def test_long_value_truncated(tmp_path: Path) -> None:
    src = "LONG = " + repr(list(range(100))) + "\n"
    path = tmp_path / "test.py"
    summary = _structured_summary_content(_result(path, src), path, tmp_path)
    assert "<complex expression>" in summary


def test_config_like_file_all_assignments(tmp_path: Path) -> None:
    src = "host = 'localhost'\nport = 5432\n"
    path = tmp_path / "config.py"
    summary = _structured_summary_content(_result(path, src), path, tmp_path)
    assert "host" in summary
    assert "port" in summary


def test_parse_failure_does_not_crash(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    summary = _structured_summary_content(_result(path, "{{{{INVALID{{{{"), path, tmp_path)
    assert isinstance(summary, str)
