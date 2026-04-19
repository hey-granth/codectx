"""Per-language import string → file path resolution."""

from __future__ import annotations

import re
from pathlib import Path

_GO_MODULE_RE = re.compile(r"^module\s+(\S+)")


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
        return _resolve_python(import_text, source_file, root, all_files)
    elif language in ("javascript", "typescript"):
        return _resolve_js_ts(import_text, source_file, root, all_files)
    elif language == "go":
        return _resolve_go(import_text, source_file, root, all_files)
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


def _resolve_python(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    m = _PYTHON_IMPORT_RE.search(import_text)
    if not m:
        return []

    # Regex can capture group 1 (from ... import) or group 2 (import ...)
    module_str = m.group(1) or m.group(2)
    if not module_str:
        return []

    # 1. Absolute import (e.g. "import os", "from myapp import utils")
    if not module_str.startswith("."):
        try:
            slash_path = module_str.replace(".", "/")
        except ValueError:
            return []

        candidates_rel = [
            f"{slash_path}.py",
            f"{slash_path}/__init__.py",
            f"src/{slash_path}.py",
            f"src/{slash_path}/__init__.py",
        ]
        resolved: list[Path] = []
        for rel in candidates_rel:
            # We can construct the absolute path here, but checking `rel in all_files`
            # confirms it exists within the project scope.
            if rel in all_files:
                resolved.append(root / rel)
        return resolved

    # 2. Relative import (e.g. ".utils", "..sub.mod")
    # "from . import utils" -> module_str="." (regex captures it as part of [\w.]+)
    # "from ..sub import mod" -> module_str="..sub"

    # Count leading dots
    level = 0
    clean_module = module_str
    for char in module_str:
        if char == ".":
            level += 1
        else:
            break

    clean_module = module_str[level:]  # remove leading dots

    # Determine base directory
    try:
        _ = source_file.relative_to(root)
    except ValueError:
        return []  # Source file outside root?

    # If source is __init__.py, its "directory" for relative imports is itself (the package)
    # If source is mod.py, its "directory" is its parent.
    if source_file.name == "__init__.py":
        current_pkg_dir = source_file.parent
    else:
        current_pkg_dir = source_file.parent

    # Go up (level - 1) times if level >= 1
    # level 1 ("from . import foo") -> current package
    # level 2 ("from .. import foo") -> parent package
    target_dir = current_pkg_dir
    for _ in range(level - 1):
        target_dir = target_dir.parent
        # Stop at root
        if target_dir == root:
            break

    try:
        # Base relative path for constructing candidates
        base_rel = target_dir.relative_to(root).as_posix()
    except ValueError:
        return []

    # If clean_module is empty (e.g. "from . import foo"), we actually need 'foo'.
    # But our regex `m` only captured the FROM part.
    # The regex is `(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))`
    # If "from . import foo", group 1 is ".". We lost "foo".
    # We must improve the regex or parsing to handle this.
    # For now, let's assume we proceed with just the FROM part if we can't get the IMPORT part easily without re-parsing.
    # BUT wait! If clean_module is empty, it means we are importing FROM the current package.
    # The import target is in the IMPORT clause which we didn't capture.
    # Without capturing the imported name, we can't resolve "from . import foo".

    # However, if module_str was "..sub", then clean_module is "sub".
    # And we look for "sub" relative to target_dir.

    if not clean_module:
        # We can't resolve "from . import foo" without capturing "foo".
        # Let's try to capture it.
        # "from . import foo"
        # We can do a second regex or improve the first one.
        # Let's extend the regex logic inside helper? No, just quick fix here.
        m2 = re.search(r"import\s+([\w.]+)", import_text)
        if m2:
            clean_module = m2.group(1)
        else:
            return []

    slash_path = clean_module.replace(".", "/")

    # Construct relative path candidates
    prefix = f"{base_rel}/{slash_path}" if base_rel != "." else slash_path

    candidates_rel = [
        f"{prefix}.py",
        f"{prefix}/__init__.py",
    ]

    resolved = []
    for rel in candidates_rel:
        if rel in all_files:
            resolved.append(root / rel)
    return resolved


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


def _find_go_mod_root(source_file: Path, repo_root: Path) -> Path | None:
    current = source_file.parent
    repo_root_resolved = repo_root.resolve()
    while True:
        go_mod = current / "go.mod"
        if go_mod.exists():
            return current
        if current == repo_root_resolved or current.parent == current:
            break
        current = current.parent

    repo_go_mod = repo_root / "go.mod"
    if repo_go_mod.exists():
        return repo_root
    return None


def _parse_go_module(repo_root: str) -> str | None:
    go_mod = Path(repo_root) / "go.mod"
    if not go_mod.exists():
        return None
    try:
        for line in go_mod.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _GO_MODULE_RE.match(line.strip())
            if match:
                return match.group(1)
    except OSError:
        return None
    return None


def _resolve_go(
    import_text: str,
    source_file: Path,
    root: Path,
    all_files: frozenset[str],
) -> list[Path]:
    # Go imports are package paths; we resolve local packages and module-prefixed imports.
    m = re.search(r'"([^"]+)"', import_text)
    if not m:
        return []

    pkg = m.group(1)
    if "/" not in pkg:
        return []

    go_root = _find_go_mod_root(source_file, root) or root
    module_name = _parse_go_module(str(go_root))

    prefixes: list[str] = []
    if module_name and pkg.startswith(module_name + "/"):
        prefixes.append(pkg[len(module_name) + 1 :])
    elif module_name and pkg == module_name:
        prefixes.append("")
    else:
        prefixes.append(pkg)

    resolved: list[Path] = []
    for prefix in prefixes:
        normalized_prefix = prefix.strip("/")
        rel_candidates: list[str] = []
        if normalized_prefix:
            rel_candidates.extend(
                [
                    f"{normalized_prefix}.go",
                    f"{normalized_prefix}/main.go",
                ]
            )
            rel_candidates.extend(
                sorted(
                    f
                    for f in all_files
                    if f.startswith(normalized_prefix + "/") and f.endswith(".go")
                )
            )
        else:
            rel_candidates.extend(sorted(f for f in all_files if f.endswith(".go")))

        for rel in rel_candidates:
            if rel in all_files:
                target = root / rel
                if target not in resolved:
                    resolved.append(target)
    return resolved


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
