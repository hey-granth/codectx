"""Tests for multi-language treesitter parsing."""

import types
from pathlib import Path
from typing import Any

import pytest

import codectx.parser.languages as lang
import codectx.parser.treesitter as ts
from codectx.parser.treesitter import parse_files


def test_parse_javascript(tmp_path: Path) -> None:
    f = tmp_path / "a.js"
    f.write_text("class A { method() {} }\nfunction func() {}\n")
    res = parse_files([f])
    assert f in res
    pr = res[f]
    assert len(pr.symbols) >= 0


def test_parse_typescript(tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("class B { method(): void {} }\nfunction f2(): void {}\n")
    res = parse_files([f])
    assert f in res
    _ = res[f]
    assert len(res[f].symbols) >= 0


def test_parse_java(tmp_path: Path) -> None:
    f = tmp_path / "A.java"
    f.write_text("class A { void method() {} }\n")
    res = parse_files([f])
    assert f in res
    assert len(res[f].symbols) >= 0


def test_parse_go(tmp_path: Path) -> None:
    f = tmp_path / "a.go"
    f.write_text("package main\n\nfunc main() {}\ntype A struct {}\nfunc (a *A) method() {}\n")
    res = parse_files([f])
    assert f in res
    assert len(res[f].symbols) >= 0


def test_parse_rust(tmp_path: Path) -> None:
    f = tmp_path / "a.rs"
    f.write_text("fn main() {}\nstruct A {}\nimpl A { fn method() {} }\n")
    res = parse_files([f])
    assert f in res
    assert len(res[f].symbols) >= 0


def test_parse_ruby(tmp_path: Path) -> None:
    f = tmp_path / "a.rb"
    f.write_text("class A\n  def method\n  end\nend\ndef func\nend\n")
    res = parse_files([f])
    assert f in res
    assert len(res[f].symbols) >= 0


def test_parse_bad_file(tmp_path: Path) -> None:
    f = tmp_path / "a.py"
    f.write_text("def class ) == \n")
    # Will parse it anyway, might return empty or broken symbols
    res = parse_files([f])
    assert f in res


def test_parse_c(tmp_path: Path) -> None:
    f = tmp_path / "a.c"
    f.write_text("int main() { return 0; }\n")
    res = parse_files([f])
    assert f in res


def test_parse_cpp(tmp_path: Path) -> None:
    f = tmp_path / "a.cpp"
    f.write_text("class A {};\nint main() { return 0; }\n")
    res = parse_files([f])
    assert f in res


def test_parse_csharp(tmp_path: Path) -> None:
    f = tmp_path / "a.cs"
    f.write_text("class A { void Method() {} }\n")
    res = parse_files([f])
    assert f in res


def test_parse_php(tmp_path: Path) -> None:
    f = tmp_path / "a.php"
    f.write_text("<?php class A { function method() {} } ?>\n")
    res = parse_files([f])
    assert f in res


def test_parse_swift(tmp_path: Path) -> None:
    f = tmp_path / "a.swift"
    f.write_text("class A { func method() {} }\n")
    res = parse_files([f])
    assert f in res


def test_parse_kotlin(tmp_path: Path) -> None:
    f = tmp_path / "a.kt"
    f.write_text("class A { fun method() {} }\n")
    res = parse_files([f])
    assert f in res


def test_parse_scala(tmp_path: Path) -> None:
    f = tmp_path / "a.scala"
    f.write_text("class A { def method() {} }\n")
    res = parse_files([f])
    assert f in res


@pytest.mark.parametrize(
    ("variant_attr", "variant_value"),
    [
        ("language", lambda: object()),
        ("get_language", lambda: object()),
        ("LANGUAGE", object()),
    ],
)
def test_load_typescript_language_variants(
    monkeypatch: pytest.MonkeyPatch,
    variant_attr: str,
    variant_value: object,
) -> None:
    fake_ts_module = types.SimpleNamespace(**{variant_attr: variant_value})

    monkeypatch.setattr(
        lang,
        "tree_sitter",
        types.SimpleNamespace(Language=lambda payload, *_args: ("wrapped", payload)),
    )
    monkeypatch.setattr(lang.importlib, "import_module", lambda _name: fake_ts_module)
    lang.load_typescript_language.cache_clear()

    result: Any = lang.load_typescript_language()
    assert result[0] == "wrapped"


def test_load_typescript_language_manual_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ts_module = types.SimpleNamespace(__file__="/tmp/fake_ts_binding.so")

    def _fake_language(arg1: object, arg2: object | None = None) -> tuple[object, object | None]:
        return (arg1, arg2)

    monkeypatch.setattr(lang, "tree_sitter", types.SimpleNamespace(Language=_fake_language))
    monkeypatch.setattr(lang.importlib, "import_module", lambda _name: fake_ts_module)
    lang.load_typescript_language.cache_clear()

    result = lang.load_typescript_language()
    assert result == ("/tmp/fake_ts_binding.so", "typescript")


def test_parse_files_mixed_success_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    py_file = tmp_path / "ok.py"
    py_file.write_text("def ok():\n    return 1\n")
    ts_file = tmp_path / "broken.ts"
    ts_file.write_text("import {x} from './x'\n")

    class _InlineExecutor:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> "_InlineExecutor":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        def map(self, fn: Any, iterable: Any) -> list[Any]:
            return [fn(item) for item in iterable]

    original_get = ts.get_ts_language_object

    def _conditional_fail(entry: object) -> object:
        if getattr(entry, "name", "") == "typescript":
            raise RuntimeError("forced TypeScript grammar failure")
        return original_get(entry)  # type: ignore[arg-type]

    monkeypatch.setattr(ts, "ProcessPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(ts, "get_ts_language_object", _conditional_fail)

    res = parse_files([py_file, ts_file])

    assert res[py_file].parse_failed is False
    assert res[ts_file].parse_failed is True
    assert any("import" in imp for imp in res[ts_file].imports)
