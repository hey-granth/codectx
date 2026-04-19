from typer.testing import CliRunner

from codectx.cli import app

runner = CliRunner()


def test_top_level_help_lists_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["analyze", "watch", "cache"]:
        assert cmd in result.output


def test_no_args_prints_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code in {0, 2}
    assert "analyze" in result.output


def test_analyze_help_lists_all_flags() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
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
        assert flag in result.output, f"Missing from analyze --help: {flag}"


def test_analyze_help_has_llm_panel() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "LLM Summarization" in result.output


def test_analyze_help_has_cache_panel() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Cache" in result.output


def test_watch_help_lists_all_flags() -> None:
    result = runner.invoke(app, ["watch", "--help"])
    assert result.exit_code == 0
    for flag in ["--debounce", "--budget", "--output", "--format", "--exclude"]:
        assert flag in result.output, f"Missing from watch --help: {flag}"


def test_cache_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["cache", "--help"])
    assert result.exit_code == 0
    for cmd in ["info", "clear"]:
        assert cmd in result.output


def test_cache_info_help() -> None:
    result = runner.invoke(app, ["cache", "info", "--help"])
    assert result.exit_code == 0


def test_cache_clear_help_lists_all_flag() -> None:
    result = runner.invoke(app, ["cache", "clear", "--help"])
    assert result.exit_code == 0
    assert "--all" in result.output


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
        lines = result.output.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--") and stripped.endswith(stripped.split()[0]):
                assert False, f"Flag with no description found in `{' '.join(cmd)}`: {stripped}"

