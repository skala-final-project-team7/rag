"""Cross-Encoder 재순위화 노드 — candidates → top_chunks + sources [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : Query 파이프라인의 재순위화 단계 LangGraph 노드. 9-B-2가 채운 RagState.
          candidates(Top-20)에 대해 9-B-1 Reranker로 (query, passage) 관련도 점수를
          산출하고, 9-A `select_reranked` 결정론 로직으로 Top-K(5 또는 3)를 선정해
          `top_chunks`와 출처 카드(`sources`)를 채운다 (`docs/rag-pipeline-design.md`
          §6 4.5·§8, `docs/api-spec.md` Source 스키마, `app/CLAUDE.md` §8).
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature9-B-3 — cross_encoder_rerank 노드 + Source 매핑
--------------------------------------------------
[호환성]
  - Python 3.11.x
  - 외부 의존성 0 (주입된 CrossEncoderReranker 구체 구현이 외부 의존성을 갖는다)
--------------------------------------------------
"""

from app.query.rerank import select_reranked
from app.query.reranker.base import CrossEncoderReranker
from app.schemas.chunk import Chunk
from app.schemas.rag_state import RagState
from app.schemas.response import Source

# select_reranked.is_low_confidence는 RagState에 별도 필드로 두지 않는다. 응답 포맷터
# (feature11)의 ``_is_low_confidence`` 가 ``Source.score`` 기반으로 동일 판정하므로
# 이중 신호가 된다 — score만 정확히 매핑하면 포맷터가 자동으로 저신뢰 분기를 적용한다.


def cross_encoder_rerank(
    state: RagState,
    *,
    reranker: CrossEncoderReranker,
) -> RagState:
    """Cross-Encoder 재순위화 LangGraph 노드 — candidates → top_chunks + sources.

    9-B-2가 채운 ``state.candidates`` (Top-20)에 대해 ``reranker.score`` 로 (query,
    passage) 관련도 점수를 산출한 뒤, 9-A ``select_reranked`` 의 결정론 선정 로직을
    적용한다. 결과를 ``state.top_chunks`` (Chunk 목록)과 ``state.sources`` (Source
    카드 목록, ``docs/api-spec.md`` 정합)에 저장한다.

    Args:
        state: ``query`` / ``candidates`` (+선택적 ``history_decision.contextualized_question``)
            를 읽고 ``top_chunks`` / ``sources`` 를 채운다.
        reranker: Cross-Encoder 어댑터. 실 운영은 ``CrossEncoderRerankerImpl`` ,
            테스트·PoC는 ``FakeCrossEncoderReranker`` 주입.

    Returns:
        ``top_chunks`` / ``sources`` 가 채워진 RagState (in-place mutation).
    """
    candidates = state.candidates

    # --- 1. 빈 candidates short-circuit ---
    # 9-B-2가 candidates를 비웠다면(검색 0건) 재순위화 무의미. top_chunks·sources도 비움.
    if not candidates:
        state.top_chunks = []
        state.sources = []
        return state

    # --- 2. 쿼리 텍스트 결정 ---
    # 멀티턴 히스토리 관리자(feature8)가 채운 contextualized_question 이 있으면 그것을,
    # 없으면 원 query를 사용한다. Cross-Encoder는 단일 query를 받으므로 rewritten_queries
    # 같은 멀티 쿼리는 지원하지 않는다 — 라우터가 contextualized_question에 압축한다.
    query_text = _query_text(state)

    # --- 3. Reranker 호출 ---
    passages = [chunk.text for chunk in candidates]
    raw_scores = reranker.score(query_text, passages)

    # --- 4. 9-A select_reranked ---
    scored_by_chunk_id = {
        chunk.metadata.chunk_id: score
        for chunk, score in zip(candidates, raw_scores, strict=True)
    }
    rerank_result = select_reranked(scored_by_chunk_id)

    # --- 5. top_chunks + sources 매핑 ---
    chunk_by_id = {chunk.metadata.chunk_id: chunk for chunk in candidates}
    top_chunks: list[Chunk] = []
    sources: list[Source] = []
    for chunk_id, score in rerank_result.top:
        # rerank_result.top의 chunk_id는 모두 입력 candidates에서 나왔으므로 보장된다.
        chunk = chunk_by_id[chunk_id]
        top_chunks.append(chunk)
        sources.append(_chunk_to_source(chunk, raw_score=score))

    state.top_chunks = top_chunks
    state.sources = sources
    return state


def _query_text(state: RagState) -> str:
    """contextualized_question 우선, 없으면 원 query."""
    if state.history_decision and state.history_decision.contextualized_question:
        return state.history_decision.contextualized_question
    return state.query


def _chunk_to_source(chunk: Chunk, *, raw_score: float) -> Source:
    """Chunk + Cross-Encoder raw score → Source 출처 카드 (docs/api-spec.md).

    raw score는 어댑터 측에서 ``[0.0, 1.0]`` 으로 정규화된 상태(9-B-1 Sigmoid)다. Source.
    score는 ``int 0~100`` 스케일이므로 ``round(raw_score * 100)`` 로 변환한다 — 포맷터
    (feature11)의 ``LOW_CONFIDENCE_SCORE`` 임계값(20)과 정합.
    """
    metadata = chunk.metadata
    # 첨부 청크는 출처 카드 제목을 attachment_filename으로, 본문 청크는 page_title로.
    title = metadata.attachment_filename or metadata.page_title
    return Source(
        title=title,
        score=round(raw_score * 100),
        path=metadata.section_path,
        space_key=metadata.space_key,
        source_type=metadata.source_type,
        confluence_url=metadata.webui_link,
        last_modified=metadata.last_modified,
        text_preview=chunk.text,
        attachment_filename=metadata.attachment_filename,
        attachment_mime=metadata.attachment_mime,
        # download_url은 ChunkMetadata에 없다 — PageObject.Attachment 단계에서만 보존.
        # 9-B-3 단계에서는 None으로 두고, 첨부 다운로드 URL이 필요해지면 별도
        # chunk lookup 어댑터(후속)에서 채운다.
    )
