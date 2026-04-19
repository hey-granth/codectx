"""Semantic search ranking using lancedb and sentence-transformers.

This module is an optional dependency — all imports are guarded.
Install with: pip install codectx[semantic]
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from codectx.cache.paths import get_embeddings_path
from codectx.parser.base import ParseResult

if TYPE_CHECKING:
    import lancedb as lancedb_module
    from sentence_transformers import SentenceTransformer as SentenceTransformerType

logger = logging.getLogger(__name__)

_HAS_LANCEDB = False
_HAS_SENTENCE_TRANSFORMERS = False
lancedb: Any | None = None
SentenceTransformer: Any | None = None

try:
    import lancedb as lancedb_module

    lancedb = lancedb_module
    _HAS_LANCEDB = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer as SentenceTransformerType

    SentenceTransformer = SentenceTransformerType
    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    pass

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


def _cache_root_dir() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "codectx"


def _as_float_list(value: Any) -> list[float]:
    if hasattr(value, "tolist"):
        return [float(v) for v in value.tolist()]
    return [float(v) for v in value]


def _ensure_embedding_table(db: Any, dim: int) -> Any:
    if lancedb is None:
        raise ImportError("lancedb is not installed. Install with: pip install codectx[semantic]")

    table_name = "codectx_embeddings"
    try:
        if table_name in db.list_tables():
            table = db.open_table(table_name)
            probe = table.limit(1).to_list()
            if probe:
                existing_dim = len(_as_float_list(probe[0].get("embedding", [])))
                if existing_dim != dim:
                    db.drop_table(table_name)
                    raise ValueError("embedding dimension mismatch")
            return table
    except Exception:
        # Fallback to recreate when schema access fails.
        if table_name in db.list_tables():
            db.drop_table(table_name)

    try:
        pa = importlib.import_module("pyarrow")

        schema = pa.schema(
            [
                ("file_path", pa.string()),
                ("file_hash", pa.string()),
                ("embedding", pa.list_(pa.float32(), list_size=dim)),
            ]
        )
        return db.create_table(table_name, schema=schema, data=[])
    except Exception:
        # Older lancedb versions may not support explicit schema creation.
        seed = [
            {
                "file_path": "__seed__",
                "file_hash": "",
                "embedding": [0.0] * dim,
            }
        ]
        table = db.create_table(table_name, data=seed)
        from contextlib import suppress

        with suppress(Exception):
            table.delete("file_path = '__seed__'")
        return table


def embed_with_cache(
    file_contents: dict[str, str],
    repo_root: str,
    model_name: str = "BAAI/bge-small-en-v1.5",
) -> dict[str, list[float]]:
    """Embed file contents with persistent lancedb cache and hash invalidation."""
    if not _HAS_LANCEDB:
        raise ImportError("lancedb is not installed. Install with: pip install codectx[semantic]")
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise ImportError(
            "sentence-transformers is not installed. Install with: pip install codectx[semantic]"
        )
    if lancedb is None or SentenceTransformer is None:
        raise ImportError("Semantic dependencies not available")

    if not file_contents:
        return {}

    cache_root = _cache_root_dir()
    cache_root.mkdir(parents=True, exist_ok=True)
    embeddings_path = get_embeddings_path(repo_root)
    db = lancedb.connect(str(embeddings_path))

    model = SentenceTransformer(model_name)
    sample_embedding = _as_float_list(model.encode(["dimension probe"], show_progress_bar=False)[0])
    dim = len(sample_embedding)
    table = _ensure_embedding_table(db, dim)

    results: dict[str, list[float]] = {}
    misses: list[str] = []
    miss_texts: list[str] = []
    hashes: dict[str, str] = {}

    for file_path in sorted(file_contents):
        content = file_contents[file_path]
        file_hash = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
        hashes[file_path] = file_hash

        rows: list[dict[str, Any]] = []
        try:
            query = file_path.replace("'", "''")
            rows = table.search().where(f"file_path = '{query}'", prefilter=True).limit(1).to_list()
        except Exception:
            try:
                rows = [r for r in table.to_list() if str(r.get("file_path", "")) == file_path][:1]
            except Exception:
                rows = []

        if rows and str(rows[0].get("file_hash", "")) == file_hash:
            results[file_path] = _as_float_list(rows[0].get("embedding", []))
        else:
            misses.append(file_path)
            miss_texts.append(content)

    if misses:
        embedded = model.encode(miss_texts, show_progress_bar=False)
        rows_to_add: list[dict[str, Any]] = []
        for file_path, vector in zip(misses, embedded, strict=False):
            vector_list = _as_float_list(vector)
            results[file_path] = vector_list
            rows_to_add.append(
                {
                    "file_path": file_path,
                    "file_hash": hashes[file_path],
                    "embedding": vector_list,
                }
            )

        for row in rows_to_add:
            try:
                query = row["file_path"].replace("'", "''")
                table.delete(f"file_path = '{query}'")
            except Exception:
                continue
        if rows_to_add:
            table.add(rows_to_add)

    _evict_stale_embeddings(table, set(file_contents.keys()))

    return results


def _evict_stale_embeddings(table: Any, current_paths: set[str]) -> None:
    """
    Delete rows from LanceDB where file_path is not in current_paths.
    Runs after embedding, on every successful call to embed_with_cache.
    Never raises.
    """
    try:
        # LanceDB delete syntax:
        # table.delete("file_path NOT IN ('a', 'b', 'c')")
        if not current_paths:
            return
        path_list = ", ".join(f"'{p}'" for p in current_paths)
        table.delete(f"file_path NOT IN ({path_list})")
    except Exception as e:
        import sys

        print(f"[codectx] embedding eviction warning: {e}", file=sys.stderr)


def is_available() -> bool:
    """Check if semantic search dependencies are available."""
    return _HAS_LANCEDB and _HAS_SENTENCE_TRANSFORMERS


def semantic_score(
    query: str,
    files: list[Path],
    parse_results: dict[Path, ParseResult],
    repo_root: str,
) -> dict[Path, float]:
    """Return semantic relevance score 0.0–1.0 per file for the given query.

    Args:
        query: Natural language query to rank files against.
        files: List of file paths to score.
        parse_results: Parse results for each file.
        repo_root: Directory to store lancedb tables for caching.

    Returns:
        Dict mapping file path to semantic similarity score (0.0–1.0).

    Raises:
        ImportError: If lancedb or sentence-transformers not installed.
    """
    if not _HAS_LANCEDB:
        raise ImportError("lancedb is not installed. Install with: pip install codectx[semantic]")
    if not _HAS_SENTENCE_TRANSFORMERS:
        raise ImportError(
            "sentence-transformers is not installed. Install with: pip install codectx[semantic]"
        )

    if lancedb is None or SentenceTransformer is None:
        raise ImportError("Semantic dependencies not available")

    # Build document texts from symbols + docstrings
    file_contents: dict[str, str] = {}
    for f in files:
        pr = parse_results.get(f)
        if pr is None:
            continue
        parts: list[str] = []
        for s in pr.symbols:
            parts.append(s.name)
            if s.docstring:
                parts.append(s.docstring)
        for d in pr.docstrings:
            parts.append(d)
        text = " ".join(parts) if parts else f.name
        file_contents[str(f)] = text

    if not file_contents:
        return {}

    doc_embeddings = embed_with_cache(file_contents, repo_root, model_name=_DEFAULT_MODEL)

    model = SentenceTransformer(_DEFAULT_MODEL)
    query_vector = _as_float_list(model.encode([query], show_progress_bar=False)[0])

    def cosine_distance(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 1.0
        similarity = dot / (norm_a * norm_b)
        return 1.0 - max(min(similarity, 1.0), -1.0)

    distances_by_path: dict[Path, float] = {}
    for raw_path, vector in doc_embeddings.items():
        distances_by_path[Path(raw_path)] = cosine_distance(query_vector, vector)

    if not distances_by_path:
        return {f: 0.0 for f in files}

    max_dist = max(distances_by_path.values())
    if max_dist == 0.0:
        max_dist = 1.0

    scores: dict[Path, float] = {}
    for path, dist in distances_by_path.items():
        # Invert: closer = higher score
        scores[path] = round(max(1.0 - (dist / max_dist), 0.0), 6)

    # Fill in files not in results with 0.0
    for f in files:
        if f not in scores:
            scores[f] = 0.0

    return scores
