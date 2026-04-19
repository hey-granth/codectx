"""Mock tests for semantic logic."""

from pathlib import Path
from unittest.mock import MagicMock

from codectx.parser.base import make_plaintext_result
from codectx.ranker import semantic


def test_semantic_score_mock(tmp_path: Path) -> None:
    # Setup mocks
    mock_lancedb = MagicMock()
    mock_db = MagicMock()
    mock_table = MagicMock()

    # search -> limit -> to_list
    mock_search = MagicMock()
    mock_search.limit.return_value.to_list.return_value = [
        {"path": str(tmp_path / "a.py"), "text": "hi", "_distance": 0.1, "vector": []}
    ]
    mock_table.search.return_value = mock_search
    mock_db.list_tables.return_value = []

    mock_db.create_table.return_value = mock_table
    mock_lancedb.connect.return_value = mock_db

    mock_model = MagicMock()
    mock_model.encode.return_value = [MagicMock(tolist=lambda: [0.1, 0.2])]
    mock_sentence_transformer = MagicMock(return_value=mock_model)

    prev_lancedb = semantic.lancedb
    prev_sentence_transformer = semantic.SentenceTransformer
    prev_has_lancedb = semantic._HAS_LANCEDB
    prev_has_st = semantic._HAS_SENTENCE_TRANSFORMERS

    semantic.lancedb = mock_lancedb
    semantic.SentenceTransformer = mock_sentence_transformer
    semantic._HAS_LANCEDB = True
    semantic._HAS_SENTENCE_TRANSFORMERS = True

    f1 = tmp_path / "a.py"
    f1.write_text("hi")

    prs = {f1: make_plaintext_result(f1, "hi")}

    try:
        res = semantic.semantic_score("query test", [f1], prs, tmp_path / "cache")
        assert f1 in res
        assert res[f1] >= 0
    finally:
        semantic.lancedb = prev_lancedb
        semantic.SentenceTransformer = prev_sentence_transformer
        semantic._HAS_LANCEDB = prev_has_lancedb
        semantic._HAS_SENTENCE_TRANSFORMERS = prev_has_st
