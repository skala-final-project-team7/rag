"""Qdrant Multi-Pool 클라이언트 어댑터 검증 (feature5-B-2).

`:memory:` Qdrant in-process 모드로 부트스트랩·Named Vector upsert·ACL 필터 검색·
키 기반 삭제를 전부 실제로 수행한다 (외부 컨테이너 불필요). Fake 임베더로 결정론
벡터를 생성하므로 모델 다운로드도 없다.

Note: ``:memory:`` 로컬 모드에서 payload 인덱스는 UserWarning과 함께 noop이지만 필터
매칭 자체는 동작한다 — 본 테스트는 인덱스 효과가 아니라 필터 결과를 검증한다.
"""

import dataclasses
import uuid
import warnings
from datetime import datetime

import pytest

# qdrant-client는 main dependency지만 매크로 안전을 위해 명시적 importorskip.
pytest.importorskip("qdrant_client")

from app.config import Settings  # noqa: E402
from app.ingestion.embedder.base import (  # noqa: E402
    FakeDenseEmbedder,
    FakeSparseEmbedder,
    SparseVector,
)
from app.ingestion.vector_store import (  # noqa: E402
    CONTENT_POOL,
    LABEL_POOL,
    POOL_NAMES,
    TITLE_POOL,
)
from app.schemas.chunk import Chunk, ChunkMetadata  # noqa: E402
from app.schemas.enums import SourceType  # noqa: E402
from app.storage.qdrant_client import (  # noqa: E402
    QdrantPoolStore,
    SearchHit,
    _chunk_id_to_point_id,
    _pool_name_to_collection,
)

# 로컬 :memory: 모드의 payload 인덱스 noop 경고는 본 테스트에서는 무관 — 시그널 노이즈 차단.
warnings.filterwarnings("ignore", message="Payload indexes have no effect.*")


# --- 픽스처·헬퍼 ---


def _settings() -> Settings:
    """기본 컬렉션 이름을 사용하는 Settings 인스턴스 (개발자 .env로부터 격리)."""
    return Settings(_env_file=None)


def _last_modified() -> datetime:
    return datetime.fromisoformat("2026-04-22T08:15:00+09:00")


def _chunk(
    *,
    chunk_id: str,
    page_id: str = "CONF-PAGE-1",
    allowed_groups: list[str] | None = None,
    doc_type: str = "operation",
    attachment_id: str | None = None,
    chunk_index: int = 0,
    text: str = "EKS 클러스터 운영 본문",
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
        last_modified=_last_modified(),
        source_type=SourceType.PAGE if attachment_id is None else SourceType.ATTACHMENT,
        attachment_id=attachment_id,
        token_count=120,
    )
    return Chunk(text=text, metadata=metadata)


@pytest.fixture()
def store() -> QdrantPoolStore:
    s = QdrantPoolStore.in_memory(_settings(), dense_dimension=8)
    s.bootstrap_collections()
    return s


@pytest.fixture()
def dense() -> FakeDenseEmbedder:
    return FakeDenseEmbedder(dimension=8)


@pytest.fixture()
def sparse() -> FakeSparseEmbedder:
    return FakeSparseEmbedder()


def _acl_for(groups: list[str]) -> dict[str, list[dict[str, object]]]:
    """build_acl_filter 출력 형태와 정합 — 테스트가 9-B 통합 시점에 깨지지 않게."""
    return {
        "should": [
            {"key": "allowed_groups", "match": {"any": groups}},
        ]
    }


# --- _chunk_id_to_point_id ---


def test_chunk_id_to_point_id_is_deterministic() -> None:
    sha1_hex = "a" * 40
    assert _chunk_id_to_point_id(sha1_hex) == _chunk_id_to_point_id(sha1_hex)


def test_chunk_id_to_point_id_returns_valid_uuid_string() -> None:
    # Qdrant Point ID는 UUID 표준 포맷을 요구한다 — uuid.UUID로 파싱 가능해야 함.
    pid = _chunk_id_to_point_id("a" * 40)
    parsed = uuid.UUID(pid)
    assert str(parsed) == pid


def test_chunk_id_to_point_id_different_for_different_chunk_ids() -> None:
    assert _chunk_id_to_point_id("a" * 40) != _chunk_id_to_point_id("b" * 40)


# --- _pool_name_to_collection ---


def test_pool_name_to_collection_maps_known_pools() -> None:
    settings = _settings()
    assert _pool_name_to_collection(settings, TITLE_POOL) == settings.qdrant_title_pool
    assert _pool_name_to_collection(settings, CONTENT_POOL) == settings.qdrant_content_pool
    assert _pool_name_to_collection(settings, LABEL_POOL) == settings.qdrant_label_pool


def test_pool_name_to_collection_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="알 수 없는 pool"):
        _pool_name_to_collection(_settings(), "phantom_pool")


# --- SearchHit ---


def test_search_hit_is_frozen() -> None:
    hit = SearchHit(chunk_id="x", score=0.9, payload={"page_id": "P1"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.score = 0.0  # type: ignore[misc]


# --- bootstrap_collections ---


def test_bootstrap_creates_three_collections(store: QdrantPoolStore) -> None:
    settings = _settings()
    expected = {
        settings.qdrant_title_pool,
        settings.qdrant_content_pool,
        settings.qdrant_label_pool,
    }
    actual = {c.name for c in store._client.get_collections().collections}
    assert expected <= actual


def test_bootstrap_is_idempotent(store: QdrantPoolStore) -> None:
    # 한 번 더 호출해도 예외·중복 생성 없이 그대로 통과해야 함.
    store.bootstrap_collections()
    settings = _settings()
    actual = {c.name for c in store._client.get_collections().collections}
    assert settings.qdrant_title_pool in actual
    assert settings.qdrant_content_pool in actual
    assert settings.qdrant_label_pool in actual


def test_bootstrap_collection_has_named_vectors(store: QdrantPoolStore) -> None:
    settings = _settings()
    info = store._client.get_collection(settings.qdrant_title_pool)
    # Named Vector(dense)와 Sparse Vector(sparse-bm25)가 둘 다 설정됨
    assert "dense" in info.config.params.vectors  # type: ignore[operator]
    sparse_cfg = info.config.params.sparse_vectors or {}
    assert "sparse-bm25" in sparse_cfg


# --- Upsert ---


def test_upsert_then_dense_search_recovers_chunk_id(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunk = _chunk(chunk_id="a" * 40)
    [d_vec] = dense.encode_passages(["EKS 클러스터 운영 본문"])
    [s_vec] = sparse.encode_passages(["EKS 클러스터 운영 본문"])
    store.upsert_chunk(TITLE_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec)

    [q_vec] = dense.encode_passages(["EKS 클러스터 운영 본문"])  # 같은 텍스트 → 같은 벡터
    hits = store.search(TITLE_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    assert len(hits) == 1
    assert hits[0].chunk_id == "a" * 40
    # Cosine 자기-매칭은 1.0
    assert pytest.approx(hits[0].score, rel=1e-3) == 1.0
    # payload 19+1 필드가 그대로 보존됨 (chunk_id 포함)
    assert hits[0].payload["chunk_id"] == "a" * 40
    assert hits[0].payload["page_id"] == "CONF-PAGE-1"


def test_upsert_batch_then_search(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunks = [
        _chunk(chunk_id="a" * 40, chunk_index=0, text="alpha alpha"),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="beta beta"),
        _chunk(chunk_id="c" * 40, chunk_index=2, text="gamma gamma"),
    ]
    items = [
        (chunk, 1, dense.encode_passages([chunk.text])[0], sparse.encode_passages([chunk.text])[0])
        for chunk in chunks
    ]
    store.upsert_chunks_batch(CONTENT_POOL, items)

    [q_vec] = dense.encode_passages(["alpha alpha"])
    hits = store.search(CONTENT_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    assert len(hits) == 3
    # alpha 쿼리에는 alpha 청크가 1순위 (Cosine 1.0)
    assert hits[0].chunk_id == "a" * 40
    assert pytest.approx(hits[0].score, rel=1e-3) == 1.0


def test_idempotent_upsert_overwrites_without_duplicating(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunk = _chunk(chunk_id="a" * 40)
    [d_vec] = dense.encode_passages(["text"])
    [s_vec] = sparse.encode_passages(["text"])

    store.upsert_chunk(TITLE_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec)
    store.upsert_chunk(TITLE_POOL, chunk, version_number=2, dense_vector=d_vec, sparse_vector=s_vec)

    settings = _settings()
    count = store._client.count(settings.qdrant_title_pool).count
    assert count == 1  # 동일 chunk_id → 동일 Point ID(uuid5) → overwrite

    # 갱신된 version_number가 payload에 반영됨
    hits = store.search(TITLE_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=d_vec)
    assert hits[0].payload["version_number"] == 2


# --- 검색: ACL 필터 ---


def test_search_acl_filter_excludes_other_groups(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    cloud_chunk = _chunk(chunk_id="a" * 40, allowed_groups=["space:CLOUD"], text="alpha")
    ccc_chunk = _chunk(chunk_id="b" * 40, allowed_groups=["space:CCC"], text="alpha")
    items = [
        (chunk, 1, dense.encode_passages([chunk.text])[0], sparse.encode_passages([chunk.text])[0])
        for chunk in (cloud_chunk, ccc_chunk)
    ]
    store.upsert_chunks_batch(TITLE_POOL, items)

    [q_vec] = dense.encode_passages(["alpha"])
    # CLOUD만 가진 사용자
    hits = store.search(TITLE_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    chunk_ids = {hit.chunk_id for hit in hits}
    assert chunk_ids == {"a" * 40}, "CLOUD 그룹만 가진 사용자는 CCC 청크 접근 불가"


def test_search_with_unmatched_acl_returns_empty(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunk = _chunk(chunk_id="a" * 40, allowed_groups=["space:CLOUD"])
    [d_vec] = dense.encode_passages(["text"])
    [s_vec] = sparse.encode_passages(["text"])
    store.upsert_chunk(TITLE_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec)

    [q_vec] = dense.encode_passages(["text"])
    hits = store.search(TITLE_POOL, acl_filter=_acl_for(["space:NONEXIST"]), dense_vector=q_vec)
    assert hits == []


# --- 검색: dense / sparse / 분기 ---


def test_search_sparse_only_returns_hits(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunk = _chunk(chunk_id="a" * 40, text="kubernetes node")
    [d_vec] = dense.encode_passages([chunk.text])
    [s_vec] = sparse.encode_passages([chunk.text])
    store.upsert_chunk(
        CONTENT_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
    )

    [q_sparse] = sparse.encode_queries(["kubernetes"])
    hits = store.search(CONTENT_POOL, acl_filter=_acl_for(["space:CLOUD"]), sparse_vector=q_sparse)
    assert len(hits) == 1
    assert hits[0].chunk_id == "a" * 40


def test_search_empty_sparse_vector_short_circuits(store: QdrantPoolStore) -> None:
    hits = store.search(
        CONTENT_POOL,
        acl_filter=_acl_for(["space:CLOUD"]),
        sparse_vector=SparseVector(indices=(), values=()),
    )
    assert hits == []


def test_search_rejects_both_dense_and_sparse(store: QdrantPoolStore) -> None:
    with pytest.raises(ValueError, match="Hybrid"):
        store.search(
            CONTENT_POOL,
            acl_filter=_acl_for(["space:CLOUD"]),
            dense_vector=[0.0] * 8,
            sparse_vector=SparseVector(indices=(0,), values=(1.0,)),
        )


def test_search_rejects_neither_dense_nor_sparse(store: QdrantPoolStore) -> None:
    with pytest.raises(ValueError, match="dense_vector 또는 sparse_vector"):
        store.search(CONTENT_POOL, acl_filter=_acl_for(["space:CLOUD"]))


def test_search_respects_top_k(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunks = [
        _chunk(chunk_id=letter * 40, chunk_index=idx, text=f"text-{idx}")
        for idx, letter in enumerate("abcde")
    ]
    items = [
        (chunk, 1, dense.encode_passages([chunk.text])[0], sparse.encode_passages([chunk.text])[0])
        for chunk in chunks
    ]
    store.upsert_chunks_batch(LABEL_POOL, items)

    [q_vec] = dense.encode_passages(["text-0"])
    hits = store.search(
        LABEL_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec, top_k=2
    )
    assert len(hits) == 2


def test_search_metadata_filters_narrow_results(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    incident_chunk = _chunk(chunk_id="a" * 40, doc_type="incident", text="alpha", chunk_index=0)
    operation_chunk = _chunk(chunk_id="b" * 40, doc_type="operation", text="alpha", chunk_index=1)
    items = [
        (chunk, 1, dense.encode_passages([chunk.text])[0], sparse.encode_passages([chunk.text])[0])
        for chunk in (incident_chunk, operation_chunk)
    ]
    store.upsert_chunks_batch(CONTENT_POOL, items)

    [q_vec] = dense.encode_passages(["alpha"])
    # doc_type 단일 값 매칭 (MatchValue)
    hits_inc = store.search(
        CONTENT_POOL,
        acl_filter=_acl_for(["space:CLOUD"]),
        dense_vector=q_vec,
        metadata_filters={"doc_type": "incident"},
    )
    assert {hit.chunk_id for hit in hits_inc} == {"a" * 40}

    # doc_type list 매칭 (MatchAny)
    hits_both = store.search(
        CONTENT_POOL,
        acl_filter=_acl_for(["space:CLOUD"]),
        dense_vector=q_vec,
        metadata_filters={"doc_type": ["incident", "operation"]},
    )
    assert {hit.chunk_id for hit in hits_both} == {"a" * 40, "b" * 40}


# --- 삭제 ---


def test_delete_by_page_id_removes_all_chunks_of_page(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    p1_chunks = [
        _chunk(chunk_id="a" * 40, page_id="P1", chunk_index=0, text="x"),
        _chunk(chunk_id="b" * 40, page_id="P1", chunk_index=1, text="y"),
    ]
    p2_chunk = _chunk(chunk_id="c" * 40, page_id="P2", text="z")

    for chunk in [*p1_chunks, p2_chunk]:
        [d_vec] = dense.encode_passages([chunk.text])
        [s_vec] = sparse.encode_passages([chunk.text])
        store.upsert_chunk(
            CONTENT_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
        )

    store.delete_by_page_id("P1")

    [q_vec] = dense.encode_passages(["z"])
    hits = store.search(CONTENT_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    remaining = {hit.chunk_id for hit in hits}
    assert remaining == {"c" * 40}


def test_delete_by_chunk_id_removes_single_point(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunks = [
        _chunk(chunk_id="a" * 40, chunk_index=0, text="alpha"),
        _chunk(chunk_id="b" * 40, chunk_index=1, text="beta"),
    ]
    for chunk in chunks:
        [d_vec] = dense.encode_passages([chunk.text])
        [s_vec] = sparse.encode_passages([chunk.text])
        store.upsert_chunk(
            TITLE_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
        )

    store.delete_by_chunk_id("a" * 40)

    [q_vec] = dense.encode_passages(["beta"])
    hits = store.search(TITLE_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    assert {hit.chunk_id for hit in hits} == {"b" * 40}


def test_delete_by_attachment_id_removes_matching(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    body_chunk = _chunk(chunk_id="a" * 40, text="body")
    attach_chunk = _chunk(chunk_id="b" * 40, attachment_id="ATT-1", chunk_index=1, text="attached")
    for chunk in (body_chunk, attach_chunk):
        [d_vec] = dense.encode_passages([chunk.text])
        [s_vec] = sparse.encode_passages([chunk.text])
        store.upsert_chunk(
            LABEL_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
        )

    store.delete_by_attachment_id("ATT-1")

    [q_vec] = dense.encode_passages(["body"])
    hits = store.search(LABEL_POOL, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=q_vec)
    assert {hit.chunk_id for hit in hits} == {"a" * 40}


# --- 모든 Pool 의 통합 (POOL_NAMES 회귀 보호) ---


def test_all_pools_can_be_independently_used(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    chunk = _chunk(chunk_id="a" * 40)
    [d_vec] = dense.encode_passages(["text"])
    [s_vec] = sparse.encode_passages(["text"])
    for pool_name in POOL_NAMES:
        store.upsert_chunk(
            pool_name, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
        )
        hits = store.search(pool_name, acl_filter=_acl_for(["space:CLOUD"]), dense_vector=d_vec)
        assert hits and hits[0].chunk_id == "a" * 40


# --- scroll_page_ids / scroll_attachment_ids (feature6 Phase 3) ---


def _index_chunk(
    store: QdrantPoolStore,
    dense: FakeDenseEmbedder,
    sparse: FakeSparseEmbedder,
    chunk: Chunk,
) -> None:
    """CONTENT_POOL 만 적재 — scroll 메서드는 CONTENT_POOL 하나만 스캔하므로 충분."""
    [d_vec] = dense.encode_passages([chunk.text])
    [s_vec] = sparse.encode_passages([chunk.text])
    store.upsert_chunk(
        CONTENT_POOL, chunk, version_number=1, dense_vector=d_vec, sparse_vector=s_vec
    )


def test_scroll_page_ids_returns_unique_set_of_body_page_ids(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    """본문 청크의 page_id를 unique set으로 반환 — 같은 page_id 중복 청크는 1회만 등장."""
    _index_chunk(store, dense, sparse, _chunk(chunk_id="a" * 40, page_id="P1", chunk_index=0))
    _index_chunk(store, dense, sparse, _chunk(chunk_id="b" * 40, page_id="P1", chunk_index=1))
    _index_chunk(store, dense, sparse, _chunk(chunk_id="c" * 40, page_id="P2", chunk_index=0))

    assert store.scroll_page_ids() == {"P1", "P2"}


def test_scroll_page_ids_excludes_attachment_chunks(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    """첨부 청크는 source_type=attachment 라 scroll_page_ids 에 포함되지 않는다."""
    _index_chunk(store, dense, sparse, _chunk(chunk_id="a" * 40, page_id="P1"))
    _index_chunk(
        store,
        dense,
        sparse,
        _chunk(chunk_id="b" * 40, page_id="P1", attachment_id="P1-att-0", chunk_index=1),
    )

    # 첨부 청크의 page_id 도 "P1" 이지만 source_type=attachment 라 scroll_page_ids 결과에서 제외.
    # 다만 본문 청크의 P1 은 포함 — 결과 set 자체는 {"P1"} 1개.
    assert store.scroll_page_ids() == {"P1"}


def test_scroll_attachment_ids_returns_unique_set_of_attachment_ids(
    store: QdrantPoolStore, dense: FakeDenseEmbedder, sparse: FakeSparseEmbedder
) -> None:
    """첨부 청크의 attachment_id 를 unique set 으로 반환 — 본문 청크는 제외."""
    _index_chunk(store, dense, sparse, _chunk(chunk_id="a" * 40, page_id="P1"))  # 본문
    _index_chunk(
        store,
        dense,
        sparse,
        _chunk(chunk_id="b" * 40, page_id="P1", attachment_id="ATT-1", chunk_index=1),
    )
    _index_chunk(
        store,
        dense,
        sparse,
        _chunk(chunk_id="c" * 40, page_id="P2", attachment_id="ATT-2"),
    )

    assert store.scroll_attachment_ids() == {"ATT-1", "ATT-2"}


def test_scroll_methods_return_empty_set_on_empty_collection(
    store: QdrantPoolStore,
) -> None:
    """청크 0건이면 두 scroll 결과 모두 빈 set — 빈 컬렉션 회귀 보호."""
    assert store.scroll_page_ids() == set()
    assert store.scroll_attachment_ids() == set()
