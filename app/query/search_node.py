"""Multi-Pool Hybrid Search 노드 — query 임베딩 + 3 Pool dense+sparse + RRF [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : Query 파이프라인의 검색 단계 LangGraph 노드. RagState의 query (+ 선택적
          rewritten_queries)를 받아 dense·sparse 임베딩(5-B-1) → 3 Pool ACL 필터 검색
          (5-B-2) → 9-A 결정론 로직(RRF + Pool 가중 합산 + Top-N 선정) → Chunk 재구성
          순으로 처리해 ``RagState.candidates`` Top-20을 채운다
          (`docs/rag-pipeline-design.md` §6 4.5, `app/CLAUDE.md` §3·§8, db-schema.md §1.2).
          ``@enforce_acl`` 가드(feature7)로 ACL 미주입 호출을 시스템 단에서 거부한다.
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature9-B-2 — hybrid_search 외부 노드 + 내부 ACL 가드
    + Chunk 재구성 + 기본 pool_weights fallback
  - 2026-05-18, 5-A 후속 — _chunk_from_search_hit가 payload.token_count를 그대로
    복원하도록 변경 (build_point_payload 동봉 확장과 짝). legacy 인덱스 호환 위해
    필드 없으면 0 fallback.
--------------------------------------------------
[호환성]
  - Python 3.11.x
  - 외부 의존성 0 (주입된 DenseEmbedder / SparseEmbedder / QdrantPoolStore의 구체
    구현이 외부 의존성을 갖는다)
--------------------------------------------------
"""

from datetime import datetime
from typing import Any

from app.ingestion.embedder.base import DenseEmbedder, SparseEmbedder
from app.ingestion.vector_store import POOL_NAMES
from app.query.acl import enforce_acl
from app.query.search import TOP_CANDIDATES, fuse_and_rank
from app.schemas.chunk import Chunk, ChunkMetadata
from app.schemas.enums import AttachmentType, DocType, ExtractedFormat, SourceType
from app.schemas.rag_state import RagState
from app.storage.qdrant_client import QdrantPoolStore, SearchHit

# 라우터(feature8)가 pool_weights를 채우지 않은 경우의 안전한 fallback. 등가 가중치 —
# 라우터의 intent 추정이 동작하면 즉시 덮어쓴다.
_DEFAULT_POOL_WEIGHTS: dict[str, float] = dict.fromkeys(POOL_NAMES, 1.0)


def hybrid_search(
    state: RagState,
    *,
    dense_embedder: DenseEmbedder,
    sparse_embedder: SparseEmbedder,
    store: QdrantPoolStore,
    top_k: int = TOP_CANDIDATES,
) -> RagState:
    """Multi-Pool Hybrid Search LangGraph 노드.

    ``(state) -> state`` 표준 시그니처. 외부 의존성은 키워드 인자로 주입한다 — LangGraph
    그래프 조립(feature11)에서 ``functools.partial`` 또는 클로저로 wiring한다.
    ACL 미주입 호출은 내부 ``@enforce_acl`` 가드로 ``ACLViolationError`` 발생.

    Args:
        state: ``query`` / 선택적 ``rewritten_queries`` / ``acl_filter`` /
            ``pool_weights`` / ``metadata_filters`` 를 읽고 ``candidates`` 를 채운다.
        dense_embedder: query 텍스트를 dense 벡터로 변환.
        sparse_embedder: query 텍스트를 sparse 벡터로 변환.
        store: Qdrant Multi-Pool 저장소.
        top_k: 반환할 후보 수. 기본값 ``TOP_CANDIDATES=20``.

    Returns:
        ``candidates`` 가 채워진 RagState (입력 state를 갱신해 반환).

    Raises:
        ACLViolationError: ``state.acl_filter`` 가 무효일 때.
    """
    return _hybrid_search_acl_guarded(
        state,
        acl_filter=state.acl_filter,
        dense_embedder=dense_embedder,
        sparse_embedder=sparse_embedder,
        store=store,
        top_k=top_k,
    )


@enforce_acl
def _hybrid_search_acl_guarded(
    state: RagState,
    *,
    acl_filter: dict[str, Any] | None,
    dense_embedder: DenseEmbedder,
    sparse_embedder: SparseEmbedder,
    store: QdrantPoolStore,
    top_k: int,
) -> RagState:
    """ACL 가드를 통과한 본 검색 로직 — 외부 호출은 ``hybrid_search`` 통해서만."""
    # @enforce_acl이 acl_filter 유효성을 검증했으므로 여기서는 사용 측에서 None이 아님이
    # 보장된다. mypy 안전을 위해 명시 단언.
    assert acl_filter is not None

    # --- 1. 쿼리 텍스트 결정 ---
    # 라우터가 rewritten_queries를 채웠으면 그것들로, 아니면 원 query 단일 사용.
    query_texts = list(state.rewritten_queries) if state.rewritten_queries else [state.query]

    # --- 2. query 배치 임베딩 (dense + sparse 한 번씩) ---
    dense_query_vectors = dense_embedder.encode_queries(query_texts)
    sparse_query_vectors = sparse_embedder.encode_queries(query_texts)

    # --- 3. 3 Pool × N query × {dense, sparse} 검색 ---
    pool_rankings: dict[str, dict[str, list[str]]] = {pool: {} for pool in POOL_NAMES}
    all_hits: dict[str, SearchHit] = {}
    metadata_filters = _coerce_metadata_filters(state.metadata_filters)

    for pool_name in POOL_NAMES:
        for idx, _ in enumerate(query_texts):
            dense_hits = store.search(
                pool_name,
                acl_filter=acl_filter,
                dense_vector=dense_query_vectors[idx],
                top_k=top_k,
                metadata_filters=metadata_filters,
            )
            sparse_hits = store.search(
                pool_name,
                acl_filter=acl_filter,
                sparse_vector=sparse_query_vectors[idx],
                top_k=top_k,
                metadata_filters=metadata_filters,
            )
            # 9-A `fuse_and_rank` 입력은 vector_type 키 단위로 묶인 ranking. query별로
            # 키를 분리해 RRF가 모든 ranking을 동등하게 합치도록 한다.
            pool_rankings[pool_name][f"dense_q{idx}"] = [hit.chunk_id for hit in dense_hits]
            pool_rankings[pool_name][f"sparse_q{idx}"] = [hit.chunk_id for hit in sparse_hits]
            # Chunk 재구성용 SearchHit 풀 — 같은 chunk_id는 payload가 동일하므로 덮어써도 안전.
            for hit in (*dense_hits, *sparse_hits):
                all_hits[hit.chunk_id] = hit

    # --- 4. 9-A 결정론 결합 (RRF → Pool 가중 → Top-N) ---
    pool_weights = state.pool_weights or _DEFAULT_POOL_WEIGHTS
    top_chunk_ids = fuse_and_rank(pool_rankings, pool_weights, limit=top_k)

    # --- 5. chunk_id → Chunk 재구성 (payload 기반) ---
    state.candidates = [
        _chunk_from_search_hit(all_hits[chunk_id])
        for chunk_id in top_chunk_ids
        if chunk_id in all_hits
    ]
    return state


def _coerce_metadata_filters(
    metadata_filters: dict[str, Any] | None,
) -> dict[str, str | list[str]] | None:
    """RagState.metadata_filters(dict[str, Any]) → QdrantPoolStore.search 시그니처 정합.

    QdrantPoolStore는 ``str | list[str]`` 만 받는다(MatchValue/MatchAny). 라우터가 채운
    값이 그 두 타입이 아니면 None으로 떨어뜨려 무시한다 — 잘못된 값으로 검색이 망가지는
    것보다 필터 미적용이 안전하다.

    빈 list (``[]``) / 빈 문자열 (``""``) 은 명시적으로 거른다 — Qdrant ``MatchAny
    (any=[])`` 는 어떤 값과도 매칭되지 않아 must 결합 시 모든 결과를 차단한다 (2026-
    05-20 라우터의 빈 배열 metadata_filters 가 검색 0건을 일관 유발하던 버그 수정).
    """
    if not metadata_filters:
        return None
    coerced: dict[str, str | list[str]] = {}
    for key, value in metadata_filters.items():
        if isinstance(value, str):
            if value:  # 빈 문자열 거름.
                coerced[key] = value
        elif isinstance(value, list):
            # 빈 list 거름 + 모든 원소가 str 일 때만 받음.
            if value and all(isinstance(item, str) for item in value):
                coerced[key] = value
    return coerced or None


def _chunk_from_search_hit(hit: SearchHit) -> Chunk:
    """SearchHit.payload(db-schema §1.2) → Chunk 도메인 객체 재구성.

    Cross-Encoder reranker(9-B-3) / 답변 생성기 / 응답 포맷터가 ``Chunk`` 모양을 요구하므로
    검색 단계에서 변환한다. ``text`` 는 payload의 ``text_preview`` (첫 200자) — 9-B-3
    재순위화는 text_preview로 점수 산출하며, 운영에서 풀 텍스트가 필요해지면 별도
    chunk lookup 어댑터를 추가한다. ``token_count`` 는 5-A 후속(2026-05-18)에서
    payload에 동봉했으므로 payload에서 직접 복원한다. legacy 인덱스에 필드가 없으면
    0으로 fallback (후방 호환).
    """
    payload = hit.payload
    metadata = ChunkMetadata(
        chunk_id=str(payload["chunk_id"]),
        page_id=str(payload["page_id"]),
        page_title=str(payload["page_title"]),
        section_header=str(payload["section_header"]),
        section_path=str(payload["section_path"]),
        chunk_index=int(payload["chunk_index"]),
        labels=list(payload.get("labels") or []),
        doc_type=_parse_doc_type(payload["doc_type"]),
        space_key=str(payload["space_key"]),
        allowed_groups=list(payload.get("allowed_groups") or []),
        allowed_users=list(payload.get("allowed_users") or []),
        webui_link=str(payload["webui_link"]),
        last_modified=datetime.fromisoformat(str(payload["last_modified"])),
        source_type=SourceType(payload["source_type"]),
        attachment_id=_optional_str(payload.get("attachment_id")),
        attachment_filename=_optional_str(payload.get("attachment_filename")),
        attachment_mime=_optional_str(payload.get("attachment_mime")),
        extracted_format=_parse_extracted_format(payload.get("extracted_format")),
        token_count=int(payload.get("token_count") or 0),
    )
    return Chunk(text=str(payload.get("text_preview") or ""), metadata=metadata)


def _parse_doc_type(value: object) -> DocType | AttachmentType:
    """db-schema §1.2의 doc_type 문자열을 DocType 또는 AttachmentType로 환원한다."""
    text = str(value)
    # StrEnum 값을 직접 매칭 시도 — 본문 6유형 우선, 실패하면 첨부 4유형으로 시도.
    try:
        return DocType(text)
    except ValueError:
        return AttachmentType(text)


def _parse_extracted_format(value: object) -> ExtractedFormat | None:
    if value is None or value == "":
        return None
    return ExtractedFormat(str(value))


def _optional_str(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
