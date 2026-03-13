"""File-level caching for parse results, token counts, and git metadata."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path

from codectx.config.defaults import CACHE_DIR_NAME
from codectx.parser.base import ParseResult, Symbol

logger = logging.getLogger(__name__)


class Cache:
    """JSON-based file cache in .codectx_cache/."""

    def __init__(self, root: Path) -> None:
        self.cache_dir = root / CACHE_DIR_NAME
        self._data: dict[str, dict[str, object]] = {}
        self._load()

    def _load(self) -> None:
        """Load existing cache from disk."""
        cache_file = self.cache_dir / "cache.json"
        if cache_file.is_file():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Cache load failed: %s", exc)
                self._data = {}

    def save(self) -> None:
        """Persist cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "cache.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, separators=(",", ":"))
        except OSError as exc:
            logger.warning("Cache save failed: %s", exc)

    def get_parse_result(self, path: Path, file_hash: str) -> ParseResult | None:
        """Retrieve a cached ParseResult if the hash matches."""
        key = str(path)
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.get("file_hash") != file_hash:
            return None

        try:
            symbols = tuple(
                Symbol(**s)
                for s in entry.get("symbols", [])  # type: ignore[arg-type]
            )
            return ParseResult(
                path=Path(entry["path"]),  # type: ignore[arg-type]
                language=str(entry["language"]),
                imports=tuple(entry.get("imports", [])),  # type: ignore[arg-type]
                symbols=symbols,
                docstrings=tuple(entry.get("docstrings", [])),  # type: ignore[arg-type]
                raw_source=str(entry.get("raw_source", "")),
                line_count=int(entry.get("line_count", 0)),  # type: ignore[arg-type]
                partial_parse=bool(entry.get("partial_parse", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("Cache entry invalid for %s: %s", path, exc)
            return None

    def put_parse_result(self, path: Path, file_hash: str, result: ParseResult) -> None:
        """Store a ParseResult in the cache."""
        self._data[str(path)] = {
            "file_hash": file_hash,
            "path": str(result.path),
            "language": result.language,
            "imports": list(result.imports),
            "symbols": [asdict(s) for s in result.symbols],
            "docstrings": list(result.docstrings),
            "raw_source": result.raw_source,
            "line_count": result.line_count,
            "partial_parse": result.partial_parse,
        }

    def get_token_count(self, path: Path, file_hash: str) -> int | None:
        """Retrieve a cached token count."""
        key = f"tokens:{path}"
        entry = self._data.get(key)
        if entry is None or entry.get("file_hash") != file_hash:
            return None
        return int(entry.get("count", 0))  # type: ignore[arg-type]

    def put_token_count(self, path: Path, file_hash: str, count: int) -> None:
        """Cache a token count."""
        self._data[f"tokens:{path}"] = {"file_hash": file_hash, "count": count}

    def invalidate(self, path: Path) -> None:
        """Remove a file from the cache."""
        key = str(path)
        self._data.pop(key, None)
        self._data.pop(f"tokens:{path}", None)

    def export_cache(self, output: Path) -> None:
        """Export cache directory as a tar.gz archive for CI sharing.

        Args:
            output: Path where the archive will be written.
        """
        import tarfile

        self.save()  # Ensure cache is persisted first
        if not self.cache_dir.is_dir():
            raise FileNotFoundError(f"Cache directory not found: {self.cache_dir}")

        with tarfile.open(output, "w:gz") as tar:
            tar.add(self.cache_dir, arcname=CACHE_DIR_NAME)

        logger.info("Cache exported to %s", output)

    @classmethod
    def import_cache(cls, archive: Path, root: Path) -> Cache:
        """Import cache from a tar.gz archive.

        Args:
            archive: Path to the archive to import.
            root: Repository root where cache should be restored.

        Returns:
            A new Cache instance loaded from the imported data.
        """
        import tarfile

        if not archive.is_file():
            raise FileNotFoundError(f"Archive not found: {archive}")

        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(path=root, filter="data")

        logger.info("Cache imported from %s to %s", archive, root / CACHE_DIR_NAME)
        return cls(root)


def file_hash(path: Path) -> str:
    """Compute a fast hash of file contents."""
    try:
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()  # noqa: S324
    except OSError:
        return ""
