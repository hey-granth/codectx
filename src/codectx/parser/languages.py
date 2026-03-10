"""Extension → language mapping for tree-sitter parsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LanguageEntry:
    """A supported language with its tree-sitter module reference."""

    name: str
    ts_module_name: str  # e.g. "tree_sitter_python"
    extensions: tuple[str, ...]


# Registry of all supported languages
_LANGUAGES: tuple[LanguageEntry, ...] = (
    LanguageEntry("python", "tree_sitter_python", (".py", ".pyi")),
    LanguageEntry("javascript", "tree_sitter_javascript", (".js", ".jsx", ".mjs", ".cjs")),
    LanguageEntry("typescript", "tree_sitter_typescript", (".ts", ".tsx")),
    LanguageEntry("go", "tree_sitter_go", (".go",)),
    LanguageEntry("rust", "tree_sitter_rust", (".rs",)),
    LanguageEntry("java", "tree_sitter_java", (".java",)),
    LanguageEntry("c", "tree_sitter_c", (".c", ".h")),
    LanguageEntry("cpp", "tree_sitter_cpp", (".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".hh")),
    LanguageEntry("ruby", "tree_sitter_ruby", (".rb",)),
)

# Extension → LanguageEntry lookup (built once)
_EXT_MAP: dict[str, LanguageEntry] = {}
for _lang in _LANGUAGES:
    for _ext in _lang.extensions:
        _EXT_MAP[_ext] = _lang


def get_language(ext: str) -> LanguageEntry | None:
    """Return the LanguageEntry for a file extension, or None if unsupported."""
    return _EXT_MAP.get(ext)


def get_language_for_path(path: Any) -> LanguageEntry | None:
    """Return the LanguageEntry for a file path (uses suffix)."""
    from pathlib import Path as _Path
    p = _Path(path) if not isinstance(path, _Path) else path
    return get_language(p.suffix)


def get_ts_language_object(entry: LanguageEntry) -> Any:
    """Dynamically import and return the tree-sitter Language object.

    Uses the modern per-package tree-sitter bindings (tree-sitter-python, etc.).
    """
    import importlib

    import tree_sitter

    module = importlib.import_module(entry.ts_module_name)
    # Modern tree-sitter packages return a PyCapsule from language(),
    # which must be wrapped in tree_sitter.Language()
    return tree_sitter.Language(module.language())


def supported_extensions() -> frozenset[str]:
    """Return all file extensions supported for tree-sitter parsing."""
    return frozenset(_EXT_MAP.keys())
