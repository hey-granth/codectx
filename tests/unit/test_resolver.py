"""Tests for import resolution."""

from pathlib import Path
from codectx.graph.resolver import resolve_import_multi_root, resolve_import

def test_resolve_python_relative(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f2 = pkg / "b.py"
    f1.write_text("")
    f2.write_text("")
    all_f = frozenset([f1.relative_to(tmp_path).as_posix(), f2.relative_to(tmp_path).as_posix()])
    
    # from . import b
    res = resolve_import("from . import b", "python", f1, tmp_path, all_f)
    assert res == [f2]

def test_resolve_python_absolute(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    f1 = pkg / "a.py"
    f2 = pkg / "b.py"
    f1.write_text("")
    f2.write_text("")
    all_f = frozenset(["pkg/a.py", "pkg/b.py"])
    
    res = resolve_import("import pkg.b", "python", f1, tmp_path, all_f)
    assert res == [f2]

def test_resolve_js_ts(tmp_path: Path) -> None:
    f1 = tmp_path / "a.js"
    f2 = tmp_path / "b.js"
    f3 = tmp_path / "c.ts"
    f1.write_text("")
    f2.write_text("")
    f3.write_text("")
    all_f = frozenset(["a.js", "b.js", "c.ts"])
    
    res = resolve_import("from './b'", "javascript", f1, tmp_path, all_f)
    assert res == [f2]

    res2 = resolve_import("from './c'", "typescript", f1, tmp_path, all_f)
    assert res2 == [f3]

    # index.js
    d = tmp_path / "src"
    d.mkdir()
    d_idx = d / "index.js"
    d_idx.write_text("")
    all_f2 = frozenset(["a.js", "src/index.js"])
    res3 = resolve_import("from './src'", "javascript", f1, tmp_path, all_f2)
    assert res3 == [d_idx]

def test_resolve_multi_root(tmp_path: Path) -> None:
    r1 = tmp_path / "r1"
    r2 = tmp_path / "r2"
    r1.mkdir()
    r2.mkdir()
    f1 = r1 / "a.py"
    f2 = r2 / "b.py"
    f1.write_text("")
    f2.write_text("")
    all_f_by_root = {
        r1: frozenset(["a.py"]),
        r2: frozenset(["b.py"]),
    }
    
    res = resolve_import_multi_root("import b", "python", f1, [r1, r2], all_f_by_root)
    assert res == [f2]

def test_resolve_c_cpp(tmp_path: Path) -> None:
    f1 = tmp_path / "a.cpp"
    f2 = tmp_path / "b.h"
    f2.write_text("")
    all_f = frozenset(["a.cpp", "b.h"])
    res = resolve_import('#include "b.h"', "cpp", f1, tmp_path, all_f)
    assert res == [f2]

def test_resolve_go(tmp_path: Path) -> None:
    f1 = tmp_path / "a.go"
    d = tmp_path / "github.com" / "foo" / "bar"
    d.mkdir(parents=True)
    f2 = d / "c.go"
    f2.write_text("")
    all_f = frozenset(["a.go", "github.com/foo/bar/c.go"])
    res = resolve_import('"github.com/foo/bar"', "go", f1, tmp_path, all_f)
    assert len(res) == 1

def test_resolve_rust(tmp_path: Path) -> None:
    f1 = tmp_path / "a.rs"
    d = tmp_path / "src" / "foo"
    d.mkdir(parents=True)
    f2 = d / "bar.rs"
    f2.write_text("")
    all_f = frozenset(["a.rs", "src/foo/bar.rs"])
    res = resolve_import("use crate::foo::bar;", "rust", f1, tmp_path, all_f)
    assert res == [f2]

def test_resolve_java(tmp_path: Path) -> None:
    f1 = tmp_path / "A.java"
    d = tmp_path / "src" / "main" / "java" / "com" / "example"
    d.mkdir(parents=True)
    f2 = d / "B.java"
    f2.write_text("")
    all_f = frozenset(["A.java", "src/main/java/com/example/B.java"])
    res = resolve_import("import com.example.B;", "java", f1, tmp_path, all_f)
    assert res == [f2]

def test_resolve_ruby(tmp_path: Path) -> None:
    f1 = tmp_path / "a.rb"
    d = tmp_path / "lib"
    d.mkdir()
    f2 = d / "b.rb"
    f2.write_text("")
    all_f = frozenset(["a.rb", "lib/b.rb"])
    res = resolve_import("require 'b'", "ruby", f1, tmp_path, all_f)
    assert res == [f2]
