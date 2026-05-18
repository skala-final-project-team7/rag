"""Chunk Text Lookup 어댑터 검증 — ChunkTextLookup ABC + Fake + Mongo.

ABC 계약 + Fake in-memory 동작 + Mongo find_one/find 응답 변환을 검증한다.
실 MongoDB 없이 pymongo collection을 mock으로 대체해 외부 의존성 0.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.storage.chunk_lookup import (
    ChunkLookupRecord,
    ChunkTextLookup,
    FakeChunkTextLookup,
    MongoChunkTextLookup,
)


def _record(chunk_id: str = "a" * 40, *, download_url: str | None = None) -> ChunkLookupRecord:
    return ChunkLookupRecord(
        chunk_id=chunk_id,
        text=f"풀 텍스트 {chunk_id[:4]}",
        download_url=download_url,
    )


# --- ABC / Fake 동작 ---


def test_fake_lookup_fetch_returns_record() -> None:
    lookup = FakeChunkTextLookup({"a" * 40: _record("a" * 40)})
    record = lookup.fetch("a" * 40)
    assert record is not None
    assert record.chunk_id == "a" * 40
    assert record.text.startswith("풀 텍스트")


def test_fake_lookup_fetch_missing_returns_none() -> None:
    lookup = FakeChunkTextLookup()
    assert lookup.fetch("missing") is None


def test_fake_lookup_fetch_many_filters_missing() -> None:
    lookup = FakeChunkTextLookup({"a" * 40: _record("a" * 40), "b" * 40: _record("b" * 40)})
    result = lookup.fetch_many(["a" * 40, "b" * 40, "missing"])
    assert set(result.keys()) == {"a" * 40, "b" * 40}
    assert all(isinstance(r, ChunkLookupRecord) for r in result.values())


def test_fake_lookup_add_overwrites_existing() -> None:
    lookup = FakeChunkTextLookup()
    lookup.add(_record("a" * 40, download_url="http://example/old"))
    lookup.add(_record("a" * 40, download_url="http://example/new"))
    record = lookup.fetch("a" * 40)
    assert record is not None
    assert record.download_url == "http://example/new"


def test_fake_lookup_implements_abc() -> None:
    # 본 ABC 계약 자체에 대한 회귀 보호 — 향후 abstractmethod 추가 시 즉시 실패.
    assert issubclass(FakeChunkTextLookup, ChunkTextLookup)
    assert issubclass(MongoChunkTextLookup, ChunkTextLookup)


# --- Mongo 어댑터 (외부 mock) ---


class _FakeCollection:
    """pymongo collection 최소 mock — find_one + find."""

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    def find_one(
        self, query: dict[str, Any], projection: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        target = query.get("chunk_id")
        for doc in self._docs:
            if doc["chunk_id"] == target:
                return dict(doc)
        return None

    def find(
        self, query: dict[str, Any], projection: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        wanted = set(query["chunk_id"]["$in"])
        return [dict(doc) for doc in self._docs if doc["chunk_id"] in wanted]


class _FakeDB:
    def __init__(self, collection: _FakeCollection) -> None:
        self._collection = collection

    def __getitem__(self, collection_name: str) -> _FakeCollection:
        return self._collection


class _DictStyleClient:
    """`client[db_name][collection_name]` 두 단계 인덱싱 지원."""

    def __init__(self, collection: _FakeCollection) -> None:
        self._db = _FakeDB(collection)

    def __getitem__(self, db_name: str) -> _FakeDB:
        return self._db


@pytest.fixture()
def mongo_lookup() -> MongoChunkTextLookup:
    docs = [
        {
            "chunk_id": "a" * 40,
            "text": "본문 풀 텍스트",
            "download_url": None,
        },
        {
            "chunk_id": "b" * 40,
            "text": "첨부 풀 텍스트",
            "download_url": "https://confluence/download/att-1",
        },
        {
            "chunk_id": "c" * 40,
            "text": "",
            # download_url 필드 누락 — 후방 호환 검증용
        },
    ]
    client = _DictStyleClient(_FakeCollection(docs))
    return MongoChunkTextLookup(client=client, db_name="lina_rag")


def test_mongo_lookup_fetch_attachment_record(mongo_lookup: MongoChunkTextLookup) -> None:
    record = mongo_lookup.fetch("b" * 40)
    assert record is not None
    assert record.text == "첨부 풀 텍스트"
    assert record.download_url == "https://confluence/download/att-1"


def test_mongo_lookup_fetch_page_record_has_no_download_url(
    mongo_lookup: MongoChunkTextLookup,
) -> None:
    record = mongo_lookup.fetch("a" * 40)
    assert record is not None
    assert record.text == "본문 풀 텍스트"
    assert record.download_url is None


def test_mongo_lookup_fetch_missing_returns_none(mongo_lookup: MongoChunkTextLookup) -> None:
    assert mongo_lookup.fetch("z" * 40) is None


def test_mongo_lookup_fetch_handles_missing_download_url_field(
    mongo_lookup: MongoChunkTextLookup,
) -> None:
    # download_url 필드 자체가 누락된 legacy 문서도 정상 처리 (None으로 떨어짐)
    record = mongo_lookup.fetch("c" * 40)
    assert record is not None
    assert record.download_url is None
    assert record.text == ""


def test_mongo_lookup_fetch_many_batches(mongo_lookup: MongoChunkTextLookup) -> None:
    result = mongo_lookup.fetch_many(["a" * 40, "b" * 40, "z" * 40])
    assert set(result.keys()) == {"a" * 40, "b" * 40}
    assert result["b" * 40].download_url == "https://confluence/download/att-1"


def test_mongo_lookup_fetch_many_empty_input(mongo_lookup: MongoChunkTextLookup) -> None:
    # 빈 입력에서는 Mongo 호출 자체를 회피한다 (find({}, ...)는 모든 문서를 반환할 위험).
    assert mongo_lookup.fetch_many([]) == {}
