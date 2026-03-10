"""Ignore-spec handling — layers ALWAYS_IGNORE, .gitignore, .ctxignore."""

from __future__ import annotations

from pathlib import Path

import pathspec

from codectx.config.defaults import ALWAYS_IGNORE


def build_ignore_spec(root: Path, extra_patterns: tuple[str, ...] = ()) -> pathspec.PathSpec:
    """Build a composite ignore spec from all sources.

    Layering order (all additive):
      1. ALWAYS_IGNORE (hardcoded)
      2. .gitignore (if present)
      3. .ctxignore (if present)
      4. extra_patterns from config
    """
    patterns: list[str] = []

    # 1. Always-ignore
    patterns.extend(ALWAYS_IGNORE)

    # 2. .gitignore
    gitignore_path = root / ".gitignore"
    if gitignore_path.is_file():
        patterns.extend(_read_pattern_file(gitignore_path))

    # 3. .ctxignore
    ctxignore_path = root / ".ctxignore"
    if ctxignore_path.is_file():
        patterns.extend(_read_pattern_file(ctxignore_path))

    # 4. Extra patterns from config
    patterns.extend(extra_patterns)

    return pathspec.PathSpec.from_lines("gitignore", patterns)


def should_ignore(spec: pathspec.PathSpec, path: Path, root: Path) -> bool:
    """Check whether a path should be ignored.

    Args:
        spec: The compiled ignore spec.
        path: Absolute path to check.
        root: Repository root (for computing relative path).

    Returns:
        True if the path matches any ignore pattern.
    """
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False

    # pathspec expects forward-slash separated POSIX paths
    rel_str = rel.as_posix()

    # Also check if any parent directory matches (e.g. node_modules/)
    return bool(spec.match_file(rel_str))


def _read_pattern_file(path: Path) -> list[str]:
    """Read a gitignore-style pattern file, stripping comments and blanks."""
    lines: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines
