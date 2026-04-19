from typer.testing import CliRunner

import re

from codectx.cli import app


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


runner = CliRunner(env={"COLUMNS": "200"})


def test_top_level_help_lists_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    for cmd in ["analyze", "watch", "cache"]:
        assert cmd in output


def test_no_args_prints_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code in {0, 2}
    output = strip_ansi(result.output)
    assert "analyze" in output


def test_analyze_help_lists_all_flags() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    for flag in [
        "--budget",
        "--output",
        "--format",
        "--exclude",
        "--force",
        "--llm",
        "--llm-provider",
        "--llm-model",
        "--llm-api-key",
        "--llm-base-url",
        "--llm-max-tokens",
    ]:
        assert flag in output, f"Missing from analyze --help: {flag}"


def test_analyze_help_has_llm_panel() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "LLM Summarization" in output


def test_analyze_help_has_cache_panel() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "Cache" in output


def test_watch_help_lists_all_flags() -> None:
    result = runner.invoke(app, ["watch", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    for flag in ["--debounce", "--budget", "--output", "--format", "--exclude"]:
        assert flag in output, f"Missing from watch --help: {flag}"


def test_cache_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["cache", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    for cmd in ["info", "clear"]:
        assert cmd in output


def test_cache_info_help() -> None:
    result = runner.invoke(app, ["cache", "info", "--help"])
    assert result.exit_code == 0


def test_cache_clear_help_lists_all_flag() -> None:
    result = runner.invoke(app, ["cache", "clear", "--help"])
    assert result.exit_code == 0
    output = strip_ansi(result.output)
    assert "--all" in output


def test_no_flag_has_empty_description() -> None:
    commands = [
        ["analyze", "--help"],
        ["watch", "--help"],
        ["cache", "info", "--help"],
        ["cache", "clear", "--help"],
    ]
    for cmd in commands:
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        lines = output.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--") and stripped.endswith(stripped.split()[0]):
                raise AssertionError(
                    f"Flag with no description found in `{' '.join(cmd)}`: {stripped}"
                )
