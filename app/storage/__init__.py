"""app.storage — 외부 저장소(Qdrant·MongoDB·MySQL) 어댑터·클라이언트 패키지 [Storage].

분리 의도 (app/CLAUDE.md §8 — 외부 호출은 어댑터/클라이언트 계층으로 분리):

- ``qdrant_client.py`` — ``QdrantPoolStore``. db-schema.md §1의 Multi-Pool Vector
  Store(title/content/label) 부트스트랩·upsert·검색·삭제. Qdrant Point ID 제약
  (UUID/uint64)을 어댑터에서 흡수해 호출자는 SHA1 hex ``chunk_id`` 만 다룬다.
- ``mongo_cache.py`` — ``EmbeddingCache`` ABC + ``MongoEmbeddingCache`` +
  ``FakeEmbeddingCache``. db-schema §2.4의 ``embedding_cache`` 컬렉션 어댑터.
  Ingestion indexer의 ``(chunk_id, version_number)`` 기반 멱등성을 강제한다.

Ingestion·Query 파이프라인은 본 패키지의 추상화만 통해 저장소에 접근하며, 모델·라이브러리
종속을 격리한다.
"""

from app.storage.mongo_cache import (
    EmbeddingCache,
    EmbeddingCacheEntry,
    FakeEmbeddingCache,
    MongoEmbeddingCache,
)
from app.storage.qdrant_client import QdrantPoolStore, SearchHit

__all__ = [
    "EmbeddingCache",
    "EmbeddingCacheEntry",
    "FakeEmbeddingCache",
    "MongoEmbeddingCache",
    "QdrantPoolStore",
    "SearchHit",
]
