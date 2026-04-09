"""Extension → language mapping for tree-sitter parsers."""

from __future__ import annotations

import functools
import importlib
from dataclasses import dataclass
from typing import Any

import tree_sitter


@dataclass(frozen=True)
class LanguageEntry:
    """A supported language with its tree-sitter module reference."""

    name: str
    ts_module_name: str  # e.g. "tree_sitter_python"
    extensions: tuple[str, ...]
    language_fn: str = "language"


class TreeSitterLanguageLoadError(RuntimeError):
    """Raised when a tree-sitter language cannot be resolved safely."""


# Registry of all supported languages
_LANGUAGES: tuple[LanguageEntry, ...] = (
    LanguageEntry("python", "tree_sitter_python", (".py", ".pyi")),
    LanguageEntry("javascript", "tree_sitter_javascript", (".js", ".jsx", ".mjs", ".cjs")),
    LanguageEntry("typescript", "tree_sitter_typescript", (".ts",), "language_typescript"),
    LanguageEntry("typescript", "tree_sitter_typescript", (".tsx",), "language_tsx"),
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
    if entry.ts_module_name == "tree_sitter_typescript":
        return load_typescript_language(entry.language_fn)

    module = importlib.import_module(entry.ts_module_name)
    language_factory = getattr(module, entry.language_fn)
    resolved = language_factory() if callable(language_factory) else language_factory
    if isinstance(resolved, tree_sitter.Language):
        return resolved
    return tree_sitter.Language(resolved)


def _coerce_language(value: Any) -> tree_sitter.Language:
    """Normalize any supported language payload into a Language object."""
    language_type = getattr(tree_sitter, "Language", None)
    if isinstance(language_type, type) and isinstance(value, language_type):
        return value
    return tree_sitter.Language(value)


@functools.lru_cache(maxsize=4)
def load_typescript_language(language_fn: str = "language_typescript") -> tree_sitter.Language:
    """Load TypeScript grammar across tree_sitter_typescript API variants.

    Supported exports across known package versions include:
    - callable factories: language(), get_language(), language_typescript(), language_tsx()
    - constants: LANGUAGE, LANGUAGE_TYPESCRIPT, LANGUAGE_TSX
    - manual binding fallback via tree_sitter.Language(<shared-library>, <name>)
    """
    try:
        module = importlib.import_module("tree_sitter_typescript")
    except Exception as exc:  # pragma: no cover - import failure environment-dependent
        raise TreeSitterLanguageLoadError("unable to import tree_sitter_typescript") from exc

    names: list[str] = [language_fn]
    if language_fn == "language_tsx":
        names.extend(["language", "get_language", "LANGUAGE_TSX", "LANGUAGE"])
    else:
        names.extend(["language", "get_language", "LANGUAGE_TYPESCRIPT", "LANGUAGE"])

    seen: set[str] = set()
    attempts: list[str] = []
    for attr_name in names:
        if attr_name in seen:
            continue
        seen.add(attr_name)
        if not hasattr(module, attr_name):
            continue
        attr = getattr(module, attr_name)
        try:
            value = attr() if callable(attr) else attr
            return _coerce_language(value)
        except Exception as exc:
            attempts.append(f"{attr_name}: {exc}")

    symbol = "tsx" if language_fn == "language_tsx" else "typescript"
    path_candidates = [
        getattr(module, "LIBRARY_PATH", None),
        getattr(module, "LIB_PATH", None),
        getattr(module, "_LIB_PATH", None),
        getattr(module, "__file__", None),
    ]
    for lib_path in path_candidates:
        if not isinstance(lib_path, str) or not lib_path:
            continue
        try:
            # Older tree-sitter Python bindings use Language(path, grammar_name).
            return tree_sitter.Language(lib_path, symbol)
        except Exception as exc:
            attempts.append(f"Language({lib_path!r}, {symbol!r}): {exc}")

    detail = "; ".join(attempts[:4])
    if detail:
        detail = f" ({detail})"
    raise TreeSitterLanguageLoadError(
        f"unsupported tree_sitter_typescript API for {language_fn}{detail}"
    )


def supported_extensions() -> frozenset[str]:
    """Return all file extensions supported for tree-sitter parsing."""
    return frozenset(_EXT_MAP.keys())
