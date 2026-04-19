"""Tests for persistent semantic embedding cache."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from codectx.ranker import semantic


@dataclass
class _FakeTable:
    rows: list[dict[str, Any]] = field(default_factory=list)
    _query: str | None = None

    def search(self, *_args: Any, **_kwargs: Any) -> _FakeTable:
        return self

    def where(self, query: str, prefilter: bool = True) -> _FakeTable:
        _ = prefilter
        self._query = query
        return self

    def limit(self, _n: int) -> _FakeTable:
        return self

    def to_list(self) -> list[dict[str, Any]]:
        if self._query and "file_path = '" in self._query:
            key = self._query.split("file_path = '", 1)[1].rstrip("'")
            return [r for r in self.rows if r.get("file_path") == key][:1]
        return list(self.rows)

    def add(self, new_rows: list[dict[str, Any]]) -> None:
        self.rows.extend(new_rows)

    def delete(self, query: str) -> None:
        key = query.split("file_path = '", 1)[1].rstrip("'")
        self.rows = [r for r in self.rows if r.get("file_path") != key]


@dataclass
class _FakeDB:
    table: _FakeTable | None = None

    def list_tables(self) -> list[str]:
        return ["codectx_embeddings"] if self.table is not None else []

    def open_table(self, _name: str) -> _FakeTable:
        assert self.table is not None
        return self.table

    def create_table(
        self, _name: str, data: list[dict[str, Any]] | None = None, **_kwargs: Any
    ) -> _FakeTable:
        self.table = _FakeTable(rows=list(data or []))
        return self.table

    def drop_table(self, _name: str) -> None:
        self.table = None


class _FakeLance:
    def __init__(self, db: _FakeDB) -> None:
        self.db = db
        self.paths: list[str] = []

    def connect(self, path: str) -> _FakeDB:
        self.paths.append(path)
        return self.db


class _FakeModel:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts: list[str], show_progress_bar: bool = False) -> list[list[float]]:
        _ = show_progress_bar
        self.calls += 1
        out: list[list[float]] = []
        for text in texts:
            base = float((sum(ord(c) for c in text) % 10) + 1)
            out.append([base, base + 1.0, base + 2.0])
        return out


@pytest.fixture
def fake_semantic(monkeypatch: pytest.MonkeyPatch) -> tuple[_FakeDB, _FakeLance, _FakeModel]:
    db = _FakeDB()
    lance = _FakeLance(db)
    model = _FakeModel()

    monkeypatch.setattr(semantic, "_HAS_LANCEDB", True)
    monkeypatch.setattr(semantic, "_HAS_SENTENCE_TRANSFORMERS", True)
    monkeypatch.setattr(semantic, "lancedb", lance)
    monkeypatch.setattr(semantic, "SentenceTransformer", lambda _name: model)

    return db, lance, model


def test_cache_miss_embeds(fake_semantic: tuple[_FakeDB, _FakeLance, _FakeModel]) -> None:
    _db, _lance, model = fake_semantic
    res = semantic.embed_with_cache({"a.py": "print('a')"})
    assert "a.py" in res
    assert model.calls >= 2  # probe + embed


def test_cache_hit_skips_embed(fake_semantic: tuple[_FakeDB, _FakeLance, _FakeModel]) -> None:
    _db, _lance, model = fake_semantic
    semantic.embed_with_cache({"a.py": "print('a')"})
    before = model.calls
    semantic.embed_with_cache({"a.py": "print('a')"})
    # only probe call should happen in second run, not per-file re-embed
    assert model.calls == before + 1


def test_cache_invalidated_on_content_change(
    fake_semantic: tuple[_FakeDB, _FakeLance, _FakeModel],
) -> None:
    _db, _lance, model = fake_semantic
    semantic.embed_with_cache({"a.py": "print('a')"})
    before = model.calls
    semantic.embed_with_cache({"a.py": "print('changed')"})
    assert model.calls >= before + 2


def test_schema_mismatch_recreates_table(
    fake_semantic: tuple[_FakeDB, _FakeLance, _FakeModel],
) -> None:
    db, _lance, _model = fake_semantic
    db.create_table(
        "codectx_embeddings",
        data=[{"file_path": "a.py", "file_hash": "x", "embedding": [1.0, 2.0]}],
    )
    res = semantic.embed_with_cache({"a.py": "print('a')"})
    assert "a.py" in res
    assert len(res["a.py"]) == 3


def test_cache_respects_xdg_cache_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_semantic: tuple[_FakeDB, _FakeLance, _FakeModel],
) -> None:
    _db, lance, _model = fake_semantic
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    semantic.embed_with_cache({"a.py": "print('a')"})
    assert lance.paths
    assert str(tmp_path / "codectx") in lance.paths[0]
