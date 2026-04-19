"""Tests for config-file demotion to peripheral tier."""

from __future__ import annotations

from pathlib import Path

from codectx.compressor.budget import TokenBudget
from codectx.compressor.tiered import compress_files, is_config_file
from codectx.parser.base import ParseResult


def _pr(path: Path, source: str = "") -> ParseResult:
    return ParseResult(
        path=path,
        language="unknown",
        imports=(),
        symbols=(),
        docstrings=(),
        raw_source=source,
        line_count=max(source.count("\n"), 1),
    )


def test_pyproject_toml_is_config() -> None:
    assert is_config_file("pyproject.toml")


def test_package_json_is_config() -> None:
    assert is_config_file("package.json")


def test_python_source_not_config() -> None:
    assert is_config_file("src/main.py") is False


def test_json_not_config_if_imported() -> None:
    assert is_config_file("data/schema.json", imported_by={"src/loader.py"}) is False


def test_config_files_demoted_to_peripheral(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname='x'\n")
    code = tmp_path / "main.py"
    code.write_text("print('x')\n")

    parse_results = {
        pyproject: _pr(pyproject, "[project]\nname='x'\n"),
        code: ParseResult(
            path=code,
            language="python",
            imports=(),
            symbols=(),
            docstrings=(),
            raw_source="print('x')\n",
            line_count=1,
        ),
    }
    scores = {pyproject: 0.99, code: 0.5}

    compressed = compress_files(parse_results, scores, TokenBudget(10000), tmp_path)
    tier_by_name = {cf.path.name: cf.tier for cf in compressed}

    assert tier_by_name["pyproject.toml"] == 3


def test_existing_core_files_unaffected(tmp_path: Path) -> None:
    core = tmp_path / "service.py"
    util = tmp_path / "helper.py"
    core.write_text("def run():\n    pass\n")
    util.write_text("def helper():\n    pass\n")

    parse_results = {
        core: ParseResult(
            path=core,
            language="python",
            imports=(),
            symbols=(),
            docstrings=(),
            raw_source=core.read_text(),
            line_count=2,
        ),
        util: ParseResult(
            path=util,
            language="python",
            imports=(),
            symbols=(),
            docstrings=(),
            raw_source=util.read_text(),
            line_count=2,
        ),
    }
    scores = {core: 1.0, util: 0.1}

    compressed = compress_files(parse_results, scores, TokenBudget(10000), tmp_path)
    tier_by_name = {cf.path.name: cf.tier for cf in compressed}

    assert tier_by_name["service.py"] == 1
