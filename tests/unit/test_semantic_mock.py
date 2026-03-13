"""Mock tests for semantic logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from codectx.parser.base import make_plaintext_result
from codectx.ranker.semantic import semantic_score


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

    mock_st = MagicMock()
    mock_model = MagicMock()
    mock_model.encode.return_value = [MagicMock(tolist=lambda: [0.1, 0.2])]
    mock_st.SentenceTransformer.return_value = mock_model

    sys.modules["lancedb"] = mock_lancedb
    sys.modules["sentence_transformers"] = mock_st

    f1 = tmp_path / "a.py"
    f1.write_text("hi")

    prs = {f1: make_plaintext_result(f1, "hi")}

    try:
        res = semantic_score("query test", [f1], prs, tmp_path / "cache")
        assert f1 in res
        assert res[f1] >= 0
    finally:
        del sys.modules["lancedb"]
        del sys.modules["sentence_transformers"]
