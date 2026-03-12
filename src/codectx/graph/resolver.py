"""Per-language import string → file path resolution."""

from __future__ import annotations

import re
from pathlib import Path


def resolve_import(
    import_text: str,
    language: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    """Resolve an import statement to file paths within the repository.

    Args:
        import_text: Raw import string from the AST.
        language: Language name (e.g. "python").
        source_file: Absolute path of the file containing the import.
        root: Repository root.
        all_files: Set of all known file paths (POSIX, relative to root).

    Returns:
        List of resolved file paths (may be empty if unresolvable).
    """
    if language == "python":
        return _resolve_python(import_text, root, all_files)
    elif language in ("javascript", "typescript"):
        return _resolve_js_ts(import_text, source_file, root, all_files)
    elif language == "go":
        return _resolve_go(import_text, root, all_files)
    elif language == "rust":
        return _resolve_rust(import_text, source_file, root, all_files)
    elif language == "java":
        return _resolve_java(import_text, root, all_files)
    elif language in ("c", "cpp"):
        return _resolve_c_cpp(import_text, source_file, root, all_files)
    elif language == "ruby":
        return _resolve_ruby(import_text, source_file, root, all_files)
    return []


def resolve_import_multi_root(
    import_text: str,
    language: str,
    source_file: Path,
    roots: list[Path],
    all_files_by_root: dict[Path, frozenset[str]],
) -> list[Path]:
    """Resolve an import trying the source file's root first, then others.

    Args:
        import_text: Raw import string from the AST.
        language: Language name.
        source_file: Absolute path of the file containing the import.
        roots: All root directories.
        all_files_by_root: Map of root → set of relative file paths.

    Returns:
        List of resolved file paths.
    """
    # Determine source root
    source_root: Path | None = None
    for r in roots:
        try:
            source_file.relative_to(r)
            source_root = r
            break
        except ValueError:
            continue

    if source_root is None:
        return []

    # Try source root first
    results = resolve_import(
        import_text,
        language,
        source_file,
        source_root,
        all_files_by_root.get(source_root, frozenset()),
    )
    if results:
        return results

    # Try other roots
    for r in roots:
        if r == source_root:
            continue
        other_results = resolve_import(
            import_text,
            language,
            source_file,
            r,
            all_files_by_root.get(r, frozenset()),
        )
        if other_results:
            return other_results

    return []


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

_PYTHON_IMPORT_RE = re.compile(r"(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")


def _resolve_python(import_text: str, root: Path, all_files: frozenset[str]) -> list[Path]:
    m = _PYTHON_IMPORT_RE.search(import_text)
    if not m:
        return []

    module_path = (m.group(1) or m.group(2)).replace(".", "/")
    candidates = [
        f"{module_path}.py",
        f"{module_path}/__init__.py",
    ]
    return [root / c for c in candidates if c in all_files]


# ---------------------------------------------------------------------------
# JavaScript / TypeScript
# ---------------------------------------------------------------------------

_JS_IMPORT_RE = re.compile(r"""(?:from|require\()\s*['"]([^'"]+)['"]""")


def _resolve_js_ts(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    m = _JS_IMPORT_RE.search(import_text)
    if not m:
        return []

    specifier = m.group(1)

    # Only resolve relative imports
    if not specifier.startswith("."):
        return []

    base_dir = source_file.parent
    resolved_base = (base_dir / specifier).resolve()
    try:
        rel = resolved_base.relative_to(root).as_posix()
    except ValueError:
        return []

    extensions = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
    candidates: list[str] = []

    # Direct file match
    for ext in extensions:
        candidates.append(f"{rel}{ext}")

    # Index file in directory
    for ext in extensions:
        candidates.append(f"{rel}/index{ext}")

    return [root / c for c in candidates if c in all_files]


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------


def _resolve_go(import_text: str, root: Path, all_files: frozenset[str]) -> list[Path]:
    # Go imports are package paths; we try to resolve them relative to root
    m = re.search(r'"([^"]+)"', import_text)
    if not m:
        return []

    pkg = m.group(1)
    # Only resolve local packages (not standard lib)
    candidates = [f for f in all_files if f.startswith(pkg) and f.endswith(".go")]
    return [root / c for c in candidates]


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------


def _resolve_rust(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    # `use crate::foo::bar;` → src/foo/bar.rs or src/foo/bar/mod.rs
    m = re.search(r"use\s+(crate::[\w:]+)", import_text)
    if not m:
        return []

    parts = m.group(1).replace("crate::", "").split("::")
    path_base = "/".join(parts)
    candidates = [f"src/{path_base}.rs", f"src/{path_base}/mod.rs"]
    return [root / c for c in candidates if c in all_files]


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------


def _resolve_java(import_text: str, root: Path, all_files: frozenset[str]) -> list[Path]:
    m = re.search(r"import\s+([\w.]+);", import_text)
    if not m:
        return []

    class_path = m.group(1).replace(".", "/")
    # Try direct match and with src/main/java prefix
    candidates = [
        f"{class_path}.java",
        f"src/main/java/{class_path}.java",
        f"src/{class_path}.java",
    ]
    return [root / c for c in candidates if c in all_files]


# ---------------------------------------------------------------------------
# C / C++
# ---------------------------------------------------------------------------


def _resolve_c_cpp(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    m = re.search(r'#include\s*"([^"]+)"', import_text)
    if not m:
        return []

    include_path = m.group(1)
    # Resolve relative to source file
    base_dir = source_file.parent
    resolved = (base_dir / include_path).resolve()
    try:
        rel = resolved.relative_to(root).as_posix()
    except ValueError:
        return []

    if rel in all_files:
        return [root / rel]
    return []


# ---------------------------------------------------------------------------
# Ruby
# ---------------------------------------------------------------------------


def _resolve_ruby(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    m = re.search(r"require(?:_relative)?\s*['\"]([^'\"]+)['\"]", import_text)
    if not m:
        return []

    spec = m.group(1)

    if "require_relative" in import_text:
        base_dir = source_file.parent
        resolved = (base_dir / spec).resolve()
        try:
            rel = resolved.relative_to(root).as_posix()
        except ValueError:
            return []
        candidates = [f"{rel}.rb", rel]
    else:
        candidates = [f"{spec}.rb", f"lib/{spec}.rb"]

    return [root / c for c in candidates if c in all_files]
