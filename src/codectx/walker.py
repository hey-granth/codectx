"""File-system walker — discovers files, applies ignore specs, filters binaries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pathspec

from codectx.config.defaults import BINARY_CHECK_BYTES, MAX_IO_WORKERS
from codectx.ignore import build_ignore_spec, should_ignore


def walk(
    root: Path,
    extra_ignore: tuple[str, ...] = (),
    output_file: Path | None = None,
) -> list[Path]:
    """Recursively discover non-ignored, non-binary files under *root*.

    Args:
        root: Repository root directory.
        extra_ignore: Additional ignore patterns from config.
        output_file: Output file to exclude from results (prevents self-inclusion).

    Returns:
        Sorted list of absolute file paths.
    """
    root = root.resolve()
    spec = build_ignore_spec(root, extra_ignore)

    # Resolve output file path for exclusion
    excluded: Path | None = None
    if output_file is not None:
        excluded = (
            (root / output_file).resolve()
            if not output_file.is_absolute()
            else output_file.resolve()
        )

    # Collect candidates (avoids descending into ignored directories)
    candidates: list[Path] = []
    _collect(root, root, spec, candidates)

    # Filter binaries in parallel
    with ThreadPoolExecutor(max_workers=MAX_IO_WORKERS) as pool:
        results = list(pool.map(lambda p: (p, _is_binary(p)), candidates))

    files = sorted(
        (p for p, is_bin in results if not is_bin and p != excluded),
        key=lambda p: p.relative_to(root).as_posix(),
    )
    return files


def _collect(
    current: Path,
    root: Path,
    spec: pathspec.PathSpec,
    out: list[Path],
) -> None:
    """Recursively collect files, pruning ignored directories."""
    try:
        entries = sorted(current.iterdir(), key=lambda e: e.name)
    except PermissionError:
        return

    for entry in entries:
        if should_ignore(spec, entry, root):
            continue
        if entry.is_dir():
            _collect(entry, root, spec, out)
        elif entry.is_file():
            out.append(entry)


def _is_binary(path: Path) -> bool:
    """Detect binary files by probing UTF-8 decoding on the initial byte chunk."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(BINARY_CHECK_BYTES)
        if b"\x00" in chunk:
            return True
        chunk.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True
    except OSError:
        return True  # treat unreadable files as binary


# ---------------------------------------------------------------------------
# Multi-root support
# ---------------------------------------------------------------------------


def walk_multi(
    roots: list[Path],
    extra_ignore: tuple[str, ...] = (),
    output_file: Path | None = None,
) -> dict[Path, list[Path]]:
    """Walk multiple roots independently, returning files grouped by root.

    Args:
        roots: List of repository root directories.
        extra_ignore: Additional ignore patterns from config.
        output_file: Output file to exclude from results.

    Returns:
        Dict mapping each root to sorted list of absolute file paths.
    """
    result: dict[Path, list[Path]] = {}
    for root in roots:
        root = root.resolve()
        files = walk(root, extra_ignore, output_file)
        result[root] = files
    return result


def find_root(file_path: Path, roots: list[Path]) -> Path | None:
    """Determine which root a file belongs to.

    Args:
        file_path: Absolute path to a file.
        roots: List of root directories.

    Returns:
        The root the file belongs to, or None if not under any root.
    """
    for root in sorted(roots, key=lambda r: len(str(r)), reverse=True):
        try:
            file_path.relative_to(root)
            return root
        except ValueError:
            continue
    return None
