"""Git metadata extraction via pygit2."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GitFileInfo:
    """Git metadata for a single file."""

    commit_count: int
    last_modified_ts: float  # unix timestamp


def collect_git_metadata(
    files: list[Path],
    root: Path,
    no_git: bool = False,
) -> dict[Path, GitFileInfo]:
    """Collect git metadata for all files.

    Args:
        files: List of absolute file paths.
        root: Repository root.
        no_git: If True, use filesystem metadata only.

    Returns:
        Mapping of file path to GitFileInfo.
    """
    if no_git:
        return _filesystem_fallback(files)

    try:
        import pygit2  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("pygit2 not available, falling back to filesystem metadata")
        return _filesystem_fallback(files)

    try:
        repo = pygit2.Repository(str(root))
    except Exception as exc:
        logger.warning("Not a git repository or git error: %s", exc)
        return _filesystem_fallback(files)

    return _collect_from_git(repo, files, root)


def _collect_from_git(
    repo: object,  # pygit2.Repository
    files: list[Path],
    root: Path,
) -> dict[Path, GitFileInfo]:
    """Walk git log to collect per-file commit counts and last-modified times."""
    import pygit2  # type: ignore[import-untyped]

    assert isinstance(repo, pygit2.Repository)

    commit_counts: dict[str, int] = {}
    last_modified: dict[str, float] = {}

    try:
        head = repo.head
        walker = repo.walk(head.target, pygit2.GIT_SORT_TIME)
    except Exception as exc:
        logger.warning("Could not walk git log: %s", exc)
        return _filesystem_fallback(files)

    # Walk commits and diff to find which files were touched
    for commit in walker:
        ts = float(commit.commit_time)

        if commit.parents:
            parent = commit.parents[0]
            try:
                diff = repo.diff(parent, commit)
            except Exception:
                continue
        else:
            # Initial commit — all files are new
            try:
                diff = commit.tree.diff_to_tree()
            except Exception:
                continue

        for delta in diff.deltas:
            fpath = delta.new_file.path
            commit_counts[fpath] = commit_counts.get(fpath, 0) + 1
            if fpath not in last_modified or ts > last_modified[fpath]:
                last_modified[fpath] = ts

    # Map back to absolute paths
    result: dict[Path, GitFileInfo] = {}
    for f in files:
        try:
            rel = f.relative_to(root).as_posix()
        except ValueError:
            continue
        result[f] = GitFileInfo(
            commit_count=commit_counts.get(rel, 0),
            last_modified_ts=last_modified.get(rel, f.stat().st_mtime),
        )

    return result


def _filesystem_fallback(files: list[Path]) -> dict[Path, GitFileInfo]:
    """Fallback using filesystem metadata when git is unavailable."""
    result: dict[Path, GitFileInfo] = {}
    for f in files:
        try:
            mtime = f.stat().st_mtime
        except OSError:
            mtime = time.time()
        result[f] = GitFileInfo(commit_count=0, last_modified_ts=mtime)
    return result
