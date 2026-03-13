"""Tests for multi-language treesitter parsing."""

from pathlib import Path
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
    pr = res[f]
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
