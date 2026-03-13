"""Semantic search ranking using lancedb and sentence-transformers.

This module is an optional dependency — all imports are guarded.
Install with: pip install codectx[semantic]
"""

from __future__ import annotations

import logging
from pathlib import Path

from codectx.parser.base import ParseResult

logger = logging.getLogger(__name__)

_HAS_LANCEDB = False
_HAS_SENTENCE_TRANSFORMERS = False

try:
    import lancedb  # noqa: F401

    _HAS_LANCEDB = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer  # noqa: F401

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    pass

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


def is_available() -> bool:
    """Check if semantic search dependencies are available."""
    return _HAS_LANCEDB and _HAS_SENTENCE_TRANSFORMERS


def semantic_score(
    query: str,
    files: list[Path],
    parse_results: dict[Path, ParseResult],
    cache_dir: Path,
) -> dict[Path, float]:
    """Return semantic relevance score 0.0–1.0 per file for the given query.

    Args:
        query: Natural language query to rank files against.
        files: List of file paths to score.
        parse_results: Parse results for each file.
        cache_dir: Directory to store lancedb tables for caching.

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

    import lancedb
    import pyarrow as pa
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(_DEFAULT_MODEL)

    # Build document texts from symbols + docstrings
    documents: list[str] = []
    doc_paths: list[str] = []
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
        documents.append(text)
        doc_paths.append(str(f))

    if not documents:
        return {}

    # Embed documents
    doc_embeddings = model.encode(documents, show_progress_bar=False)

    # Store in lancedb
    db_path = str(cache_dir / "semantic.lance")
    db = lancedb.connect(db_path)

    # Create table with embeddings
    data = [
        {"path": p, "text": t, "vector": e.tolist()}
        for p, t, e in zip(doc_paths, documents, doc_embeddings)
    ]

    table_name = "files"
    if table_name in db.list_tables():
        db.drop_table(table_name)
    table = db.create_table(table_name, data=data)

    # Embed query and search
    query_embedding = model.encode([query], show_progress_bar=False)[0]
    results = table.search(query_embedding.tolist()).limit(len(files)).to_list()

    # Normalize distances to 0.0–1.0 scores (lower distance = higher score)
    if not results:
        return {}

    distances = [r.get("_distance", 0.0) for r in results]
    max_dist = max(distances) if distances else 1.0
    if max_dist == 0.0:
        max_dist = 1.0

    scores: dict[Path, float] = {}
    for r in results:
        p = Path(r["path"])
        dist = r.get("_distance", 0.0)
        # Invert: closer = higher score
        scores[p] = round(max(1.0 - (dist / max_dist), 0.0), 6)

    # Fill in files not in results with 0.0
    for f in files:
        if f not in scores:
            scores[f] = 0.0

    return scores
