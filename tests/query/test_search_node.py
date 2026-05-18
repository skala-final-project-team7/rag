"""Hybrid Search 노드 검증 (feature9-B-2).

`:memory:` Qdrant + FakeDenseEmbedder + FakeSparseEmbedder 조합으로 hybrid_search 노드의
끝-끝 흐름을 통합 검증한다. ACL 강제 / multi-query / pool_weights 분기 /
metadata_filters / Chunk 재구성 / 0건 처리까지 모두 외부 컨테이너·모델 없이 검증.
"""

import warnings
from datetime import datetime

import pytest

from app.config import Settings
from app.ingestion.embedder.base import FakeDenseEmbedder, FakeSparseEmbedder
from app.ingestion.indexer import index_chunks
from app.query.acl import ACLViolationError
from app.query.search_node import hybrid_search
from app.schemas.chunk import Chunk, ChunkMetadata
from app.schemas.enums import SourceType
from app.schemas.rag_state import RagState
from app.storage.mongo_cache import FakeEmbeddingCache
from app.storage.qdrant_client import QdrantPoolStore

# 로컬 :memory: payload 인덱스 noop 경고 차단.
warnings.filterwarnings("ignore", message="Payload indexes have no effect.*")


# --- 픽스처·헬퍼 ---


def _settings() -> Settings:
    return Settings(_env_file=None)


def _chunk(
    *,
    chunk_id: str,
    page_id: str = "P1",
    chunk_index: int = 0,
    text: str = "alpha",
    allowed_groups: list[str] | None = None,
    doc_type: str = "operation",
) -> Chunk:
    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        page_id=page_id,
        page_title="EKS 운영 가이드",
        section_header="개요",
        section_path="Cloud 운영 문서 > 개요",
        chunk_index=chunk_index,
        labels=["eks", "운영"],
        doc_type=doc_type,
        space_key="CLOUD",
        allowed_groups=allowed_groups or ["space:CLOUD"],
        allowed_users=[],
        webui_link="/display/CLOUD/eks",
        last_modified=datetime.fromisoformat("2026-04-22T08:15:00+09:00"),
        source_type=SourceType.PAGE,
        token_count=120,
    )
    return Chunk(text=text, metadata=metadata)


def _acl_for_cloud() -> dict[str, list[dict[str, object]]]:
    return {"should": [{"key": "allowed_groups", "match": {"any": ["space:CLOUD"]}}]}


@pytest.fixture()
def dense() -> FakeDenseEmbedder:
    return FakeDenseEmbedder(dimension=8)


@pytest.fixture()
def sparse() -> FakeSparseEmbedder:
    return FakeSparseEmbedder()


@pytest.fixture()
def store(dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder) -> QdrantPoolStore:
    """3 청크가 미리 인덱싱된 :memory: 저장소."""
    s = QdrantPoolStore.in_memory(_settings(), dense_dimension=8)
    s.bootstrap_collections()
    chunks = [
        _chunk(chunk_id="a" * 40, chunk_index=0, text="alpha"),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="beta"),
        _chunk(chunk_id="c" * 40, chunk_index=2, text="gamma"),
    ]
    index_chunks(
        chunks,
        version_by_page_id={"P1": 1},
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=s,
        cache=FakeEmbeddingCache(),
    )
    return s


def _make_state(
    *,
    query: str = "alpha",
    acl_filter: dict[str, list[dict[str, object]]] | None = None,
    rewritten_queries: list[str] | None = None,
    pool_weights: dict[str, float] | None = None,
    metadata_filters: dict[str, object] | None = None,
) -> RagState:
    return RagState(
        query=query,
        user_id="user-test",
        acl_filter=acl_filter if acl_filter is not None else _acl_for_cloud(),
        rewritten_queries=rewritten_queries or [],
        pool_weights=pool_weights,
        metadata_filters=metadata_filters,
    )


# --- 단일 query 정상 동작 ---


def test_hybrid_search_populates_candidates(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    state = _make_state(query="alpha")
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)

    assert result is state  # in-place mutation
    assert len(result.candidates) > 0
    candidate_ids = {chunk.metadata.chunk_id for chunk in result.candidates}
    # 모든 후보가 인덱스된 3개 청크 중 하나여야 함
    assert candidate_ids <= {"a" * 40, "b" * 40, "c" * 40}


def test_hybrid_search_returns_chunks_with_reconstructed_metadata(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    state = _make_state(query="alpha")
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)

    candidate = result.candidates[0]
    # payload → ChunkMetadata 재구성이 정상적으로 동작
    assert candidate.metadata.page_id == "P1"
    assert candidate.metadata.page_title == "EKS 운영 가이드"
    assert candidate.metadata.section_header == "개요"
    assert candidate.metadata.space_key == "CLOUD"
    assert candidate.metadata.source_type is SourceType.PAGE
    assert candidate.metadata.doc_type.value == "operation"
    # text는 payload의 text_preview (5-A: 첫 200자)
    assert candidate.text in {"alpha", "beta", "gamma"}
    # token_count는 9-B-2에서 0 default (별도 follow-up으로 payload에 추가 예정)
    assert candidate.metadata.token_count == 0


def test_hybrid_search_top_k_limit(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    state = _make_state(query="alpha")
    result = hybrid_search(
        state, dense_embedder=dense, sparse_embedder=sparse, store=store, top_k=2
    )
    assert len(result.candidates) <= 2


# --- ACL ---


def test_hybrid_search_rejects_when_acl_filter_is_none(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    state = _make_state(query="alpha", acl_filter=None)
    with pytest.raises(ACLViolationError):
        hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)


def test_hybrid_search_rejects_when_acl_filter_is_empty(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    # _is_valid_acl_filter는 should 절 구조까지 검사 — 빈 dict는 무효
    state = _make_state(query="alpha", acl_filter={})
    with pytest.raises(ACLViolationError):
        hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)


def test_hybrid_search_filters_out_other_groups(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    # CCC 그룹 청크와 CLOUD 그룹 청크 혼합
    s = QdrantPoolStore.in_memory(_settings(), dense_dimension=8)
    s.bootstrap_collections()
    chunks = [
        _chunk(chunk_id="a" * 40, text="alpha", allowed_groups=["space:CLOUD"]),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="alpha", allowed_groups=["space:CCC"]),
    ]
    index_chunks(
        chunks,
        version_by_page_id={"P1": 1},
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=s,
        cache=FakeEmbeddingCache(),
    )

    state = _make_state(query="alpha", acl_filter=_acl_for_cloud())
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=s)
    assert {c.metadata.chunk_id for c in result.candidates} == {"a" * 40}


# --- 빈 결과 ---


def test_hybrid_search_returns_empty_candidates_when_acl_matches_nothing(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    nonexistent_acl: dict[str, list[dict[str, object]]] = {
        "should": [{"key": "allowed_groups", "match": {"any": ["space:NONEXIST"]}}]
    }
    state = _make_state(query="alpha", acl_filter=nonexistent_acl)
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)
    assert result.candidates == []


# --- multi-query (rewritten_queries) ---


def test_hybrid_search_uses_rewritten_queries_when_present(
    sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    """rewritten_queries가 있으면 모든 query에 대해 임베딩·검색이 일어난다."""

    class _Spy(FakeDenseEmbedder):
        def __init__(self) -> None:
            super().__init__(dimension=8)
            self.encoded_batches: list[list[str]] = []

        def encode_queries(self, texts: list[str]) -> list[list[float]]:
            self.encoded_batches.append(list(texts))
            return super().encode_queries(texts)

    dense_spy = _Spy()
    state = _make_state(query="alpha", rewritten_queries=["alpha 확장", "alpha 원본"])
    hybrid_search(state, dense_embedder=dense_spy, sparse_embedder=sparse, store=store)
    # rewritten_queries 둘 다 한 번에 배치 임베딩됨
    assert dense_spy.encoded_batches == [["alpha 확장", "alpha 원본"]]


def test_hybrid_search_falls_back_to_query_when_no_rewritten(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    class _Spy(FakeDenseEmbedder):
        def __init__(self) -> None:
            super().__init__(dimension=8)
            self.encoded_batches: list[list[str]] = []

        def encode_queries(self, texts: list[str]) -> list[list[float]]:
            self.encoded_batches.append(list(texts))
            return super().encode_queries(texts)

    dense_spy = _Spy()
    state = _make_state(query="alpha", rewritten_queries=[])
    hybrid_search(state, dense_embedder=dense_spy, sparse_embedder=sparse, store=store)
    assert dense_spy.encoded_batches == [["alpha"]]


# --- pool_weights / metadata_filters ---


def test_hybrid_search_uses_default_pool_weights_when_none(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    """라우터가 pool_weights를 안 채워도 등가 fallback으로 동작한다."""
    state = _make_state(query="alpha", pool_weights=None)
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)
    # candidates가 정상적으로 채워진다 (가중치 fallback이 작동했다는 증거)
    assert len(result.candidates) > 0


def test_hybrid_search_uses_provided_pool_weights(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    state = _make_state(
        query="alpha",
        pool_weights={"title_pool": 1.0, "content_pool": 5.0, "label_pool": 0.5},
    )
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)
    assert len(result.candidates) > 0


def test_hybrid_search_passes_metadata_filters_to_store(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    """metadata_filters가 store.search에 정확히 전달되는지 — doc_type으로 좁힘."""
    s = QdrantPoolStore.in_memory(_settings(), dense_dimension=8)
    s.bootstrap_collections()
    chunks = [
        _chunk(chunk_id="a" * 40, text="alpha", doc_type="incident"),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="alpha", doc_type="operation"),
    ]
    index_chunks(
        chunks,
        version_by_page_id={"P1": 1},
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=s,
        cache=FakeEmbeddingCache(),
    )

    state = _make_state(query="alpha", metadata_filters={"doc_type": "incident"})
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=s)
    assert {c.metadata.chunk_id for c in result.candidates} == {"a" * 40}


def test_hybrid_search_drops_invalid_metadata_filter_types(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder, store: QdrantPoolStore
) -> None:
    """비-str/list 타입의 metadata filter는 무시 — 강건 fallback."""
    state = _make_state(query="alpha", metadata_filters={"version_number": 42})
    # 잘못된 필터로 검색이 깨지지 않고 정상 결과 반환 (필터 미적용)
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=store)
    assert len(result.candidates) > 0


def test_hybrid_search_accepts_list_metadata_filter(
    dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    s = QdrantPoolStore.in_memory(_settings(), dense_dimension=8)
    s.bootstrap_collections()
    chunks = [
        _chunk(chunk_id="a" * 40, text="alpha", doc_type="incident"),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="alpha", doc_type="operation"),
        _chunk(chunk_id="c" * 40, chunk_index=2, text="alpha", doc_type="faq"),
    ]
    index_chunks(
        chunks,
        version_by_page_id={"P1": 1},
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=s,
        cache=FakeEmbeddingCache(),
    )

    state = _make_state(query="alpha", metadata_filters={"doc_type": ["incident", "operation"]})
    result = hybrid_search(state, dense_embedder=dense, sparse_embedder=sparse, store=s)
    assert {c.metadata.chunk_id for c in result.candidates} == {"a" * 40, "b" * 40}
