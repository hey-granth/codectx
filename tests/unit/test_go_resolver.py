"""Tests for Go resolver go.mod module parsing behavior."""

from __future__ import annotations

from pathlib import Path

from codectx.graph.resolver import _parse_go_module, resolve_import


def test_parse_go_module_standard(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module github.com/user/repo\n\ngo 1.21\n")
    assert _parse_go_module(str(tmp_path)) == "github.com/user/repo"


def test_parse_go_module_missing(tmp_path: Path) -> None:
    assert _parse_go_module(str(tmp_path)) is None


def test_import_resolved_with_module_prefix(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module github.com/user/repo\n")
    (tmp_path / "pkg" / "util").mkdir(parents=True)
    target = tmp_path / "pkg" / "util" / "util.go"
    target.write_text("package util\n")
    source = tmp_path / "main.go"
    source.write_text('import "github.com/user/repo/pkg/util"\n')

    all_files = frozenset(["main.go", "pkg/util/util.go"])
    resolved = resolve_import('"github.com/user/repo/pkg/util"', "go", source, tmp_path, all_files)

    assert resolved == [target]


def test_stdlib_import_not_resolved(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module github.com/user/repo\n")
    source = tmp_path / "main.go"
    source.write_text('import "fmt"\n')
    all_files = frozenset(["main.go"])

    assert resolve_import('"fmt"', "go", source, tmp_path, all_files) == []


def test_external_module_not_resolved(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module github.com/user/repo\n")
    source = tmp_path / "main.go"
    source.write_text('import "github.com/some/other/pkg"\n')
    all_files = frozenset(["main.go"])

    assert resolve_import('"github.com/some/other/pkg"', "go", source, tmp_path, all_files) == []
